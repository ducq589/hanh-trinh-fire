"""Nguồn giá tự động (adapter).

Mỗi tài sản có trường `price_source` dạng  "<nguồn>[:<tham số>...]":

  fmarket            NAV quỹ mở theo mã quỹ (= Mã tài sản)          VD: fmarket  hoặc  fmarket:DCDS
  vndirect           Giá đóng cửa cổ phiếu/ETF (nghìn đồng × 1000)  VD: vndirect  hoặc  vndirect:FPT
  vndirect_index     Chỉ số (điểm, không nhân)                       VD: vndirect_index:VNINDEX
  pnj:<SP>:<mua|ban> Giá vàng PNJ / chỉ (nghìn đồng × 1000)         VD: pnj:SJC:mua   pnj:N24K:mua
  (để trống)         Nhập tay

Lưu ý: đây là các endpoint công khai mà chính website của nhà cung cấp sử dụng, KHÔNG phải API
có hợp đồng/tài liệu. Chỉ dùng cho mục đích cá nhân, tần suất thấp (tối đa vài lần/ngày), có thể
ngừng hoạt động bất cứ lúc nào – khi đó app vẫn cho nhập giá tay như cũ.
Nguồn chặn truy cập tự động (SJC, TCBS…) KHÔNG được dùng.
"""
from __future__ import annotations

import datetime as dt
import time
from dataclasses import dataclass

import requests

UA = "HanhTrinhFIRE/1.0 (personal portfolio tracker; low-frequency)"
TIMEOUT = 20


@dataclass(frozen=True)
class Quote:
    date: dt.date
    code: str      # Mã tài sản trong app
    price: float   # VND
    source: str


class SourceError(Exception):
    pass


def _session() -> requests.Session:
    s = requests.Session()
    s.headers.update({"User-Agent": UA, "Accept": "application/json"})
    return s


def parse_spec(spec: str | None, code: str) -> tuple[str, list[str]] | None:
    if not spec or not str(spec).strip():
        return None
    parts = [p.strip() for p in str(spec).split(":")]
    name, args = parts[0].lower(), parts[1:]
    if name in ("fmarket", "vndirect", "vndirect_index") and not args:
        args = [code]
    return name, args


# ---------------------------------------------------------------- Fmarket (NAV quỹ mở)
_FM_BASE = "https://api.fmarket.vn/res"
_fm_ids: dict[str, int] = {}


def _fmarket_ids(sess) -> dict[str, int]:
    if _fm_ids:
        return _fm_ids
    body = {"types": ["NEW_FUND", "TRADING_FUND"], "issuerIds": [], "sortOrder": "DESC", "sortField": "navTo6Months",
            "page": 1, "pageSize": 500, "isIpo": False, "fundAssetTypes": [], "bondRemainPeriods": [],
            "searchField": "", "isBuyByReward": False, "thirdAppIds": []}
    r = sess.post(f"{_FM_BASE}/products/filter", json=body, timeout=TIMEOUT)
    r.raise_for_status()
    for p in r.json().get("data", {}).get("rows", []):
        if p.get("shortName"):
            _fm_ids[p["shortName"].upper()] = p["id"]
    return _fm_ids


def fmarket(sess, code: str, symbol: str, since: dt.date, today: dt.date) -> list[Quote]:
    pid = _fmarket_ids(sess).get(symbol.upper())
    if pid is None:
        raise SourceError(f"Fmarket không có quỹ {symbol}")
    body = {"isAllData": 0, "productId": pid, "fromDate": since.strftime("%Y%m%d"), "toDate": today.strftime("%Y%m%d")}
    r = sess.post(f"{_FM_BASE}/product/get-nav-history", json=body, timeout=TIMEOUT)
    r.raise_for_status()
    out = []
    for row in r.json().get("data") or []:
        if row.get("nav") and row.get("navDate"):
            out.append(Quote(dt.date.fromisoformat(row["navDate"][:10]), code, float(row["nav"]), "Fmarket (NAV)"))
    return out


# ---------------------------------------------------------------- VNDirect (cổ phiếu, chỉ số)
def _vnd(sess, symbol: str, since: dt.date, today: dt.date) -> list[tuple[dt.date, float]]:
    t0 = int(time.mktime(since.timetuple()))
    t1 = int(time.mktime((today + dt.timedelta(days=1)).timetuple()))
    r = sess.get("https://dchart-api.vndirect.com.vn/dchart/history",
                 params={"resolution": "D", "symbol": symbol.upper(), "from": t0, "to": t1},
                 headers={"Accept": "*/*"}, timeout=TIMEOUT)
    r.raise_for_status()
    j = r.json()
    if j.get("s") not in (None, "ok") or not j.get("t"):
        raise SourceError(f"VNDirect không có dữ liệu cho {symbol}")
    tz = dt.timezone(dt.timedelta(hours=7))
    return [(dt.datetime.fromtimestamp(t, tz).date(), float(c)) for t, c in zip(j["t"], j["c"])]


def vndirect(sess, code, symbol, since, today):
    return [Quote(d, code, round(c * 1000, 2), "VNDirect (đóng cửa)") for d, c in _vnd(sess, symbol, since, today)]


def vndirect_index(sess, code, symbol, since, today):
    return [Quote(d, code, c, "VNDirect (chỉ số)") for d, c in _vnd(sess, symbol, since, today)]


# ---------------------------------------------------------------- PNJ (vàng)
def pnj(sess, code: str, product: str, side: str, today: dt.date) -> list[Quote]:
    r = sess.get("https://edge-api.pnj.io/ecom-frontend/v1/get-gold-price", params={"zone": "00"}, timeout=TIMEOUT)
    r.raise_for_status()
    key = "giamua" if side.lower().startswith("mua") else "giaban"
    for p in r.json().get("data") or []:
        if str(p.get("masp", "")).upper() == product.upper() and p.get(key):
            label = "mua vào" if key == "giamua" else "bán ra"
            return [Quote(today, code, float(p[key]) * 1000, f"PNJ {p.get('tensp', product)} ({label})")]
    raise SourceError(f"PNJ không có sản phẩm {product}")


PNJ_PRODUCTS_HINT = "SJC (vàng miếng SJC), N24K (nhẫn trơn 999.9), KB (Kim Bảo), TL (Phúc Lộc Tài)"


# ---------------------------------------------------------------- orchestrator
def fetch(assets: list[dict], last_dates: dict[str, dt.date], today: dt.date | None = None,
          max_backfill_days: int = 30) -> tuple[list[Quote], list[str]]:
    """Lấy giá cho mọi tài sản có price_source. Mỗi nguồn lỗi chỉ ghi log, không làm hỏng nguồn khác.

    last_dates: ngày có giá gần nhất của từng mã → chỉ lấy phần còn thiếu (tối đa max_backfill_days ngày).
    """
    today = today or dt.date.today()
    sess = _session()
    quotes, log = [], []
    for a in assets:
        spec = parse_spec(a.get("price_source"), a["code"])
        if not spec:
            continue
        name, args = spec
        last = last_dates.get(a["code"])
        since = max(last or today - dt.timedelta(days=max_backfill_days), today - dt.timedelta(days=max_backfill_days))
        try:
            if name == "fmarket":
                got = fmarket(sess, a["code"], args[0], since, today)
            elif name == "vndirect":
                got = vndirect(sess, a["code"], args[0], since, today)
            elif name == "vndirect_index":
                got = vndirect_index(sess, a["code"], args[0], since, today)
            elif name == "pnj":
                if len(args) < 2:
                    raise SourceError("cú pháp pnj:<SẢN PHẨM>:<mua|ban>")
                got = pnj(sess, a["code"], args[0], args[1], today)
            else:
                raise SourceError(f"nguồn không hỗ trợ: {name}")
            new = [q for q in got if last is None or q.date >= last]
            quotes.extend(new)
            latest = max(got, key=lambda q: q.date) if got else None
            log.append(f"✓ {a['code']}: {len(new)} giá" + (f", mới nhất {latest.date:%d/%m/%Y} = {latest.price:,.2f}" if latest else ""))
        except (requests.RequestException, SourceError, ValueError, KeyError) as exc:
            log.append(f"✗ {a['code']} ({name}): {exc}")
    return quotes, log

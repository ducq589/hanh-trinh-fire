"""Danh mục tài sản có sẵn nguồn giá tự động: chứng chỉ quỹ (Fmarket), cổ phiếu/ETF (VNDirect), vàng (PNJ).

Người dùng mới chọn tài sản từ danh mục → app tự điền Loại, Tầng, Lợi suất kỳ vọng, Nguồn giá,
sau đó lấy giá ngay. Không cần file Excel.
"""
from __future__ import annotations

import datetime as dt
import re

from . import db, sources

# Sản phẩm vàng PNJ phổ biến: mã PNJ → tên hiển thị
GOLD_PRODUCTS = {
    "SJC": "Vàng miếng SJC 999.9",
    "N24K": "Nhẫn trơn PNJ 999.9",
    "KB": "Vàng Kim Bảo 999.9",
    "TL": "Vàng Phúc Lộc Tài 999.9",
    "PNJ": "Vàng PNJ – Phượng Hoàng",
    "24K": "Vàng nữ trang 999.9",
}

# Giả định dài hạn mặc định theo loại (người dùng sửa được trong bảng)
_DEFAULTS = {
    "Quỹ mở cổ phiếu": dict(tier="Tăng trưởng", fire_include=1, exp_return=0.12, unit="CCQ"),
    "Quỹ mở trái phiếu": dict(tier="Thu nhập", fire_include=1, exp_return=0.07, unit="CCQ"),
    "Cổ phiếu": dict(tier="Tăng trưởng", fire_include=1, exp_return=0.12, unit="CP"),
    "ETF": dict(tier="Tăng trưởng", fire_include=1, exp_return=0.11, unit="CCQ"),
    "Vàng": dict(tier="Phòng thủ", fire_include=0, exp_return=0.05, unit="chỉ"),
}

_CODE_RE = re.compile(r"^[A-Z0-9][A-Z0-9_.-]{0,11}$")


def fund_type(asset_type_name: str | None) -> str:
    """Nhóm quỹ trên Fmarket → Loại tài sản trong app."""
    n = (asset_type_name or "").lower()
    return "Quỹ mở trái phiếu" if any(k in n for k in ("trái phiếu", "mmf", "tiền tệ")) else "Quỹ mở cổ phiếu"


def list_funds() -> list[dict]:
    """Toàn bộ quỹ mở đang giao dịch trên Fmarket: code, name, group, nav."""
    sess = sources._session()
    body = {"types": ["NEW_FUND", "TRADING_FUND"], "issuerIds": [], "sortOrder": "ASC", "sortField": "name",
            "page": 1, "pageSize": 500, "isIpo": False, "fundAssetTypes": [], "bondRemainPeriods": [],
            "searchField": "", "isBuyByReward": False, "thirdAppIds": []}
    r = sess.post(f"{sources._FM_BASE}/products/filter", json=body, timeout=sources.TIMEOUT)
    r.raise_for_status()
    out = []
    for p in r.json().get("data", {}).get("rows", []):
        if not p.get("shortName"):
            continue
        group = (p.get("dataFundAssetType") or {}).get("name") or ""
        out.append({"code": p["shortName"].upper(), "name": " ".join(str(p.get("name", "")).split()),
                    "group": group, "nav": p.get("nav")})
    return sorted(out, key=lambda f: f["code"])


def stock_quote(symbol: str) -> tuple[dt.date, float] | None:
    """Giá đóng cửa gần nhất của mã cổ phiếu/ETF (VND) – dùng để kiểm tra mã có tồn tại."""
    today = dt.date.today()
    try:
        rows = sources._vnd(sources._session(), symbol, today - dt.timedelta(days=14), today)
    except (sources.SourceError, Exception):  # noqa: BLE001 – mạng lỗi/mã sai đều coi là không tra được
        return None
    if not rows:
        return None
    d, c = rows[-1]
    return d, round(c * 1000, 2)


def build(kind: str, code: str, name: str, *, asset_type: str | None = None, gold_product: str | None = None) -> dict:
    """Tạo dòng tài sản đầy đủ cho một lựa chọn trong danh mục.

    kind: "fund" | "stock" | "gold"
    """
    code = (code or "").strip().upper()
    if not _CODE_RE.match(code):
        raise ValueError("Mã chỉ gồm chữ/số, tối đa 12 ký tự, không dấu cách")
    if kind == "fund":
        typ = asset_type or "Quỹ mở cổ phiếu"
        src = "fmarket"
    elif kind == "stock":
        typ = asset_type if asset_type in ("Cổ phiếu", "ETF") else "Cổ phiếu"
        src = "vndirect"
    elif kind == "gold":
        if gold_product not in GOLD_PRODUCTS:
            raise ValueError("Chọn loại vàng")
        typ, src = "Vàng", f"pnj:{gold_product}:mua"
    else:
        raise ValueError(kind)
    return {"code": code, "name": (name or code).strip(), "type": typ, "valuation": "Thị trường",
            "price_source": src, "target_weight": None, "note": None, **_DEFAULTS[typ]}


def add(store: db.Store, asset: dict) -> None:
    """Thêm tài sản (báo lỗi nếu trùng mã)."""
    if store.one("SELECT COUNT(*) AS n FROM assets WHERE code = ?", (asset["code"],)):
        raise ValueError(f"Mã {asset['code']} đã có trong danh mục")
    order = int(store.one("SELECT COALESCE(MAX(sort_order), -1) AS m FROM assets")) + 1
    with store.tx():
        store.x("INSERT INTO assets(code,name,type,tier,fire_include,exp_return,target_weight,valuation,"
                "price_source,unit,note,sort_order) VALUES (?,?,?,?,?,?,?,?,?,?,?,?)",
                (asset["code"], asset["name"], asset["type"], asset["tier"], asset["fire_include"],
                 asset["exp_return"], asset["target_weight"], asset["valuation"], asset["price_source"],
                 asset["unit"], asset["note"], order))


def _is_etf(code: str) -> bool:
    return code.startswith(("E1", "FUE")) or "ETF" in code


def detect(code: str, funds: list[dict] | None, quote=None) -> dict:
    """Tự nhận diện mã: quỹ mở (Fmarket) → cổ phiếu/ETF (VNDirect). Không tìm thấy → ValueError.

    funds: danh sách từ list_funds() (None nếu không tải được); quote: hàm tra giá cổ phiếu (mặc định stock_quote).
    """
    code = (code or "").strip().upper()
    if not _CODE_RE.match(code):
        raise ValueError("Mã chỉ gồm chữ/số, tối đa 12 ký tự, không dấu cách")
    fund = next((f for f in funds or [] if f["code"] == code), None)
    if fund:
        typ = fund_type(fund["group"])
        return build("fund", code, f"{typ} {code}", asset_type=typ)
    if (quote or stock_quote)(code):
        typ = "ETF" if _is_etf(code) else "Cổ phiếu"
        return build("stock", code, f"{typ} {code}", asset_type=typ)
    raise ValueError(f"Không tìm thấy mã {code} trên Fmarket (quỹ mở) hay VNDirect (cổ phiếu/ETF)")


def removable(store: db.Store, code: str) -> bool:
    """Bỏ được khi chưa có lệnh Mua/Bán/Cổ tức và chưa có sổ tiết kiệm (chỉ có số dư đầu kỳ hoặc trống)."""
    orders = store.one("SELECT COUNT(*) AS n FROM transactions WHERE code = ? AND type <> ?", (code, db.OPENING))
    books = store.one("SELECT COUNT(*) AS n FROM savings WHERE code = ?", (code,))
    return not orders and not books


def remove(store: db.Store, code: str) -> None:
    """Bỏ tài sản khỏi danh mục cùng số dư đầu kỳ và giá nhập tay của nó (giá thị trường dùng chung giữ nguyên)."""
    if not removable(store, code):
        raise ValueError(f"{code} đã có lệnh giao dịch hoặc sổ tiết kiệm – xoá chúng trước")
    with store.tx():
        store.x("DELETE FROM transactions WHERE code = ? AND type = ?", (code, db.OPENING))
        store.x("DELETE FROM prices WHERE code = ?", (code,))
        store.x("DELETE FROM assets WHERE code = ?", (code,))

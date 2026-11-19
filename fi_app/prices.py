"""Giá: nhập/xuất gia.csv và mô hình adapter (cùng thiết kế với cap_nhat_gia.py ở thư mục dự án).

gia.csv: Ngày (YYYY-MM-DD), Mã, Giá (VND), Nguồn – khoá duy nhất (Ngày, Mã).
"""
from __future__ import annotations

import csv
import datetime as dt
import os
import shutil
import tempfile
from dataclasses import dataclass
from pathlib import Path

from . import db

GIA_CSV = db.PROJECT_DIR / "gia.csv"
HEADER = ["Ngày", "Mã", "Giá", "Nguồn"]


@dataclass(frozen=True)
class PriceRow:
    ngay: dt.date
    ma: str
    gia: float
    nguon: str


def parse_row(raw: dict, default_source: str) -> PriceRow:
    ngay = dt.date.fromisoformat(str(raw["Ngày"]).strip()[:10])
    ma = str(raw["Mã"]).strip().upper()
    if not ma or " " in ma:
        raise ValueError(f"Mã không hợp lệ: {raw['Mã']!r}")
    gia = float(str(raw["Giá"]).replace(",", "").strip())
    if gia <= 0:
        raise ValueError(f"Giá phải > 0: {raw['Giá']!r}")
    return PriceRow(ngay, ma, gia, (raw.get("Nguồn") or default_source or "").strip())


def read_csv(path: Path, default_source: str = "gia.csv") -> tuple[list[PriceRow], list[str]]:
    rows, errors = [], []
    with Path(path).open(newline="", encoding="utf-8-sig") as fh:
        for i, raw in enumerate(csv.DictReader(fh), start=2):
            if not any((str(v or "")).strip() for v in raw.values()):
                continue
            try:
                rows.append(parse_row(raw, default_source))
            except (KeyError, ValueError) as exc:
                errors.append(f"dòng {i}: {exc}")
    return rows, errors


def import_csv(store: db.Store, path=GIA_CSV, is_manual: int = 0) -> dict:
    """Nhập gia.csv (đường dẫn hoặc file tải lên) vào bảng giá của người dùng."""
    if hasattr(path, "read"):
        import io
        tmp = Path(tempfile.mkstemp(suffix=".csv")[1])
        tmp.write_bytes(path.read())
        path = tmp
    rows, errors = read_csv(path)
    existing = {(r["date"], r["code"]): r["price"]
                for r in store.q("SELECT date, code, price FROM prices WHERE is_manual = ?", (is_manual,))}
    added = sum(1 for r in rows if (r.ngay.isoformat(), r.ma) not in existing)
    updated = sum(1 for r in rows if (r.ngay.isoformat(), r.ma) in existing
                  and abs(existing[(r.ngay.isoformat(), r.ma)] - r.gia) > 1e-9)
    store.many("INSERT INTO prices(date,code,price,source,is_manual) VALUES (?,?,?,?,?) "
               "ON CONFLICT(date, code, is_manual) DO UPDATE SET price=excluded.price, source=excluded.source",
               [(r.ngay.isoformat(), r.ma, r.gia, r.nguon, is_manual) for r in rows])
    return {"rows": len(rows), "added": added, "updated": updated, "errors": errors}


def export_rows(store: db.Store) -> list[PriceRow]:
    """Mỗi (Ngày, Mã) một dòng theo thứ tự ưu tiên: giá tay > giá người dùng > giá thị trường."""
    best: dict[tuple, tuple] = {}
    for r in db.load_all(store)["prices"]:
        k = (str(r["date"])[:10], r["code"])
        if k not in best or int(r["is_manual"]) > best[k][0]:
            best[k] = (int(r["is_manual"]), r)
    out = [PriceRow(dt.date.fromisoformat(k[0]), k[1], float(v[1]["price"]), v[1].get("source") or "")
           for k, v in best.items()]
    return sorted(out, key=lambda p: (p.ngay, p.ma))


def write_csv(rows: list[PriceRow], path: Path) -> None:
    fd, tmp = tempfile.mkstemp(dir=Path(path).parent, suffix=".tmp")
    with os.fdopen(fd, "w", newline="", encoding="utf-8") as fh:
        w = csv.writer(fh)
        w.writerow(HEADER)
        for r in rows:
            w.writerow([r.ngay.isoformat(), r.ma, f"{r.gia:.4f}".rstrip("0").rstrip("."), r.nguon])
    os.replace(tmp, path)


def csv_bytes(store: db.Store) -> bytes:
    import io
    buf = io.StringIO()
    w = csv.writer(buf)
    w.writerow(HEADER)
    for r in export_rows(store):
        w.writerow([r.ngay.isoformat(), r.ma, f"{r.gia:.4f}".rstrip("0").rstrip("."), r.nguon])
    return buf.getvalue().encode("utf-8")


def export_csv(store: db.Store, path: Path = GIA_CSV, keep_backup: bool = True) -> dict:
    """Ghi gia.csv cho Power Query của file Excel. Bản cũ được sao lưu vào webapp/data/backups."""
    path = Path(path)
    if keep_backup and path.exists():
        db.BACKUP_DIR.mkdir(parents=True, exist_ok=True)
        shutil.copy2(path, db.BACKUP_DIR / f"gia_{dt.datetime.now():%Y%m%d_%H%M%S}.csv")
    rows = export_rows(store)
    write_csv(rows, path)
    return {"rows": len(rows), "path": str(path)}


# ----------------------------------------------------------------- lấy giá tự động
def fetch_auto(store: db.Store, today: dt.date | None = None) -> dict:
    """Lấy giá cho mọi tài sản có price_source (+ chỉ số VNINDEX), ghi vào bảng giá thị trường dùng chung."""
    from . import sources
    assets = store.q("SELECT DISTINCT code, price_source FROM assets "
                     "WHERE price_source IS NOT NULL AND price_source <> ''")
    targets, seen = [], set()
    for a in assets + [{"code": c, "price_source": s} for c, s in db.BENCHMARKS.items()]:
        sym = db.asset_symbol(a)
        if sym and sym not in seen:
            seen.add(sym)
            targets.append({"code": sym, "price_source": a["price_source"], "_asset": a["code"]})
    last = {}
    if seen:
        marks = ",".join("?" * len(seen))
        for r in store.q(f"SELECT symbol, MAX(date) AS d FROM market_prices WHERE symbol IN ({marks}) GROUP BY symbol",
                         tuple(seen)):
            last[r["symbol"]] = dt.date.fromisoformat(str(r["d"])[:10])
    # adapter dùng mã tài sản để tra (VD fmarket: DCDS) → truyền spec đầy đủ, code = symbol
    fixed = []
    for t in targets:
        name_args = sources.parse_spec(t["price_source"], t["_asset"])
        fixed.append({"code": t["code"], "price_source": ":".join([name_args[0], *name_args[1]])})
    quotes, log = sources.fetch(fixed, last, today)
    n = store.market_upsert([(q.code, q.date.isoformat(), q.price, q.source) for q in quotes])
    if store.kind == "sqlite" or store.user_id:          # job hệ thống (không có người dùng) không ghi meta
        db.set_kv(store, "meta", {"last_auto_fetch": dt.datetime.now().isoformat(timespec="seconds")})
    return {"saved": n, "log": log}


def should_auto_fetch(store: db.Store, hours: float = 6) -> bool:
    if db.kv(store, "settings").get("auto_fetch", "1") != "1":
        return False
    last = db.kv(store, "meta").get("last_auto_fetch")
    if not last:
        return True
    return (dt.datetime.now() - dt.datetime.fromisoformat(last)).total_seconds() > hours * 3600


# ----------------------------------------------------------------- adapters
class Adapter:
    """Nguồn giá tự động. fetch() trả về list[PriceRow] (Giá tính bằng VND)."""
    name = "base"
    enabled = False

    def fetch(self) -> list[PriceRow]:
        raise NotImplementedError


class WebAdapterTemplate(Adapter):
    """KHUÔN MẪU – chưa bật. Trước khi cài đặt: đọc điều khoản sử dụng của nguồn dữ liệu,
    ưu tiên API chính thức, giới hạn tần suất gọi (1 lần/ngày sau giờ công bố)."""
    name = "Web (mẫu)"


ADAPTERS: list[Adapter] = []  # thêm adapter đã cấu hình và đặt enabled = True


def run_adapters(conn: sqlite3.Connection) -> list[str]:
    log = []
    for ad in ADAPTERS:
        if not ad.enabled:
            continue
        try:
            got = ad.fetch()
            for r in got:
                db.upsert_price(conn, r.ngay, r.ma, r.gia, r.nguon or ad.name, is_manual=0)
            log.append(f"{ad.name}: {len(got)} giá")
        except Exception as exc:  # một nguồn lỗi không ảnh hưởng nguồn khác
            log.append(f"{ad.name}: LỖI {exc}")
    return log

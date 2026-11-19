"""Xuất dữ liệu app ra Excel mới (không ghi đè Investment_tracking_v3.xlsx)."""
from __future__ import annotations

import datetime as dt
from pathlib import Path

import pandas as pd

from . import db, engine


def export_excel(store: db.Store, path: Path | None = None) -> Path:
    """Ghi file Excel vào webapp/xuat/ (chế độ local)."""
    db.EXPORT_DIR.mkdir(parents=True, exist_ok=True)
    path = Path(path or db.EXPORT_DIR / f"FIRE_xuat_{dt.datetime.now():%Y%m%d_%H%M}.xlsx")
    _write(store, path)
    return path


def export_excel_bytes(store: db.Store) -> bytes:
    """Tạo file Excel trong bộ nhớ (chế độ cloud – không lưu dữ liệu cá nhân lên ổ đĩa máy chủ)."""
    import io
    buf = io.BytesIO()
    _write(store, buf)
    return buf.getvalue()


def _write(store: db.Store, target) -> None:
    data = db.load_all(store)
    h = engine.holdings(data)
    fp = engine.fire_plan(data, h)

    danh_muc = pd.DataFrame([{
        "Mã": r["code"], "Tên": r["name"], "Tầng": r["tier"], "Cách định giá": r["valuation"],
        "Số lượng": r["qty"], "Vốn thuần": r["cost"], "Cổ tức đã nhận": r["dividends"],
        "Ngày giá": r["price_date"], "Giá mới nhất": r["price"], "Giá trị hiện tại": r["value"],
        "Lãi/lỗ": r["pnl"], "% Lãi/lỗ": r["pnl_pct"], "XIRR": r["xirr"], "Tỷ trọng": r["weight"],
        "Tính FIRE?": "Có" if r["fire_include"] else "Không", "Cần bổ sung": r["rebalance_need"],
    } for r in h["rows"]])
    tong_quan = pd.DataFrame([
        ("Tổng tài sản", h["total_value"]), ("Vốn thuần", h["total_cost"]), ("Lãi/lỗ", h["total_pnl"]),
        ("Tổng nợ", fp["debt"]), ("Tài sản ròng", h["total_value"] - fp["debt"]),
        ("Tài sản tính FIRE (ròng)", fp["assets"]), ("Số FIRE", fp["fire_number"]),
        ("Tiến độ Full FIRE", fp["progress"]), ("Năm dự kiến đạt Full FIRE", fp["year_full"]),
    ], columns=["Chỉ số", "Giá trị"])
    sheets = {
        "TongQuan": tong_quan,
        "DanhMuc": danh_muc,
        "DM_TaiSan": pd.DataFrame(data["assets"]),
        "GiaoDich": pd.DataFrame(data["transactions"]),
        "Gia": pd.DataFrame(data["prices"]),
        "SoTietKiem": pd.DataFrame(data["savings"]),
        "MucTieu": pd.DataFrame(data["goals"]),
        "No": pd.DataFrame(data["liabilities"]),
        "ThuChi": pd.DataFrame(data["cashflow"]),
        "DuPhong_FIRE": pd.DataFrame(fp["projection"]),
        "Snapshot": pd.DataFrame(data["snapshots"]),
    }
    with pd.ExcelWriter(target, engine="openpyxl") as xw:
        for name, df in sheets.items():
            df.to_excel(xw, sheet_name=name, index=False)
            ws = xw.sheets[name]
            for col in ws.columns:
                width = max((len(str(c.value)) for c in col if c.value is not None), default=8)
                ws.column_dimensions[col[0].column_letter].width = min(max(10, width + 2), 45)

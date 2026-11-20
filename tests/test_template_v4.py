"""File mẫu v4: trống dữ liệu cá nhân, nhập được vào app cả khi trống lẫn khi người dùng đã điền."""
import datetime as dt
import sys
from pathlib import Path

import openpyxl
import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from fi_app import db, engine, importer  # noqa: E402

V4 = ROOT / "mau" / "Investment_tracking_v4.xlsx"
pytestmark = pytest.mark.skipif(not V4.exists(), reason="chưa tạo mẫu v4")


@pytest.fixture
def store(tmp_path):
    return db.connect_local(tmp_path / "t.db")


def test_empty_template_imports(store):
    counts = importer.import_v3(store, V4)
    assert counts["assets"] == counts["transactions"] == counts["savings"] == 0
    assert counts["goals"] == counts["liabilities"] == counts["prices"] == counts["snapshots"] == 0
    cf = db.load_all(store)["cashflow"]
    assert len(cf) >= 15 and all(c["amount"] is None for c in cf)     # khoản mục gợi ý, chưa có số tiền


def test_filled_template_imports(store, tmp_path):
    wb = openpyxl.load_workbook(V4)
    ws = wb["DM_TaiSan"]
    for col, v in zip("ABCDEFHI", ["FPT", "Cổ phiếu FPT", "Cổ phiếu", "Tăng trưởng", "Có", 0.12, "Thị trường", "CP"]):
        ws[f"{col}2"] = v
    ws["A3"], ws["B3"], ws["C3"], ws["D3"], ws["E3"], ws["H3"] = "QKC", "Quỹ khẩn cấp", "Tiết kiệm", "Bảo vệ", "Không", "Sổ tiết kiệm"
    ws.tables["tblTaiSan"].ref = "A1:J3"
    g = wb["GiaoDich"]
    g["A2"], g["B2"], g["C2"], g["E2"], g["F2"] = dt.datetime(2026, 1, 5), "FPT", "Mua", 100000, 100
    s = wb["SoTietKiem"]
    s["A2"], s["B2"], s["E2"], s["F2"], s["H2"], s["I2"] = "Sổ 6 tháng", "QKC", dt.datetime(2027, 1, 5), 50e6, 50e6, 1.5e6
    p = wb["Profile"]
    p["D6"] = 30_000_000
    f = tmp_path / "filled.xlsx"
    wb.save(f)
    counts = importer.import_v3(store, f)
    assert (counts["assets"], counts["transactions"], counts["savings"]) == (2, 1, 1)
    data = db.load_all(store)
    assert {a["code"]: a["price_source"] for a in data["assets"]} == {"FPT": "vndirect", "QKC": None}
    assert engine.cashflow_summary(data["cashflow"])["income"] == 30_000_000

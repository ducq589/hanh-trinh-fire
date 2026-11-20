"""Thêm tài sản từ danh mục: tự gắn loại, tầng, nguồn giá; không cần file Excel."""
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from fi_app import catalog, db, engine  # noqa: E402


@pytest.fixture
def store(tmp_path):
    return db.connect_local(tmp_path / "t.db")


def test_build_fund_stock_gold():
    f = catalog.build("fund", "dcbf", "Quỹ mở trái phiếu DCBF", asset_type=catalog.fund_type("Quỹ trái phiếu"))
    assert (f["code"], f["type"], f["tier"], f["price_source"]) == ("DCBF", "Quỹ mở trái phiếu", "Thu nhập", "fmarket")
    assert catalog.fund_type("Quỹ cân bằng") == "Quỹ mở cổ phiếu" and catalog.fund_type("Quỹ MMF") == "Quỹ mở trái phiếu"
    s = catalog.build("stock", "fpt", "Cổ phiếu FPT", asset_type="Cổ phiếu")
    assert (s["price_source"], s["tier"], s["fire_include"]) == ("vndirect", "Tăng trưởng", 1)
    g = catalog.build("gold", "vang", "Nhẫn trơn", gold_product="N24K")
    assert (g["price_source"], g["type"], g["unit"]) == ("pnj:N24K:mua", "Vàng", "chỉ")
    assert db.asset_symbol(g) == "pnj:N24K:MUA" and db.asset_symbol(f) == "fmarket:DCBF"


@pytest.mark.parametrize("code", ["", "CÓ DẤU", "QUA_DAI_1234567"])
def test_build_rejects_bad_code(code):
    with pytest.raises(ValueError):
        catalog.build("stock", code, "x")


def test_add_new_user_without_excel(store):
    assert db.is_empty(store)
    catalog.add(store, catalog.build("fund", "DCDS", "Quỹ mở cổ phiếu DCDS"))
    catalog.add(store, catalog.build("gold", "VANG", "Nhẫn trơn", gold_product="N24K"))
    with pytest.raises(ValueError, match="đã có"):
        catalog.add(store, catalog.build("fund", "DCDS", "trùng"))
    data = db.load_all(store)
    assert [(a["code"], a["sort_order"]) for a in data["assets"]] == [("DCDS", 0), ("VANG", 1)]
    # giá thị trường dùng chung được gán vào tài sản mới
    store.market_upsert([("fmarket:DCDS", "2026-11-19", 100000.0, "Fmarket (NAV)")])
    db.add_transaction(store, "2026-11-01", "DCDS", "Mua", amount=10_000_000, price=95000, qty=105.26)
    h = engine.holdings(db.load_all(store))
    row = next(r for r in h["rows"] if r["code"] == "DCDS")
    assert row["price"] == 100000.0 and round(row["value"]) == 10_526_000

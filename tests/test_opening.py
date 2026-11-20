"""Số dư đầu kỳ: khai Số lượng + Giá vốn BQ thay cho lịch sử lệnh; XIRR tính từ ngày khai."""
import datetime as dt
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from fi_app import catalog, db, engine  # noqa: E402

D0 = dt.date(2026, 6, 1)


@pytest.fixture
def store(tmp_path):
    s = db.connect_local(tmp_path / "t.db")
    catalog.add(s, catalog.build("fund", "DCDS", "Quỹ DCDS"))
    return s


def _opening(s):
    return s.q("SELECT * FROM transactions WHERE type = ?", (db.OPENING,))


def _row(s, today):
    return next(r for r in engine.holdings(db.load_all(s), today)["rows"] if r["code"] == "DCDS")


def test_set_opening_one_row_update_delete(store):
    assert db.set_opening(store, "DCDS", 100, 20_000, D0) == "added"
    assert db.set_opening(store, "DCDS", 120.5, 21_000, D0) == "updated"
    rows = _opening(store)
    assert len(rows) == 1 and rows[0]["qty"] == 120.5 and rows[0]["price"] == 21_000
    assert rows[0]["note"] == db.OPENING_NOTE
    assert db.set_opening(store, "DCDS", 0, None, D0) == "deleted" and _opening(store) == []
    assert db.set_opening(store, "DCDS", None, None, D0) == "none"


def test_pnl_from_opening_and_later_buy(store):
    db.set_opening(store, "DCDS", 100, 20_000, D0)
    store.market_upsert([("fmarket:DCDS", "2026-06-01", 22_000.0, "t"), ("fmarket:DCDS", "2026-06-10", 24_000.0, "t"),
                         ("fmarket:DCDS", "2026-07-15", 25_000.0, "t")])
    r = _row(store, dt.date(2026, 6, 15))
    assert r["qty"] == 100 and r["cost"] == 2_000_000
    db.add_transaction(store, "2026-06-10", "DCDS", "Mua", amount=2_400_000)        # NAV tự tra 24.000 → 100 CCQ
    r = _row(store, dt.date(2026, 7, 15))
    assert r["qty"] == 200 and r["cost"] == 4_400_000
    assert r["value"] == 5_000_000 and r["pnl"] == 600_000


def test_xirr_since_declaration(store):
    db.set_opening(store, "DCDS", 100, 20_000, D0)            # giá vốn 20.000 nhưng giá thị trường ngày khai 22.000
    store.market_upsert([("fmarket:DCDS", "2026-05-29", 22_000.0, "t"),   # ngày khai rơi vào cuối tuần → lấy giá thứ Sáu
                         ("fmarket:DCDS", "2026-06-20", 23_000.0, "t")])
    r = _row(store, dt.date(2026, 6, 20))
    assert r["xirr_since"] == D0 and r["xirr"] is None        # mới 19 ngày → chưa hiện
    store.market_upsert([("fmarket:DCDS", "2026-12-01", 24_200.0, "t")])
    r = _row(store, dt.date(2026, 12, 1))
    expected = engine.xirr([-2_200_000, 2_420_000], [D0, dt.date(2026, 12, 1)])   # +10% theo giá thị trường, không theo giá vốn
    assert r["xirr"] == pytest.approx(expected) and r["xirr"] > 0.15


def test_no_market_price_near_declaration_no_xirr(store):
    db.set_opening(store, "DCDS", 100, 20_000, dt.date(2025, 1, 1))
    store.market_upsert([("fmarket:DCDS", "2026-12-01", 24_200.0, "t")])
    assert _row(store, dt.date(2026, 12, 1))["xirr"] is None

"""Mua CCQ chờ phân bổ: lưu số tiền trước, số CCQ tính khi có NAV ngày phân bổ."""
import datetime as dt

import pytest

from fi_app import engine

TODAY = dt.date(2026, 11, 26)
TOMORROW = TODAY + dt.timedelta(days=1)


def _data(prices):
    return {
        "settings": {},
        "assets": [{"code": "QA", "name": "Quỹ A", "type": "Quỹ mở cổ phiếu", "tier": "Tăng trưởng",
                    "valuation": "Thị trường", "fire_include": 1}],
        "transactions": [
            {"id": 1, "date": "2026-11-01", "code": "QA", "type": "Mua", "amount": 1_000_000, "price": None,
             "qty": None, "fee": None, "tax": None, "note": None},
            {"id": 2, "date": TOMORROW.isoformat(), "code": "QA", "type": "Mua", "amount": 2_000_000, "price": None,
             "qty": None, "fee": None, "tax": None, "note": "Đặt mua 26/11/2026"},
        ],
        "prices": prices, "savings": [], "goals": [],
    }


def test_pending_counted_at_cost_until_nav():
    prices = [{"date": "2026-11-01", "code": "QA", "price": 10_000}, {"date": TODAY.isoformat(), "code": "QA", "price": 10_000}]
    r = engine.holdings(_data(prices), TODAY)["rows"][0]
    assert r["qty"] == pytest.approx(100)                      # chỉ lệnh đã có NAV
    assert r["pending_amount"] == 2_000_000
    assert r["value"] == pytest.approx(3_000_000)              # 100 × 10.000 + 2 tr chờ phân bổ
    assert r["pnl"] == pytest.approx(0)                        # không hiện lỗ giả
    assert "Chờ NAV ngày 27/11" in r["warning"]


def test_pending_resolves_when_nav_arrives():
    prices = [{"date": "2026-11-01", "code": "QA", "price": 10_000}, {"date": TOMORROW.isoformat(), "code": "QA", "price": 8_000}]
    r = engine.holdings(_data(prices), TOMORROW)["rows"][0]
    assert r["qty"] == pytest.approx(100 + 250)                # 2.000.000 / 8.000
    assert "pending_amount" not in r
    assert "Chờ NAV" not in r["warning"]

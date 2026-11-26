"""Lô CCQ theo tháng, bán theo lô cũ nhất trước (FIFO)."""
import datetime as dt

import pytest

from fi_app import engine


def _tx(i, date, typ, amount=None, price=None, qty=None, fee=None, tax=None):
    return {"id": i, "date": date, "code": "QA", "type": typ, "amount": amount, "price": price, "qty": qty,
            "fee": fee, "tax": tax, "note": None}


PRICES = [{"date": d, "code": "QA", "price": p} for d, p in
          [("2026-01-05", 10_000), ("2026-02-05", 20_000), ("2026-03-05", 12_500), ("2026-04-01", 15_000)]]


def _run(txs):
    book = engine.PriceBook(PRICES)
    derived = [engine.derive_tx(t, book) for t in txs]
    return engine.fund_lots(derived, book, "QA")


def test_lots_without_sales():
    res = _run([_tx(1, "2026-01-05", "Mua", amount=1_000_000), _tx(2, "2026-02-05", "Mua", amount=1_000_000)])
    a, b = res["lots"]
    assert (a["qty"], b["qty"]) == (100, 50)
    assert a["value"] == pytest.approx(1_500_000) and a["pct"] == pytest.approx(0.5)     # giá hiện tại 15.000
    assert b["pnl"] == pytest.approx(-250_000) and b["pct"] == pytest.approx(-0.25)
    assert res["sales"] == []


def test_partial_sale_takes_oldest_lot_first():
    res = _run([_tx(1, "2026-01-05", "Mua", amount=1_000_000), _tx(2, "2026-02-05", "Mua", amount=1_000_000),
                _tx(3, "2026-03-05", "Bán", price=12_500, qty=60, fee=5_000)])
    a, b = res["lots"]
    assert a["remaining"] == pytest.approx(40) and b["remaining"] == pytest.approx(50)
    s = res["sales"][0]
    assert s["cost"] == pytest.approx(600_000)                     # 60 CCQ của lô tháng 1 (giá vốn 10.000)
    assert s["pnl"] == pytest.approx(60 * 12_500 - 5_000 - 600_000)
    assert s["sources"] == [(dt.date(2026, 1, 5), 60)] and not s["short"]


def test_sale_spanning_two_lots():
    res = _run([_tx(1, "2026-01-05", "Mua", amount=1_000_000), _tx(2, "2026-02-05", "Mua", amount=1_000_000),
                _tx(3, "2026-03-05", "Bán", price=12_500, qty=120)])
    a, b = res["lots"]
    assert a["remaining"] == 0 and b["remaining"] == pytest.approx(30)
    s = res["sales"][0]
    assert s["cost"] == pytest.approx(1_000_000 + 20 * 20_000)
    assert [q for _, q in s["sources"]] == pytest.approx([100, 20])


def test_monthly_grouping():
    res = _run([_tx(1, "2026-01-05", "Mua", amount=1_000_000), _tx(2, "2026-02-05", "Mua", amount=500_000),
                _tx(3, "2026-02-05", "Mua", amount=500_000)])
    months = engine.monthly_lots([res])
    assert [(m["year"], m["month"]) for m in months] == [(2026, 1), (2026, 2)]
    assert months[1]["cost"] == pytest.approx(1_000_000) and months[1]["qty"] == pytest.approx(50)

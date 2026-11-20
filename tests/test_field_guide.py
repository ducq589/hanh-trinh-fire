"""Giải thích cột: đủ cột cho mọi bảng nhập liệu, và ví dụ trong hướng dẫn khớp công thức thật của engine."""
import datetime as dt
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from fi_app import engine, field_guide  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]


def test_every_tooltip_in_views_exists_and_nonempty():
    """Mọi field_guide.tip(key, nhãn) trong views/ phải có giải thích (KeyError nếu thiếu)."""
    calls = []
    for f in (ROOT / "views").glob("*.py"):
        calls += re.findall(r'field_guide\.tip\("(\w+)", "([^"]+)"\)', f.read_text(encoding="utf-8"))
    assert len(calls) >= 45
    for key, label in calls:
        assert field_guide.tip(key, label).strip()


def test_every_guided_column_is_used_on_a_page():
    used = set()
    for f in (ROOT / "views").glob("*.py"):
        used |= set(re.findall(r'field_guide\.tip\("(\w+)", "([^"]+)"\)', f.read_text(encoding="utf-8")))
    for key, g in field_guide.GUIDES.items():
        for col in g["cols"]:
            assert (key, col[0]) in used, f"{key}: cột {col[0]!r} có giải thích nhưng chưa gắn vào bảng"


def test_markdown_tables_have_no_stray_pipes():
    for key in field_guide.GUIDES:
        for line in field_guide.table_md(key).splitlines():
            assert line.count("|") == 7, (key, line)


def test_savings_example_matches_engine():
    s = engine.derive_savings({"start_balance": 50e6, "interest_gross": 50e6 * 0.052 * 6 / 12, "principal": 50e6,
                               "topup": 0, "maturity": "2027-05-15"}, 0.05, dt.date(2026, 11, 20), 15)
    assert round(s["received"]) == 51_235_000
    assert "51.235.000" in " ".join(field_guide.GUIDES["savings"]["example"])


def test_transaction_examples_match_engine():
    book = engine.PriceBook([])
    buy = engine.derive_tx({"date": "2026-11-18", "code": "DCDS", "type": "Mua", "amount": 3e6, "price": 25000}, book)
    assert buy["qty_calc"] == 120 and buy["cashflow"] == -3e6
    stock = engine.derive_tx({"date": "2026-11-18", "code": "FPT", "type": "Mua", "price": 120000, "qty": 100,
                              "fee": 18000}, book)
    assert stock["net_in"] == 12_018_000
    sell = engine.derive_tx({"date": "2026-11-20", "code": "FPT", "type": "Bán", "price": 125000, "qty": 100,
                             "fee": 18750, "tax": 12500}, book)
    assert sell["cashflow"] == 12_468_750
    ex = " ".join(field_guide.GUIDES["transactions"]["example"])
    for s in ("120,00", "12.018.000", "12.468.750"):
        assert s in ex


def test_cashflow_example_monthly():
    assert round(engine.monthly(12e6, "Năm")) == 1_000_000
    assert round(engine.monthly(20e6, "Năm")) == 1_666_667

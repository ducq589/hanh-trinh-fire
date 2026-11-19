"""Đối chiếu engine với các số Excel đã tính trên Investment_tracking_v3.xlsx (ngày 19/11/2026).

Chạy:  webapp/.venv/bin/python -m pytest webapp/tests -q
"""
import datetime as dt
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from fi_app import db, engine, importer  # noqa: E402

TODAY = dt.date(2026, 11, 19)


@pytest.fixture(scope="module")
def data(tmp_path_factory):
    if not importer.V3_PATH.exists():
        pytest.skip("cần file Investment_tracking_v3.xlsx ở thư mục cha (chỉ có trên máy cá nhân)")
    conn = db.connect_local(tmp_path_factory.mktemp("db") / "test.db")
    importer.import_v3(conn)
    d = db.load_all(conn)
    yield d
    conn.close()


@pytest.fixture(scope="module")
def h(data):
    return engine.holdings(data, TODAY)


def row(h, code):
    return next(r for r in h["rows"] if r["code"] == code)


def test_totals(h):
    assert h["total_value"] == pytest.approx(845_738_174.2964, abs=0.01)
    assert h["total_cost"] == pytest.approx(700_624_183.8095, abs=0.01)
    assert h["total_pnl"] == pytest.approx(146_213_990.4869, abs=0.01)
    assert h["fire_value_gross"] == pytest.approx(297_871_376.0964, abs=0.01)


@pytest.mark.parametrize("code,qty,value,cost,x", [
    ("DCDS", 930.28, 84_800_212.9624, 86_990_294.4703, -0.03332592649385333),
    ("VESAF", 3164.56, 95_878_446.4736, 101_594_370.8794, -0.06144089343142696),
    ("VNDBF", 3761.32, 62_202_716.6604, 57_499_536.4598, 0.07224088609218597),
    ("MBB", 2925, 54_990_000, 60_071_982, -0.1855625631287694),
])
def test_market_assets(h, code, qty, value, cost, x):
    r = row(h, code)
    assert r["qty"] == pytest.approx(qty, abs=1e-6)
    assert r["value"] == pytest.approx(value, abs=0.01)
    assert r["cost"] == pytest.approx(cost, abs=0.01)
    assert r["xirr"] == pytest.approx(x, abs=1e-6)


def test_savings_and_declared(h):
    assert row(h, "QKC")["value"] == pytest.approx(127_500_378.25, abs=0.01)
    assert row(h, "VLD")["value"] == pytest.approx(10_236_752.05, abs=0.01)
    assert row(h, "SF")["value"] == pytest.approx(85_621_667.9, abs=0.01)
    assert row(h, "VANG")["value"] == pytest.approx(185_250_000)
    assert row(h, "BHNT")["value"] == pytest.approx(139_258_000)
    assert row(h, "VANG")["xirr"] is None  # có "Vốn đầu kỳ" → không tính XIRR


def test_rebalance(h):
    assert row(h, "DCDS")["rebalance_need"] == pytest.approx(2_283_590.3622, abs=0.01)
    assert row(h, "VESAF")["rebalance_need"] == pytest.approx(3_645_900.1830, abs=0.01)
    assert row(h, "VNDBF")["rebalance_need"] == pytest.approx(0, abs=0.01)


def test_tiers(h):
    t = {x["tier"]: x for x in h["tiers"]}
    assert t["Tăng trưởng"]["value"] == pytest.approx(235_668_659.436, abs=0.01)
    assert t["Phòng thủ"]["value"] == pytest.approx(324_508_000)


def test_goal(h):
    g = h["goals"][0]
    assert g["have"] == pytest.approx(37_753_844.35, abs=0.01)
    assert g["months_left"] == 9
    assert g["need_monthly"] == pytest.approx(249_572.85, abs=0.01)


def test_cashflow(data):
    cf = engine.cashflow_summary(data["cashflow"])
    assert cf["expense"] == pytest.approx(28_416_666.6667, abs=0.01)
    assert cf["essential"] == pytest.approx(24_833_333.3333, abs=0.01)
    assert cf["savings_rate"] == pytest.approx(0.2942880794701988, abs=1e-9)


def test_fire_plan_matches_excel(data, h):
    fp = engine.fire_plan(data, h, TODAY)
    assert fp["fire_number"] == pytest.approx(8_525_000_000, abs=1)
    assert fp["lean"] == pytest.approx(7_450_000_000, abs=1)
    assert fp["coast"] == pytest.approx(2_228_301_480.114, abs=1)
    assert fp["assets"] == pytest.approx(237_871_376.0964, abs=0.01)
    assert fp["progress"] == pytest.approx(0.027902800715120236, abs=1e-9)
    assert fp["passive_ratio"] == pytest.approx(0.03142186229869795, abs=1e-9)
    assert fp["years_full"] == pytest.approx(17.58439089228278, abs=1e-6)
    assert fp["years_lean"] == pytest.approx(16.31118573429778, abs=1e-6)
    assert fp["year_full"] == 2044 and fp["age_full"] == 56
    assert fp["emergency_months"] == pytest.approx(5.134243419463088, abs=1e-9)
    first_full = next(p["year"] for p in fp["projection"] if p["milestone"] == "Full FIRE")
    assert first_full == 2044  # bảng dự phóng khớp NPER


def test_whatif_more_dca_is_faster(data, h):
    base = engine.fire_plan(data, h, TODAY)
    more = engine.fire_plan(data, h, TODAY, extra_invest=5_000_000)
    assert more["years_full"] < base["years_full"]


def test_add_new_asset_like_excel(data):
    """Phép thử đã làm trên Excel: thêm quỹ TEST → tổng tài sản tăng đúng 2.147.530."""
    d = {k: (list(v) if isinstance(v, list) else v) for k, v in data.items()}
    d["assets"] = d["assets"] + [{"code": "TEST", "name": "Quỹ thử", "type": "Quỹ mở trái phiếu", "tier": "Thu nhập",
                                   "fire_include": 1, "exp_return": 0.07, "target_weight": None,
                                   "valuation": "Thị trường"}]
    d["transactions"] = d["transactions"] + [
        {"date": "2026-10-01", "code": "TEST", "type": "Mua", "amount": 1_000_000, "price": 10_000},
        {"date": "2026-11-01", "code": "TEST", "type": "Mua", "amount": 1_000_000, "price": 10_500}]
    d["prices"] = d["prices"] + [{"date": "2026-11-18", "code": "TEST", "price": 11_000, "is_manual": 1}]
    h2 = engine.holdings(d, TODAY)
    assert h2["total_value"] - 845_738_174.2964 == pytest.approx(2_147_530, abs=0.01)
    assert row(h2, "TEST")["qty"] == pytest.approx(195.23)


def test_finance_primitives():
    assert engine.trunc2(1_000_000 / 10_500) == 95.23
    assert engine.months_between(dt.date(2026, 11, 19), dt.date(2027, 8, 1)) == 8
    k = engine.nper(0.01, -100, -1000, 5000)
    assert engine.fv(0.01, k, -100, -1000) == pytest.approx(5000, abs=1e-6)
    assert engine.nper(0.0, 0, -1000, 5000) is None

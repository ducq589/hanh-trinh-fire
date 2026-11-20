"""Hướng dẫn thiết lập 5 bước và bảng sức khoẻ tài chính (engine thuần, không cần Streamlit)."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from fi_app import catalog, db, engine  # noqa: E402


def _calc(s):
    data = db.load_all(s)
    h = engine.holdings(data)
    return data, h, engine.fire_plan(data, h)


def _cf(s, grp, amount, name=None):
    s.x("INSERT INTO cashflow_items(name, grp, amount, freq) VALUES (?,?,?,?)", (name or grp, grp, amount, "Tháng"))


def _health(s):
    data, h, fp = _calc(s)
    return {x["key"]: x for x in engine.health(data, h, fp)}


def test_onboarding_progresses_step_by_step(tmp_path):
    s = db.connect_local(tmp_path / "a.db")
    done = lambda: [x["done"] for x in engine.onboarding(*_calc(s)[::2])]   # noqa: E731  (data, fp)
    assert done() == [False] * 5
    _cf(s, "Thu nhập chủ động", 30e6)
    assert done()[0] is False                       # chưa có khoản chi
    _cf(s, "Chi thiết yếu", 10e6)
    assert done()[:1] == [True]
    db.set_kv(s, "assumptions", {"current_age": "30"})
    assert done()[:2] == [True, True]
    catalog.add(s, catalog.build("fund", "DCDS", "Quỹ DCDS"))
    assert done()[:3] == [True, True, True] and done()[4] is False
    db.set_opening(s, "DCDS", 10, 50000, "2026-11-01")
    assert done() == [True] * 5


def test_health_without_cashflow_is_na_not_crash(tmp_path):
    s = db.connect_local(tmp_path / "b.db")
    hl = _health(s)
    for k in ("emergency", "savings_rate", "essential_ratio", "debt_ratio", "invest_ratio"):
        assert hl[k]["status"] == "na", k
    assert hl["insurance"]["status"] == "warn"


def test_health_thresholds(tmp_path):
    s = db.connect_local(tmp_path / "c.db")
    _cf(s, "Thu nhập chủ động", 20e6)
    _cf(s, "Chi thiết yếu", 9e6)          # 45% → tốt
    _cf(s, "Chi linh hoạt", 7e6)          # tiết kiệm 4/20 = 20% → tốt
    _cf(s, "Đầu tư định kỳ", 2e6)         # 10% → tạm
    hl = _health(s)
    assert hl["essential_ratio"]["status"] == "good"
    assert hl["savings_rate"]["status"] == "good"
    assert hl["invest_ratio"]["status"] == "warn"
    assert hl["debt_ratio"]["status"] == "good" and hl["debt_ratio"]["display"] == "Không có nợ"
    assert hl["emergency"]["status"] == "na" and "QKC" in hl["emergency"]["hint"]   # chưa có tài sản quỹ khẩn cấp

    s.x("INSERT INTO liabilities(name, balance, monthly_payment) VALUES (?,?,?)", ("Vay mua nhà", 500e6, 8e6))
    assert _health(s)["debt_ratio"]["status"] == "bad"          # 40% > 35%

    # quỹ khẩn cấp: mã QKC, giá trị 2 tháng chi thiết yếu → cần cải thiện; 6 tháng → tốt
    s.x("INSERT INTO assets(code, name, type, tier, valuation) VALUES ('QKC','Quỹ khẩn cấp','Tiền mặt','Phòng thủ','Khai báo')")
    db.set_opening(s, "QKC", 1, 18e6, "2026-11-01")            # giá trị = số lượng × giá
    db.upsert_price(s, "2026-11-01", "QKC", 18e6)
    hl = _health(s)
    assert hl["emergency"]["status"] == "bad", hl["emergency"]
    db.upsert_price(s, "2026-11-02", "QKC", 54e6)
    assert _health(s)["emergency"]["status"] == "good"

    s.x("INSERT INTO assets(code, name, type, tier, valuation) VALUES ('BH','Bảo hiểm','Bảo hiểm','Bảo vệ','Khai báo')")
    assert _health(s)["insurance"]["status"] == "good"


def test_grade_edges():
    assert engine._grade(0.20, 0.20, 0.10) == "good"
    assert engine._grade(0.10, 0.20, 0.10) == "warn"
    assert engine._grade(0.05, 0.20, 0.10) == "bad"
    assert engine._grade(0.0, 0.15, 0.0) == "bad" and engine._grade(0.01, 0.15, 0.0) == "warn"
    assert engine._grade(0.70, 0.50, 0.70, False) == "warn" and engine._grade(0.71, 0.50, 0.70, False) == "bad"

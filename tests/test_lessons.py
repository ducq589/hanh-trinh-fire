"""Bài học Nền tảng tài chính: so sánh ngân sách với 50/30/20 và 'trả cho mình trước'."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from fi_app import engine  # noqa: E402


def _cf(rows):
    return engine.cashflow_summary([{"grp": g, "amount": a, "freq": "Tháng"} for g, a in rows])


def test_budget_check_ratios():
    b = engine.budget_check(_cf([("Thu nhập chủ động", 20e6), ("Chi thiết yếu", 9e6), ("Chi linh hoạt", 5e6),
                                 ("Đầu tư định kỳ", 3e6)]))
    assert round(b["essential"], 4) == 0.45 and round(b["flexible"], 4) == 0.25
    assert round(b["save"], 4) == 0.30            # 3 tr đầu tư + 3 tr dư
    assert round(b["pay_first"], 4) == 0.15
    assert (round(b["buffer_low"]), round(b["buffer_high"])) == (700_000, 1_400_000)


def test_budget_check_no_income():
    assert engine.budget_check(_cf([("Chi thiết yếu", 9e6)])) is None


def test_overcommitted_invest_does_not_reduce_saving():
    b = engine.budget_check(_cf([("Thu nhập chủ động", 10e6), ("Chi thiết yếu", 8e6), ("Đầu tư định kỳ", 4e6)]))
    assert round(b["save"], 4) == 0.40            # phần dư âm không trừ thêm


def test_emergency_plan_example():
    p = engine.emergency_plan(6.3e6, 0, "Độc thân", "Không ai", False, 6e6)
    assert p["months"] == 6 and round(p["target"]) == 37_800_000
    assert p["months_to_goal"] == 7                      # 37,8 tr / 6 tr = 6,3 → 7 tháng
    assert engine.emergency_plan(6.3e6, 0, "Độc thân", "3–4 người", True, 0)["months"] == 21
    assert engine.emergency_plan(6.3e6, 0, "Độc thân", "Không ai", False, 0)["months_to_goal"] is None
    done = engine.emergency_plan(5e6, 20e6, "Vợ chồng đều có thu nhập", "Không ai", False, 1e6)
    assert done["gap"] == 0 and done["months_to_goal"] == 0 and done["progress"] == 1.0


def test_ladder_sums_to_total():
    for scheme in engine.LADDERS:
        parts = engine.ladder(100e6, scheme)
        assert round(sum(a for _, _, a in parts)) == 100_000_000

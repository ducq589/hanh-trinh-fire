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

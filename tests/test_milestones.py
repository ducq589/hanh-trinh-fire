"""Thành tựu & lời động viên: mốc thiết lập, % Số FIRE, nền móng; chuỗi snapshot; chọn mốc để chúc mừng."""
import datetime as dt
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from fi_app import catalog, db, engine, intro  # noqa: E402


def _calc(s):
    data = db.load_all(s)
    h = engine.holdings(data)
    return data, h, engine.fire_plan(data, h)


def _ms(s):
    return {m["key"]: m for m in engine.milestones(*_calc(s))}


def test_every_milestone_has_text():
    data ={"assets": [], "transactions": [], "savings": [], "liabilities": [], "cashflow": [], "snapshots": [],
            "assumptions": {}, "settings": {}, "prices": [], "goals": []}
    h = engine.holdings(data)
    keys = {m["key"] for m in engine.milestones(data, h, engine.fire_plan(data, h))}
    assert keys == set(intro.MILESTONE_TEXT)


def test_empty_then_setup_progress(tmp_path):
    s = db.connect_local(tmp_path / "a.db")
    ms = engine.milestones(*_calc(s))
    assert not any(m["reached"] for m in ms)
    assert engine.next_milestone(ms)["key"] == "setup_cf"
    s.x("INSERT INTO cashflow_items(name, grp, amount, freq) VALUES ('Lương','Thu nhập chủ động',30e6,'Tháng')")
    s.x("INSERT INTO cashflow_items(name, grp, amount, freq) VALUES ('Ăn','Chi thiết yếu',10e6,'Tháng')")
    m = _ms(s)
    assert m["setup_cf"]["reached"] and not m["setup_asset"]["reached"]
    assert m["save_20"]["reached"]                                      # tiết kiệm 20/30 ≈ 67%
    catalog.add(s, catalog.build("fund", "DCDS", "Quỹ DCDS"))
    assert _ms(s)["setup_asset"]["reached"]


def test_fire_percent_and_gap(tmp_path):
    s = db.connect_local(tmp_path / "b.db")
    s.x("INSERT INTO cashflow_items(name, grp, amount, freq) VALUES ('Lương','Thu nhập chủ động',30e6,'Tháng')")
    s.x("INSERT INTO cashflow_items(name, grp, amount, freq) VALUES ('Ăn','Chi thiết yếu',10e6,'Tháng')")
    # Số FIRE = 10tr × 12 / 4% = 3 tỷ; tài sản FIRE 90 tr = 3%
    s.x("INSERT INTO assets(code, name, type, tier, valuation, fire_include) "
        "VALUES ('X','X','Khác','Tăng trưởng','Khai báo',1)")
    db.set_opening(s, "X", 1, 90e6, "2026-11-01")
    db.upsert_price(s, "2026-11-01", "X", 90e6)
    m = _ms(s)
    assert m["fire_1"]["reached"] and not m["fire_5"]["reached"]
    assert m["fire_5"]["gap"] == "Còn 60,0 tr để chạm 5% Số FIRE"
    assert abs(m["fire_5"]["progress"] - 0.6) < 1e-9
    nxt = engine.next_milestone([x for x in engine.milestones(*_calc(s)) if x["group"] == "Hành trình FIRE"])
    assert nxt["key"] == "fire_5"


def test_snapshot_streak():
    today = dt.date(2026, 11, 20)
    snaps = [{"date": f"2026-{mo:02d}-01"} for mo in range(6, 12)]          # 6 → 11: 6 tháng liền
    assert engine.snapshot_streak(snaps, today) == 6
    assert engine.snapshot_streak([x for x in snaps if x["date"] != "2026-08-01"], today) == 3   # đứt tháng 8
    assert engine.snapshot_streak(snaps[:-1], today) == 5                   # tháng này chưa chụp → tính tới tháng 10
    jan = [{"date": "2025-12-01"}, {"date": "2026-01-03"}]
    assert engine.snapshot_streak(jan, dt.date(2026, 1, 15)) == 2           # qua năm


def test_new_milestones_highest_first_and_seen():
    ms = [{"key": "setup_cf", "group": "Thiết lập", "reached": True},
          {"key": "setup_done", "group": "Thiết lập", "reached": True},
          {"key": "fire_1", "group": "Hành trình FIRE", "reached": True},
          {"key": "fire_5", "group": "Hành trình FIRE", "reached": True},
          {"key": "fire_10", "group": "Hành trình FIRE", "reached": False},
          {"key": "em_full", "group": "Nền móng", "reached": True}]
    fresh = engine.new_milestones(ms, {})
    assert [m["key"] for m in fresh] == ["fire_5", "fire_1", "setup_done", "setup_cf", "em_full"]
    assert [m["key"] for m in engine.new_milestones(ms, {k: "2026-11-20" for k in
                                                         ("setup_cf", "setup_done", "fire_1", "fire_5")})] == ["em_full"]

"""Kiểm tra chế độ cloud trên Postgres thật (cục bộ, qua gói pgserver) với schema Supabase + RLS.

Mô phỏng phần Supabase cần thiết: schema auth, bảng auth.users, hàm auth.uid(), role authenticated/anon.
Bỏ qua nếu máy không có pgserver:  pip install pgserver
"""
import datetime as dt
import sys
import uuid
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
pgserver = pytest.importorskip("pgserver")
psycopg = pytest.importorskip("psycopg")
from fi_app import db, engine, importer  # noqa: E402

SHIM = """
DO $$ BEGIN
  IF NOT EXISTS (SELECT 1 FROM pg_roles WHERE rolname='anon') THEN CREATE ROLE anon NOLOGIN; END IF;
  IF NOT EXISTS (SELECT 1 FROM pg_roles WHERE rolname='authenticated') THEN CREATE ROLE authenticated NOLOGIN; END IF;
END $$;
GRANT authenticated TO CURRENT_USER;
CREATE SCHEMA IF NOT EXISTS auth;
CREATE TABLE IF NOT EXISTS auth.users (id uuid PRIMARY KEY, email text);
CREATE OR REPLACE FUNCTION auth.uid() RETURNS uuid LANGUAGE sql STABLE AS $f$
  SELECT nullif(coalesce(nullif(current_setting('request.jwt.claim.sub', true), ''),
                         (nullif(current_setting('request.jwt.claims', true), '')::jsonb ->> 'sub')), '')::uuid
$f$;
GRANT USAGE ON SCHEMA auth TO authenticated, anon;
GRANT USAGE ON SCHEMA public TO authenticated, anon;
"""
TODAY = dt.date(2026, 11, 19)


@pytest.fixture(scope="module")
def dsn(tmp_path_factory):
    srv = pgserver.get_server(str(tmp_path_factory.mktemp("pg")), cleanup_mode="stop")
    uri = srv.get_uri()
    with psycopg.connect(uri, autocommit=True) as c:
        c.execute(SHIM)
        c.execute((Path(db.APP_DIR) / "supabase" / "schema.sql").read_text())
    yield uri
    srv.cleanup()


def _user(dsn, email):
    uid = str(uuid.uuid4())
    with psycopg.connect(dsn, autocommit=True) as c:
        c.execute("INSERT INTO auth.users(id, email) VALUES (%s, %s)", (uid, email))
    return uid


def test_import_and_isolation(dsn):
    if not importer.V3_PATH.exists():
        pytest.skip("cần file Investment_tracking_v3.xlsx")
    a_id, b_id = _user(dsn, "a@example.com"), _user(dsn, "b@example.com")
    a = db.connect_cloud(dsn, a_id, "a@example.com")
    counts = importer.import_v3(a)
    assert counts["transactions"] == 279 and counts["assets"] == 9
    h = engine.holdings(db.load_all(a), TODAY)
    assert h["total_value"] == pytest.approx(845_738_174.2964, abs=0.01)
    xirr = {r["code"]: r["xirr"] for r in h["rows"]}
    assert xirr["DCDS"] == pytest.approx(-0.03332592649385333, abs=1e-6)

    b = db.connect_cloud(dsn, b_id, "b@example.com")
    assert db.is_empty(b)                                         # B không thấy dữ liệu của A
    assert b.q("SELECT COUNT(*) AS n FROM transactions")[0]["n"] == 0
    assert b.x("UPDATE assets SET name = 'hack'") == 0             # không sửa được dòng của A
    assert b.x("DELETE FROM transactions") == 0                    # không xoá được dòng của A
    with pytest.raises(psycopg.Error):                             # không chèn được dòng mang user_id của A
        b.x("INSERT INTO goals(user_id, name, target) VALUES (?, ?, ?)", (a_id, "x", 1))
    b.conn.rollback()
    # defaults riêng cho từng người
    assert db.kv(b, "settings")["stale_days"] == "7"
    db.set_kv(b, "settings", {"stale_days": "3"})
    assert float(db.kv(a, "settings")["stale_days"]) == 7   # thay đổi của B không ảnh hưởng A
    # A vẫn nguyên vẹn
    assert a.q("SELECT COUNT(*) AS n FROM transactions")[0]["n"] == 279
    a.close(); b.close()


def test_market_prices_shared_but_not_user_writable(dsn):
    uid = _user(dsn, "c@example.com")
    s = db.connect_cloud(dsn, uid, "c@example.com")
    with pytest.raises(psycopg.Error):                             # người dùng không ghi trực tiếp được
        s.x("INSERT INTO market_prices(symbol, date, price) VALUES ('fmarket:DCDS', '2026-11-20', 1)")
    s.conn.rollback()
    s._set_user_role()
    assert s.market_upsert([("fmarket:DCDS", "2026-11-20", 92000.0, "test")]) == 1   # chỉ code lấy giá ghi được
    assert s.q("SELECT price FROM market_prices WHERE symbol='fmarket:DCDS'")[0]["price"] == 92000.0
    # sau market_upsert phiên vẫn ở role authenticated (RLS còn hiệu lực)
    assert s.q("SELECT current_user AS u")[0]["u"] == "authenticated"
    s.close()


def test_transactions_crud_roundtrip(dsn):
    uid = _user(dsn, "d@example.com")
    s = db.connect_cloud(dsn, uid, "d@example.com")
    s.x("INSERT INTO assets(code, name, tier, valuation, price_source) VALUES ('DCDS','Quỹ DCDS','Tăng trưởng','Thị trường','fmarket')")
    tid = db.add_transaction(s, "2026-11-19", "DCDS", "Mua", amount=1_000_000, price=92000)
    assert isinstance(tid, int)
    db.upsert_price(s, "2026-11-19", "DCDS", 92000, "test", 1)
    db.upsert_price(s, "2026-11-19", "DCDS", 93000, "test", 1)    # ON CONFLICT (user_id, ...) hoạt động
    d = db.load_all(s)
    assert len(d["prices"]) >= 1 and d["prices"][0]["price"] == 93000
    h = engine.holdings(d, TODAY)
    assert h["rows"][0]["qty"] == pytest.approx(10.86)
    s.close()


def test_system_price_job_reads_all_users(dsn, monkeypatch):
    """Job GitHub Actions (quyền hệ thống) gom nguồn giá của mọi người dùng, ghi market_prices."""
    from fi_app import prices, sources
    u1, u2 = _user(dsn, "e@example.com"), _user(dsn, "f@example.com")
    for uid, code, src in ((u1, "VESAF", "fmarket"), (u2, "FPT", "vndirect")):
        s = db.connect_cloud(dsn, uid)
        s.x("INSERT INTO assets(code, name, tier, valuation, price_source) VALUES (?, ?, 'Tăng trưởng', 'Thị trường', ?)",
            (code, code, src))
        s.close()
    seen = []

    def fake_fetch(assets, last, today=None, **kw):
        seen.extend(a["code"] for a in assets)
        return [sources.Quote(TODAY, a["code"], 100.0, "fake") for a in assets], ["ok"]

    monkeypatch.setattr(sources, "fetch", fake_fetch)
    conn = psycopg.connect(dsn, row_factory=psycopg.rows.dict_row, prepare_threshold=None)
    res = prices.fetch_auto(db.Store("pg", conn))
    assert {"fmarket:VESAF", "vndirect:FPT"} <= set(seen) and res["saved"] >= 2
    s = db.connect_cloud(dsn, u2)                     # người dùng thấy giá của mã mình qua load_all
    assert any(p["code"] == "FPT" and p["is_manual"] == -1 for p in db.load_all(s)["prices"])
    s.close()


def test_migration_script(dsn, monkeypatch, tmp_path):
    """scripts/len_cloud.py: chuyển SQLite → Supabase, số dòng khớp."""
    import importlib
    uid = _user(dsn, "g@example.com")
    local_path = tmp_path / "local.db"
    loc = db.connect_local(local_path)
    loc.x("INSERT INTO assets(code, name, tier, valuation) VALUES ('X', 'Tài sản X', 'Thu nhập', 'Khai báo')")
    db.add_transaction(loc, "2026-11-01", "X", "Vốn đầu kỳ", amount=5_000_000, price=5_000_000, qty=1)
    loc.market_upsert([("fmarket:DCDS", "2026-11-18", 91155.58, "test")])
    loc.close()
    mig = importlib.import_module("scripts.len_cloud") if (db.APP_DIR / "scripts" / "__init__.py").exists() \
        else importlib.machinery.SourceFileLoader("len_cloud", str(db.APP_DIR / "scripts" / "len_cloud.py")).load_module()
    monkeypatch.setenv("DATABASE_URL", dsn)
    monkeypatch.setattr(mig.db, "connect_local", lambda path=local_path: db.Store.__new__(db.Store) and _open(local_path))
    monkeypatch.setattr("builtins.input", lambda *_: "co")
    mig.main("g@example.com")
    s = db.connect_cloud(dsn, uid)
    assert s.q("SELECT COUNT(*) AS n FROM transactions")[0]["n"] == 1
    assert s.q("SELECT name FROM assets")[0]["name"] == "Tài sản X"
    s.close()


def _open(path):
    import sqlite3
    conn = sqlite3.connect(path)
    conn.row_factory = sqlite3.Row
    return db.Store("sqlite", conn)


def test_delete_my_account_removes_only_own_data(dsn):
    """public.delete_my_account(): xoá user đang đăng nhập + mọi dữ liệu (cascade); người khác còn nguyên; anon bị chặn."""
    a_id, b_id = _user(dsn, "del-a@example.com"), _user(dsn, "del-b@example.com")
    for uid in (a_id, b_id):
        s = db.connect_cloud(dsn, uid)
        s.x("INSERT INTO assets(code, name, tier, valuation) VALUES ('X','X','Tăng trưởng','Khai báo')")
        db.add_transaction(s, "2026-11-19", "X", "Vốn đầu kỳ", price=1000, qty=5)
        s.x("INSERT INTO cashflow_items(name, grp, amount, freq) VALUES ('Lương','Thu nhập chủ động',1,'Tháng')")
        s.close()

    a = db.connect_cloud(dsn, a_id)
    db.delete_my_account(a)
    a.close()
    with psycopg.connect(dsn, autocommit=True) as c:                # kiểm tra bằng quyền hệ thống
        assert c.execute("SELECT count(*) FROM auth.users WHERE id = %s", (a_id,)).fetchone()[0] == 0
        for t in ("assets", "transactions", "cashflow_items", "settings", "assumptions"):
            assert c.execute(f"SELECT count(*) FROM public.{t} WHERE user_id = %s", (a_id,)).fetchone()[0] == 0, t
        assert c.execute("SELECT count(*) FROM public.transactions WHERE user_id = %s", (b_id,)).fetchone()[0] == 1
        assert c.execute("SELECT count(*) FROM auth.users WHERE id = %s", (b_id,)).fetchone()[0] == 1
        with pytest.raises(psycopg.Error):                           # anon không gọi được hàm
            c.execute("SET ROLE anon")
            c.execute("SELECT public.delete_my_account()")
        c.execute("RESET ROLE")


def test_delete_my_account_missing_function_message(dsn):
    uid = _user(dsn, "del-c@example.com")
    s = db.connect_cloud(dsn, uid)
    s.conn.execute("RESET ROLE")
    s.conn.execute("ALTER FUNCTION public.delete_my_account() RENAME TO delete_my_account_tmp")
    s.conn.commit()
    s._set_user_role()
    try:
        with pytest.raises(db.AccountDeleteError, match="xoa_tai_khoan.sql"):
            db.delete_my_account(s)
    finally:
        s.conn.execute("RESET ROLE")
        s.conn.execute("ALTER FUNCTION public.delete_my_account_tmp() RENAME TO delete_my_account")
        s.conn.commit()
        s.close()

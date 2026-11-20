"""Chạy app.py thật ở chế độ cloud với phiên đã đăng nhập (Supabase thay bằng SQLite tạm) và mở mọi trang.

Bắt các lỗi chỉ xuất hiện sau khi đăng nhập, VD StreamlitDuplicateElementKey khi cầu nối ghi nhớ đăng nhập bị
gắn nhiều lần trong một lượt chạy.
"""
import os
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
PAGES = ["tong_quan", "ke_hoach_fire", "lich_su", "giao_dich", "gia", "tai_san", "tiet_kiem", "thu_chi",
         "gioi_thieu", "huong_dan", "sao_luu"]

ENTRY = '''
import pathlib, time, streamlit as st
from fi_app import db, ui
ui.cloud_config = lambda: {"url": "https://x.supabase.co", "anon_key": "anon", "db_url": "postgres://unused"}
def _fake_cloud(dsn, user_id, email=None):
    s = db.connect_local(pathlib.Path(%r))
    s.user_id, s.email = user_id, email
    return s
db.connect_cloud = _fake_cloud
st.session_state.setdefault("auth", {"user_id": "u-1", "email": "toi@example.com", "access_token": "at",
                                     "refresh_token": "rt", "at": time.time()})
exec(compile(open("app.py", encoding="utf-8").read(), "app.py", "exec"))
'''


@pytest.fixture
def entry(tmp_path):
    from fi_app import catalog, db
    dbfile = tmp_path / "c.db"
    s = db.connect_local(dbfile)
    catalog.add(s, catalog.build("fund", "DCDS", "Quỹ mở cổ phiếu DCDS"))
    s.market_upsert([("fmarket:DCDS", "2026-11-19", 90000.0, "t")])
    db.set_opening(s, "DCDS", 100, 80000, "2026-11-01")
    db.set_kv(s, "meta", {"last_auto_fetch": "2099-01-01T00:00:00"})     # không gọi mạng lấy giá
    f = ROOT / f"_test_entry_{os.getpid()}.py"                          # cùng thư mục app.py để tìm views/
    f.write_text(ENTRY % str(dbfile), encoding="utf-8")
    from fi_app import ui
    saved = (db.connect_cloud, ui.cloud_config)          # script test thay 2 hàm này → khôi phục cho test khác
    try:
        yield f
    finally:
        db.connect_cloud, ui.cloud_config = saved
        f.unlink(missing_ok=True)


def test_all_pages_render_when_logged_in(entry):
    from streamlit.testing.v1 import AppTest
    cwd = os.getcwd()
    os.chdir(ROOT)
    try:
        at = AppTest.from_file(str(entry), default_timeout=90).run()
        assert not at.exception, at.exception[0].value
        for p in PAGES:
            at.switch_page(f"views/{p}.py").run()
            assert not at.exception, f"{p}: {at.exception[0].value}"
    finally:
        os.chdir(cwd)


@pytest.mark.parametrize("google", [True, False])
def test_login_screen_shows_intro_and_promise(tmp_path, google):
    """Chưa đăng nhập: màn hình đăng nhập có phần giới thiệu ngắn và cam kết không khuyến nghị đầu tư."""
    from streamlit.testing.v1 import AppTest
    from fi_app import db, ui
    f = ROOT / f"_test_login_{os.getpid()}.py"
    f.write_text('''
import streamlit as st
from fi_app import ui
ui.cloud_config = lambda: {"url": "https://x.supabase.co", "anon_key": "anon", "db_url": "postgres://unused",
                           "google": %s, "allow_signup": True, "site_url": "https://app.example"}
st.session_state["_bridge_skip"] = True          # trong test không có trình duyệt chạy JS cầu nối
exec(compile(open("app.py", encoding="utf-8").read(), "app.py", "exec"))
''' % google, encoding="utf-8")
    saved = (db.connect_cloud, ui.cloud_config)
    cwd = os.getcwd()
    os.chdir(ROOT)
    try:
        at = AppTest.from_file(str(f), default_timeout=60).run()
        assert not at.exception, at.exception[0].value
        page = " ".join(str(getattr(e, "value", "")) for e in at.main)
        texts = [m.value for m in at.markdown] + [c.value for c in at.caption]
        assert any("Nhìn rõ con đường" in t for t in texts)
        assert any(x.label.startswith("Về Hành trình FIRE") for x in at.expander)
        assert page is not None
        assert any("tạo tài khoản mới" in t for t in texts)                    # đang mở đăng ký
        links = [b.proto.label for b in at.get("link_button")]
        assert ("Đăng nhập bằng Google" in links) is google
    finally:
        db.connect_cloud, ui.cloud_config = saved
        os.chdir(cwd)
        f.unlink(missing_ok=True)

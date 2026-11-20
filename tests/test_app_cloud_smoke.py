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


def _entry(tmp_path, seed: bool):
    from fi_app import catalog, db, ui
    dbfile = tmp_path / "c.db"
    s = db.connect_local(dbfile)
    if seed:
        catalog.add(s, catalog.build("fund", "DCDS", "Quỹ mở cổ phiếu DCDS"))
        s.market_upsert([("fmarket:DCDS", "2026-11-19", 90000.0, "t")])
        db.set_opening(s, "DCDS", 100, 80000, "2026-11-01")
    db.set_kv(s, "meta", {"last_auto_fetch": "2099-01-01T00:00:00"})     # không gọi mạng lấy giá
    s.close()
    f = ROOT / f"_test_entry_{os.getpid()}.py"                          # cùng thư mục app.py để tìm views/
    f.write_text(ENTRY % str(dbfile), encoding="utf-8")
    saved = (db.connect_cloud, ui.cloud_config)          # script test thay 2 hàm này → khôi phục cho test khác
    try:
        yield f, dbfile
    finally:
        db.connect_cloud, ui.cloud_config = saved
        f.unlink(missing_ok=True)


@pytest.fixture
def entry(tmp_path):
    for f, _ in _entry(tmp_path, seed=True):
        yield f


@pytest.fixture
def seeded(tmp_path):
    yield from _entry(tmp_path, seed=True)


@pytest.fixture
def empty_entry(tmp_path):
    for f, _ in _entry(tmp_path, seed=False):
        yield f


def _run(f):
    from streamlit.testing.v1 import AppTest
    return AppTest.from_file(str(f), default_timeout=90).run()


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


def test_new_user_sees_5_step_onboarding(empty_entry):
    cwd = os.getcwd()
    os.chdir(ROOT)
    try:
        at = _run(empty_entry)
        assert not at.exception, at.exception[0].value
        html = " ".join(str(h.proto.body) for h in at.get("html"))
        assert "Đã xong" in html and "0/5" in html and "Khai hồ sơ thu chi" in html
        assert "Thiết lập trong 5 bước" in " ".join(x.value for x in at.subheader)
    finally:
        os.chdir(cwd)


def test_onboarding_can_be_hidden_and_health_shown(seeded):
    from fi_app import db
    f, dbfile = seeded
    cwd = os.getcwd()
    os.chdir(ROOT)
    try:
        at = _run(f)
        assert not at.exception, at.exception[0].value
        assert any(x.label == "Hoàn tất thiết lập" for x in at.expander)       # chưa khai thu chi → chưa xong
        at.button(key="ic-circle-x-ob_hide").click().run()
        assert not at.exception, at.exception[0].value
        assert not any(x.label == "Hoàn tất thiết lập" for x in at.expander)
        assert db.kv(db.connect_local(dbfile), "settings").get("onboarding_hidden") == "1"
        at.switch_page("views/ke_hoach_fire.py").run()
        assert not at.exception, at.exception[0].value
        assert any("Sức khoẻ tài chính" in x.value for x in at.subheader)
        assert "Chưa đủ dữ liệu" in " ".join(str(h.proto.body) for h in at.get("html"))
    finally:
        os.chdir(cwd)


def test_celebration_ack_and_intro_tabs(seeded):
    import json
    from fi_app import db
    f, dbfile = seeded
    cwd = os.getcwd()
    os.chdir(ROOT)
    try:
        at = _run(f)
        assert not at.exception, at.exception[0].value
        html = " ".join(str(h.proto.body) for h in at.get("html"))
        assert "Chúc mừng – mốc mới!" in html and "Tài sản đầu tiên" in html
        assert any(x.label == "Thành tựu của bạn" for x in at.expander)
        at.button(key="ic-trophy-ms_ack").click().run()
        assert not at.exception, at.exception[0].value
        assert "Chúc mừng – mốc mới!" not in " ".join(str(h.proto.body) for h in at.get("html"))
        seen = json.loads(db.kv(db.connect_local(dbfile), "settings")["milestones_seen"])
        assert "setup_asset" in seen and "fire_1" not in seen
        at.switch_page("views/thu_chi.py").run()
        assert not at.exception, at.exception[0].value
        assert any("Nền tảng tài chính" in x.value for x in at.subheader)
        assert sum(x.label[:1].isdigit() and " · " in x.label for x in at.expander) == 5
        at.switch_page("views/tiet_kiem.py").run()
        assert not at.exception, at.exception[0].value
        assert any("quỹ khẩn cấp" in x.value for x in at.subheader)
        assert sum(x.label[:1].isdigit() and " · " in x.label for x in at.expander) == 4
        at.switch_page("views/gioi_thieu.py").run()
        assert not at.exception, at.exception[0].value
        assert [t.label for t in at.tabs] == ["Về app", "Tính năng", "Câu chuyện", "Hành trình", "Ví dụ tính", "Hỏi đáp"]
        assert "Giá tự cập nhật mỗi ngày" in " ".join(str(h.proto.body) for h in at.get("html"))
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
        assert any("?doc=privacy" in str(h.proto.body) for h in at.get("html"))  # trang chủ có link chính sách
        links = [b.proto.label for b in at.get("link_button")]
        assert ("Đăng nhập bằng Google" in links) is google
    finally:
        db.connect_cloud, ui.cloud_config = saved
        os.chdir(cwd)
        f.unlink(missing_ok=True)


@pytest.mark.parametrize("doc,title", [("privacy", "Chính sách quyền riêng tư"), ("terms", "Điều khoản sử dụng")])
@pytest.mark.parametrize("email", ["lienhe@example.com", ""])
def test_public_legal_pages_without_login(doc, title, email):
    """?doc=privacy / ?doc=terms mở được khi CHƯA đăng nhập (Google OAuth yêu cầu), không hiện form đăng nhập."""
    from streamlit.testing.v1 import AppTest
    f = ROOT / f"_test_doc_{os.getpid()}.py"
    f.write_text('''
import streamlit as st
st.query_params["doc"] = %r
exec(compile(open("app.py", encoding="utf-8").read(), "app.py", "exec"))
''' % doc, encoding="utf-8")
    cwd = os.getcwd()
    os.chdir(ROOT)
    try:
        secrets = {"supabase": {"url": "https://x.supabase.co", "anon_key": "anon", "db_url": "postgres://unused",
                                "site_url": "https://app.example", "contact_email": email}}
        at = AppTest.from_file(str(f), default_timeout=60)
        for k, v in secrets.items():
            at.secrets[k] = v
        at.run()
        assert not at.exception, at.exception[0].value
        body = " ".join(m.value for m in at.markdown)
        html = " ".join(str(h.proto.body) for h in at.get("html"))
        assert title in html
        assert "Gửi mã đăng nhập" not in " ".join(b.label for b in at.button)      # không có form đăng nhập
        assert (email in body) if email else ("người quản trị app" in body)
        assert "https://app.example/?doc=" in html                                # link tuyệt đối, mở cửa sổ chính
        if doc == "terms":
            assert "Không khuyến nghị" in body
    finally:
        os.chdir(cwd)
        f.unlink(missing_ok=True)

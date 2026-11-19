"""Ghi nhớ đăng nhập: refresh token trong cookie → tự đăng nhập lại; đăng xuất → thu hồi + xoá cookie.

Giả lập Supabase Auth (requests.post) và Streamlit (session_state, context.cookies, html).
"""
import sys
import types
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from fi_app import auth  # noqa: E402

CFG = {"url": "https://x.supabase.co", "anon_key": "anon"}


class Resp:
    def __init__(self, status, body):
        self.status_code, self._body = status, body

    @property
    def ok(self):
        return 200 <= self.status_code < 300

    def json(self):
        return self._body

    text = ""


class FakeSupabase:
    """Refresh token xoay vòng: mỗi lần dùng cấp token mới, token cũ bị vô hiệu."""

    def __init__(self):
        self.valid = {"rt-1": "u-1"}
        self.calls = []
        self.n = 1

    def post(self, url, json=None, headers=None, timeout=None):
        self.calls.append(url)
        if "grant_type=refresh_token" in url:
            uid = self.valid.pop(json["refresh_token"], None)
            if not uid:
                return Resp(400, {"error": "invalid_grant", "error_description": "Invalid Refresh Token"})
            self.n += 1
            new = f"rt-{self.n}"
            self.valid[new] = uid
            return Resp(200, {"access_token": f"at-{self.n}", "refresh_token": new,
                              "user": {"id": uid, "email": "toi@example.com"}})
        if "/logout" in url:
            self.valid.clear()                     # thu hồi phiên
            return Resp(204, {})
        raise AssertionError(url)


@pytest.fixture
def env(monkeypatch):
    sb = FakeSupabase()
    fake_st = types.SimpleNamespace(session_state={}, context=types.SimpleNamespace(cookies={}), rendered=[])
    fake_st.html = lambda body, unsafe_allow_javascript=False: fake_st.rendered.append(body)
    monkeypatch.setattr(auth, "st", fake_st)
    monkeypatch.setattr(auth.requests, "post", sb.post)
    return sb, fake_st


def test_restore_from_cookie_rotates_token(env):
    sb, st = env
    st.context.cookies = {auth.COOKIE: "rt-1"}
    assert auth.restore(CFG) is True
    assert st.session_state["auth"]["user_id"] == "u-1"
    auth.flush_cookie()
    assert "rt-2" in st.rendered[-1] and "Max-Age=2592000" in st.rendered[-1]   # cookie mới, 30 ngày
    assert "rt-1" not in sb.valid                                                 # token cũ đã vô hiệu


def test_restore_only_once_per_session(env):
    sb, st = env
    st.context.cookies = {auth.COOKIE: "rt-1"}
    auth.restore(CFG)
    st.session_state.pop("auth")
    assert auth.restore(CFG) is False                     # không gọi lại Supabase trong cùng phiên
    assert sum("refresh_token" in c for c in sb.calls) == 1


def test_invalid_cookie_is_cleared(env):
    sb, st = env
    st.context.cookies = {auth.COOKIE: "rt-hết-hạn"}
    assert auth.restore(CFG) is False
    assert "auth" not in st.session_state
    auth.flush_cookie()
    assert "Max-Age=0" in st.rendered[-1]


def test_no_cookie_no_call(env):
    sb, st = env
    assert auth.restore(CFG) is False and sb.calls == []


def test_logout_revokes_and_blocks_auto_relogin(env):
    sb, st = env
    st.context.cookies = {auth.COOKIE: "rt-1"}
    auth.restore(CFG)
    auth.flush_cookie()
    auth.logout(CFG)
    assert any("/logout" in c for c in sb.calls) and not sb.valid      # phiên bị thu hồi trên Supabase
    assert "auth" not in st.session_state
    st.session_state.pop("_restore_tried")
    assert auth.restore(CFG) is False                                  # cookie cũ trong phiên này bị bỏ qua
    auth.flush_cookie()
    assert "Max-Age=0" in st.rendered[-1]                              # cookie bị xoá


def test_cookie_js_escapes_value(env):
    sb, st = env
    auth._queue_cookie("abc';alert(1);//")
    auth.flush_cookie()
    assert "\"abc';alert(1);//\"" in st.rendered[-1]                  # giá trị nằm trong chuỗi JSON

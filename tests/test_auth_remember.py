"""Ghi nhớ đăng nhập: refresh token trong localStorage (qua component cầu nối) → tự đăng nhập lại;
đăng xuất → thu hồi + xoá token.

Giả lập Supabase Auth (requests.post), trình duyệt và Streamlit.
"""
import contextlib
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


class FakeBrowser:
    """localStorage của trình duyệt + component cầu nối (thay st.components.v2)."""

    def __init__(self):
        self.storage = {}
        self.data_seen = []

    def component(self, name, js=None):
        def render(key=None, data=None, on_rt_change=None, on_pkce_change=None):
            self.data_seen.append(data)
            before = types.SimpleNamespace(rt=self.storage.get(auth.COOKIE, ""),
                                           pkce=self.storage.get(auth.PKCE_KEY, ""))
            for k, name in ((auth.COOKIE, "rt"), (auth.PKCE_KEY, "pkce")):
                op = (data or {}).get(name)
                if op and op.get("op") == "set":
                    self.storage[k] = op["value"]
                if op and op.get("op") == "clear":
                    self.storage.pop(k, None)
            return before                 # như JS thật: báo giá trị TRƯỚC khi ghi lệnh mới
        return render


@pytest.fixture
def env(monkeypatch):
    sb = FakeSupabase()
    br = FakeBrowser()
    fake_st = types.SimpleNamespace(session_state={}, context=types.SimpleNamespace(cookies={}),
                                    components=types.SimpleNamespace(v2=types.SimpleNamespace(component=br.component)),
                                    container=lambda key=None: contextlib.nullcontext())
    monkeypatch.setattr(auth, "st", fake_st)
    monkeypatch.setattr(auth, "_bridge_renderer", None)
    monkeypatch.setattr(auth.requests, "post", sb.post)
    return sb, fake_st, br


def test_restore_from_browser_rotates_token(env):
    sb, st, br = env
    br.storage[auth.COOKIE] = "rt-1"
    token = auth.bridge()
    assert token == "rt-1"
    assert auth.restore(CFG, token) is True
    assert st.session_state["auth"]["user_id"] == "u-1"
    auth.bridge()                                              # lượt chạy sau: lưu token mới
    assert br.storage[auth.COOKIE] == "rt-2" and "rt-1" not in sb.valid


def test_restore_only_once_per_session(env):
    sb, st, br = env
    br.storage[auth.COOKIE] = "rt-1"
    auth.restore(CFG, auth.bridge())
    st.session_state.pop("auth")
    assert auth.restore(CFG, "rt-2") is False                  # không gọi lại Supabase trong cùng phiên
    assert sum("refresh_token" in c for c in sb.calls) == 1


def test_invalid_token_is_cleared(env):
    sb, st, br = env
    br.storage[auth.COOKIE] = "rt-hết-hạn"
    assert auth.restore(CFG, auth.bridge()) is False
    assert "auth" not in st.session_state
    auth.bridge()
    assert auth.COOKIE not in br.storage


def test_no_token_no_call(env):
    sb, st, br = env
    assert auth.bridge() == ""
    assert auth.restore(CFG, "") is False and sb.calls == []


def test_login_with_remember_saves_token(env):
    sb, st, br = env
    auth._queue_cookie("rt-1")                                 # như sau khi nhập mã có tick Ghi nhớ
    auth.bridge()
    assert br.storage[auth.COOKIE] == "rt-1"


def test_logout_revokes_and_clears_browser(env):
    sb, st, br = env
    br.storage[auth.COOKIE] = "rt-1"
    auth.restore(CFG, auth.bridge())
    auth.bridge()
    auth.logout(CFG)
    assert any("/logout" in c for c in sb.calls) and not sb.valid      # phiên bị thu hồi trên Supabase
    assert "auth" not in st.session_state
    st.session_state.pop("_restore_tried")
    assert auth.restore(CFG, "rt-2") is False                          # đã đăng xuất → không tự đăng nhập lại
    auth.bridge()
    assert auth.COOKIE not in br.storage                               # token bị xoá khỏi trình duyệt


def test_cookie_fallback_when_running_locally(env):
    sb, st, br = env
    st.context.cookies = {auth.COOKIE: "rt-1"}                         # chạy trên máy: cookie cũ vẫn tới server
    assert auth.restore(CFG, "") is True

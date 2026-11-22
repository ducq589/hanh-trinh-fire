"""Đăng nhập Google (Supabase OAuth + PKCE) và tự đăng ký bằng email."""
import base64
import contextlib
import hashlib
import sys
import types
from pathlib import Path
from urllib.parse import parse_qs, urlsplit

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from fi_app import auth  # noqa: E402
from tests.test_auth_remember import FakeBrowser, Resp  # noqa: E402

CFG = {"url": "https://x.supabase.co", "anon_key": "anon", "google": True, "site_url": "https://app.example"}


class QP(dict):
    """Giả st.query_params."""


class FakeSupabase:
    def __init__(self):
        self.codes = {}          # code → (challenge, user_id)
        self.calls = []

    def post(self, url, json=None, headers=None, timeout=None):
        self.calls.append((url, json))
        if "grant_type=pkce" in url:
            entry = self.codes.pop(json["auth_code"], None)
            if not entry:
                return Resp(400, {"error": "invalid_grant"})
            challenge, uid = entry
            got = base64.urlsafe_b64encode(hashlib.sha256(json["code_verifier"].encode()).digest()).rstrip(b"=").decode()
            if got != challenge:
                return Resp(400, {"error": "invalid_grant", "error_description": "code verifier mismatch"})
            return Resp(200, {"access_token": "at-g", "refresh_token": "rt-g", "user": {"id": uid, "email": "g@gmail.com"}})
        if url.endswith("/otp"):
            return Resp(200, {})
        raise AssertionError(url)


@pytest.fixture
def env(monkeypatch):
    sb, br = FakeSupabase(), FakeBrowser()
    fake_st = types.SimpleNamespace(session_state={}, query_params=QP(),
                                    context=types.SimpleNamespace(cookies={}, url="https://app.example/"),
                                    components=types.SimpleNamespace(v2=types.SimpleNamespace(component=br.component)),
                                    container=lambda key=None: contextlib.nullcontext())
    monkeypatch.setattr(auth, "st", fake_st)
    monkeypatch.setattr(auth, "_bridge_renderer", None)
    monkeypatch.setattr(auth.requests, "post", sb.post)
    return sb, fake_st, br


def test_pkce_pair_is_s256():
    v, c = auth.pkce_pair()
    assert 43 <= len(v) <= 128
    assert c == base64.urlsafe_b64encode(hashlib.sha256(v.encode()).digest()).rstrip(b"=").decode()


def test_google_full_flow(env):
    sb, st, br = env
    # Tab 1: màn đăng nhập – tạo mã PKCE, lưu vào trình duyệt, dựng link Google
    auth.prepare_google(CFG)
    auth.bridge()
    verifier, challenge = st.session_state["_pkce_verifier"], st.session_state["_pkce_challenge"]
    assert br.storage[auth.PKCE_KEY] == verifier
    q = parse_qs(urlsplit(auth.google_url(CFG, challenge)).query)
    assert q["provider"] == ["google"] and q["redirect_to"] == ["https://app.example"]
    assert q["code_challenge"] == [challenge] and q["code_challenge_method"] == ["s256"]
    # Google xác nhận → Supabase cấp code; quay về app ở phiên MỚI (tab mới) với ?code=
    sb.codes["c-1"] = (challenge, "u-g")
    st.session_state.clear()
    st.query_params.update(code="c-1")
    auth.prepare_google(CFG)                       # đang quay về → không tạo mã mới đè lên
    assert "_pkce_op" not in st.session_state
    auth.bridge()                                  # trình duyệt báo mã PKCE đã lưu
    assert auth.handle_google_return(CFG) is True
    assert st.session_state["auth"]["user_id"] == "u-g" and not st.query_params
    auth.bridge()                                  # lượt sau: lưu token ghi nhớ, xoá mã PKCE
    assert br.storage[auth.COOKIE] == "rt-g" and auth.PKCE_KEY not in br.storage


def test_google_return_wrong_or_missing_verifier(env):
    sb, st, br = env
    sb.codes["c-2"] = ("thach-thuc-khac", "u-g")
    br.storage[auth.PKCE_KEY] = "verifier-sai"
    st.query_params.update(code="c-2")
    auth.bridge()
    assert auth.handle_google_return(CFG) is False
    assert "auth" not in st.session_state and "không thành công" in st.session_state["_google_error"]
    st.session_state.clear(); br.storage.clear()
    st.query_params.update(code="c-3")
    auth.bridge()
    assert auth.handle_google_return(CFG) is False
    assert "Không tìm thấy mã xác thực" in st.session_state["_google_error"]


def test_google_error_param(env):
    sb, st, br = env
    st.query_params.update(error="access_denied", error_description="User cancelled")
    assert auth.handle_google_return(CFG) is False
    assert "User cancelled" in st.session_state["_google_error"] and not st.query_params


def test_google_disabled_no_pkce(env):
    sb, st, br = env
    auth.prepare_google({**CFG, "google": False})
    assert "_pkce_verifier" not in st.session_state


@pytest.mark.parametrize("flag", [True, False])
def test_send_code_respects_allow_signup(env, flag):
    sb, st, br = env
    assert auth.send_code({**CFG, "allow_signup": flag}, "moi@example.com") is None
    assert sb.calls[-1][1]["create_user"] is flag


def test_in_app_browser_detection():
    """Zalo/Facebook/Messenger: Google chặn OAuth → app nhắc mở bằng Chrome/Safari."""
    zalo = "Mozilla/5.0 (iPhone; CPU iPhone OS 18_0 like Mac OS X) AppleWebKit/605.1.15 Mobile/15E148 Zalo iOS/600"
    fb = "Mozilla/5.0 (Linux; Android 14) AppleWebKit/537.36 Chrome/131 Mobile [FB_IAB/FB4A;FBAV/480.0]"
    safari = "Mozilla/5.0 (iPhone; CPU iPhone OS 18_0 like Mac OS X) AppleWebKit/605.1.15 Version/18.0 Mobile Safari/604.1"
    chrome = "Mozilla/5.0 (Linux; Android 14) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0 Mobile Safari/537.36"
    assert auth.in_app_browser(zalo) and auth.in_app_browser(fb)
    assert not auth.in_app_browser(safari) and not auth.in_app_browser(chrome) and not auth.in_app_browser("")

"""Đăng nhập bằng email + mã OTP 6 số (Supabase Auth). Chỉ dùng ở chế độ cloud."""
from __future__ import annotations

import json
import re
import time
from urllib.parse import unquote

import requests
import streamlit as st

EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")
COOKIE = "fire_rt"                  # refresh token Supabase, lưu trên trình duyệt để ghi nhớ đăng nhập
REMEMBER_DAYS = 30


def _post(cfg: dict, path: str, body: dict) -> requests.Response:
    return requests.post(f"{cfg['url'].rstrip('/')}/auth/v1/{path}", json=body, timeout=20,
                         headers={"apikey": cfg["anon_key"], "Content-Type": "application/json"})


def _err(r: requests.Response) -> str:
    try:
        j = r.json()
        msg = j.get("msg") or j.get("error_description") or j.get("message") or j.get("error") or r.text
    except ValueError:
        msg = r.text
    low = str(msg).lower()
    if "signups not allowed" in low or "user not found" in low:
        return "Email này chưa được cấp quyền dùng app. Hãy liên hệ người quản trị."
    if "rate limit" in low or r.status_code == 429:
        return "Gửi mã quá nhiều lần – vui lòng đợi vài phút rồi thử lại."
    if "expired" in low or "invalid" in low:
        return "Mã không đúng hoặc đã hết hạn. Hãy gửi lại mã mới."
    return f"Lỗi đăng nhập ({r.status_code}): {msg}"


def send_code(cfg: dict, email: str) -> str | None:
    r = _post(cfg, "otp", {"email": email, "create_user": bool(cfg.get("allow_signup", False))})
    return None if r.ok else _err(r)


def _session(j: dict, email: str = "") -> dict | None:
    user = j.get("user") or {}
    if not user.get("id"):
        return None
    return {"user_id": user["id"], "email": user.get("email", email), "access_token": j.get("access_token"),
            "refresh_token": j.get("refresh_token"), "at": time.time()}


def verify_code(cfg: dict, email: str, code: str) -> tuple[dict | None, str | None]:
    r = _post(cfg, "verify", {"type": "email", "email": email, "token": code.strip()})
    if not r.ok:
        return None, _err(r)
    auth = _session(r.json(), email)
    return (auth, None) if auth else (None, "Không nhận được thông tin người dùng.")


def refresh(cfg: dict, refresh_token: str) -> dict | None:
    """Đổi refresh token lấy phiên mới (Supabase cấp refresh token mới, token cũ hết hiệu lực)."""
    try:
        r = _post(cfg, "token?grant_type=refresh_token", {"refresh_token": refresh_token})
        return _session(r.json()) if r.ok else None
    except (requests.RequestException, ValueError, TypeError):
        return None


def revoke(cfg: dict, access_token: str | None) -> None:
    """Thu hồi phiên trên Supabase (refresh token của phiên này không dùng lại được nữa)."""
    if not access_token:
        return
    try:
        requests.post(f"{cfg['url'].rstrip('/')}/auth/v1/logout?scope=local", timeout=10,
                      headers={"apikey": cfg["anon_key"], "Authorization": f"Bearer {access_token}"})
    except requests.RequestException:
        pass


# ---------------------------------------------------------------- cookie ghi nhớ đăng nhập
def _queue_cookie(value: str | None) -> None:
    """Hẹn ghi (value) hoặc xoá (None) cookie ở lượt vẽ trang tiếp theo."""
    st.session_state["_cookie_op"] = ("set", value) if value else ("clear", None)


def flush_cookie() -> None:
    """Chạy đoạn JS ghi/xoá cookie trên trang chính (gọi 1 lần mỗi lượt chạy)."""
    op = st.session_state.pop("_cookie_op", None)
    if not op:
        return
    kind, value = op
    if kind == "set":
        js = (f"var v={json.dumps(value)};var s=location.protocol==='https:'?';Secure':'';"
              f"document.cookie='{COOKIE}='+encodeURIComponent(v)+';Path=/;Max-Age={REMEMBER_DAYS * 86400};"
              f"SameSite=Strict'+s;")
    else:
        js = f"document.cookie='{COOKIE}=;Path=/;Max-Age=0;SameSite=Strict';"
    st.html(f"<script>{js}</script>", unsafe_allow_javascript=True)


def restore(cfg: dict) -> bool:
    """Lần đầu trong phiên: nếu trình duyệt có cookie ghi nhớ, tự đăng nhập lại. Trả về True nếu thành công."""
    if st.session_state.get("_restore_tried") or st.session_state.get("_logged_out"):
        return False
    st.session_state["_restore_tried"] = True
    try:
        raw = st.context.cookies.get(COOKIE)
    except Exception:
        raw = None
    if not isinstance(raw, str) or not raw.strip():
        return False
    auth = refresh(cfg, unquote(raw).strip())
    if not auth:
        _queue_cookie(None)            # token hết hạn / đã thu hồi → xoá cookie
        return False
    st.session_state["auth"] = auth
    _queue_cookie(auth["refresh_token"])   # lưu token mới (token cũ đã bị Supabase vô hiệu)
    return True


def login_screen(cfg: dict) -> None:
    """Vẽ màn hình đăng nhập; khi thành công lưu st.session_state['auth'] và chạy lại."""
    st.markdown("<style>[data-testid='stSidebar'],[data-testid='stSidebarCollapsedControl']{display:none}</style>"
                "<div style='height:6vh'></div>", unsafe_allow_html=True)
    _, mid, _ = st.columns([1, 2, 1])
    with mid:
        st.title("🔥 Hành trình FIRE")
        st.caption("Đăng nhập bằng email – không cần mật khẩu. Mã 6 số sẽ được gửi vào hộp thư của bạn.")
        step = st.session_state.get("_login_step", "email")
        if step == "email":
            with st.form("login_email"):
                email = st.text_input("Email", placeholder="ban@example.com").strip().lower()
                if st.form_submit_button("Gửi mã đăng nhập", type="primary", width="stretch"):
                    if not EMAIL_RE.match(email):
                        st.error("Email không hợp lệ.")
                    else:
                        err = send_code(cfg, email)
                        if err:
                            st.error(err)
                        else:
                            st.session_state["_login_email"] = email
                            st.session_state["_login_step"] = "code"
                            st.rerun()
        else:
            email = st.session_state.get("_login_email", "")
            st.info(f"Đã gửi mã tới **{email}**. Kiểm tra cả hộp thư Spam/Quảng cáo.")
            with st.form("login_code"):
                code = st.text_input("Mã đăng nhập (6 số)", max_chars=10)
                remember = st.checkbox(f"Ghi nhớ đăng nhập trên thiết bị này ({REMEMBER_DAYS} ngày)", value=True,
                                       help="Bỏ chọn nếu đang dùng máy tính/điện thoại của người khác.")
                if st.form_submit_button("Đăng nhập", type="primary", width="stretch"):
                    auth, err = verify_code(cfg, email, code)
                    if err:
                        st.error(err)
                    else:
                        st.session_state["auth"] = auth
                        st.session_state.pop("_login_step", None)
                        st.session_state.pop("_logged_out", None)
                        if remember and auth.get("refresh_token"):
                            _queue_cookie(auth["refresh_token"])
                        st.rerun()
            if st.button("← Dùng email khác / gửi lại mã"):
                st.session_state["_login_step"] = "email"
                st.rerun()
        st.caption("Dữ liệu của mỗi tài khoản được tách riêng; người khác không xem được dữ liệu của bạn.")
        with st.expander("Lần đầu dùng app? Xem cách đăng nhập"):
            from . import style
            st.html(style.steps([
                ("Nhập email", "Email phải được người quản trị cấp quyền trước. Bấm <b>Gửi mã đăng nhập</b>."),
                ("Mở Gmail", "Tìm email <b>“Mã đăng nhập Hành trình FIRE”</b> (xem cả Spam) và lấy mã 6 số."),
                ("Nhập mã", "Giữ ô <b>Ghi nhớ đăng nhập</b> để lần sau vào thẳng, rồi bấm <b>Đăng nhập</b>."),
                ("Sau khi vào", "Mở <b>Hệ thống → Hướng dẫn</b> để xem các bước thiết lập và sử dụng."),
            ]))


def logout(cfg: dict | None = None) -> None:
    """Đăng xuất: thu hồi phiên trên Supabase, xoá cookie ghi nhớ, xoá trạng thái phiên."""
    a = st.session_state.get("auth") or {}
    if cfg:
        revoke(cfg, a.get("access_token"))
    for k in ("auth", "_store", "_startup_done", "_login_step", "_login_email"):
        st.session_state.pop(k, None)
    st.session_state["_logged_out"] = True      # không tự đăng nhập lại bằng cookie cũ trong phiên này
    _queue_cookie(None)

"""Đăng nhập bằng email + mã OTP 6 số (Supabase Auth). Chỉ dùng ở chế độ cloud."""
from __future__ import annotations

import re
import time

import requests
import streamlit as st

EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")


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


def verify_code(cfg: dict, email: str, code: str) -> tuple[dict | None, str | None]:
    r = _post(cfg, "verify", {"type": "email", "email": email, "token": code.strip()})
    if not r.ok:
        return None, _err(r)
    j = r.json()
    user = j.get("user") or {}
    if not user.get("id"):
        return None, "Không nhận được thông tin người dùng."
    return {"user_id": user["id"], "email": user.get("email", email), "access_token": j.get("access_token"),
            "refresh_token": j.get("refresh_token"), "at": time.time()}, None


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
                if st.form_submit_button("Đăng nhập", type="primary", width="stretch"):
                    auth, err = verify_code(cfg, email, code)
                    if err:
                        st.error(err)
                    else:
                        st.session_state["auth"] = auth
                        st.session_state.pop("_login_step", None)
                        st.rerun()
            if st.button("← Dùng email khác / gửi lại mã"):
                st.session_state["_login_step"] = "email"
                st.rerun()
        st.caption("Dữ liệu của mỗi tài khoản được tách riêng; người khác không xem được dữ liệu của bạn.")


def logout() -> None:
    for k in ("auth", "_store", "_startup_done", "_login_step", "_login_email"):
        st.session_state.pop(k, None)

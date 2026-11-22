"""Đăng nhập (Supabase Auth): Google là cách chính; email + mã OTP 6 số cho người không dùng Gmail. Chỉ ở chế độ cloud."""
from __future__ import annotations

import base64
import hashlib
import re
import secrets
import time
from urllib.parse import quote, unquote, urlencode, urlsplit

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
        return "Email này chưa có tài khoản và app đang tạm đóng đăng ký mới. Hãy liên hệ người quản trị."
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


# ---------------------------------------------------------------- ghi nhớ đăng nhập
# Refresh token lưu ở localStorage của trình duyệt, chuyển qua lại bằng một component JS nhỏ (st.components.v2).
# Không dùng cookie vì Streamlit Community Cloud không chuyển cookie của app tới server (st.context.cookies trống).
PKCE_KEY = "fire_pkce"              # mã bí mật PKCE khi đăng nhập Google (dùng 1 lần)
_BRIDGE_JS = """
export default function(component) {
  const { data, setStateValue } = component;
  const RT = '%s', PK = '%s';
  const get = (k) => { try { return localStorage.getItem(k); } catch (e) { return null; } };
  const put = (k, op) => {
    try {
      if (!op) return;
      if (op.op === 'set' && op.value) localStorage.setItem(k, op.value);
      if (op.op === 'clear') {
        localStorage.removeItem(k);
        if (k === RT) document.cookie = RT + '=;Path=/;Max-Age=0;SameSite=Strict';
      }
    } catch (e) {}
  };
  // Báo cho Python 1 lần mỗi lần tải trang – giá trị TRƯỚC khi ghi lệnh mới (tab quay về từ Google giữ đúng mã)
  if (!window.__fireRtReported) {
    window.__fireRtReported = true;
    let rt = get(RT);
    if (!rt) {                                   // chuyển từ cookie cũ (bản trước) sang localStorage
      const m = document.cookie.match(new RegExp('(?:^|; )' + RT + '=([^;]*)'));
      if (m && m[1]) { rt = decodeURIComponent(m[1]); try { localStorage.setItem(RT, rt); } catch (e) {} }
    }
    setStateValue('pkce', get(PK) || '');
    setStateValue('rt', rt || '');
  }
  put(RT, data && data.rt);
  put(PK, data && data.pkce);
}
""" % (COOKIE, PKCE_KEY)
_bridge_renderer = None


def _op(value: str | None) -> tuple:
    return ("set", value) if value else ("clear", None)


def _queue_cookie(value: str | None) -> None:
    """Hẹn ghi (value) hoặc xoá (None) token ghi nhớ ở lượt vẽ trang tiếp theo."""
    st.session_state["_cookie_op"] = _op(value)


def _queue_pkce(value: str | None) -> None:
    st.session_state["_pkce_op"] = _op(value)


def _op_data(op) -> dict | None:
    if not op:
        return None
    return {"op": "set", "value": op[1]} if op[0] == "set" else {"op": "clear"}


def bridge() -> str | None:
    """Gắn component cầu nối (mỗi lượt chạy 1 lần): thực hiện lệnh ghi/xoá đang hẹn và trả về token trình duyệt
    đang giữ – None nếu trình duyệt chưa báo (lượt chạy đầu tiên), '' nếu không có.
    Mã PKCE (đăng nhập Google) trình duyệt đang giữ được đặt vào st.session_state['_bridge_pkce']."""
    global _bridge_renderer
    if _bridge_renderer is None:
        _bridge_renderer = st.components.v2.component("fire_auth_bridge", js=_BRIDGE_JS)
    rt_op, pk_op = st.session_state.pop("_cookie_op", None), st.session_state.pop("_pkce_op", None)
    data = {"rt": _op_data(rt_op), "pkce": _op_data(pk_op)} if (rt_op or pk_op) else None
    with st.container(key="fire_auth_bridge_box"):
        res = _bridge_renderer(key="fire_auth_bridge", data=data, on_rt_change=lambda: None,
                               on_pkce_change=lambda: None)
    pk = getattr(res, "pkce", None)
    if isinstance(pk, str):
        st.session_state["_bridge_pkce"] = pk
    rt = getattr(res, "rt", None)
    return rt if isinstance(rt, str) else None


# ---------------------------------------------------------------- đăng nhập Google (Supabase OAuth + PKCE)
def pkce_pair() -> tuple[str, str]:
    """(code_verifier, code_challenge S256) theo RFC 7636."""
    verifier = secrets.token_urlsafe(64)[:96]
    challenge = base64.urlsafe_b64encode(hashlib.sha256(verifier.encode()).digest()).rstrip(b"=").decode()
    return verifier, challenge


def site_url(cfg: dict) -> str:
    """Địa chỉ app để Supabase đưa người dùng quay về sau khi đăng nhập Google."""
    if cfg.get("site_url"):
        return str(cfg["site_url"]).rstrip("/")
    try:
        u = urlsplit(st.context.url)
        return f"{u.scheme}://{u.netloc}"
    except Exception:
        return ""


def google_url(cfg: dict, challenge: str) -> str:
    q = urlencode({"provider": "google", "redirect_to": site_url(cfg), "code_challenge": challenge,
                   "code_challenge_method": "s256"})
    return f"{cfg['url'].rstrip('/')}/auth/v1/authorize?{q}"


def prepare_google(cfg: dict) -> None:
    """Trước khi gắn cầu nối: tạo mã PKCE cho phiên (1 lần) và hẹn lưu vào trình duyệt.
    Không tạo khi đang quay về từ Google (?code=) để không ghi đè mã cũ."""
    if not cfg.get("google") or st.session_state.get("auth") or st.session_state.get("_pkce_verifier"):
        return
    try:
        if "code" in st.query_params or "error" in st.query_params:
            return
    except Exception:
        return
    verifier, challenge = pkce_pair()
    st.session_state["_pkce_verifier"], st.session_state["_pkce_challenge"] = verifier, challenge
    _queue_pkce(verifier)


def exchange_code(cfg: dict, code: str, verifier: str) -> tuple[dict | None, str | None]:
    """Đổi mã Google trả về lấy phiên Supabase."""
    try:
        r = _post(cfg, "token?grant_type=pkce", {"auth_code": code, "code_verifier": verifier})
    except requests.RequestException as e:
        return None, f"Không kết nối được máy chủ đăng nhập: {e}"
    if not r.ok:
        return None, "Đăng nhập Google không thành công hoặc đã hết hạn – hãy thử lại."
    auth = _session(r.json())
    return (auth, None) if auth else (None, "Không nhận được thông tin người dùng.")


def handle_google_return(cfg: dict) -> bool:
    """Nếu địa chỉ có ?code= (vừa đăng nhập Google xong): đổi mã lấy phiên. True nếu đăng nhập thành công."""
    try:
        qp = st.query_params
        code, err = qp.get("code"), qp.get("error_description") or qp.get("error")
    except Exception:
        return False
    if err:
        st.session_state["_google_error"] = f"Google từ chối đăng nhập: {err}"
        qp.clear()
        return False
    if not code:
        return False
    verifier = st.session_state.get("_bridge_pkce") or ""
    qp.clear()
    st.session_state.pop("_pkce_verifier", None)
    if not verifier:
        st.session_state["_google_error"] = ("Không tìm thấy mã xác thực trên trình duyệt này – hãy bấm lại "
                                             "Tiếp tục với Google (mở trên cùng trình duyệt).")
        return False
    auth, err = exchange_code(cfg, code, verifier)
    _queue_pkce(None)                    # mã PKCE chỉ dùng 1 lần
    st.session_state.pop("_pkce_verifier", None)
    if err:
        st.session_state["_google_error"] = err
        return False
    st.session_state["auth"] = auth
    st.session_state.pop("_logged_out", None)
    _queue_cookie(auth["refresh_token"])  # đăng nhập Google: luôn ghi nhớ trên trình duyệt này
    return True


def restore(cfg: dict, token: str | None = None) -> bool:
    """Lần đầu trong phiên: nếu trình duyệt có token ghi nhớ, tự đăng nhập lại. Trả về True nếu thành công.

    token: giá trị từ bridge(); nếu trống thử cookie (chạy trên máy, nơi cookie vẫn tới được server)."""
    if st.session_state.get("_restore_tried") or st.session_state.get("_logged_out"):
        return False
    raw = token
    if not raw:
        try:
            raw = st.context.cookies.get(COOKIE)
        except Exception:
            raw = None
    if not isinstance(raw, str) or not raw.strip():
        return False
    st.session_state["_restore_tried"] = True
    auth = refresh(cfg, unquote(raw).strip())
    if not auth:
        _queue_cookie(None)            # token hết hạn / đã thu hồi → xoá
        return False
    st.session_state["auth"] = auth
    _queue_cookie(auth["refresh_token"])   # lưu token mới (token cũ đã bị Supabase vô hiệu)
    return True


def waiting_screen() -> None:
    """Trong lúc chờ trình duyệt báo token (thường < 1 giây)."""
    _, mid, _ = st.columns([1, 2, 1])
    with mid:
        st.caption("Đang kiểm tra phiên đăng nhập…")
        if st.button("Đăng nhập bằng mã email", key="skip_wait_login"):
            st.session_state["_bridge_skip"] = True
            st.rerun()


# Nút Google theo phong cách nút đăng nhập chính thức của Google: nền trắng, chữ tối, logo "G" 4 màu.
_GOOGLE_G = quote(
    '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 48 48">'
    '<path fill="#EA4335" d="M24 9.5c3.54 0 6.71 1.22 9.21 3.6l6.85-6.85C35.9 2.38 30.47 0 24 0 14.62 0 6.51 5.38 2.56 13.22l7.98 6.19C12.43 13.72 17.74 9.5 24 9.5z"/>'
    '<path fill="#4285F4" d="M46.98 24.55c0-1.57-.15-3.09-.38-4.55H24v9.02h12.94c-.58 2.96-2.26 5.48-4.78 7.18l7.73 6c4.51-4.18 7.09-10.36 7.09-17.65z"/>'
    '<path fill="#FBBC05" d="M10.53 28.59c-.48-1.45-.76-2.99-.76-4.59s.27-3.14.76-4.59l-7.98-6.19C.92 16.46 0 20.12 0 24c0 3.88.92 7.54 2.56 10.78l7.97-6.19z"/>'
    '<path fill="#34A853" d="M24 48c6.48 0 11.93-2.13 15.89-5.81l-7.73-6c-2.15 1.45-4.92 2.3-8.16 2.3-6.26 0-11.57-4.22-13.47-9.91l-7.98 6.19C6.51 42.62 14.62 48 24 48z"/>'
    '</svg>')
_GOOGLE_BTN_CSS = f"""<style>
.st-key-google_btn a {{ background:#FFFFFF !important; border:1px solid #DADCE0 !important; min-height:52px;
  box-shadow:0 1px 3px rgba(0,0,0,.35); transition:background .15s, box-shadow .15s; }}
.st-key-google_btn a:hover {{ background:#F1F3F4 !important; box-shadow:0 2px 8px rgba(0,0,0,.45); }}
.st-key-google_btn a p {{ color:#1F1F1F !important; font-weight:600 !important; font-size:1rem; }}
.st-key-google_btn a p::before {{ content:''; display:inline-block; width:20px; height:20px; margin-right:12px;
  vertical-align:-4px; background:url("data:image/svg+xml,{_GOOGLE_G}") center/contain no-repeat; }}
</style>"""


def intro_promise() -> str:
    from . import intro
    p = intro.PROMISE_SHORT
    return p[0].lower() + p[1:]


# Trình duyệt nhúng trong app mạng xã hội – Google chặn đăng nhập OAuth ở đây (lỗi 403 disallowed_useragent).
IN_APP_UA = ("zalo", "fban", "fbav", "fb_iab", "messenger", "instagram", "line/", "tiktok", "bytedancewebview")


def in_app_browser(user_agent: str | None = None) -> bool:
    if user_agent is None:
        try:
            user_agent = st.context.headers.get("User-Agent") or ""
        except Exception:  # noqa: BLE001 – không có ngữ cảnh trình duyệt
            user_agent = ""
    ua = user_agent.lower()
    return any(k in ua for k in IN_APP_UA)


def _email_form(cfg: dict, _s) -> None:
    """Ô email → gửi mã 6 số."""
    with st.form("login_email"):
        email = st.text_input("Email", placeholder="ban@example.com").strip().lower()
        if st.form_submit_button("Gửi mã đăng nhập", type="primary", width="stretch", key=_s.ic("mail", "guima")):
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


def _code_form(cfg: dict, _s) -> None:
    """Nhập mã 6 số vừa gửi qua email."""
    email = st.session_state.get("_login_email", "")
    st.info(f"Đã gửi mã tới **{email}**. Kiểm tra cả hộp thư Spam/Quảng cáo.")
    with st.form("login_code"):
        code = st.text_input("Mã đăng nhập (6 số)", max_chars=10)
        remember = st.checkbox(f"Ghi nhớ đăng nhập trên thiết bị này ({REMEMBER_DAYS} ngày)", value=True,
                               help="Bỏ chọn nếu đang dùng máy tính/điện thoại của người khác.")
        if st.form_submit_button("Đăng nhập", type="primary", width="stretch", key=_s.ic("login", "dangnhap")):
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
    if st.button("Dùng email khác / gửi lại mã", key=_s.ic("arrow-left", "doiemail")):
        st.session_state["_login_step"] = "email"
        st.rerun()


def login_screen(cfg: dict) -> None:
    """Vẽ màn hình đăng nhập; khi thành công lưu st.session_state['auth'] và chạy lại."""
    st.markdown("<style>[data-testid='stSidebar'],[data-testid='stSidebarCollapsedControl']{display:none}</style>"
                "<div style='height:6vh'></div>", unsafe_allow_html=True)
    _, mid, _ = st.columns([1, 2, 1])
    with mid:
        from . import style as _s
        _s.title("flame", "Hành trình FIRE")
        signup = bool(cfg.get("allow_signup", False))
        google = bool(cfg.get("google")) and bool(st.session_state.get("_pkce_challenge"))
        if st.session_state.pop("_account_deleted", None):
            st.success("Đã xoá tài khoản và toàn bộ dữ liệu. Cảm ơn bạn đã đồng hành cùng Hành trình FIRE.")
        g_err = st.session_state.pop("_google_error", None)
        if g_err:
            st.error(g_err)
        step = st.session_state.get("_login_step", "email")
        if step == "code":
            _code_form(cfg, _s)
        elif google:
            st.caption(("**Đăng nhập hoặc tạo tài khoản mới chỉ với 1 lần bấm** – lần đầu bấm, app tự tạo tài khoản "
                        "từ Google của bạn." if signup else "Đăng nhập bằng tài khoản Google của bạn.")
                       + " Không cần mật khẩu riêng.")
            if in_app_browser():
                st.warning("Bạn đang mở app trong **Zalo/Facebook/Messenger** – Google không cho đăng nhập ở đây. "
                           "Bấm **⋯** ở góc màn hình → **Mở bằng trình duyệt** (Chrome/Safari), rồi đăng nhập lại.")
            st.html(_GOOGLE_BTN_CSS)
            with st.container(key="google_btn"):
                st.link_button("Tiếp tục với Google", google_url(cfg, st.session_state["_pkce_challenge"]),
                               width="stretch")
            st.caption("Trang Google mở ở thẻ mới; đăng nhập xong app tự vào và ghi nhớ trên trình duyệt này. "
                       "Nếu Google báo lỗi khi mở từ Zalo/Facebook, hãy mở link app bằng Chrome hoặc Safari.")
            with st.expander("Không dùng Gmail? Đăng nhập bằng mã email", key=_s.ic("mail", "email_login")):
                st.caption("Dành cho email Outlook, Yahoo, email cơ quan… "
                           + ("Lần đầu dùng, app tự tạo tài khoản. " if signup else "")
                           + "Mã 6 số sẽ được gửi vào hộp thư của bạn.")
                _email_form(cfg, _s)
            st.caption("Tiếp tục nghĩa là bạn đã đọc cam kết: app " + intro_promise())
        else:
            st.caption(("Nhập email để **đăng nhập hoặc tạo tài khoản mới**" if signup else "Đăng nhập bằng email")
                       + " – không cần mật khẩu. Mã 6 số sẽ được gửi vào hộp thư của bạn.")
            _email_form(cfg, _s)
            st.caption("Tiếp tục nghĩa là bạn đã đọc cam kết: app " + intro_promise())
        st.caption("Dữ liệu của mỗi tài khoản được tách riêng; người khác không xem được dữ liệu của bạn.")
        from . import intro
        intro.css()
        st.markdown(f"#### {intro.TAGLINE}")
        intro.values(one=True)
        st.html(f'<span class="pill">{_s.svg("circle-check", 16, _s.LIME)}{intro.PROMISE_SHORT}</span>')
        st.write("")
        with st.expander("Về Hành trình FIRE – vì sao có app này?", key=_s.ic("info-circle", "intro_login")):
            intro.why_story(short=True)
            st.markdown("**Tính năng nổi bật**")
            intro.features(compact=True)
            intro.promise_card(one=True)
            st.markdown("**Câu hỏi thường gặp**")
            intro.faq()
        with st.expander("Lần đầu dùng app? Xem cách đăng nhập"):
            from . import style
            st.html(style.steps([
                ("Bấm Tiếp tục với Google", "Chọn tài khoản Gmail của bạn – <b>lần đầu bấm là app tự tạo tài khoản</b>, "
                                            "không cần chờ ai đăng ký giúp. Mở link bằng <b>Chrome/Safari</b> "
                                            "(không mở trong Zalo/Facebook)."),
                ("Không dùng Gmail?", "Mở mục <b>Đăng nhập bằng mã email</b>, gõ email rồi bấm "
                                      "<b>Gửi mã đăng nhập</b>; lấy mã 6 số trong hộp thư (xem cả Spam) và nhập vào."),
                ("Ghi nhớ đăng nhập", "Lần sau mở app trên cùng trình duyệt là vào thẳng, không cần đăng nhập lại."),
                ("Sau khi vào", "Mở <b>Hệ thống → Hướng dẫn</b> để xem các bước thiết lập và sử dụng."),
            ]))
        from . import legal
        st.html(legal.links_html())


def logout(cfg: dict | None = None) -> None:
    """Đăng xuất: thu hồi phiên trên Supabase, xoá cookie ghi nhớ, xoá trạng thái phiên."""
    a = st.session_state.get("auth") or {}
    if cfg:
        revoke(cfg, a.get("access_token"))
    for k in ("auth", "_store", "_startup_done", "_login_step", "_login_email"):
        st.session_state.pop(k, None)
    st.session_state["_logged_out"] = True      # không tự đăng nhập lại bằng cookie cũ trong phiên này
    _queue_cookie(None)

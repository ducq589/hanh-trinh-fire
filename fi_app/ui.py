"""Tiện ích dùng chung cho các trang Streamlit."""
from __future__ import annotations

import datetime as dt
import math

import pandas as pd
import streamlit as st

from . import db, engine, importer

from .style import TIER_COLORS as PALETTE  # noqa: E402  (màu theo tầng tháp)


def display_name(email: str | None) -> str:
    """Tên hiển thị từ email: 'quangduc589@gmail.com' → 'quangduc589'."""
    return (email or "").split("@")[0] or "bạn"


# ---------------------------------------------------------------- data access
def cloud_config() -> dict | None:
    """Có mục [supabase] trong secrets (Streamlit Cloud hoặc .streamlit/secrets.toml) → chế độ cloud."""
    try:
        cfg = st.secrets.get("supabase")
    except Exception:          # không có file secrets → chế độ local
        return None
    if cfg and cfg.get("url") and cfg.get("anon_key") and cfg.get("db_url"):
        return dict(cfg)
    return None


def store(entry: bool = False) -> db.Store:
    """Store cho lượt chạy hiện tại.

    local: SQLite (tự import v3 ở lần chạy đầu).  cloud: bắt buộc đăng nhập, kết nối Postgres theo người dùng.
    """
    cfg = cloud_config()
    if cfg is None:
        s = db.connect_local()
        if db.is_empty(s) and importer.V3_PATH.exists() and not st.session_state.get("_import_tried"):
            st.session_state["_import_tried"] = True
            importer.import_v3(s)
            st.toast("Đã nhập dữ liệu lần đầu từ Investment_tracking_v3.xlsx")
        return s
    from . import auth
    a = st.session_state.get("auth")
    # Cầu nối ghi nhớ đăng nhập chỉ gắn 1 lần mỗi lượt chạy – ở lời gọi đầu tiên (app.py, entry=True).
    # Các trang gọi lại store() qua ui.state() không gắn nữa (trùng key → StreamlitDuplicateElementKey).
    token = auth.bridge() if entry else None
    if not a:
        waiting = (entry and token is None and not st.session_state.get("_bridge_skip")
                   and not st.session_state.get("_logged_out") and not st.session_state.get("_restore_tried"))
        if waiting:                           # lượt chạy đầu: trình duyệt chưa kịp báo token → chờ (tự chạy lại)
            auth.waiting_screen()
            st.stop()
        if auth.restore(cfg, token) or "_cookie_op" in st.session_state:
            st.rerun()                        # chạy lại để bridge lưu token mới / xoá token hỏng ngay
        auth.login_screen(cfg)
        st.stop()
    s = st.session_state.get("_store")
    if s is None or getattr(s.conn, "closed", False) or s.user_id != a["user_id"]:
        s = db.connect_cloud(cfg["db_url"], a["user_id"], a["email"])
        st.session_state["_store"] = s
    else:
        try:
            s.q("SELECT 1 AS ok")
        except Exception:
            s.close()
            s = db.connect_cloud(cfg["db_url"], a["user_id"], a["email"])
            st.session_state["_store"] = s
    return s


conn = store  # tên cũ


def state(c=None):
    """Tính toàn bộ: dữ liệu, danh mục, kế hoạch FIRE."""
    c = c or store()
    data = db.load_all(c)
    h = engine.holdings(data)
    fp = engine.fire_plan(data, h)
    return c, data, h, fp


# ---------------------------------------------------------------- formatting (kiểu Việt Nam)
def _ok(x) -> bool:
    return x is not None and not (isinstance(x, float) and math.isnan(x))


def vnd(x, dec: int = 0) -> str:
    if not _ok(x):
        return "–"
    s = f"{x:,.{dec}f}".replace(",", "§").replace(".", ",").replace("§", ".")
    return f"{s} ₫"


def tr(x) -> str:
    """Rút gọn: 845,7 tr / 8,53 tỷ."""
    if not _ok(x):
        return "–"
    if abs(x) >= 1e9:
        return f"{x / 1e9:,.2f} tỷ".replace(".", ",")
    return f"{x / 1e6:,.1f} tr".replace(",", "§").replace(".", ",").replace("§", ".")


def pct(x, dec: int = 1) -> str:
    if not _ok(x):
        return "–"
    return f"{x * 100:.{dec}f}%".replace(".", ",")


def num(x, dec: int = 2) -> str:
    if not _ok(x):
        return "–"
    return f"{x:,.{dec}f}".replace(",", "§").replace(".", ",").replace("§", ".")


def d(x) -> str:
    x = engine.to_date(x) if x not in (None, "") else None
    return x.strftime("%d/%m/%Y") if x else "–"


# ---------------------------------------------------------------- editable tables
def _clean(v):
    if v is None:
        return None
    if isinstance(v, float) and math.isnan(v):
        return None
    if isinstance(v, pd.Timestamp):
        return v.date().isoformat()
    if isinstance(v, (dt.date, dt.datetime)):
        return db._d(v)
    if hasattr(v, "item"):          # numpy scalar
        return v.item()
    if v is pd.NA or v is pd.NaT:
        return None
    return v


def save_editor(c, table: str, key_col: str, df: pd.DataFrame, editor_key: str, cols: list[str],
                transform=None) -> tuple[int, int, int]:
    """Ghi thay đổi của st.data_editor (sửa / thêm / xoá) xuống bảng SQLite.

    df: DataFrame đã hiển thị (giữ cột khoá `key_col`), cols: các cột được phép ghi.
    transform(dict) → dict: chuẩn hoá một dòng trước khi ghi (ví dụ đổi Có/Không → 1/0).
    """
    ch = st.session_state.get(editor_key, {})
    transform = transform or (lambda r: r)
    edited = added = deleted = 0
    with c.tx():
        for idx, changes in ch.get("edited_rows", {}).items():
            key = _clean(df.iloc[int(idx)][key_col])
            row = transform({k: _clean(v) for k, v in changes.items() if k in cols})
            row = {k: v for k, v in row.items() if k in cols}
            if row:
                c.x(f"UPDATE {table} SET {', '.join(f'{k}=?' for k in row)} WHERE {key_col}=?",
                          [*row.values(), key])
                edited += 1
        for new in ch.get("added_rows", []):
            row = transform({k: _clean(v) for k, v in new.items() if k in cols or k == key_col})
            row = {k: v for k, v in row.items() if (k in cols or k == key_col) and v is not None}
            if row:
                c.x(f"INSERT INTO {table}({', '.join(row)}) VALUES ({', '.join('?' * len(row))})",
                          list(row.values()))
                added += 1
        for idx in ch.get("deleted_rows", []):
            c.x(f"DELETE FROM {table} WHERE {key_col}=?", (_clean(df.iloc[int(idx)][key_col]),))
            deleted += 1
    return edited, added, deleted


def has_changes(editor_key: str) -> bool:
    ch = st.session_state.get(editor_key, {})
    return bool(ch.get("edited_rows") or ch.get("added_rows") or ch.get("deleted_rows"))


def flash(msg: str, icon: str | None = None):
    st.session_state["_flash"] = (msg, icon)


def show_flash():
    f = st.session_state.pop("_flash", None)
    if f:
        st.toast(f[0], icon=f[1]) if f[1] else st.toast(f[0])


def xirr_label(r: dict) -> str:
    """XIRR hiển thị; mã khai số dư đầu kỳ ghi kèm '*' (tính từ ngày khai báo)."""
    if r.get("xirr") is None:
        return "–"
    return pct(r["xirr"], 2) + (" *" if r.get("xirr_since") else "")


XIRR_NOTE = "\\* XIRR tính từ ngày khai số dư đầu kỳ (không có lịch sử lệnh trước đó)."


# ---------------------------------------------------------------- thêm tài sản từ danh mục (dùng chung)
@st.cache_data(ttl=24 * 3600, show_spinner="Đang tải danh sách quỹ…")
def funds() -> list[dict]:
    from . import catalog
    return catalog.list_funds()


def funds_or_none() -> list[dict] | None:
    try:
        return funds()
    except Exception:  # noqa: BLE001 – Fmarket không trả lời: vẫn thêm được cổ phiếu
        return None


def add_asset(c, asset: dict, hint: str = "") -> bool:
    """Thêm tài sản, lấy giá ngay (kèm ~13 tháng lịch sử) rồi tải lại trang. Trùng mã → báo lỗi, trả False."""
    from . import catalog, prices
    try:
        catalog.add(c, asset)
    except ValueError as e:
        st.error(str(e))
        return False
    sym = db.asset_symbol(asset)
    with st.spinner("Đang lấy giá…"):
        try:
            ok = any(x.startswith(f"✓ {sym}:") for x in prices.fetch_auto(c, backfill_days=400)["log"])
        except Exception:  # noqa: BLE001 – mất mạng: tài sản vẫn được thêm, giá lấy lần sau
            ok = False
    flash(f"Đã thêm {asset['code']} – {asset['name']}. "
          + ("Đã lấy giá tự động." if ok else "Chưa lấy được giá lúc này, app sẽ thử lại khi mở lần sau.") + hint)
    st.rerun()
    return True

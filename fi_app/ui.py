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


def store() -> db.Store:
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
    if not a and auth.restore(cfg):           # ghi nhớ đăng nhập (cookie)
        a = st.session_state.get("auth")
    auth.flush_cookie()
    if not a:
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

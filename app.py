"""Hành trình FIRE – webapp (Streamlit).

- Trên máy:  nhấp đúp Chay_app.command  (SQLite, 1 người dùng)
- Trên cloud: Streamlit Community Cloud + Supabase (đăng nhập email, nhiều người dùng) – xem Trien_khai_cloud.md
"""
import streamlit as st

from fi_app import auth, db, engine, prices, ui

st.set_page_config(page_title="Hành trình FIRE", page_icon="🔥", layout="wide")

store = ui.store()          # cloud: hiện màn hình đăng nhập nếu chưa đăng nhập

# Việc tự động mỗi phiên: sao lưu ngày (local), lấy giá (≤ 6 giờ/lần), Snapshot đầu tháng
if not st.session_state.get("_startup_done"):
    st.session_state["_startup_done"] = True
    if not store.is_cloud:
        db.daily_backup()
    try:
        if not db.is_empty(store) and prices.should_auto_fetch(store):
            with st.spinner("Đang cập nhật giá mới nhất…"):
                res = prices.fetch_auto(store)
            st.toast(f"Đã cập nhật {res['saved']} giá tự động", icon="💹")
    except Exception as exc:  # mất mạng / nguồn lỗi: app vẫn chạy bình thường
        st.toast(f"Không lấy được giá tự động: {exc}", icon="⚠️")
    s, data, h, fp = ui.state(store)
    if data["assets"] and engine.needs_monthly_snapshot(data["snapshots"]):
        db.save_snapshot(store, engine.snapshot(data, h, fp, note="Tự động đầu tháng"))
        st.toast("Đã tự chụp Snapshot tài sản tháng này", icon="📸")

if store.is_cloud:
    with st.sidebar:
        st.caption(f"👤 {store.email}")
        st.button("Đăng xuất", width="stretch", on_click=lambda: (store.close(), auth.logout()))

pages = {
    "Theo dõi": [
        st.Page("views/tong_quan.py", title="Tổng quan", icon="🏠", default=True),
        st.Page("views/ke_hoach_fire.py", title="Kế hoạch FIRE", icon="🔥"),
        st.Page("views/lich_su.py", title="Lịch sử", icon="📈"),
    ],
    "Nhập liệu": [
        st.Page("views/giao_dich.py", title="Giao dịch", icon="🧾"),
        st.Page("views/gia.py", title="Giá", icon="💹"),
        st.Page("views/tai_san.py", title="Tài sản", icon="🗂️"),
        st.Page("views/tiet_kiem.py", title="Tiết kiệm, Mục tiêu & Nợ", icon="🏦"),
        st.Page("views/thu_chi.py", title="Thu chi", icon="💰"),
    ],
    "Hệ thống": [
        st.Page("views/sao_luu.py", title="Sao lưu & Cài đặt", icon="⚙️"),
    ],
}
nav = st.navigation(pages)
ui.show_flash()
nav.run()

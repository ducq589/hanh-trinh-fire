import datetime as dt
from pathlib import Path

import streamlit as st

from fi_app import db, engine, exporter, importer, prices, style, ui

c, data, h, fp = ui.state()
style.title("settings", "Sao lưu & Cài đặt")

# --------------------------------------------------------------- backup
st.subheader("Sao lưu dữ liệu")
if c.is_cloud:
    st.caption("Dữ liệu của bạn lưu trên Supabase (Postgres), tách riêng theo tài khoản. Nên tải bản Excel "
               "định kỳ (nút bên dưới) để tự giữ một bản sao.")
else:
    st.caption(f"Dữ liệu app nằm ở `{db.DB_PATH.relative_to(db.PROJECT_DIR)}`. App tự sao lưu mỗi ngày "
               f"(giữ 30 bản) vào `{db.BACKUP_DIR.relative_to(db.PROJECT_DIR)}`. Nên chép thêm thư mục này "
               "ra ổ ngoài/iCloud định kỳ.")
    b1, b2 = st.columns(2)
    if b1.button("Sao lưu ngay", key=style.ic("device-floppy", "saoluu")):
        p = db.backup(tag="thu_cong")
        ui.flash(f"Đã sao lưu: {p.name}")
        st.rerun()
    if db.DB_PATH.exists():
        with b2, open(db.DB_PATH, "rb") as fh:
            st.download_button("Tải file dữ liệu (.db)", fh.read(), file_name=f"fi_{dt.date.today():%Y%m%d}.db", key=style.ic("download", "taidb"))
    backups = db.list_backups()
    if backups:
        with st.expander(f"Khôi phục từ bản sao lưu ({len(backups)} bản)"):
            pick = st.selectbox("Chọn bản", backups, format_func=lambda p: p.name)
            ok = st.checkbox("Tôi hiểu dữ liệu hiện tại sẽ được thay bằng bản này (dữ liệu hiện tại được sao lưu trước)")
            if st.button("Khôi phục", disabled=not ok, key=style.ic("history", "khoiphuc")):
                c.close()
                db.restore(pick)
                ui.flash(f"Đã khôi phục từ {pick.name}")
                st.rerun()

# --------------------------------------------------------------- export
st.subheader("Xuất dữ liệu")
e1, e2 = st.columns(2)
if c.is_cloud:
    if e1.button("Tạo báo cáo Excel", key=style.ic("file-spreadsheet", "baocao1")):
        st.session_state["_export_bytes"] = exporter.export_excel_bytes(c)
    if st.session_state.get("_export_bytes"):
        e1.download_button("Tải file Excel", st.session_state["_export_bytes"], key=style.ic("download", "taixlsx1"),
                           file_name=f"FIRE_xuat_{dt.datetime.now():%Y%m%d_%H%M}.xlsx")
elif e1.button("Tạo báo cáo Excel", key=style.ic("file-spreadsheet", "baocao2")):
    st.session_state["_last_export"] = str(exporter.export_excel(c))
if not c.is_cloud and st.session_state.get("_last_export"):
    p = st.session_state["_last_export"]
    with open(p, "rb") as fh:
        e1.download_button("Tải file Excel", fh.read(), file_name=p.split("/")[-1], key=style.ic("download", "taixlsx2"))
if c.is_cloud:
    e2.download_button("Tải gia.csv", prices.csv_bytes(c), file_name="gia.csv", mime="text/csv", key=style.ic("download", "taicsv2"))
elif e2.button("Xuất gia.csv cho Excel v3", key=style.ic("file-export", "xuatcsv2")):
    res = prices.export_csv(c)
    e2.success(f"Đã ghi {res['rows']} dòng vào gia.csv – mở Excel v3 ▸ Data ▸ Refresh All.")

# --------------------------------------------------------------- settings
st.subheader("Cài đặt")
s = data["settings"]
with st.form("settings"):
    c1, c2, c3, c4 = st.columns(4)
    tax = c1.number_input("Thuế lãi tiền gửi (%)", 0.0, 50.0, engine.n(s.get("tax_interest")) * 100, 0.5)
    stale = c2.number_input("Cảnh báo giá cũ sau (ngày)", 1, 90, int(engine.n(s.get("stale_days")) or 7))
    mat = c3.number_input("Cảnh báo sắp đáo hạn trước (ngày)", 1, 90, int(engine.n(s.get("maturity_days")) or 15))
    auto = c4.toggle("Tự lấy giá khi mở app", value=s.get("auto_fetch", "1") == "1")
    if st.form_submit_button("Lưu cài đặt", type="primary", key=style.ic("device-floppy", "luucaidat")):
        db.set_kv(c, "settings", {"tax_interest": tax / 100, "stale_days": stale, "maturity_days": mat,
                                  "auto_fetch": "1" if auto else "0"})
        ui.flash("Đã lưu cài đặt")
        st.rerun()

# --------------------------------------------------------------- import
st.subheader("Nhập dữ liệu từ Excel")
TEMPLATE = Path(__file__).resolve().parents[1] / "mau" / "Investment_tracking_v4.xlsx"
with st.container(border=True):
    m1, m2 = st.columns([5, 2], vertical_alignment="center")
    m1.markdown("**Chưa có file? Tải file mẫu trống v4**")
    m1.caption("Điền thu chi, tài sản, giao dịch, sổ tiết kiệm trên Excel (sheet *HuongDan* có hướng dẫn từng bước), "
               "rồi tải lên ở ô bên dưới. Ghi Mã tài sản đúng mã quỹ/cổ phiếu để app tự lấy giá.")
    if TEMPLATE.exists():
        m2.download_button("Tải mẫu v4", TEMPLATE.read_bytes(), file_name=TEMPLATE.name, width="stretch",
                           mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                           key=style.ic("download", "taimau"))
meta = db.kv(c, "meta")
st.caption(f"Lần nhập gần nhất: {meta.get('imported_at', '–')} từ {meta.get('imported_from', '–')}. "
           "File Excel chỉ được ĐỌC, không bị sửa.")
st.warning("Nhập sẽ **xoá toàn bộ dữ liệu hiện có của tài khoản này** (giao dịch, giá, thu chi…) và thay bằng nội dung "
           "file Excel." + ("" if c.is_cloud else " Dữ liệu hiện tại được sao lưu trước."))
src = st.file_uploader("Chọn file Excel đã điền (mẫu v4 hoặc Investment_tracking_v3)", type=["xlsx"])
if src is None and not c.is_cloud and importer.V3_PATH.exists():
    src = importer.V3_PATH
    st.caption("Không chọn file → dùng Investment_tracking_v3.xlsx trong thư mục dự án.")
ok = st.checkbox("Tôi hiểu và muốn nhập")
if st.button("Nhập từ Excel", disabled=not ok or src is None, key=style.ic("file-import", "nhapv3")):
    if not c.is_cloud:
        db.backup(tag="truoc_nhap_lai")
    with st.spinner("Đang nhập…"):
        counts = importer.import_v3(c, src)
    st.session_state.pop("_startup_done", None)
    ui.flash("Đã nhập: " + ", ".join(f"{k} {v}" for k, v in counts.items()))
    st.rerun()

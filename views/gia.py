import datetime as dt

import pandas as pd
import plotly.express as px
import streamlit as st

from fi_app import db, engine, prices, sources, ui

c, data, h, fp = ui.state()
st.title("💹 Giá")

market = [r for r in h["rows"] if r["valuation"] != "Sổ tiết kiệm"]
stale = int(engine.n(data["settings"].get("stale_days", 7)))

# --------------------------------------------------------------- auto fetch
st.subheader("Lấy giá tự động")
meta = db.kv(c, "meta")
auto_assets = [a for a in data["assets"] if a.get("price_source")]
last = meta.get("last_auto_fetch")
last_txt = f"{dt.datetime.fromisoformat(last):%H:%M %d/%m/%Y}" if last else "chưa lấy lần nào"
st.caption(
    f"{len(auto_assets)} tài sản có nguồn giá tự động (Fmarket cho quỹ mở, VNDirect cho cổ phiếu, PNJ cho vàng – "
    f"cài ở trang **Tài sản**, cột *Nguồn giá*). App tự lấy giá khi mở (tối đa 6 giờ/lần). Lần lấy gần nhất: {last_txt}.")
if st.button("🔄 Lấy giá mới nhất", type="primary"):
    with st.spinner("Đang lấy giá…"):
        res = prices.fetch_auto(c)
    st.session_state["_fetch_log"] = res["log"]
    ui.flash(f"Đã lưu {res['saved']} giá từ nguồn tự động")
    st.rerun()
if st.session_state.get("_fetch_log"):
    with st.expander("Kết quả lần lấy giá vừa rồi", expanded=True):
        for line in st.session_state["_fetch_log"]:
            (st.error if line.startswith("✗") else st.write)(line)

# --------------------------------------------------------------- quick entry
st.subheader("Nhập giá tay")
st.caption("Dùng cho tài sản không có nguồn tự động (vàng, bảo hiểm, BĐS…) hoặc để ghi đè. Điền **Giá mới** (VND đầy đủ, "
           "ví dụ MBB 18800), chọn ngày rồi bấm Lưu. Ô để trống sẽ bỏ qua. Giá tay luôn được ưu tiên khi trùng ngày.")
day = st.date_input("Ngày giá", dt.date.today(), format="DD/MM/YYYY")
quick = pd.DataFrame([{
    "Mã": r["code"], "Tên": r["name"], "Nguồn": r.get("price_source") or "Nhập tay",
    "Giá mới nhất": r["price"], "Ngày giá": r["price_date"],
    "Tình trạng": ("⚠ " + r["warning"]) if r["warning"] else "✓ Mới", "Giá mới": None,
} for r in market])
edited = st.data_editor(quick, key="quick_px", hide_index=True, width="stretch",
                        disabled=["Mã", "Tên", "Nguồn", "Giá mới nhất", "Ngày giá", "Tình trạng"],
                        column_config={
                            "Giá mới nhất": st.column_config.NumberColumn(format="localized"),
                            "Ngày giá": st.column_config.DateColumn(format="DD/MM/YYYY"),
                            "Giá mới": st.column_config.NumberColumn(format="localized", min_value=0),
                        })
new = edited.dropna(subset=["Giá mới"])
new = new[new["Giá mới"] > 0]
if st.button(f"💾 Lưu {len(new)} giá ngày {day:%d/%m/%Y}", disabled=new.empty):
    for _, r in new.iterrows():
        db.upsert_price(c, day, r["Mã"], float(r["Giá mới"]), "Nhập trên app", is_manual=1)
    ui.flash(f"Đã lưu {len(new)} giá ngày {day:%d/%m/%Y}")
    st.rerun()

# --------------------------------------------------------------- csv bridge
st.subheader("Đồng bộ với gia.csv (Power Query của Excel)")
col1, col2 = st.columns(2)
with col1:
    st.markdown("**Nhập từ gia.csv**")
    if c.is_cloud:
        up = st.file_uploader("Chọn file gia.csv", type=["csv"], label_visibility="collapsed")
        if up and st.button("⬇️ Nhập file đã chọn"):
            res = prices.import_csv(c, up, is_manual=0)
            ui.flash(f"gia.csv: {res['rows']} dòng, thêm {res['added']}, cập nhật {res['updated']}")
            st.rerun()
    elif st.button("⬇️ Nhập giá từ gia.csv"):
        res = prices.import_csv(c, prices.GIA_CSV, is_manual=0)
        ui.flash(f"gia.csv: {res['rows']} dòng, thêm {res['added']}, cập nhật {res['updated']}"
                 + (f", {len(res['errors'])} dòng lỗi" if res["errors"] else ""))
        st.rerun()
with col2:
    st.markdown("**Xuất ra gia.csv** – để file Excel v3 bấm *Refresh All* là có giá mới.")
    if c.is_cloud:
        st.download_button("⬆️ Tải gia.csv", prices.csv_bytes(c), file_name="gia.csv", mime="text/csv")
    elif st.button("⬆️ Xuất giá ra gia.csv"):
        res = prices.export_csv(c)
        ui.flash(f"Đã ghi {res['rows']} dòng vào gia.csv (bản cũ đã được sao lưu)")
        st.rerun()

# --------------------------------------------------------------- history chart
st.subheader("Lịch sử giá")
all_codes = sorted({p["code"] for p in data["prices"]})
default = [x for x in ("DCDS", "VESAF", "VNDBF") if x in all_codes] or all_codes[:1]
pick = st.multiselect("Mã", all_codes, default=default)
normalize = st.toggle("So sánh theo % (gốc = 100 tại ngày đầu)", value=len(pick) > 1)
hist = pd.DataFrame([{"Ngày": d, "Mã": code, "Giá": p} for code in pick for d, p in h["book"].history(code)])
if not hist.empty:
    if normalize:
        hist["Giá"] = hist.groupby("Mã")["Giá"].transform(lambda s: s / s.iloc[0] * 100)
    fig = px.line(hist, x="Ngày", y="Giá", color="Mã", labels={"Giá": "Chỉ số (gốc 100)" if normalize else "Giá (₫)"})
    fig.update_layout(height=380, margin=dict(t=10, b=10), legend=dict(orientation="h", y=-0.2))
    st.plotly_chart(fig, width="stretch")

with st.expander("Giá đã nhập tay (sửa/xoá)"):
    man = pd.DataFrame([p for p in data["prices"] if p["is_manual"] == 1],
                       columns=["date", "code", "price", "source", "is_manual"])
    man = man.sort_values("date", ascending=False).reset_index(drop=True)
    st.data_editor(man[["date", "code", "price", "source"]], key="man_px", hide_index=True, width="stretch",
                   num_rows="dynamic", disabled=["date", "code"], column_config={
                       "date": "Ngày", "code": "Mã",
                       "price": st.column_config.NumberColumn("Giá", format="localized"), "source": "Nguồn"})
    ch = st.session_state.get("man_px", {})
    if ch.get("edited_rows") or ch.get("deleted_rows"):
        if st.button("💾 Lưu thay đổi giá tay"):
            with c.tx():
                for i, chg in ch.get("edited_rows", {}).items():
                    r = man.iloc[int(i)]
                    for k, v in chg.items():
                        if k in ("price", "source"):
                            c.x(f"UPDATE prices SET {k}=? WHERE date=? AND code=? AND is_manual=1",
                                (v, r["date"], r["code"]))
                for i in ch.get("deleted_rows", []):
                    r = man.iloc[int(i)]
                    c.x("DELETE FROM prices WHERE date=? AND code=? AND is_manual=1", (r["date"], r["code"]))
            ui.flash("Đã lưu thay đổi giá nhập tay")
            st.rerun()
st.caption(f"Cảnh báo giá cũ sau {stale} ngày (đổi ở Sao lưu & Cài đặt). Thứ tự ưu tiên khi trùng ngày: "
           "giá nhập tay > giá từ gia.csv/Excel > giá tự động. Nguồn tự động là endpoint công khai của nhà cung cấp, "
           "không phải API có hợp đồng – nếu một nguồn ngừng hoạt động, hãy nhập tay.")

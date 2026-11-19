import datetime as dt

import pandas as pd
import plotly.express as px
import streamlit as st

from fi_app import db, engine, ui

c, data, h, fp = ui.state()
st.title("💰 Hồ sơ thu chi")
st.caption("Khai **một lần** số tiền điển hình của từng khoản theo đúng tần suất (tháng/quý/năm); app tự quy về mỗi "
           "tháng. Không cần ghi chép hằng ngày – chỉ rà soát mỗi quý hoặc khi có thay đổi lớn.")

pu = engine.to_date(data["assumptions"].get("profile_updated"))
c1, c2 = st.columns([1, 3])
new_pu = c1.date_input("Ngày rà soát gần nhất", pu or dt.date.today(), format="DD/MM/YYYY")
if pu is None or (dt.date.today() - pu).days > 90:
    c2.warning("Đã quá 90 ngày chưa rà soát – hãy xem lại các khoản bên dưới rồi bấm **Đã rà soát hôm nay**.")
else:
    c2.success(f"Còn hiệu lực – rà soát lần tới trước {(pu + dt.timedelta(days=90)):%d/%m/%Y}.")
b1, b2 = st.columns([1, 3])
if b1.button("✓ Đã rà soát hôm nay"):
    db.set_kv(c, "assumptions", {"profile_updated": dt.date.today().isoformat()})
    ui.flash("Đã cập nhật ngày rà soát")
    st.rerun()
if new_pu != pu and b2.button("Lưu ngày đã chọn"):
    db.set_kv(c, "assumptions", {"profile_updated": new_pu.isoformat()})
    st.rerun()

cf = fp["cf"]
k = st.columns(5)
k[0].metric("Thu nhập/tháng", ui.tr(cf["income"]))
k[1].metric("Chi tiêu/tháng", ui.tr(cf["expense"]), f"thiết yếu {ui.tr(cf['essential'])}", delta_color="off", delta_arrow="off")
k[2].metric("Dòng tiền dư", ui.tr(cf["surplus"]))
k[3].metric("Tỷ lệ tiết kiệm", ui.pct(cf["savings_rate"]))
k[4].metric("Còn lại sau đầu tư", ui.tr(cf["after_invest"]),
            "⚠ cam kết đầu tư vượt dòng tiền dư" if cf["after_invest"] < 0 else None, delta_color="inverse", delta_arrow="off")

df = pd.DataFrame(data["cashflow"], columns=["id", "name", "grp", "member", "amount", "freq", "note", "sort_order"])
df["Quy đổi/tháng"] = [engine.monthly(a, f or "Tháng") for a, f in zip(df["amount"], df["freq"])]
st.data_editor(df, key="cf_ed", hide_index=True, width="stretch", num_rows="dynamic",
               disabled=["id", "Quy đổi/tháng"], column_config={
                   "id": None, "sort_order": None,
                   "name": st.column_config.TextColumn("Khoản mục", required=True),
                   "grp": st.column_config.SelectboxColumn("Nhóm", options=db.CF_GROUPS, required=True),
                   "member": st.column_config.TextColumn("Thành viên"),
                   "amount": st.column_config.NumberColumn("Số tiền", format="localized", min_value=0),
                   "freq": st.column_config.SelectboxColumn("Tần suất", options=db.FREQS, required=True, default="Tháng"),
                   "note": st.column_config.TextColumn("Ghi chú"),
                   "Quy đổi/tháng": st.column_config.NumberColumn(format="localized"),
               })
if ui.has_changes("cf_ed") and st.button("💾 Lưu hồ sơ thu chi", type="primary"):
    e, a, x = ui.save_editor(c, "cashflow_items", "id", df, "cf_ed", ["name", "grp", "member", "amount", "freq", "note"])
    db.set_kv(c, "assumptions", {"profile_updated": dt.date.today().isoformat()})
    ui.flash(f"Thu chi: sửa {e}, thêm {a}, xoá {x}")
    st.rerun()

st.subheader("Cơ cấu mỗi tháng")
g = pd.DataFrame([("Chi thiết yếu", cf["essential"]), ("Chi linh hoạt", cf["flexible"]),
                  ("Đầu tư định kỳ", cf["invest"]), ("Còn lại", max(0.0, cf["after_invest"]))],
                 columns=["Khoản", "Số tiền"])
fig = px.bar(g, x="Số tiền", y=["Thu nhập"] * len(g), color="Khoản", orientation="h",
             color_discrete_sequence=["#C0392B", "#F2A93B", "#2E75B6", "#00A389"], labels={"y": ""})
fig.update_layout(height=170, margin=dict(t=10, b=10), barmode="stack", legend=dict(orientation="h", y=-0.4),
                  xaxis_tickformat=",.0f")
st.plotly_chart(fig, width="stretch")

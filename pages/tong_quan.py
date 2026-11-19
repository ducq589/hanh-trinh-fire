import pandas as pd
import plotly.express as px
import streamlit as st

from fi_app import engine, ui

c, data, h, fp = ui.state()

st.title("🏠 Tổng quan gia sản")
latest = max((r["price_date"] for r in h["rows"] if r["price_date"]), default=None)
st.caption(f"Giá cập nhật đến {ui.d(latest)} · {len(data['transactions'])} giao dịch · {len(data['assets'])} tài sản")

if not data["assets"]:
    st.info("Chưa có dữ liệu. Vào **Sao lưu & Cài đặt** để nhập từ Investment_tracking_v3.xlsx.")
    st.stop()

k = st.columns(5)
k[0].metric("Tổng tài sản", ui.tr(h["total_value"]), help=ui.vnd(h["total_value"]))
k[1].metric("Lãi/lỗ", ui.tr(h["total_pnl"]), ui.pct(h["total_pnl_pct"]), help=f"Vốn thuần {ui.vnd(h['total_cost'])}")
k[2].metric("Tài sản ròng", ui.tr(h["total_value"] - fp["debt"]), help=f"Trừ nợ {ui.vnd(fp['debt'])}")
k[3].metric("Tiến độ Full FIRE", ui.pct(fp["progress"]),
            help=f"Tài sản tính FIRE {ui.vnd(fp['assets'])} / Số FIRE {ui.vnd(fp['fire_number'])}")
k[4].metric("Năm dự kiến đạt FIRE", fp["year_full"] or "–",
            f"{fp['years_full']:.1f} năm nữa".replace(".", ",") if fp["years_full"] is not None else None,
            delta_color="off", delta_arrow="off")

if fp["progress"] is not None:
    st.progress(min(1.0, fp["progress"]), text=f"Hành trình Full FIRE: {ui.pct(fp['progress'])} "
                                                 f"· Lean FIRE: {ui.pct(fp['lean_progress'])}")

# --------------------------------------------------------------- reminders
rem = engine.reminders(data, h, fp)
with st.expander(f"🔔 Việc cần chú ý ({len(rem)})", expanded=bool([r for r in rem if r[0] != "info"])):
    if not rem:
        st.success("Không có việc gì cần xử lý.")
    for level, head in (("error", "Cần xử lý ngay"), ("warning", "Nên làm sớm"), ("info", "Để ý")):
        items = [t for lv, t in rem if lv == level]
        if items:
            getattr(st, level)(f"**{head}**\n" + "\n".join(f"- {t}" for t in items))

# --------------------------------------------------------------- pyramid
st.subheader("Tháp tài sản theo tầng")
tiers = pd.DataFrame(h["tiers"])
col1, col2 = st.columns([3, 2])
with col1:
    st.dataframe(
        tiers.assign(**{"Tầng": tiers["tier"], "Vốn thuần": tiers["cost"].map(ui.vnd),
                        "Giá trị hiện tại": tiers["value"].map(ui.vnd), "Lãi/lỗ": tiers["pnl"].map(ui.vnd),
                        "% Lãi/lỗ": tiers["pnl_pct"].map(ui.pct), "Tỷ trọng": tiers["weight"].map(ui.pct)})
        [["Tầng", "Vốn thuần", "Giá trị hiện tại", "Lãi/lỗ", "% Lãi/lỗ", "Tỷ trọng"]],
        hide_index=True, width="stretch")
with col2:
    fig = px.pie(tiers, names="tier", values="value", hole=0.55, color="tier", color_discrete_map=ui.PALETTE)
    fig.update_traces(textinfo="percent+label", hovertemplate="%{label}: %{value:,.0f} ₫<extra></extra>")
    fig.update_layout(showlegend=False, margin=dict(t=10, b=10, l=10, r=10), height=260)
    st.plotly_chart(fig, width="stretch")

# --------------------------------------------------------------- assets
st.subheader("Hiệu suất từng tài sản")
rows = pd.DataFrame(h["rows"])
view = pd.DataFrame({
    "Mã": rows["code"], "Tên": rows["name"], "Tầng": rows["tier"],
    "Vốn thuần": rows["cost"], "Giá trị hiện tại": rows["value"], "Lãi/lỗ": rows["pnl"],
    "% Lãi/lỗ": rows["pnl_pct"] * 100, "XIRR": pd.to_numeric(rows["xirr"], errors="coerce") * 100, "Tỷ trọng": rows["weight"] * 100,
    "Cảnh báo": rows["warning"],
})
st.dataframe(view, hide_index=True, width="stretch", column_config={
    "Vốn thuần": st.column_config.NumberColumn(format="localized"),
    "Giá trị hiện tại": st.column_config.NumberColumn(format="localized"),
    "Lãi/lỗ": st.column_config.NumberColumn(format="localized"),
    "% Lãi/lỗ": st.column_config.NumberColumn(format="%.1f%%"),
    "XIRR": st.column_config.NumberColumn(format="%.2f%%", help="Tỷ suất quy năm theo dòng tiền"),
    "Tỷ trọng": st.column_config.ProgressColumn(format="%.1f%%", min_value=0, max_value=100),
})
fig = px.bar(rows.sort_values("value"), x="value", y="name", orientation="h", color="tier",
             color_discrete_map=ui.PALETTE, labels={"value": "Giá trị (₫)", "name": "", "tier": "Tầng"})
fig.update_layout(height=60 + 34 * len(rows), margin=dict(t=10, b=10), legend=dict(orientation="h", y=-0.15))
st.plotly_chart(fig, width="stretch")

# --------------------------------------------------------------- savings soon
soon = [s for s in h["savings"] if s["status"] in ("Sắp đáo hạn", "Quá hạn xử lý")]
if soon:
    st.subheader("Sổ tiết kiệm sắp/đã đáo hạn")
    st.dataframe(pd.DataFrame([{"Gói": s["name"], "Nhóm": s["code"], "Đáo hạn": ui.d(s["maturity"]),
                                "Nhận cuối kỳ": ui.vnd(s["received"]), "Trạng thái": s["status"],
                                "Mục đích": s.get("purpose")} for s in soon]),
                 hide_index=True, width="stretch")

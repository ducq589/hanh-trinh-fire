import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from fi_app import db, engine, style, ui

c, data, h, fp = ui.state()
style.title("chart-line", "Lịch sử tài sản ròng")
st.caption("App tự chụp 1 Snapshot mỗi tháng khi mở lần đầu trong tháng. Có thể chụp thêm bất cứ lúc nào.")

col1, col2 = st.columns([1, 3])
note = col2.text_input("Ghi chú cho lần chụp", placeholder="VD: sau khi nhận thưởng Tết")
if col1.button("Chụp ngay", type="primary", key=style.ic("camera", "chup")):
    db.save_snapshot(c, engine.snapshot(data, h, fp, note=note or "Chụp thủ công"))
    ui.flash("Đã lưu Snapshot hôm nay")
    st.rerun()

snaps = pd.DataFrame(data["snapshots"])
if snaps.empty:
    st.info("Chưa có Snapshot.")
    st.stop()
snaps["date"] = pd.to_datetime(snaps["date"])
fig = go.Figure()
fig.add_trace(go.Scatter(x=snaps["date"], y=snaps["net_worth"], name="Tài sản ròng", mode="lines+markers",
                         line=dict(color=style.TEXT, width=3)))
fig.add_trace(go.Scatter(x=snaps["date"], y=snaps["fire_assets"], name="Tài sản tính FIRE", mode="lines+markers",
                         line=dict(color=style.LIME, width=3)))
if snaps["fire_number"].notna().any():
    fig.add_trace(go.Scatter(x=snaps["date"], y=snaps["fire_number"], name="Số FIRE", line=dict(color=style.TARGET_FULL, dash="dash")))
fig.update_layout(height=400, margin=dict(t=10, b=10), hovermode="x unified", yaxis_tickformat=",.0f",
                  legend=dict(orientation="h", y=-0.15))
st.plotly_chart(style.fig(fig), width="stretch")
if len(snaps) == 1:
    st.caption("Mới có 1 điểm dữ liệu – biểu đồ sẽ rõ dần sau mỗi tháng.")

view = snaps.sort_values("date", ascending=False)
st.dataframe(pd.DataFrame({
    "Ngày": view["date"].dt.strftime("%d/%m/%Y"), "Tổng tài sản": view["total_assets"].map(ui.vnd),
    "Nợ": view["liabilities"].map(ui.vnd), "Tài sản ròng": view["net_worth"].map(ui.vnd),
    "Tài sản FIRE": view["fire_assets"].map(ui.vnd), "Số FIRE": view["fire_number"].map(ui.vnd),
    "% Full FIRE": view["fire_progress"].map(ui.pct), "Tỷ lệ tiết kiệm": view["savings_rate"].map(ui.pct),
    "Ghi chú": view["note"]}), hide_index=True, width="stretch")

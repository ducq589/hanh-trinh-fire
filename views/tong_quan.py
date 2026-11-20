import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from fi_app import db, engine, style, ui

c, data, h, fp = ui.state()

latest = max((r["price_date"] for r in h["rows"] if r["price_date"]), default=None)
style.title("home", "Tổng quan gia sản", f"Bức tranh tài chính của bạn · giá cập nhật đến {ui.d(latest)} · "
            f"{len(data['transactions'])} giao dịch · {len(data['assets'])} tài sản")

if not data["assets"]:
    with st.container(border=True):
        st.subheader("Chào mừng! Thiết lập trong 5 bước")
        st.caption("Mỗi bước tự đánh dấu ✓ khi bạn khai xong. Làm lần lượt – khoảng 15 phút.")
        ui.onboarding(data, fp, key="ob_new")
        with st.container(key=style.ic("book", "start_huong_dan")):
            st.page_link("views/huong_dan.py", label="Xem hướng dẫn chi tiết", width="stretch")
        st.caption("Thích khai trên Excel? Tải **file mẫu v4** ở trang **Sao lưu & Cài đặt**, điền xong tải lên 1 lần.")
    st.stop()

if not all(x["done"] for x in engine.onboarding(data, fp)) and data["settings"].get("onboarding_hidden") != "1":
    with st.expander("Hoàn tất thiết lập", expanded=True, key=style.ic("list-details", "ob_box")):
        ui.onboarding(data, fp, key="ob_rest")
        if st.button("Ẩn hướng dẫn", key=style.ic("circle-x", "ob_hide")):
            db.set_kv(c, "settings", {"onboarding_hidden": "1"})
            ui.flash("Đã ẩn – xem lại tiến độ ở trang Hướng dẫn")
            st.rerun()

# --------------------------------------------------------------- KPI cards
net = h["total_value"] - fp["debt"]
st.html(style.kpi_grid([
    style.kpi("Tổng tài sản", ui.tr(h["total_value"]),
              f"{'+' if h['total_pnl'] >= 0 else ''}{ui.pct(h['total_pnl_pct'])} so với vốn",
              lime=True, trend="up" if h["total_pnl"] >= 0 else "down", icon="wallet"),
    style.kpi("Lãi/lỗ", ui.tr(h["total_pnl"]), f"Vốn thuần {ui.tr(h['total_cost'])}", icon="trending-up"),
    style.kpi("Tài sản ròng", ui.tr(net), f"Đã trừ nợ {ui.tr(fp['debt'])}", icon="pig-money"),
    style.kpi("Tiến độ Full FIRE", ui.pct(fp["progress"]),
              (f"Đạt năm {fp['year_full']} · còn {ui.num(fp['years_full'], 1)} năm"
               if fp["year_full"] else "Cần khai Thu chi để tính"),
              progress=fp["progress"] or 0, icon="target"),
]))

st.write("")

# --------------------------------------------------------------- structure + side cards
left, right = st.columns([3, 2], gap="medium")
tiers = pd.DataFrame(h["tiers"])
with left:
    with st.container(border=True):
        st.subheader("Cơ cấu tài sản")
        d1, d2 = st.columns([1.1, 1])
        with d1:
            f = go.Figure(go.Pie(labels=tiers["tier"], values=tiers["value"], hole=0.58, sort=False,
                                 marker=dict(colors=[style.TIER_COLORS[t] for t in tiers["tier"]],
                                             line=dict(color=style.CARD, width=3)),
                                 textinfo="none", hovertemplate="%{label}: %{value:,.0f} ₫ (%{percent})<extra></extra>"))
            st.plotly_chart(style.fig(f, height=260, legend_bottom=False).update_layout(showlegend=False),
                            width="stretch", config={"displayModeBar": False})
        with d2:
            st.html(f'<div class="big-total"><div class="lb">Tổng giá trị</div>'
                    f'<div class="v">{style.esc(ui.tr(h["total_value"]))}</div></div><hr style="border-color:#333">')
            st.html(style.legend([(style.TIER_COLORS[t["tier"]], t["tier"],
                                   f"{ui.tr(t['value'])} · {ui.pct(t['weight'], 0)}") for t in h["tiers"]]))

with right:
    with st.container(border=True):
        proj = pd.DataFrame(fp["projection"])
        horizon = int(fp["years_full"] or 20) + 3 if fp["years_full"] is not None else 20
        proj = proj[proj["k"] <= min(horizon, 39)]
        st.caption("Tài sản FIRE dự phóng")
        st.html(f'<div class="big-total"><div class="v" style="color:#F2F2F2">{style.esc(ui.tr(fp["assets"]))}</div>'
                f'<div class="lb">mục tiêu {style.esc(ui.tr(fp["fire_number"]))}</div></div>')
        f = go.Figure()
        f.add_trace(go.Scatter(x=proj["year"], y=proj["assets"] / 1e9, mode="lines", line=dict(color=style.LIME, width=3,
                               shape="spline"), fill="tozeroy", fillcolor="rgba(182,243,106,0.08)",
                               hovertemplate="%{x}: %{y:.2f} tỷ<extra></extra>", name="Tài sản"))
        if fp["fire_number"]:
            f.add_hline(y=fp["fire_number"] / 1e9, line=dict(color=style.TARGET_FULL, dash="dot", width=1.5))
        f.update_yaxes(ticksuffix=" tỷ")
        st.plotly_chart(style.fig(f, height=170, legend_bottom=False).update_layout(showlegend=False),
                        width="stretch", config={"displayModeBar": False})
    with st.container(border=True):
        a1, a2 = st.columns([3, 2], vertical_alignment="center")
        a1.markdown("**Thao tác nhanh**")
        a1.caption("Ghi một lần mua DCA hoặc cập nhật giá")
        with a2.container(key=style.ic("plus", "lk_dca")):
            st.page_link("views/giao_dich.py", label="Mua DCA", width="stretch")
        with a2.container(key=style.ic("refresh", "lk_gia")):
            st.page_link("views/gia.py", label="Giá", width="stretch")

# --------------------------------------------------------------- reminders
rem = engine.reminders(data, h, fp)
urgent = [r for r in rem if r[0] != "info"]
with st.expander(f"Việc cần chú ý ({len(rem)})", expanded=bool(urgent), key=style.ic("bell", "nhacviec")):
    if not rem:
        st.success("Không có việc gì cần xử lý.")
    for level, head in (("error", "Cần xử lý ngay"), ("warning", "Nên làm sớm"), ("info", "Để ý")):
        items = [t for lv, t in rem if lv == level]
        if items:
            getattr(st, level)(f"**{head}**\n" + "\n".join(f"- {t}" for t in items))

# --------------------------------------------------------------- financial health (tóm tắt)
good, known = ui.health_summary(data, h, fp)
hc1, hc2 = st.columns([3, 1], vertical_alignment="center")
hc1.markdown(f"**Sức khoẻ tài chính:** {good}/{known} chỉ số ở mức tốt" if known
             else "**Sức khoẻ tài chính:** chưa đủ dữ liệu – hãy khai Thu chi")
with hc2.container(key=style.ic("circle-check", "lk_health")):
    st.page_link("views/ke_hoach_fire.py", label="Xem chi tiết", width="stretch")

# --------------------------------------------------------------- performance
with st.container(border=True):
    st.subheader("Hiệu suất từng tài sản")
    rows = pd.DataFrame(h["rows"])
    view = pd.DataFrame({
        "Tài sản": rows["name"], "Tầng": rows["tier"],
        "Giá trị hiện tại": rows["value"].map(ui.vnd), "Lãi/lỗ": rows["pnl"].map(ui.vnd),
        "% Lãi/lỗ": rows["pnl_pct"].map(ui.pct), "XIRR": [ui.xirr_label(r) for r in h["rows"]],
        "Tỷ trọng": rows["weight"] * 100, "Cảnh báo": rows["warning"],
    })
    st.dataframe(view, hide_index=True, width="stretch", column_config={
        "XIRR": st.column_config.TextColumn(help="Tỷ suất quy năm theo dòng tiền (– : không áp dụng)"),
        "Tỷ trọng": st.column_config.ProgressColumn(format="%.1f%%", min_value=0, max_value=100, color="#B6F36A"),
    })
    if any(r.get("xirr_since") and r.get("xirr") is not None for r in h["rows"]):
        st.caption(ui.XIRR_NOTE)

soon = [s for s in h["savings"] if s["status"] in ("Sắp đáo hạn", "Quá hạn xử lý")]
if soon:
    with st.container(border=True):
        st.subheader("Sổ tiết kiệm sắp / đã đáo hạn")
        st.dataframe(pd.DataFrame([{"Gói": s["name"], "Nhóm": s["code"], "Đáo hạn": ui.d(s["maturity"]),
                                    "Nhận cuối kỳ": ui.vnd(s["received"]), "Trạng thái": s["status"],
                                    "Mục đích": s.get("purpose")} for s in soon]),
                     hide_index=True, width="stretch")

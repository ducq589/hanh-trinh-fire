import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from fi_app import db, engine, style, ui

c, data, h, fp = ui.state()
st.title("🔥 Kế hoạch FIRE")
st.caption("FIRE – Financial Independence, Retire Early. Số liệu dự phóng tính theo **sức mua hôm nay** "
           "(đã trừ lạm phát). Các giả định chỉ là tham số để lập kế hoạch, không phải khuyến nghị đầu tư.")

if not fp["cf"]["expense"]:
    st.warning("Chưa có dữ liệu chi tiêu – hãy khai ở trang **Thu chi** để tính kế hoạch FIRE.")

# --------------------------------------------------------------- assumptions
with st.expander("⚙️ Giả định", expanded=False):
    a = data["assumptions"]
    with st.form("assump"):
        c1, c2, c3 = st.columns(3)
        age = c1.number_input("Tuổi hiện tại", 0, 100, int(engine.n(a.get("current_age")) or 0))
        tgt = c2.number_input("Tuổi mong muốn đạt FIRE", 0, 100, int(engine.n(a.get("target_age")) or 50))
        infl = c3.number_input("Lạm phát/năm (%)", 0.0, 20.0, engine.n(a.get("inflation")) * 100, 0.1)
        c4, c5, c6 = st.columns(3)
        auto = c4.checkbox("Lợi suất kỳ vọng tự tính", value=fp["return_is_auto"],
                           help=f"Bình quân gia quyền 'Lợi suất KV' của tài sản tính FIRE = {ui.pct(fp['return_auto'], 2)}")
        ret = c4.number_input("Lợi suất danh nghĩa/năm (%)", 0.0, 30.0, fp["return_nominal"] * 100, 0.1,
                              disabled=auto)
        swr = c5.number_input("Tỷ lệ rút an toàn SWR (%)", 1.0, 10.0, fp["swr"] * 100, 0.1,
                              help="Quy tắc 4%. Thận trọng hơn 3–3,5% nếu nghỉ sớm, thời gian rút dài.")
        em = c6.number_input("Quỹ khẩn cấp mục tiêu (tháng chi thiết yếu)", 1, 24, int(fp["emergency_target"]))
        if st.form_submit_button("Lưu giả định", type="primary"):
            db.set_kv(c, "assumptions", {"current_age": age or "", "target_age": tgt, "inflation": infl / 100,
                                         "return_nominal": "" if auto else ret / 100, "swr": swr / 100,
                                         "emergency_months": em})
            ui.flash("Đã lưu giả định")
            st.rerun()
    st.caption(f"Lợi suất thực sau lạm phát: **{ui.pct(fp['real'], 2)}** · Tài sản tính FIRE chọn ở trang **Tài sản** "
               f"(cột Tính FIRE?) · Nợ được trừ: {ui.vnd(fp['debt'])}")

# --------------------------------------------------------------- key metrics
k = st.columns(4)
k[0].metric("Số FIRE (Full)", ui.tr(fp["fire_number"]), help="Chi tiêu năm ÷ SWR")
k[1].metric("Tiến độ Full FIRE", ui.pct(fp["progress"]), help="Chỉ số 1: Tài sản tính FIRE ÷ Số FIRE")
k[2].metric("Thu nhập thụ động / Chi tiêu", ui.pct(fp["passive_ratio"]),
            help="Chỉ số 2: (rút bền vững từ danh mục + thu nhập thụ động khác) ÷ chi tiêu. ≥ 100% là đạt FIRE")
k[3].metric("Năm đạt Full FIRE", fp["year_full"] or "–",
            f"tuổi {fp['age_full']}" if fp["age_full"] else None, delta_color="off", delta_arrow="off")

st.subheader("Các mốc")
ms = pd.DataFrame([
    ("Lean FIRE", fp["lean"], fp["lean_progress"], fp["years_lean"], "Chỉ đủ chi thiết yếu"),
    ("Coast FIRE", fp["coast"], (fp["assets"] / fp["coast"]) if fp["coast"] else None, None,
     "Có đủ số này thì không cần góp thêm vẫn đạt FIRE ở tuổi mục tiêu"),
    ("Full FIRE", fp["fire_number"], fp["progress"], fp["years_full"], "Đủ trang trải toàn bộ chi tiêu"),
], columns=["Mốc", "Cần có", "Tiến độ", "Số năm nữa", "Ý nghĩa"])
st.dataframe(ms.assign(**{"Cần có": ms["Cần có"].map(ui.vnd), "Tiến độ": ms["Tiến độ"].map(ui.pct),
                          "Số năm nữa": ms["Số năm nữa"].map(lambda x: ui.num(x, 1) if x is not None else "–")}),
             hide_index=True, width="stretch")
c1, c2, c3 = st.columns(3)
c1.metric("Tài sản tính FIRE (ròng)", ui.tr(fp["assets"]), help=ui.vnd(fp["assets"]))
c2.metric("Đầu tư mỗi tháng", ui.tr(fp["invest"]), help="Khoản 'Đầu tư định kỳ' trong trang Thu chi")
c3.metric("Quỹ khẩn cấp", f"{ui.num(fp['emergency_months'], 1)} / {fp['emergency_target']:.0f} tháng"
          if fp["emergency_months"] is not None else "–",
          f"thiếu {ui.tr(fp['emergency_gap'])}" if fp["emergency_gap"] else "đủ",
          delta_color="inverse" if fp["emergency_gap"] else "normal", delta_arrow="off")


# --------------------------------------------------------------- what-if
st.subheader("Nếu… thì sao?")
w1, w2 = st.columns(2)
extra = w1.slider("Tăng đầu tư mỗi tháng thêm (triệu ₫)", 0.0, 30.0, 0.0, 0.5)
cut = w2.slider("Giảm tổng chi tiêu (%)", 0, 50, 0, 5)
alt = engine.fire_plan(data, h, extra_invest=extra * 1e6, expense_factor=1 - cut / 100)
if extra or cut:
    a1, a2, a3 = st.columns(3)
    a1.metric("Số FIRE mới", ui.tr(alt["fire_number"]),
              ui.tr(alt["fire_number"] - fp["fire_number"]) if alt["fire_number"] and fp["fire_number"] else None,
              delta_color="inverse")
    a2.metric("Năm đạt Full FIRE", alt["year_full"] or "–",
              f"{alt['year_full'] - fp['year_full']:+d} năm" if alt["year_full"] and fp["year_full"] else None,
              delta_color="inverse")
    a3.metric("Số năm nữa", ui.num(alt["years_full"], 1) if alt["years_full"] is not None else "–")

# --------------------------------------------------------------- projection
st.subheader("Dự phóng")
cur = alt if (extra or cut) else fp
proj = pd.DataFrame(cur["projection"])
horizon = st.slider("Số năm hiển thị", 5, 40, min(40, int(cur["years_full"] or 30) + 8))
proj = proj[proj["k"] < horizon]
fig = go.Figure()
fig.add_trace(go.Scatter(x=proj["year"], y=proj["assets"] / 1e9, name="Tài sản FIRE", line=dict(color=style.LIME, width=3),
                         fill="tozeroy", fillcolor="rgba(182,243,106,0.10)", hovertemplate="%{y:.2f} tỷ"))
fig.add_trace(go.Scatter(x=proj["year"], y=proj["full"] / 1e9, name="Mục tiêu Full FIRE",
                         line=dict(color=style.TARGET_FULL, dash="dash"), hovertemplate="%{y:.2f} tỷ"))
fig.add_trace(go.Scatter(x=proj["year"], y=proj["lean"] / 1e9, name="Mục tiêu Lean FIRE",
                         line=dict(color=style.TARGET_LEAN, dash="dot"), hovertemplate="%{y:.2f} tỷ"))
if cur["year_full"] and cur["year_full"] <= proj["year"].max():
    fig.add_vline(x=cur["year_full"], line=dict(color="#8A8A8A", dash="dot"),
                  annotation_text=f"Full FIRE {cur['year_full']}", annotation_position="top left")
fig.update_layout(height=420, margin=dict(t=30, b=10), hovermode="x unified",
                  legend=dict(orientation="h", y=-0.15), yaxis_title="tỷ ₫ (sức mua hôm nay)")
st.plotly_chart(style.fig(fig).update_layout(margin=dict(t=30)), width="stretch")
with st.expander("Bảng dự phóng"):
    st.dataframe(pd.DataFrame({
        "Năm": proj["year"], "Tuổi": proj["age"], "Tài sản FIRE": proj["assets"].map(ui.vnd),
        "% Full FIRE": proj["pct"].map(ui.pct), "Full FIRE (tiền danh nghĩa)": proj["full_nominal"].map(ui.vnd),
        "Mốc": proj["milestone"]}), hide_index=True, width="stretch")
st.caption("Giả định: góp đều hằng tháng theo sức mua hôm nay (tăng theo lạm phát), lãi kép theo tháng, lợi suất thực "
           "không đổi. Kết quả khớp với sheet FI_Plan của file Excel v3.")

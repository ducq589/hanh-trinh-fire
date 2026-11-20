"""Trang Giới thiệu: vì sao có app, app đồng hành thế nào trên hành trình tới tự do tài chính, và cam kết."""
import plotly.graph_objects as go
import streamlit as st

from fi_app import engine, intro, legal, style, ui

intro.css()
style.title("info-circle", "Giới thiệu Hành trình FIRE", intro.TAGLINE)
st.html(f'<span class="pill">{style.svg("circle-check", 16, style.LIME)}{intro.PROMISE_SHORT}</span>')
st.write("")

t_app, t_feat, t_story, t_journey, t_example, t_faq = st.tabs(
    ["Về app", "Tính năng", "Câu chuyện", "Hành trình", "Ví dụ tính", "Hỏi đáp"], key="tabs_gt")
style.tab_icons("tabs_gt", ["info-circle", "stack-2", "user", "target", "calculator", "help-circle"])

with t_app:
    st.subheader("App giúp bạn điều gì")
    intro.values()
    st.subheader("Cam kết của app")
    intro.promise_card()

with t_feat:
    st.subheader("Tính năng nổi bật")
    st.caption("Mỗi thẻ có nút mở thẳng trang tương ứng.")
    intro.features()

with t_story:
    st.subheader("Vì sao tôi xây dựng app này")
    intro.why_story()

with t_journey:
    st.subheader("Hành trình 4 chặng tới tự do tài chính")
    st.caption("Mỗi chặng kèm trang của app giúp bạn thực hiện.")
    intro.journey()
    st.subheader("Nguyên tắc cốt lõi")
    intro.principles()

# --------------------------------------------------------------- ví dụ minh hoạ
with t_example:
    st.subheader("Ví dụ: bạn mới đi làm, bắt đầu từ vốn nhỏ")
    with st.container(border=True):
        s1, s2, s3 = st.columns(3)
        invest = s1.slider("Đầu tư mỗi tháng (triệu ₫)", 0.5, 30.0, 3.0, 0.5, key="ex_invest")
        spend = s2.slider("Chi tiêu mỗi tháng (triệu ₫)", 3.0, 60.0, 10.0, 0.5, key="ex_spend")
        real = s3.slider("Lợi suất thực giả định (%/năm)", 1.0, 10.0, 6.0, 0.5, key="ex_ret",
                         help="Lợi suất sau khi trừ lạm phát – giả định để minh hoạ, không phải cam kết")
        i = (1 + real / 100) ** (1 / 12) - 1                  # lãi kép theo tháng
        full = spend * 1e6 * 12 / 0.04                         # quy tắc 25 lần – 4%
        lean = full * 0.6                                      # Lean FIRE: chỉ phần chi thiết yếu (~60%)
        n_full = engine.nper(i, -invest * 1e6, 0, full)
        n_lean = engine.nper(i, -invest * 1e6, 0, lean)
        yrs = lambda n: f"{n / 12:.1f} năm".replace(".", ",") if n else "–"   # noqa: E731
        st.html(style.kpi_grid([
            style.kpi("Số Full FIRE", ui.tr(full), "= chi tiêu năm × 25", lime=True, icon="target"),
            style.kpi("Số Lean FIRE", ui.tr(lean), "chỉ chi thiết yếu (~60%)", icon="pig-money"),
            style.kpi("Đạt Lean FIRE sau", yrs(n_lean), f"đầu tư {ui.num(invest, 1)} tr/tháng", icon="clock"),
            style.kpi("Đạt Full FIRE sau", yrs(n_full), f"lợi suất thực {ui.num(real, 1)}%/năm", icon="flame"),
        ]))
        horizon = int(min(50, max(10, (n_full or 600) / 12 + 3)))
        xs = list(range(horizon + 1))
        ys = [engine.fv(i, 12 * y, -invest * 1e6, 0) / 1e9 for y in xs]
        f = go.Figure(go.Scatter(x=xs, y=ys, mode="lines", line=dict(color=style.LIME, width=3, shape="spline"),
                                 fill="tozeroy", fillcolor="rgba(182,243,106,0.08)", name="Tài sản",
                                 hovertemplate="Năm %{x}: %{y:.2f} tỷ<extra></extra>"))
        f.add_hline(y=full / 1e9, line=dict(color=style.TARGET_FULL, dash="dot"), annotation_text="Full FIRE")
        f.add_hline(y=lean / 1e9, line=dict(color=style.TARGET_LEAN, dash="dot"), annotation_text="Lean FIRE")
        f.update_xaxes(title="Số năm tích luỹ")
        f.update_yaxes(ticksuffix=" tỷ")
        st.plotly_chart(style.fig(f, height=300, legend_bottom=False).update_layout(showlegend=False),
                        width="stretch", config={"displayModeBar": False})
        st.html(style.tip(intro.EXAMPLE_NOTE + " Muốn tính bằng số liệu thật của bạn? Vào <b>Kế hoạch FIRE</b>."))

with t_faq:
    st.subheader("Câu hỏi thường gặp về an toàn")
    intro.faq()
    st.html(legal.links_html())

st.write("")
with st.container(key=style.ic("rocket", "intro_start")):
    st.page_link("views/huong_dan.py", label="Bắt đầu: xem Hướng dẫn thiết lập lần đầu", width="stretch")

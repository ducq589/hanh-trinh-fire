"""Bài học "Nền tảng tài chính" ở cuối trang Thu chi: theo dõi chi tiêu và lập ngân sách cho người mới đi làm.

Muốn sửa câu chữ: chỉ cần sửa các hằng số ở phần đầu file (cho phép thẻ <b>, <i>, <br>).
"""
from __future__ import annotations

import streamlit as st

from . import engine, intro, style

# =====================================================================  NỘI DUNG (sửa ở đây)
WHY_EARLY = [  # (icon, tiêu đề, mô tả)
    ("pig-money", "Ít tiền càng dễ tập",
     "Tập thói quen khi thu nhập còn 5–10 triệu/tháng thì khi thu nhập lên 30–40 triệu bạn vẫn kiểm soát được – "
     "thay vì càng kiếm nhiều càng tiêu nhiều."),
    ("chart-donut", "Thấy dòng tiền mới kiểm soát được",
     "Không thể tiết kiệm nếu không biết tiền <b>đi vào</b> và <b>đi ra</b> như thế nào mỗi tháng."),
    ("bulb", "Giai đoạn “sai rẻ” nhất",
     "Khi còn trẻ, chưa có người phụ thuộc, sai một chút vẫn còn gia đình hỗ trợ. Cùng sai lầm ấy ở tuổi 30–40 "
     "sẽ đắt hơn nhiều."),
]

TRACK_STEPS = [
    ("Liệt kê thu nhập và chi tiêu",
     "Ghi lại mọi nguồn tiền nhận được và mọi khoản đã chi để hiểu rõ tình hình hiện tại."),
    ("Phân loại các khoản",
     "Thu nhập: <b>chính · phụ · bất thường</b>. Chi tiêu: <b>thiết yếu · không thiết yếu · bất thường</b> "
     "(xem bảng đối chiếu bên dưới)."),
    ("Đánh giá lại (review)",
     "Dành 15–30 phút mỗi cuối tuần hoặc cuối tháng: khoản nào chi nhiều nhất? phân loại đã đúng chưa? "
     "khoản nào khiến bạn <b>hối tiếc</b>? mục tiêu cho tháng sau là gì?"),
]

CATEGORY_MAP = """
| Nhóm trong bài học | Ví dụ | Khai trong app (bảng thu chi ở trên) |
|---|---|---|
| Thu nhập **chính** | lương cứng, tiền gia đình chu cấp đều đặn | **Thu nhập chủ động** |
| Thu nhập **phụ** | freelance, bán hàng online | **Thu nhập chủ động** – khai **mức thấp nhất** |
| Thu nhập **bất thường** | lì xì, học bổng, quà tặng | **Không khai** – đừng dựa vào để chi tiêu |
| Chi **thiết yếu** | ăn uống cơ bản, nhà trọ, điện nước, xăng xe | **Chi thiết yếu** |
| Chi **không thiết yếu** | ăn ngoài, cà phê, xem phim, mua sắm | **Chi linh hoạt** |
| Chi **bất thường / phát sinh** | sửa xe, ốm đau, đám cưới | Ước tính cả năm → **Chi linh hoạt**, tần suất *Năm*; biến cố lớn dùng **Quỹ khẩn cấp** |
| **Tích luỹ** (trả cho mình trước) | tiền trích ra ngay khi nhận lương | **Đầu tư định kỳ** |
"""

TOOLS = [  # (icon, tiêu đề, mô tả)
    ("edit", "Sổ tay / ghi chú điện thoại · ★★½",
     "<b>+</b> Dễ bắt đầu.<br><b>−</b> Bất tiện khi mang theo, dễ cộng nhầm, sổ giấy có thể mất dữ liệu."),
    ("device-floppy", "App quản lý chi tiêu · ★★★★",
     "<b>+</b> Tiện lợi, có sẵn biểu đồ.<br><b>−</b> Thường tốn phí duy trì; dữ liệu thói quen chi tiêu nằm ở bên thứ ba."),
    ("file-spreadsheet", "File Excel · nên dùng",
     "<b>+</b> Miễn phí, dữ liệu của riêng bạn, tuỳ biến biểu đồ, rèn luôn kỹ năng tin học văn phòng."
     "<br><b>−</b> Cần tự thiết kế hoặc dùng một file mẫu."),
]

MISTAKES = [
    "Chỉ ghi số tiền mà <b>không phân nhóm</b> – cuối tháng không biết tiền đi đâu.",
    "Ghi <b>quá chi tiết</b> từng món nhỏ lẻ – nhanh nản và bỏ cuộc.",
    "Chỉ ghi mà <b>không bao giờ xem lại</b> – dữ liệu không giúp thay đổi hành vi.",
    "<b>Đổi phương pháp liên tục</b> làm đứt gãy dữ liệu – giữ một cách ít nhất 3 tháng rồi mới đổi.",
]

BUDGET_STEPS = [
    ("Chọn phương pháp phù hợp", "Phong bì, 50/30/20 hoặc Trả cho mình trước (so sánh bên dưới)."),
    ("Ước tính thu nhập dự kiến",
     "Lấy mức <b>cố định</b> của thu nhập chính + mức <b>thấp nhất</b> của thu nhập phụ. "
     "<b>Không</b> tính thu nhập bất thường."),
    ("Dự kiến các khoản chi", "Dựa trên số liệu đã theo dõi, cộng thêm <b>5–10% dự phòng</b> cho phát sinh."),
    ("Cân đối thu – chi",
     "<b>Dương</b>: đưa phần dư vào tiết kiệm/đầu tư. <b>Âm</b>: cắt khoản không thiết yếu hoặc tìm cách tăng thu nhập."),
]

METHODS = [  # (icon, tiêu đề, mô tả)
    ("wallet", "Phong bì / 6 chiếc hũ · ★★",
     "Chia tiền vào từng mục riêng.<br><b>+</b> Kiểm soát chặt.<br><b>−</b> Cứng nhắc, tốn công chia, dễ nản khi có biến cố."),
    ("chart-pie", "Quy tắc 50/30/20 · ★★★",
     "50% thiết yếu · 30% không thiết yếu · 20% tiết kiệm/đầu tư.<br><b>+</b> Đơn giản, dễ nhớ."
     "<br><b>−</b> Tỷ lệ cố định không hợp với mọi mức thu nhập."),
    ("target", "Trả cho mình trước · ★★★★",
     "Nhận tiền là trích ngay <b>10–20%</b> vào tiết kiệm/đầu tư, phần còn lại mới chi tiêu."
     "<br><b>+</b> Hiệu quả nhất.<br><b>−</b> Cần biết rõ mức chi tối thiểu của bản thân."),
]

OVER_BUDGET = [  # (icon, tiêu đề, mô tả)
    ("adjustments", "Vượt vì ngân sách đặt quá thấp",
     "Ngân sách chưa sát thực tế – điều chỉnh lại cho tháng sau dựa trên số đã chi."),
    ("alert-triangle", "Vượt vì thiếu kỷ luật",
     "Thay đổi hành vi: <b>gỡ liên kết thẻ/ví</b> khỏi app mua sắm, <b>cất thẻ</b> ở chỗ khó lấy, áp dụng "
     "<b>quy tắc chờ 72 giờ</b> trước khi bấm mua."),
]

FOUR_WEEKS = [
    ("Tuần 1 – Ghi chép", "Ghi lại mọi khoản thu, chi."),
    ("Tuần 2 – Phân loại", "Xếp các khoản đã ghi vào đúng nhóm."),
    ("Tuần 3 – Lập ngân sách", "Thử đặt ngân sách cho thời gian tới."),
    ("Tuần 4 – Review", "Nhìn lại cả quá trình, rút kinh nghiệm và lặp lại chu kỳ ở các tháng sau."),
]

APPLY = {
    "why": "Bảng <b>Hồ sơ thu chi</b> ở trên chính là bức tranh dòng tiền của bạn – khai xong là thấy ngay tỷ lệ tiết kiệm.",
    "track": "Trong app <b>không cần ghi hằng ngày</b>. Theo dõi chi tiết 1–3 tháng bằng công cụ bạn thích, lấy "
             "<b>số trung bình mỗi tháng</b> khai vào bảng ở trên rồi bấm <b>Đã rà soát hôm nay</b> – app nhắc rà soát "
             "lại sau 90 ngày.",
    "budget": "Khoản <b>Đầu tư định kỳ</b> chính là “trả cho mình trước”: app trừ khoản này trước, và cảnh báo khi "
              "cam kết đầu tư vượt dòng tiền dư.",
    "over": "Vào <b>Kế hoạch FIRE → Nếu… thì sao?</b>, kéo thanh <i>Giảm tổng chi tiêu</i> để thấy cắt bớt chi linh hoạt "
            "kéo năm đạt FIRE gần lại bao nhiêu.",
    "weeks": "Cuối tuần 4: khai số điển hình vào <b>Hồ sơ thu chi</b> ở trên, bấm <b>Đã rà soát hôm nay</b>, rồi xem "
             "<b>Kế hoạch FIRE</b> của bạn.",
}


# =====================================================================  GIAO DIỆN
def _apply(key: str) -> None:
    st.html(style.tip("<b>Áp dụng trong app:</b> " + APPLY[key]))


def _grade(ok: bool, warn: bool) -> str:
    return "Đạt" if ok else ("Gần đạt" if warn else "Chưa đạt")


def _budget_check(cf: dict) -> None:
    st.markdown("**Ngân sách của bạn so với các quy tắc**")
    b = engine.budget_check(cf)
    if b is None:
        st.info("Khai thu nhập ở bảng **Hồ sơ thu chi** phía trên để so sánh.")
        return
    pct = lambda x: f"{x:.0%}"   # noqa: E731
    st.html(style.kpi_grid([
        style.kpi("Chi thiết yếu", pct(b["essential"]),
                  f"Mốc 50% · {_grade(b['essential'] <= .5, b['essential'] <= .6)}",
                  trend="up" if b["essential"] <= .5 else "down", icon="home"),
        style.kpi("Chi linh hoạt", pct(b["flexible"]),
                  f"Mốc 30% · {_grade(b['flexible'] <= .3, b['flexible'] <= .35)}",
                  trend="up" if b["flexible"] <= .3 else "down", icon="coin"),
        style.kpi("Tích luỹ", pct(b["save"]),
                  f"Đầu tư + phần dư · Mốc 20% · {_grade(b['save'] >= .2, b['save'] >= .1)}",
                  lime=b["save"] >= .2, trend="up" if b["save"] >= .2 else "down", icon="pig-money"),
        style.kpi("Trả cho mình trước", pct(b["pay_first"]),
                  f"Mốc 10–20% · {_grade(b['pay_first'] >= .1, b['pay_first'] > 0)}",
                  trend="up" if b["pay_first"] >= .1 else "down", icon="target"),
    ]))
    tr = lambda x: f"{x / 1e6:.1f}".replace(".", ",")   # noqa: E731
    st.caption(f"Gợi ý: thêm dòng **Dự phòng phát sinh** khoảng 5–10% chi tiêu (≈ {tr(b['buffer_low'])}–"
               f"{tr(b['buffer_high'])} tr/tháng) vào nhóm *Chi linh hoạt*. Các mốc chỉ để tham khảo – hãy điều "
               "chỉnh theo hoàn cảnh của bạn.")


def render(cf: dict) -> None:
    """5 khung bài học ở cuối trang Thu chi."""
    intro.css()
    st.subheader("Nền tảng tài chính – học từ sớm")
    st.caption("Dành cho sinh viên và người mới đi làm: hai kỹ năng cốt lõi là **theo dõi chi tiêu** và **lập ngân sách**.")

    with st.expander("1 · Vì sao nên quản lý tài chính từ sớm?", key=style.ic("bulb", "ls_why")):
        st.html(intro._cards(WHY_EARLY))
        _apply("why")

    with st.expander("2 · Theo dõi chi tiêu – nhìn lại quá khứ", key=style.ic("receipt", "ls_track")):
        st.html(style.steps(TRACK_STEPS))
        st.markdown("**Phân loại thu – chi và cách khai trong app**")
        st.markdown(CATEGORY_MAP)
        st.markdown("**Chọn công cụ theo dõi**")
        st.html(intro._cards(TOOLS))
        st.markdown("**4 sai lầm thường gặp**")
        st.html('<div class="promise one"><div class="col no"><ul>' + "".join(
            f"<li>{style.svg('circle-x', 18, '#FF7A6B')}<span>{m}</span></li>" for m in MISTAKES) + "</ul></div></div>")
        _apply("track")

    with st.expander("3 · Lập ngân sách – chủ động cho tương lai", key=style.ic("calculator", "ls_budget")):
        st.caption("Theo dõi chi tiêu là nhìn về quá khứ; lập ngân sách là phân bổ tiền **trước khi tiêu**.")
        st.html(style.steps(BUDGET_STEPS))
        st.markdown("**3 phương pháp phổ biến**")
        st.html(intro._cards(METHODS))
        _budget_check(cf)
        _apply("budget")

    with st.expander("4 · Khi vượt ngân sách & mẹo kiểm soát", key=style.ic("alert-triangle", "ls_over")):
        st.html(intro._cards(OVER_BUDGET))
        _apply("over")

    with st.expander("5 · Lộ trình thực hành 4 tuần", key=style.ic("calendar-event", "ls_weeks")):
        st.html(style.steps(FOUR_WEEKS))
        _apply("weeks")
        with st.container(key=style.ic("arrow-right", "ls_go_fire")):
            st.page_link("views/ke_hoach_fire.py", label="Xem Kế hoạch FIRE", width="stretch")


# =====================================================================  BÀI HỌC: QUỸ KHẨN CẤP (trang Tiết kiệm)
EM_WHAT = [  # (icon, tiêu đề, mô tả)
    ("alert-triangle", "Quỹ khẩn cấp là gì?",
     "Khoản tiền để dành riêng, <b>chỉ dùng khi có chuyện bất ngờ</b>: ốm đau, nằm viện, sửa xe, sửa nhà, "
     "mất việc hay mất thu nhập (như nhiều người đã gặp thời Covid)."),
    ("building-bank", "Vì sao phải để riêng?",
     "Để chung với tiền tiêu hằng ngày thì rất dễ lỡ tay tiêu mất. Nên mở <b>một tài khoản riêng</b> chỉ cho khoản này."),
    ("coin", "Giữ thêm ít tiền mặt",
     "Luôn có một ít tiền mặt trong ví hoặc ở nhà – gặp việc gấp ngoài đường không phải động tới quỹ."),
]

EM_SIZE_TABLE = """
| Hoàn cảnh | Không ai phụ thuộc | 1–2 người phụ thuộc | 3–4 người phụ thuộc |
|---|---|---|---|
| Độc thân | 6 tháng | 12 tháng | 18 tháng |
| Vợ chồng đều có thu nhập | 3 tháng | 6 tháng | 12 tháng |
"""
EM_SIZE_NOTE = ("Tính theo <b>chi tiêu bắt buộc</b> (tiền nhà, ăn uống, điện nước, bảo hiểm…) – không tính mua sắm, du lịch. "
                "<b>Người phụ thuộc</b> là người sống nhờ thu nhập của bạn: con đang đi học, bố mẹ không còn đi làm và "
                "không có lương hưu. Làm tự do hay tự kinh doanh thì nên để nhiều hơn vì thu nhập thất thường.")

EM_FIRST = [  # (icon, tiêu đề, mô tả)
    ("user", "Mới ra trường, còn ở với bố mẹ",
     "Để dành <b>1–2 tháng chi tiêu</b> là đủ bước đầu, sau đó vừa đầu tư vừa để dành tiếp cho đủ quỹ."),
    ("home", "Đã có gia đình / nhiều trách nhiệm",
     "Làm <b>quỹ khẩn cấp trước</b>. Đã đầu tư nhiều mà chưa có quỹ thì nên tạm dừng đầu tư để bổ sung – vì chuyện "
     "xui thường đến cùng lúc: kinh tế khó dễ mất việc, đúng lúc khoản đầu tư đang lỗ, phải bán ra là thiệt."),
]

EM_WHERE_RULES = [
    "<b>Rút được nhanh</b> – trong vòng 24 giờ.",
    "<b>An toàn</b> – không mất tiền gốc.",
    "<b>Lãi cao hơn trượt giá</b> – tiền nằm im 5 năm thì 10 triệu bây giờ chỉ còn sức mua khoảng 8 triệu.",
]
EM_WHERE = [  # (icon, tiêu đề, mô tả)
    ("pig-money", "Tiết kiệm có kỳ hạn ở ngân hàng",
     "<b>+</b> An toàn, lãi kỳ hạn tốt hơn hẳn.<br><b>−</b> Rút trước hạn mất lãi – nên chia nhiều sổ (bên dưới). "
     "Không nên để ở tài khoản <b>không kỳ hạn</b> vì lãi chỉ khoảng 0,1%/năm."),
    ("chart-line", "Quỹ trái phiếu",
     "<b>+</b> Mua từng ít một (vài chục nghìn mỗi tuần), rút ra không mất lãi đã tích luỹ."
     "<br><b>−</b> Giá có thể lên xuống (cuối năm 2022 có quỹ giảm khoảng 20%), có thể mất phí mua/bán – "
     "chỉ nên giữ <b>một phần</b> quỹ khẩn cấp ở đây."),
]

EM_LADDER_NOTE = ("Khi có chuyện gấp thường chỉ cần khoảng <b>10–20%</b> quỹ. Chia thành nhiều sổ với kỳ hạn khác nhau, "
                  "sổ nào đến hạn thì gửi tiếp: vẫn hưởng lãi cao mà lúc cần vẫn có tiền rút ngay.")

EM_APPLY = {
    "what": "App tính quỹ khẩn cấp từ tài sản có mã <b>QKC</b>. Tạo tài sản này ở trang <b>Tài sản</b> (loại Tiết kiệm/"
            "Tiền mặt) hoặc gán các sổ dành cho quỹ vào mã QKC ở tab <b>Sổ tiết kiệm</b>.",
    "size": "Số tháng tính ở trên có thể đặt làm <b>mục tiêu quỹ khẩn cấp</b> – app dùng nó ở bảng "
            "Sức khoẻ tài chính và mốc thành tựu <i>Quỹ khẩn cấp đủ</i>.",
    "first": "Bảng <b>Sức khoẻ tài chính</b> ở trang Kế hoạch FIRE cho biết quỹ hiện đủ bao nhiêu tháng và còn thiếu bao nhiêu.",
    "ladder": "Mỗi phần là một dòng ở tab <b>Sổ tiết kiệm</b> phía trên (mã QKC) – app nhắc khi sổ sắp đáo hạn để bạn gửi tiếp.",
}


def _em_calculator(c, data: dict, fp: dict) -> None:
    from . import db
    essential = fp["cf"]["essential"]
    st.markdown("**Tính quỹ khẩn cấp của bạn**")
    if not essential:
        st.info("Khai khoản **Chi thiết yếu** ở trang **Thu chi** để app tính quỹ khẩn cấp theo số liệu của bạn.")
        return
    a1, a2, a3 = st.columns(3)
    household = a1.selectbox("Hoàn cảnh", engine.HOUSEHOLDS, key="em_house")
    dependents = a2.selectbox("Người phụ thuộc", engine.DEPENDENTS, key="em_dep")
    save = a3.number_input("Để dành mỗi tháng (triệu ₫)", 0.0, 500.0,
                           round(max(0.0, fp["cf"]["surplus"]) / 1e6, 1), 0.5, key="em_save")
    freelance = st.checkbox(f"Thu nhập tự do / tự kinh doanh (để thêm {engine.FREELANCE_EXTRA} tháng)", key="em_free")
    p = engine.emergency_plan(essential, fp["emergency_value"], household, dependents, freelance, save * 1e6)
    tr = lambda x: f"{x / 1e6:,.1f} tr".replace(",", "§").replace(".", ",").replace("§", ".")   # noqa: E731
    st.html(style.kpi_grid([
        style.kpi("Nên có", f"{p['months']} tháng", f"chi bắt buộc {tr(essential)}/tháng", icon="target"),
        style.kpi("Số tiền mục tiêu", tr(p["target"]), f"{p['months']} × chi bắt buộc", lime=True, icon="pig-money"),
        style.kpi("Đang có (mã QKC)", tr(p["current"]), f"{p['progress']:.0%} mục tiêu" if p["progress"] is not None else "",
                  progress=p["progress"], icon="wallet"),
        style.kpi("Đủ quỹ sau", "Đã đủ" if p["gap"] == 0 else
                  (f"{p['months_to_goal']} tháng" if p["months_to_goal"] else "–"),
                  f"còn thiếu {tr(p['gap'])}" if p["gap"] else "", icon="clock"),
    ]))
    current_target = int(fp["emergency_target"])
    if p["months"] != current_target:
        if st.button(f"Đặt {p['months']} tháng làm mục tiêu quỹ khẩn cấp (hiện {current_target} tháng)",
                     key=style.ic("target", "em_set")):
            db.set_kv(c, "assumptions", {"emergency_months": p["months"]})
            from . import ui
            ui.flash(f"Đã đặt mục tiêu quỹ khẩn cấp {p['months']} tháng chi thiết yếu")
            st.rerun()
    else:
        st.caption(f"Mục tiêu quỹ khẩn cấp trong app đang là **{current_target} tháng** – khớp với hoàn cảnh đã chọn.")

    st.markdown("**Chia quỹ thành nhiều sổ**")
    scheme = st.radio("Cách chia", list(engine.LADDERS), horizontal=True, key="em_ladder", index=1)
    st.dataframe([{"Kỳ hạn": lb, "Tỷ lệ": f"{pc:.0%}", "Số tiền": tr(amt)}
                  for lb, pc, amt in engine.ladder(p["target"], scheme)], hide_index=True, width="stretch")


def render_emergency(c, data: dict, fp: dict) -> None:
    """Bài học Xây dựng quỹ khẩn cấp – cuối trang Tiết kiệm, Mục tiêu & Nợ."""
    intro.css()
    st.subheader("Xây dựng quỹ khẩn cấp – lớp đệm an toàn")
    st.caption("Nền móng đầu tiên trước khi tăng tốc đầu tư: một khoản tiền sẵn sàng cho những chuyện không ai muốn.")

    with st.expander("1 · Quỹ khẩn cấp là gì, vì sao phải để riêng?", key=style.ic("alert-triangle", "em_what")):
        st.html(intro._cards(EM_WHAT))
        st.html(style.tip("<b>Áp dụng trong app:</b> " + EM_APPLY["what"]))

    with st.expander("2 · Cần bao nhiêu tiền? – máy tính theo hoàn cảnh của bạn",
                     key=style.ic("calculator", "em_size")):
        st.markdown(EM_SIZE_TABLE)
        st.html(f'<div class="story"><p>{EM_SIZE_NOTE}</p></div>')
        _em_calculator(c, data, fp)
        st.html(style.tip("<b>Áp dụng trong app:</b> " + EM_APPLY["size"]))

    with st.expander("3 · Đầu tư trước hay làm quỹ khẩn cấp trước?", key=style.ic("help-circle", "em_first")):
        st.html(intro._cards(EM_FIRST))
        st.html(style.steps([("Ví dụ", "Thu nhập 15 triệu/tháng, chi bắt buộc khoảng 6,3 triệu → quỹ 6 tháng ≈ 38 triệu, "
                                       "quỹ 1 năm ≈ 76 triệu. Bớt một phần tiền đầu tư và cắt bớt mua sắm để dành được "
                                       "khoảng 6 triệu/tháng thì <b>chỉ hơn 6 tháng</b> là có quỹ 6 tháng, thay vì gần 8 "
                                       "tháng. Ý chính: <b>biết rõ chi tiêu hằng tháng</b> giúp để dành nhanh hơn.")]))
        st.html(style.tip("<b>Áp dụng trong app:</b> " + EM_APPLY["first"]))

    with st.expander("4 · Để tiền ở đâu & chia thành nhiều sổ", key=style.ic("building-bank", "em_where")):
        st.markdown("**Nơi gửi cần đủ 3 điều**")
        st.html('<div class="promise one"><div class="col"><ul>' + "".join(
            f"<li>{style.svg('circle-check', 18, style.LIME)}<span>{r}</span></li>" for r in EM_WHERE_RULES)
            + "</ul></div></div>")
        st.html(intro._cards(EM_WHERE))
        st.markdown("**Chia nhiều phần, không gửi một chỗ**")
        st.html(f'<div class="story"><p>{EM_LADDER_NOTE}</p></div>')
        st.markdown("- **50/50**: nửa gửi kỳ hạn dài (lãi cao), nửa gửi ngắn (2 tuần – 1 tháng).\n"
                    "- **50/30/20**: dài hạn 8–13 tháng · trung hạn 3–5 tháng · ngắn hạn 1 tháng.\n"
                    "- **40/30/20/10**: tương tự nhưng chia nhỏ hơn.\n\n"
                    "Bảng số tiền theo từng cách chia nằm ở **mục 2** (theo quỹ mục tiêu của bạn).")
        st.html(style.tip("<b>Áp dụng trong app:</b> " + EM_APPLY["ladder"]))
        st.caption("Mức lãi suất và sản phẩm thay đổi theo thời gian – app không khuyến nghị nơi gửi cụ thể.")

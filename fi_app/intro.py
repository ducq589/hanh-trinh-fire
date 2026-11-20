"""Nội dung phần Giới thiệu app – dùng chung cho trang Giới thiệu và màn hình đăng nhập.

Muốn sửa câu chữ: chỉ cần sửa các hằng số ở phần đầu file (cho phép thẻ <b>, <i>, <br>).
"""
from __future__ import annotations

import streamlit as st

from . import style

# =====================================================================  NỘI DUNG (sửa ở đây)
TAGLINE = "Nhìn rõ con đường – bám sát mục tiêu tự do tài chính"

VALUES = [  # (icon Tabler, tiêu đề, mô tả)
    ("wallet", "Một nơi cho mọi tài sản",
     "Quỹ mở, cổ phiếu, tiết kiệm, vàng, bảo hiểm… gom về một bức tranh, giá tự cập nhật mỗi ngày."),
    ("target", "Kế hoạch FIRE theo số của bạn",
     "Từ thu chi và tài sản thật, app tính số tiền cần có và năm bạn có thể đạt tự do tài chính."),
    ("repeat", "Đồng hành mỗi tháng",
     "Không cần ghi chi tiêu hằng ngày – khai một lần, cập nhật khi có giao dịch, app nhắc việc cần làm."),
]

APP_DOES = [
    "Lập kế hoạch tự do tài chính từ số liệu của chính bạn",
    "Theo dõi tài sản, lãi/lỗ, tỷ trọng và tiến độ FIRE",
    "Nhắc việc: giá cũ, sổ sắp đáo hạn, cần tái cân bằng, rà soát thu chi",
]
APP_DOES_NOT = [
    "Không giữ tiền, <b>không yêu cầu nạp tiền</b> dưới bất kỳ hình thức nào",
    "Không mua/bán hộ, không kết nối tài khoản giao dịch của bạn",
    "<b>Không khuyến nghị</b> mã, sản phẩm hay thời điểm đầu tư",
    "Không phải dịch vụ tư vấn đầu tư",
]
PROMISE_NOTE = ("Mọi quyết định và giao dịch do bạn tự thực hiện tại nơi bạn mở tài khoản (công ty chứng khoán, "
                "công ty quỹ, ngân hàng…). App chỉ ghi lại và tính toán để bạn nhìn rõ hành trình của mình.")
PROMISE_SHORT = "Chỉ lập kế hoạch & theo dõi – không giữ tiền, không yêu cầu nạp tiền, không khuyến nghị đầu tư."

STORY = [
    "Như nhiều người trẻ, tôi bắt đầu tích sản bằng những khoản nhỏ: mỗi tháng vài triệu mua chứng chỉ quỹ, "
    "thêm ít cổ phiếu, vài sổ tiết kiệm online, một chút vàng và một hợp đồng bảo hiểm.",
    "Đa dạng hoá là đúng – nhưng chẳng bao lâu tài sản của tôi nằm rải rác ở năm, sáu ứng dụng khác nhau. "
    "Muốn biết <b>tổng mình đang có bao nhiêu, lãi hay lỗ, còn bao xa tới mục tiêu</b>, tôi phải mở từng app "
    "rồi cộng tay vào một file Excel.",
    "File Excel ấy dần thành công cụ theo dõi hành trình của tôi: khai thu chi một lần, ghi mỗi lần mua, "
    "giá tự cập nhật, và quan trọng nhất – <b>thấy rõ con số FIRE và năm mình có thể chạm tới</b>. "
    "Nhìn thấy con đường giúp tôi giữ kỷ luật hơn bất kỳ lời khuyên nào.",
    "<b>Hành trình FIRE</b> là phiên bản app của công cụ đó – để bạn cũng có thể bắt đầu, dù với số vốn nhỏ.",
]
WHY_CARDS = [  # (icon, tiêu đề, nội dung)
    ("target", "Mục tiêu",
     "Nhìn rõ con đường và bám sát mục tiêu tự do tài chính – biết mình đang ở đâu, cần làm gì tiếp theo."),
    ("user", "Dành cho ai",
     "Người muốn đặt mục tiêu và thực hiện nó – đặc biệt là <b>người trẻ, người mới đi làm</b>: bắt đầu tích sản "
     "với số vốn nhỏ, hình thành thói quen và kỷ luật ngay từ đầu."),
    ("alert-triangle", "Nỗi đau app giải quyết",
     "Đa dạng hoá danh mục vô tình khiến tài sản phân tán ở nhiều nơi, khó quản lý và khó thấy bức tranh tổng."),
]

JOURNEY = [  # (tiêu đề chặng, nội dung, [(trang, nhãn nút)])
    ("Kiểm soát dòng tiền & xử lý nợ",
     "<b>Liệt kê thu, chi, tài sản và nợ</b> để nắm rõ bức tranh hiện tại. <b>Tích luỹ trước khi tiêu</b>: thay vì "
     "<i>Thu nhập − Chi tiêu = Tiết kiệm</i>, hãy trích phần tích luỹ ngay khi có thu nhập (tham khảo quy tắc "
     "<b>50/30/20</b>: thiết yếu / hưởng thụ / tích luỹ). <b>Tất toán nợ lãi suất cao</b> để giải phóng dòng tiền."
     "<br><i>App:</i> khai hồ sơ thu chi một lần, xem tỷ lệ tiết kiệm; ghi các khoản vay ở tab Nợ phải trả.",
     [("thu_chi", "Thu chi"), ("tiet_kiem", "Nợ phải trả")]),
    ("Xây dựng lớp đệm an toàn",
     "<b>Quỹ dự phòng khẩn cấp</b> bằng <b>3–6 tháng chi tiêu thiết yếu</b> để ứng phó biến cố mà không phải bán "
     "tháo tài sản hay vay nợ. <b>Bảo vệ rủi ro</b> bằng bảo hiểm phù hợp cho sức khoẻ, thu nhập và tài sản."
     "<br><i>App:</i> theo dõi từng sổ tiết kiệm, mục tiêu cần tiền (học phí…), tầng Bảo vệ/Phòng thủ của tháp tài sản.",
     [("tiet_kiem", "Tiết kiệm & Mục tiêu")]),
    ("Gia tăng thu nhập & đầu tư sinh lời",
     "<b>Phát triển thu nhập chủ động</b>: nâng cao kỹ năng, mở rộng nguồn thu để tăng tốc tích luỹ. "
     "<b>Đầu tư có kỷ luật</b>: phân bổ theo mục tiêu, thời hạn và mức chịu rủi ro; tránh chạy theo tâm lý FOMO."
     "<br><i>App:</i> gom mọi tài sản về một nơi, ghi mua định kỳ (DCA) nhanh, gợi ý chia tiền để về đúng tỷ lệ mục tiêu "
     "do <b>chính bạn</b> đặt.",
     [("tai_san", "Tài sản"), ("giao_dich", "Giao dịch")]),
    ("Đo lường mốc tự do tài chính",
     "Theo quy tắc <b>25 lần – 4%</b>, tài sản mục tiêu khoảng <b>25 lần chi phí sinh hoạt mỗi năm</b> (giả định rút "
     "an toàn khoảng 4%/năm). Tự do tài chính đạt được khi dòng tiền từ tài sản đầu tư và nguồn thu thụ động đủ duy "
     "trì lối sống mong muốn mà không phụ thuộc vào công việc toàn thời gian."
     "<br><i>App:</i> tính Số FIRE, các mốc Lean / Coast / Full FIRE, năm và tuổi dự kiến đạt được.",
     [("ke_hoach_fire", "Kế hoạch FIRE")]),
]

PRINCIPLES = [  # (nguyên tắc, nội dung, app giúp bằng cách)
    ("Trả cho mình trước & tự động hoá",
     "Trích tiết kiệm/đầu tư (thường khuyến nghị tối thiểu <b>10–20% thu nhập</b>) trước khi chi tiêu, dùng lệnh "
     "chuyển khoản tự động để giữ kỷ luật.",
     "Khai khoản <b>Đầu tư định kỳ</b> trong Thu chi – app trừ ra trước để biết phần còn lại."),
    ("Kiểm soát lạm phát lối sống",
     "Thu nhập tăng không đồng nghĩa với việc dồn hết vào tiêu sản (xe đắt tiền, mua sắm phô trương).",
     "Tỷ lệ tiết kiệm và cảnh báo khi cam kết đầu tư vượt dòng tiền dư."),
    ("Tăng thu, không chỉ cắt giảm",
     "Tiết kiệm giúp giữ tiền, nhưng nâng cao năng lực và tạo thêm nguồn thu giúp mở rộng quy mô tài sản nhanh hơn.",
     "Ở Kế hoạch FIRE, thử ô <b>Đầu tư thêm mỗi tháng</b> để thấy năm đạt FIRE thay đổi ra sao."),
    ("Theo dõi và điều chỉnh định kỳ",
     "Đánh giá lại ngân sách, quỹ dự phòng và danh mục theo từng giai đoạn cuộc sống.",
     "App tự chụp <b>Snapshot</b> tài sản mỗi tháng (trang Lịch sử) và nhắc rà soát thu chi mỗi quý – "
     "không cần ghi chi tiêu hằng ngày như các app quản lý chi tiêu."),
]

FAQ = [  # (câu hỏi, trả lời – markdown)
    ("App có giữ tiền hay yêu cầu nạp tiền không?",
     "**Không.** App không có ví, không nhận chuyển khoản, không kết nối tài khoản ngân hàng hay chứng khoán. "
     "Tiền của bạn luôn nằm ở nơi bạn đã mở tài khoản; app chỉ ghi lại số liệu bạn khai."),
    ("App có gợi ý nên mua mã nào không?",
     "**Không.** Danh mục quỹ/cổ phiếu trong app chỉ để bạn tìm nhanh và khai báo tài sản **bạn đã chọn**. "
     "Các con số như lợi suất kỳ vọng, tỷ lệ mục tiêu là **giả định do bạn tự đặt** để lập kế hoạch, "
     "không phải khuyến nghị hay cam kết lợi nhuận."),
    ("Ai xem được dữ liệu của tôi?",
     "Chỉ bạn. Dữ liệu mỗi tài khoản được tách riêng trên cơ sở dữ liệu (phân quyền theo từng dòng dữ liệu – "
     "tài khoản khác không đọc được). Đăng nhập bằng mã gửi qua email, app không lưu mật khẩu."),
    ("Giá lấy từ đâu, có chính xác không?",
     "Từ các nguồn công khai: NAV quỹ (Fmarket), giá đóng cửa cổ phiếu/ETF (VNDirect), giá vàng (PNJ). "
     "Giá có thể chậm khoảng 1 ngày – hãy đối chiếu với nơi bạn giao dịch khi cần con số chính xác."),
    ("Tôi có mang dữ liệu đi được không?",
     "Có. Trang **Sao lưu & Cài đặt** → **Tạo báo cáo Excel** để tải toàn bộ dữ liệu về máy bất cứ lúc nào."),
]

EXAMPLE_NOTE = ("Số liệu chỉ để minh hoạ cách tính, dùng lợi suất <b>giả định</b> đã trừ lạm phát – không phải cam kết "
                "lợi nhuận hay khuyến nghị đầu tư. Kết quả thực tế phụ thuộc thị trường và kỷ luật của bạn.")

# =====================================================================  GIAO DIỆN
_CSS = """<style>
.icards{display:grid;grid-template-columns:repeat(3,minmax(0,1fr));gap:14px;margin:6px 0 4px}
.icard{background:%(card)s;border:1px solid #2C2C2C;border-radius:18px;padding:16px 18px}
.icard .h{display:flex;align-items:center;gap:10px;font-weight:600;color:#F2F2F2;margin-bottom:6px}
.icard .h .b{width:32px;height:32px;border-radius:10px;background:rgba(182,243,106,.12);display:flex;
  align-items:center;justify-content:center;flex:none}
.icard .d{color:#BDBDBD;font-size:.9rem;line-height:1.55}
.promise{display:grid;grid-template-columns:1fr 1fr;gap:14px}
.promise .col{background:%(card)s;border:1px solid #2C2C2C;border-radius:18px;padding:16px 18px}
.promise .col.no{border-color:rgba(255,122,107,.35)}
.promise .t{font-weight:700;margin-bottom:8px;color:#F2F2F2}
.promise ul{list-style:none;margin:0;padding:0}
.promise li{display:flex;gap:10px;align-items:flex-start;color:#D0D0D0;font-size:.9rem;line-height:1.5;padding:4px 0}
.story p{color:#D0D0D0;line-height:1.75;margin:0 0 10px}
.pill{display:inline-flex;align-items:center;gap:8px;background:rgba(182,243,106,.10);color:%(lime)s;
  border:1px solid rgba(182,243,106,.35);border-radius:999px;padding:6px 14px;font-size:.85rem;font-weight:600}
.icards.one,.promise.one{grid-template-columns:1fr}
@media (max-width:760px){.icards{grid-template-columns:1fr}.promise{grid-template-columns:1fr}}
</style>""" % {"card": style.CARD, "lime": style.LIME}


def css() -> None:
    st.html(_CSS)


def _cards(items, one: bool = False) -> str:
    out = "".join(f'<div class="icard"><div class="h"><span class="b">{style.svg(i, 18, style.LIME)}</span>'
                  f'{style.esc(t)}</div><div class="d">{d}</div></div>' for i, t, d in items)
    return f'<div class="icards{" one" if one else ""}">{out}</div>'


def values(one: bool = False) -> None:
    """one=True: xếp 1 cột (khung hẹp như màn hình đăng nhập)."""
    st.html(_cards(VALUES, one))


def promise_card(one: bool = False) -> None:
    """Khung cam kết: app làm gì / không làm gì."""
    yes = "".join(f"<li>{style.svg('circle-check', 18, style.LIME)}<span>{x}</span></li>" for x in APP_DOES)
    no = "".join(f"<li>{style.svg('circle-x', 18, '#FF7A6B')}<span>{x}</span></li>" for x in APP_DOES_NOT)
    st.html(f'<div class="promise{" one" if one else ""}"><div class="col"><div class="t">App làm</div><ul>{yes}</ul></div>'
            f'<div class="col no"><div class="t">App không làm</div><ul>{no}</ul></div></div>')
    st.caption(PROMISE_NOTE)


def why_story(short: bool = False) -> None:
    """short=True: bản ngắn, xếp 1 cột cho màn hình đăng nhập."""
    paras = STORY[1:3] if short else STORY
    st.html('<div class="story">' + "".join(f"<p>{p}</p>" for p in paras) + "</div>")
    st.html(_cards(WHY_CARDS, one=short))


def journey(links: bool = True) -> None:
    st.graphviz_chart(style.flow(
        [("a", "1. Dòng tiền\\n& nợ"), ("b", "2. Lớp đệm\\nan toàn"), ("c", "3. Thu nhập\\n& đầu tư"),
         ("d", "4. Mốc tự do\\ntài chính")], highlight=("d",)), width="content")
    for i, (t, d, pages) in enumerate(JOURNEY, 1):
        st.html(style.steps([(t, d)], start=i))
        if links:
            cols = st.columns(len(pages) + 2)
            for col, (page, label) in zip(cols, pages):
                with col.container(key=style.ic("arrow-right", f"intro_{i}_{page}")):
                    st.page_link(f"views/{page}.py", label=label, width="stretch")


def principles() -> None:
    items = [(t, f"{d}<br><span style='color:{style.LIME}'>→ App giúp:</span> {a}") for t, d, a in PRINCIPLES]
    st.html(style.steps(items))


def faq() -> None:
    for q, a in FAQ:
        with st.expander(q):
            st.markdown(a)

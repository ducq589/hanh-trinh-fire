"""Trang Hướng dẫn: từng bước cho người mới, sơ đồ quy trình và hình minh hoạ."""
import plotly.graph_objects as go
import streamlit as st

from fi_app import engine, style, ui

c, data, h, fp = ui.state()
style.title("book", "Hướng dẫn sử dụng", "Đọc theo thứ tự các tab. Mỗi bước có nút mũi tên đưa bạn tới đúng trang cần thao tác.")


_links = [0]


def go_to(page: str, label: str):
    _links[0] += 1                       # mỗi nút một key riêng (cùng trang có thể xuất hiện nhiều lần)
    with st.container(key=style.ic("arrow-right", f"go_{_links[0]}_{page}")):
        st.page_link(f"views/{page}.py", label=label)


t1, t2, t3, t4, t5 = st.tabs(["Bắt đầu", "Thiết lập lần đầu", "Dùng hằng ngày", "Hiểu các chỉ số", "Hỏi đáp"],
                             key="tabs_hd")
style.tab_icons("tabs_hd", ["rocket", "stack-2", "repeat", "chart-donut", "help-circle"])

# =====================================================================
with t1:
    st.subheader("App này giúp bạn làm gì?")
    st.markdown("Theo dõi **toàn bộ tài sản tích sản** (quỹ mở, cổ phiếu, tiết kiệm, vàng, bảo hiểm…) ở một nơi, "
                "tự cập nhật giá, và cho biết **bạn còn bao xa tới tự do tài chính (FIRE)**. "
                "Bạn chỉ cần khai báo **một lần** rồi cập nhật khi có giao dịch – không phải ghi chép chi tiêu hằng ngày.")
    st.graphviz_chart(style.flow(
        [("a", "1. Đăng nhập\\nemail + mã 6 số"), ("b", "2. Thiết lập lần đầu\\ntài sản · thu chi"),
         ("c", "3. Ghi giao dịch\\nkhi mua / bán"), ("d", "4. Giá tự cập nhật\\nmỗi ngày"),
         ("e", "5. Theo dõi\\nTổng quan · Kế hoạch FIRE")],
        edges=[("a", "b", ""), ("b", "c", ""), ("c", "d", ""), ("d", "e", ""), ("e", "c", "lặp lại")],
        highlight=("e",)), width="stretch")

    st.subheader("Đăng nhập")
    l, r = st.columns([3, 2], gap="large")
    with l:
        st.html(style.steps([
            ("Mở địa chỉ app", "Trên điện thoại hoặc máy tính, mở đường link app mà người quản trị gửi cho bạn."),
            ("Nhập email", "Gõ email đã được cấp quyền rồi bấm <b>Gửi mã đăng nhập</b>."),
            ("Mở hộp thư", "Bạn nhận email <b>“Mã đăng nhập Hành trình FIRE”</b> chứa mã 6 số "
                           "(xem cả mục Spam/Quảng cáo nếu chưa thấy)."),
            ("Nhập mã", "Gõ mã 6 số, giữ ô <b>Ghi nhớ đăng nhập (30 ngày)</b> nếu là thiết bị của bạn, "
                        "rồi bấm <b>Đăng nhập</b>."),
            ("Xong!", "Những lần sau mở app sẽ vào thẳng, không cần mã. Muốn thoát: bấm <b>Đăng xuất</b> ở thanh bên."),
        ]))
    with r:
        st.graphviz_chart(style.flow(
            [("e", "Nhập email"), ("s", "Gửi mã"), ("m", "Mã 6 số\\ntrong Gmail"), ("v", "Đăng nhập"),
             ("ok", "Vào app")],
            rankdir="TB", highlight=("ok",)), width="content")
        st.html(style.tip("Không nhận được mã? Đợi 1 phút rồi bấm <b>← Dùng email khác / gửi lại mã</b>. "
                          "Email chưa được cấp quyền sẽ báo lỗi – hãy nhờ người quản trị thêm email của bạn."))

    st.subheader("Cài app lên màn hình điện thoại")
    a, b = st.columns(2)
    with a:
        st.html(style.steps([("iPhone (Safari)", "Mở link app → nút <b>Chia sẻ</b> (ô vuông có mũi tên) → "
                                                 "<b>Thêm vào MH chính</b> → <b>Thêm</b>.")]))
    with b:
        st.html(style.steps([("Android (Chrome)", "Mở link app → nút <b>⋮</b> → <b>Thêm vào màn hình chính</b> "
                                                  "(hoặc <b>Cài đặt ứng dụng</b>).")]))
    st.html(style.tip("Trên điện thoại, menu các trang nằm sau nút <b>»</b> ở góc trên bên trái."))

# =====================================================================
with t2:
    st.subheader("Chọn cách khai báo")
    st.caption("**Cách A – khai ngay trên app** (khuyên dùng, không cần Excel). "
               "**Cách B – điền file Excel mẫu v4** rồi tải lên app 1 lần – tiện khi bạn quen Excel hoặc có nhiều số liệu.")
    st.graphviz_chart(style.flow(
        [("q", "Khai trên Excel?"),
         ("tc", "A① Thu chi"), ("ts", "A② Tài sản"), ("od", "A③ Tài sản đang có"), ("gia", "A④ Giá tay\\n(nếu cần)"),
         ("tk", "A⑤ Tiết kiệm · Nợ"), ("fire", "A⑥ Kế hoạch FIRE"),
         ("b1", "B① Tải mẫu v4"), ("b2", "B② Điền Excel"), ("b3", "B③ Tải lên app"),
         ("done", "Dữ liệu sẵn sàng")],
        edges=[("q", "tc", "Không"), ("tc", "ts", ""), ("ts", "od", ""), ("od", "gia", ""), ("gia", "tk", ""),
               ("tk", "fire", ""), ("fire", "done", ""),
               ("q", "b1", "Có"), ("b1", "b2", ""), ("b2", "b3", ""), ("b3", "done", "")],
        rankdir="TB", highlight=("done",)).replace('q [label="Khai trên Excel?"]',
                                                   'q [label="Khai trên Excel?", shape=diamond, fillcolor="#1C1C1C"]'),
        width="content")

    # ------------------------------------------------------------- Cách A
    st.markdown("#### Cách A – Khai ngay trên app (6 bước)")
    st.html(style.steps([
        ("Khai hồ sơ thu chi", "Trang <b>Thu chi</b>: điền số tiền <b>điển hình</b> của từng khoản thu/chi theo "
                               "đúng tần suất (Tháng/Quý/Năm) – app tự quy đổi ra mỗi tháng. Bấm <b>Lưu hồ sơ thu chi</b>. "
                               "Không cần ghi chi tiêu hằng ngày."),
    ]))
    go_to("thu_chi", "Thu chi")
    st.html(style.steps([
        ("Chọn tài sản đầu tư", "Trang <b>Tài sản</b> → khung <b>Thêm tài sản</b>:"
                                "<br>• <b>Chứng chỉ quỹ</b>: gõ mã/tên quỹ (DCDS, VESAF, VNDBF…) rồi bấm Thêm."
                                "<br>• <b>Cổ phiếu / ETF</b>: gõ mã (FPT, MBB, E1VFVN30…) → Kiểm tra & thêm."
                                "<br>• <b>Vàng</b>: chọn loại (SJC, nhẫn trơn…) → Thêm vàng."
                                "<br>App tự điền Tầng, lợi suất kỳ vọng và <b>tự lấy giá hằng ngày</b>. "
                                "Tiết kiệm, bảo hiểm, BĐS: tab <b>Khác</b> (thêm dòng ở bảng bên dưới)."
                                "<br><i>Quỹ/cổ phiếu cũng có thể thêm thẳng ở bước 3.</i>"),
    ], start=2))
    go_to("tai_san", "Tài sản")
    st.html(style.steps([
        ("Ghi tài sản đang có", "Trang <b>Giao dịch</b>:"
                                "<br>• <b>Không muốn nhập lại lịch sử</b> (đã mua nhiều lần) → tab <b>Tài sản đang có</b>:"
                                "<br>&nbsp;&nbsp;– Bảng chỉ hiện tài sản <b>chưa có dữ liệu</b>; chưa có mã thì gõ ở ô <b>Thêm</b> (VD: DCBF, FPT)."
                                "<br>&nbsp;&nbsp;– Điền <b>Số lượng đang có</b> và <b>Giá vốn BQ</b> (hoặc Tổng vốn) – xem trong app Fmarket / "
                                "app chứng khoán → <b>Lưu khai báo</b>. Lãi/lỗ tính ngay; XIRR tính từ ngày khai."
                                "<br>&nbsp;&nbsp;– Lưu xong mã rời khỏi bảng (chỉ dùng cho lần khai đầu). Muốn sửa: tab "
                                "<b>Lịch sử & sửa</b> (dòng Vốn đầu kỳ). Thêm nhầm mã: mục <b>Bỏ mã thêm nhầm</b>."
                                "<br>• <b>Muốn đủ lịch sử</b> → tab <b>Giao dịch khác</b>, nhập từng lần mua – XIRR chính xác từ đầu."),
    ], start=3))
    st.graphviz_chart(style.flow(
        [("q", "Có muốn nhập\\nlịch sử lệnh?"), ("a", "Tab Giao dịch khác\\nnhập từng lần mua"),
         ("b", "Tab Tài sản đang có\\nSố lượng + Giá vốn BQ"), ("ok", "Lãi/lỗ, FIRE\\ntính ngay")],
        edges=[("q", "a", "Có"), ("q", "b", "Không"), ("a", "ok", ""), ("b", "ok", "")],
        highlight=("ok",)).replace('q [label="Có muốn nhập\\nlịch sử lệnh?"]',
                                   'q [label="Có muốn nhập\\nlịch sử lệnh?", shape=diamond, fillcolor="#1C1C1C"]'),
        width="content")
    go_to("giao_dich", "Giao dịch")
    st.html(style.steps([
        ("Kiểm tra giá", "Quỹ, cổ phiếu, vàng chọn từ danh mục đã có giá tự động. Trang <b>Giá</b>: chỉ cần điền "
                         "<b>Giá mới</b> cho tài sản tự khai báo (bảo hiểm, BĐS…) rồi bấm <b>Lưu</b>."),
    ], start=4))
    go_to("gia", "Giá")
    st.html(style.steps([
        ("Sổ tiết kiệm, mục tiêu, nợ", "Trang <b>Tiết kiệm, Mục tiêu & Nợ</b>: mở <b>Sửa / thêm / xoá sổ tiết kiệm</b> "
                                       "để thêm từng sổ; tab <b>Mục tiêu</b> cho các khoản cần tiền (học phí…); "
                                       "tab <b>Nợ phải trả</b> cho khoản vay."),
    ], start=5))
    go_to("tiet_kiem", "Tiết kiệm, Mục tiêu & Nợ")
    st.html(style.steps([
        ("Đặt giả định FIRE", "Trang <b>Kế hoạch FIRE</b> → mở <b>Giả định</b>: nhập tuổi, tuổi mong muốn đạt FIRE, "
                              "lạm phát, tỷ lệ rút an toàn (SWR). Bấm <b>Lưu giả định</b>."),
    ], start=6))
    go_to("ke_hoach_fire", "Kế hoạch FIRE")

    # ------------------------------------------------------------- Cách B
    st.markdown("#### Cách B – Khai bằng file Excel mẫu v4")
    with st.container(border=True):
        st.graphviz_chart(style.flow(
            [("t", "Tải mẫu v4"), ("d", "Điền theo\\nsheet HuongDan"), ("u", "Tải lên app"), ("k", "Kiểm tra\\n& dùng tiếp")],
            highlight=("k",)), width="content")
        st.html(style.steps([
            ("Tải file mẫu", "Trang <b>Sao lưu & Cài đặt</b> → mục <b>Nhập dữ liệu từ Excel</b> → bấm <b>Tải mẫu v4</b>."),
            ("Điền theo sheet HuongDan", "Mở file bằng Excel:"
                                         "<br>• <b>Profile</b>: thu chi điển hình (Tháng/Quý/Năm)."
                                         "<br>• <b>DM_TaiSan</b>: mỗi tài sản 1 dòng – ghi <b>Mã đúng mã quỹ/cổ phiếu</b> "
                                         "(DCDS, FPT…) để app tự lấy giá; cột <b>Tính FIRE?</b>."
                                         "<br>• <b>GiaoDich</b>: đã có tài sản mà không muốn nhập lịch sử → mỗi tài sản "
                                         "<b>1 dòng Vốn đầu kỳ</b> (Ngày = hôm nay, Số lượng = số đang có, Giá = giá vốn BQ); "
                                         "hoặc nhập từng lệnh mua/bán."
                                         "<br>• <b>SoTietKiem</b>, <b>MucTieu</b>, <b>No</b>: sổ tiết kiệm, mục tiêu, khoản vay."
                                         "<br>• <b>FIRE_Plan</b> ô B4:B10: tuổi, tuổi muốn đạt FIRE, lạm phát, SWR…"),
            ("Tải lên app", "Quay lại <b>Sao lưu & Cài đặt</b> → <b>Upload</b> file đã điền → tick <b>Tôi hiểu và muốn nhập</b> "
                            "→ <b>Nhập từ Excel</b>. ⚠ Thao tác này <b>thay toàn bộ dữ liệu</b> của tài khoản – chỉ dùng khi mới bắt đầu."),
            ("Kiểm tra & dùng tiếp", "Mở <b>Tổng quan</b> đối chiếu số liệu. Giá quỹ/cổ phiếu tự lấy (hoặc bấm <b>Lấy giá mới nhất</b> "
                                     "ở trang Giá). Vàng: chọn nguồn giá PNJ ở trang Tài sản (cột Nguồn giá, VD <code>pnj:N24K:mua</code>) "
                                     "hoặc nhập giá tay. Từ đó trở đi ghi giao dịch mới ngay trên app."),
        ]))
        st.caption("File Investment_tracking_v3 cũ cũng nhập được theo cách này.")
        go_to("sao_luu", "Sao lưu & Cài đặt")

    st.markdown("#### Tháp tài sản – chọn Tầng cho từng tài sản")
    st.html(style.legend([
        (style.TIER_COLORS["Tăng trưởng"], "Tăng trưởng – cổ phiếu, quỹ mở cổ phiếu, ETF", "rủi ro cao, sinh lời cao"),
        (style.TIER_COLORS["Thu nhập"], "Thu nhập – quỹ trái phiếu, tài sản cho thuê", "dòng tiền đều"),
        (style.TIER_COLORS["Bảo vệ"], "Bảo vệ – quỹ khẩn cấp, tiết kiệm có mục đích", "an toàn, thanh khoản"),
        (style.TIER_COLORS["Phòng thủ"], "Phòng thủ – vàng, bảo hiểm", "giữ giá trị dài hạn"),
    ]))
    with st.expander("Bảng mã nguồn giá tự động (cột “Nguồn giá” ở trang Tài sản)"):
        st.markdown(
            "| Gõ vào cột Nguồn giá | Dùng cho | Ví dụ |\n|---|---|---|\n"
            "| `fmarket` | Quỹ mở (NAV từ Fmarket) – Mã tài sản phải trùng mã quỹ | DCDS, VESAF, VNDBF |\n"
            "| `vndirect` | Cổ phiếu, ETF (giá đóng cửa) | MBB, FPT, E1VFVN30 |\n"
            "| `vndirect:FPT` | Khi Mã tài sản khác mã chứng khoán | |\n"
            "| `pnj:SJC:mua` / `pnj:N24K:mua` | Vàng miếng SJC / nhẫn trơn 9999 (giá mua vào mỗi chỉ) | |\n"
            "| *(để trống)* | Nhập giá tay (bảo hiểm, BĐS, tiền gửi…) | |")

# =====================================================================
with t3:
    st.subheader("Lịch sử dụng gợi ý")
    st.html('<div class="cal">'
            f'<div class="c"><div class="h">{style.svg("bolt")} Mỗi lần mua</div><ul><li>Giao dịch → Mua DCA nhanh</li>'
            '<li>Chọn quỹ, nhập số tiền, Lưu</li></ul></div>'
            f'<div class="c"><div class="h">{style.svg("calendar-event")} Mỗi tuần</div><ul><li>Xem hộp <b>Việc cần chú ý</b></li>'
            '<li>Cập nhật giá vàng/BĐS nếu có</li></ul></div>'
            f'<div class="c"><div class="h">{style.svg("calendar-event")} Cuối tháng</div><ul><li>Kiểm tra Lịch sử (Snapshot tự chụp)</li>'
            '<li>Xem Tái cân bằng ở trang Tài sản</li><li>Tạo báo cáo Excel để lưu</li></ul></div>'
            f'<div class="c"><div class="h">{style.svg("repeat")} Mỗi quý</div><ul><li>Rà lại Thu chi → <b>Đã rà soát hôm nay</b></li>'
            '<li>Xem lại Kế hoạch FIRE</li></ul></div></div>')

    st.subheader("Ghi một lần mua quỹ (DCA) – 30 giây")
    l, r = st.columns([3, 2], gap="large")
    with l:
        st.html(style.steps([
            ("Mở Giao dịch → Mua DCA nhanh", "Hoặc bấm <b>Mua DCA</b> ở thẻ Thao tác nhanh của trang Tổng quan."),
            ("Chọn tài sản & ngày", "Ngày mặc định là hôm nay."),
            ("Nhập số tiền", "App tự tra NAV đúng ngày và tính số chứng chỉ quỹ = Số tiền ÷ NAV (cắt 2 số lẻ). "
                             "Nếu chưa có NAV ngày đó, gõ NAV vào ô bên cạnh."),
            ("Bấm Lưu giao dịch mua", "Tổng quan, Tài sản, Kế hoạch FIRE cập nhật ngay."),
        ]))
        go_to("giao_dich", "Giao dịch")
    with r:
        st.graphviz_chart(style.flow([("m", "Số tiền"), ("n", "NAV đúng ngày\\n(tự tra)"), ("q", "Số CCQ\\n= tiền ÷ NAV"),
                                      ("s", "Lưu"), ("u", "Tổng quan\\ncập nhật")], rankdir="TB", highlight=("u",)),
                          width="content")

    st.subheader("Các loại giao dịch")
    st.markdown(
        "| Loại | Khi nào dùng | Nhập gì |\n|---|---|---|\n"
        "| **Mua** | Mua quỹ / cổ phiếu / vàng | Quỹ: Số tiền · Cổ phiếu: Giá + Số lượng + Phí |\n"
        "| **Bán** | Bán bớt tài sản | Giá + Số lượng + Phí + Thuế |\n"
        "| **Cổ tức TM** | Nhận cổ tức tiền mặt | Số tiền |\n"
        "| **Cổ tức CP/Thưởng** | Nhận cổ phiếu thưởng / cổ tức bằng cổ phiếu | Số lượng |\n"
        "| **Vốn đầu kỳ** | Tài sản đã có, không muốn nhập lịch sử lệnh | Số lượng đang có + Giá vốn BQ (XIRR tính từ ngày khai) |")
    st.html(style.tip("Nhập sai? Vào tab <b>Lịch sử & sửa</b>, sửa trực tiếp trong bảng (hoặc chọn dòng → biểu tượng thùng rác) rồi bấm "
                      "<b>Lưu thay đổi</b>."))

    st.subheader("Khi sổ tiết kiệm sắp đáo hạn")
    st.graphviz_chart(style.flow(
        [("y", "Sắp đáo hạn\\n(còn ≤ 15 ngày)"), ("d", "Ngân hàng / app\\ntất toán hay tái tục?"),
         ("t", "Tái tục: sửa Ngày đáo hạn,\\nGửi đầu kỳ, Lãi trước thuế"), ("x", "Tất toán: xoá sổ\\n(hoặc chuyển sang tài sản khác)"),
         ("g", "Đang sinh lời")],
        edges=[("y", "d", ""), ("d", "t", "tái tục"), ("d", "x", "rút ra"), ("t", "g", "")], highlight=("g",)),
        width="stretch")
    go_to("tiet_kiem", "Tiết kiệm, Mục tiêu & Nợ")

# =====================================================================
with t4:
    st.subheader("Các con số ở trang Tổng quan")
    st.markdown(
        "| Chỉ số | Ý nghĩa |\n|---|---|\n"
        "| **Tổng tài sản** | Giá trị hiện tại của mọi tài sản = Số lượng × Giá mới nhất (sổ tiết kiệm: số nhận cuối kỳ) |\n"
        "| **Vốn thuần** | Tiền đã bỏ vào (gồm phí) − tiền đã rút ra khi bán |\n"
        "| **Lãi/lỗ** | Tổng tài sản − Vốn thuần + cổ tức tiền mặt đã nhận |\n"
        "| **Tài sản ròng** | Tổng tài sản − Nợ phải trả |\n"
        "| **XIRR** | Lãi suất quy năm có tính thời điểm từng lần nạp tiền – cách đo đúng cho đầu tư định kỳ (DCA). "
        "Với khoảng thời gian dưới 1 năm, XIRR phóng đại cả lãi lẫn lỗ |\n"
        "| **Tái cân bằng** | Số tiền nên mua thêm cho từng quỹ để về đúng Tỷ lệ mục tiêu mà không phải bán |")

    st.subheader("FIRE – tự do tài chính đo thế nào?")
    st.html(style.steps([
        ("Số FIRE (Full FIRE)", "= Chi tiêu một năm ÷ Tỷ lệ rút an toàn (SWR). Với SWR 4%: <b>Số FIRE = 25 × chi tiêu năm</b>. "
                                "Có số tài sản này, mỗi năm rút 4% vẫn đủ sống mà vốn không cạn."),
        ("Lean FIRE", "Chỉ tính <b>chi tiêu thiết yếu</b> – mốc an toàn đầu tiên."),
        ("Coast FIRE", "Số tiền mà nếu có ngay hôm nay thì <b>không cần góp thêm</b>, lãi kép vẫn đưa bạn tới Số FIRE "
                       "đúng tuổi mục tiêu."),
        ("Tiến độ & năm đạt FIRE", "Tiến độ = Tài sản tính FIRE ÷ Số FIRE. Năm đạt FIRE tính theo số tiền bạn đầu tư "
                                   "mỗi tháng (khai ở Thu chi) và lợi suất sau lạm phát."),
    ]))
    st.caption("Ví dụ minh hoạ (số giả định, không phải dữ liệu của bạn): chi tiêu 25 tr/tháng (thiết yếu 18 tr), "
               "đang có 300 tr, đầu tư thêm 10 tr/tháng, lợi suất thực 6%/năm, SWR 4%.")
    full, lean = 25e6 * 12 / 0.04, 18e6 * 12 / 0.04
    xs, ys, v = [], [], 300e6
    for k in range(31):
        if k:
            v = engine.fv(0.06 / 12, 12, -10e6, -v)
        xs.append(k); ys.append(v / 1e9)
    y_full = next((x for x, y in zip(xs, ys) if y * 1e9 >= full), None)
    y_lean = next((x for x, y in zip(xs, ys) if y * 1e9 >= lean), None)
    f = go.Figure()
    f.add_trace(go.Scatter(x=xs, y=ys, name="Tài sản (ví dụ)", line=dict(color=style.LIME, width=3, shape="spline"),
                           fill="tozeroy", fillcolor="rgba(182,243,106,0.08)", hovertemplate="Năm %{x}: %{y:.2f} tỷ<extra></extra>"))
    f.add_hline(y=full / 1e9, line=dict(color=style.TARGET_FULL, dash="dash"),
                annotation_text=f"Full FIRE {full / 1e9:.1f} tỷ", annotation_position="top left")
    f.add_hline(y=lean / 1e9, line=dict(color=style.TARGET_LEAN, dash="dot"),
                annotation_text=f"Lean FIRE {lean / 1e9:.1f} tỷ", annotation_position="bottom right")
    for yr, lbl in ((y_lean, "Đạt Lean"), (y_full, "Đạt Full")):
        if yr is not None:
            f.add_vline(x=yr, line=dict(color="#8A8A8A", dash="dot"), annotation_text=f"{lbl}: năm {yr}",
                        annotation_position="top right")
    f.update_xaxes(title="Số năm kể từ hôm nay"); f.update_yaxes(title="tỷ ₫ (sức mua hôm nay)")
    st.plotly_chart(style.fig(f, height=360, legend_bottom=False).update_layout(showlegend=False, margin=dict(t=30)),
                    width="stretch", config={"displayModeBar": False})
    st.html(style.tip("Ở trang <b>Kế hoạch FIRE</b>, kéo thanh <b>Nếu… thì sao?</b> (tăng đầu tư / giảm chi tiêu) để thấy "
                      "năm đạt FIRE thay đổi ngay."))
    go_to("ke_hoach_fire", "Kế hoạch FIRE")

# =====================================================================
with t5:
    faq = [
        ("Không nhận được email chứa mã?",
         "Xem mục Spam/Quảng cáo. Đợi 1–2 phút rồi gửi lại. Nếu báo *“Email này chưa được cấp quyền”*, nhờ người quản trị "
         "thêm email của bạn trong Supabase."),
        ("Mở lại app vẫn phải nhập mã?",
         "Khi nhập mã, giữ ô *Ghi nhớ đăng nhập (30 ngày)*. Chế độ ẩn danh/riêng tư của trình duyệt sẽ không ghi nhớ được."),
        ("Giá không cập nhật / hiện cảnh báo “Giá cũ”?",
         "Vào trang **Giá** → *Lấy giá mới nhất*. Kiểm tra cột *Nguồn giá* ở trang **Tài sản**. Quỹ mở công bố NAV "
         "chậm 1 ngày nên “giá cũ 1–2 ngày” là bình thường. Nguồn nào lỗi thì nhập giá tay."),
        ("Lần đầu mở app sau một thời gian bị chậm?",
         "App trên gói miễn phí “ngủ” khi lâu không dùng; lần mở đầu mất khoảng 30 giây để khởi động."),
        ("Thêm một quỹ / cổ phiếu mới?",
         "Trang **Tài sản** → thêm 1 dòng (Mã, Tên, Tầng, Nguồn giá) → *Lưu danh mục* → ghi giao dịch mua. "
         "Tài sản mới tự hiện ở mọi trang."),
        ("Nhập nhầm giao dịch?",
         "Trang **Giao dịch** → tab *Lịch sử & sửa*: sửa trực tiếp, hoặc chọn dòng và bấm biểu tượng thùng rác, rồi *Lưu thay đổi*."),
        ("Dữ liệu của tôi có ai xem được không?",
         "Không. Mỗi tài khoản có dữ liệu riêng; cơ sở dữ liệu tự chặn mọi truy cập vào dữ liệu của người khác."),
        ("Sao lưu dữ liệu thế nào?",
         "Mỗi tháng vào **Sao lưu & Cài đặt** → *Tạo báo cáo Excel* → tải file về máy."),
        ("Các con số có phải lời khuyên đầu tư?",
         "Không. Lợi suất kỳ vọng, lạm phát, SWR là giả định để lập kế hoạch; hãy tự điều chỉnh cho phù hợp."),
    ]
    for q, a in faq:
        with st.expander(q):
            st.markdown(a)

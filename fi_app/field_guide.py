"""Giải thích từng cột của các bảng nhập liệu + cách điền (trang Thu chi, Tiết kiệm/Mục tiêu/Nợ, Tài sản, Giao dịch).

- `render(key)`: khung thu gọn "Cách điền bảng này" đặt ngay trên bảng.
- `tip(key, nhãn cột)`: câu ngắn hiện khi rê chuột vào tiêu đề cột (truyền vào help= của st.column_config).

Muốn sửa câu chữ: chỉ sửa GUIDES bên dưới. Câu chữ bám đúng công thức trong fi_app/engine.py
(derive_tx, derive_savings, derive_goals, holdings, cashflow_summary, fire_plan) – tests/test_field_guide.py kiểm tra ví dụ.
Không dùng ký tự "|" trong nội dung (vỡ bảng markdown).
"""
from __future__ import annotations

import re

import streamlit as st

from . import style

# Mỗi cột: (nhãn cột, loại & định dạng, bắt buộc, ý nghĩa & cách app dùng, liên kết, ví dụ, gợi ý ngắn khi rê chuột)
GUIDES: dict[str, dict] = {
    # ------------------------------------------------------------------ Thu chi
    "cashflow": {
        "title": "Hồ sơ thu chi",
        "intro": "Mỗi dòng là **một khoản thu hoặc chi điển hình** của gia đình. App quy mọi khoản về **mỗi tháng** "
                 "để tính tỷ lệ tiết kiệm, Số FIRE, quỹ khẩn cấp. Khai một lần, rà soát mỗi quý.",
        "cols": [
            ("Khoản mục", "Chữ", "Có", "Tên khoản để bạn tự nhận ra.", "", "Lương chính; Tiền nhà; Học phí con",
             "Tên khoản thu/chi, VD: Lương, Tiền nhà"),
            ("Nhóm", "Chọn 1 trong 5", "Có",
             "Quyết định khoản được cộng vào đâu: **Thu nhập chủ động** (lương, freelance) và **Thu nhập thụ động** "
             "(cho thuê, lãi…) → tổng thu. **Chi thiết yếu** (ăn ở, điện nước, đi lại, bảo hiểm, trả nợ) → Lean FIRE "
             "và quỹ khẩn cấp. **Chi linh hoạt** (ăn ngoài, mua sắm, du lịch). **Đầu tư định kỳ** (DCA, tích luỹ) → "
             "dự phóng tài sản.",
             "Kế hoạch FIRE: Số FIRE = (thiết yếu + linh hoạt) × 12 ÷ SWR; Lean FIRE chỉ dùng chi thiết yếu",
             "Chi thiết yếu",
             "5 nhóm: thu chủ động/thụ động, chi thiết yếu/linh hoạt, đầu tư định kỳ – quyết định cách app tính"),
            ("Thành viên", "Chữ", "Không", "Chỉ để ghi chú khoản của ai, không ảnh hưởng tính toán.", "",
             "Chồng; Vợ; Chung", "Khoản của ai (không ảnh hưởng tính toán)"),
            ("Số tiền", "Số ₫, không âm, không cần dấu chấm", "Nên có",
             "Số tiền **mỗi lần phát sinh theo đúng Tần suất** – không tự chia ra tháng. Trống = 0.", "",
             "20000000", "Số tiền mỗi lần theo Tần suất (₫) – app tự quy ra tháng"),
            ("Tần suất", "Tháng / Quý / Năm", "Có",
             "Khoản trả **mỗi quý** chọn Quý (app chia 3), **mỗi năm** chọn Năm (app chia 12).", "Cột Quy đổi/tháng",
             "Năm (bảo hiểm 12 tr/năm → 1 tr/tháng)", "Tháng / Quý / Năm – app quy về mỗi tháng"),
            ("Ghi chú", "Chữ", "Không", "Ghi chú tuỳ ý.", "", "Tăng 10% từ tháng 1", "Ghi chú tuỳ ý"),
        ],
        "computed": [("Quy đổi/tháng", "Số tiền ÷ 1 (Tháng), ÷ 3 (Quý), ÷ 12 (Năm). Các thẻ phía trên cộng cột này theo Nhóm.")],
        "example": [
            "Lương chính · Thu nhập chủ động · Chồng · 20.000.000 · Tháng",
            "Thưởng Tết · Thu nhập chủ động · Chồng · 20.000.000 · Năm → 1.666.667/tháng",
            "Tiền nhà + điện nước · Chi thiết yếu · Chung · 6.000.000 · Tháng",
            "Bảo hiểm sức khoẻ · Chi thiết yếu · Vợ · 12.000.000 · Năm → 1.000.000/tháng",
            "Mua CCQ định kỳ · Đầu tư định kỳ · Chung · 3.000.000 · Tháng",
        ],
        "tips": [
            "Đừng khai thu nhập bất thường (lì xì, quà) – kế hoạch sẽ lạc quan quá mức.",
            "Khoản đầu tư định kỳ để ở nhóm **Đầu tư định kỳ**, không để ở Chi – nếu không app tính sai tỷ lệ tiết kiệm.",
            "Trả góp nợ hằng tháng nên khai cả ở đây (Chi thiết yếu) và ở tab Nợ phải trả.",
        ],
    },
    # ------------------------------------------------------------------ Sổ tiết kiệm
    "savings": {
        "title": "Sổ tiết kiệm",
        "intro": "Mỗi dòng là **một sổ / một kỳ gửi**. Giá trị các sổ được cộng vào tài sản có mã ở cột **Nhóm** "
                 "(VD QKC, SF). Sổ gán **Mục tiêu** được tính vào tiến độ mục tiêu đó.",
        "cols": [
            ("Gói", "Chữ", "Có", "Tên sổ để nhận ra (ngân hàng, kỳ hạn, lãi suất).", "",
             "VCB 6T 5,2%", "Tên sổ, VD: VCB 6T 5,2%"),
            ("Nhóm (Mã TS)", "Chọn mã tài sản", "Có",
             "Sổ thuộc tài sản nào. Danh sách chỉ gồm tài sản có **Cách định giá = Sổ tiết kiệm** (tạo ở trang Tài sản). "
             "Giá trị tài sản = tổng *Nhận cuối kỳ* các sổ cùng mã.",
             "Trang Tài sản (mã QKC = quỹ khẩn cấp)", "QKC",
             "Mã tài sản chứa sổ (định giá = Sổ tiết kiệm). QKC = quỹ khẩn cấp"),
            ("Mục tiêu", "Chọn tên mục tiêu hoặc để trống", "Không",
             "Gán sổ cho một mục tiêu cần tiền – *Nhận cuối kỳ* của sổ được cộng vào cột **Đã có** của mục tiêu.",
             "Tab Mục tiêu (Sinking Fund)", "Học phí 2027", "Gán sổ cho mục tiêu ở tab Mục tiêu"),
            ("Mục đích", "Chữ", "Không", "Ghi chú mục đích, không ảnh hưởng tính toán.", "", "Dự phòng ốm đau",
             "Ghi chú mục đích"),
            ("Ngày đáo hạn", "Ngày dd/mm/yyyy", "Nên có",
             "Dùng để tính trạng thái: **Sắp đáo hạn** (trong 15 ngày – chỉnh ở Cài đặt), **Quá hạn xử lý** (đã qua ngày).",
             "Nhắc việc ở Tổng quan", "15/05/2027", "Ngày đáo hạn – app nhắc trước 15 ngày"),
            ("Gốc", "Số ₫", "Nên có", "Tiền gốc **ban đầu** bạn bỏ vào sổ (lần đầu mở).",
             "Tăng trưởng = (Nhận cuối kỳ − Gốc − Nạp thêm) ÷ (Gốc + Nạp thêm)", "50000000",
             "Tiền gốc ban đầu bỏ vào sổ"),
            ("Nạp thêm", "Số ₫", "Không",
             "Tiền gốc **nộp thêm** sau ngày mở sổ (không phải lãi). Không có thì để trống.", "", "0",
             "Tiền gốc nộp thêm sau khi mở sổ (không phải lãi)"),
            ("Gửi đầu kỳ", "Số ₫", "Có",
             "Số dư **đầu kỳ hiện tại** của sổ. Lần đầu = Gốc. Khi **tái tục** = số tiền gửi lại cho kỳ mới "
             "(gốc + lãi kỳ trước nếu nhập gốc).", "", "50000000", "Số dư đầu kỳ hiện tại (tái tục: số gửi lại)"),
            ("Lãi trước thuế", "Số ₫", "Nên có",
             "Tiền lãi **cả kỳ** trước thuế = Gửi đầu kỳ × lãi suất năm × số tháng ÷ 12. App trừ thuế lãi (mặc định 5%).",
             "Cài đặt: thuế lãi tiết kiệm", "1300000", "Lãi cả kỳ trước thuế (₫), app tự trừ thuế 5%"),
        ],
        "computed": [("Nhận cuối kỳ", "Gửi đầu kỳ + Lãi trước thuế × (1 − thuế)."),
                     ("Tăng trưởng", "(Nhận cuối kỳ − Gốc − Nạp thêm) ÷ (Gốc + Nạp thêm)."),
                     ("Trạng thái", "Đang sinh lời / Sắp đáo hạn / Quá hạn xử lý – theo Ngày đáo hạn.")],
        "example": [
            "Gửi 50 triệu, kỳ hạn 6 tháng, lãi 5,2%/năm: Lãi trước thuế = 50.000.000 × 5,2% × 6 ÷ 12 = **1.300.000**.",
            "Điền: VCB 6T 5,2% · QKC · (trống) · Dự phòng · 15/05/2027 · 50.000.000 · 0 · 50.000.000 · 1.300.000",
            "App tính Nhận cuối kỳ = 50.000.000 + 1.300.000 × 95% = **51.235.000**.",
            "Khi tái tục nhập lãi vào gốc: sửa Ngày đáo hạn mới, Gửi đầu kỳ = 51.235.000, Lãi trước thuế = lãi kỳ mới.",
        ],
        "tips": [
            "Cột Nhóm trống danh sách? Tạo tài sản (VD mã QKC) với **Cách định giá = Sổ tiết kiệm** ở trang Tài sản trước.",
            "Không cộng lãi vào **Nạp thêm** – Nạp thêm chỉ là tiền gốc bỏ thêm.",
            "Đã tất toán và rút tiền ra: xoá dòng sổ (hoặc chuyển sang sổ mới) để tài sản không bị tính hai lần.",
        ],
    },
    # ------------------------------------------------------------------ Mục tiêu
    "goals": {
        "title": "Mục tiêu (Sinking Fund)",
        "intro": "Các khoản **cần tiền vào một thời điểm** (học phí, sửa nhà, mua xe…). App tính đã có bao nhiêu từ các "
                 "sổ được gán và mỗi tháng cần góp thêm bao nhiêu.",
        "cols": [
            ("Mục tiêu", "Chữ, không trùng", "Có",
             "Tên mục tiêu. Tên này xuất hiện ở cột **Mục tiêu** của tab Sổ tiết kiệm để gán sổ.",
             "Tab Sổ tiết kiệm → cột Mục tiêu", "Học phí 2027", "Tên mục tiêu – dùng để gán sổ tiết kiệm"),
            ("Số tiền mục tiêu", "Số ₫", "Nên có", "Tổng số tiền cần có vào ngày hoàn thành.", "", "60000000",
             "Tổng tiền cần có (₫)"),
            ("Ngày hoàn thành", "Ngày dd/mm/yyyy", "Nên có",
             "Hạn cần đủ tiền – dùng để chia số còn thiếu ra mỗi tháng.", "", "01/09/2027",
             "Hạn cần đủ tiền – để chia ra số tiền góp mỗi tháng"),
        ],
        "computed": [("Đã có", "Tổng Nhận cuối kỳ của các sổ có cột Mục tiêu = tên này."),
                     ("Còn lại", "Số tiền mục tiêu − Đã có (không âm)."),
                     ("Số tháng còn", "Từ tháng này tới tháng hoàn thành (tính cả tháng hiện tại)."),
                     ("Cần góp/tháng", "Còn lại ÷ Số tháng còn."),
                     ("Trạng thái", "Done / Đang góp / Quá hạn.")],
        "example": ["Học phí 2027 · 60.000.000 · 01/09/2027 → gán 2 sổ (mỗi sổ nhận cuối kỳ 20 tr) ở tab Sổ → "
                    "Đã có 40 tr, Còn lại 20 tr, chia đều cho số tháng còn lại."],
        "tips": ["Đổi tên mục tiêu thì nhớ chọn lại tên mới ở cột Mục tiêu của các sổ đã gán."],
    },
    # ------------------------------------------------------------------ Nợ
    "debts": {
        "title": "Nợ phải trả",
        "intro": "Các khoản vay còn dư nợ. Tổng dư nợ được **trừ khỏi tài sản tính FIRE và tài sản ròng**.",
        "cols": [
            ("Khoản nợ", "Chữ", "Có", "Tên khoản vay.", "", "Vay mua nhà BIDV", "Tên khoản vay"),
            ("Dư nợ", "Số ₫", "Có", "Số tiền gốc **còn phải trả** tại thời điểm hiện tại. Cập nhật định kỳ.",
             "Tổng quan: Tài sản ròng; Kế hoạch FIRE: tài sản tính FIRE", "450000000",
             "Gốc còn phải trả hiện tại – được trừ khỏi tài sản"),
            ("Lãi suất (%/năm)", "Số %, gõ 8,5 = 8,5%", "Không",
             "Để bạn so sánh, ưu tiên trả khoản lãi cao trước. Không dùng trong công thức.", "", "8,5",
             "Gõ 8,5 nghĩa là 8,5%/năm"),
            ("Trả hằng tháng", "Số ₫", "Nên có",
             "Số tiền trả mỗi tháng (gốc + lãi). Dùng cho chỉ số **Trả nợ / thu nhập** ở Sức khoẻ tài chính.",
             "Kế hoạch FIRE → Sức khoẻ tài chính", "8000000", "Trả gốc + lãi mỗi tháng (₫)"),
            ("Ngày tất toán", "Ngày dd/mm/yyyy", "Không", "Ngày dự kiến trả hết nợ – để theo dõi.", "", "01/01/2040",
             "Ngày dự kiến trả hết"),
            ("Ghi chú", "Chữ", "Không", "Ghi chú tuỳ ý.", "", "Ân hạn gốc 12 tháng", "Ghi chú tuỳ ý"),
        ],
        "computed": [],
        "example": ["Vay mua nhà BIDV · 450.000.000 · 8,5 · 8.000.000 · 01/01/2040"],
        "tips": ["Khoản trả nợ hằng tháng cũng nên khai ở trang Thu chi (nhóm Chi thiết yếu) để dòng tiền đúng."],
    },
    # ------------------------------------------------------------------ Tài sản
    "assets": {
        "title": "Danh sách tài sản",
        "intro": "Mỗi dòng là **một tài sản**. **Mã** là khoá nối tài sản với Giao dịch, Giá và Sổ tiết kiệm. "
                 "Quỹ, cổ phiếu, vàng nên thêm bằng khung **Thêm tài sản** phía trên (điền sẵn mọi cột).",
        "cols": [
            ("Mã", "Chữ in hoa, ≤ 12 ký tự, không trùng", "Có",
             "Khoá của tài sản. **Không đổi được sau khi lưu** (muốn đổi: thêm mã mới). Mã **QKC** được app hiểu là "
             "quỹ khẩn cấp.", "Giao dịch, Giá, Sổ tiết kiệm (cột Nhóm)", "DCDS; FPT; QKC",
             "Khoá nối Giao dịch/Giá/Sổ – không đổi sau khi lưu. QKC = quỹ khẩn cấp"),
            ("Tên", "Chữ", "Có", "Tên đầy đủ hiển thị trong báo cáo.", "", "Quỹ cổ phiếu Dragon Capital",
             "Tên hiển thị"),
            ("Loại", "Chọn danh sách", "Không",
             "Phân loại để xem; loại **Bảo hiểm** được tính ở chỉ số Bảo vệ rủi ro (Sức khoẻ tài chính).", "",
             "Quỹ mở cổ phiếu", "Phân loại tài sản (Bảo hiểm → chỉ số bảo vệ rủi ro)"),
            ("Tầng", "Tăng trưởng / Thu nhập / Bảo vệ / Phòng thủ", "Có",
             "Vị trí trong **tháp tài sản**: Tăng trưởng (cổ phiếu, quỹ CP), Thu nhập (trái phiếu, cho thuê), "
             "Bảo vệ (bảo hiểm, vàng), Phòng thủ (tiền gửi, quỹ khẩn cấp).", "Tổng quan: Cơ cấu tài sản",
             "Tăng trưởng", "Tầng trong tháp tài sản – dùng cho biểu đồ cơ cấu"),
            ("Tính FIRE?", "Tick / bỏ tick", "Có",
             "Tick nếu tài sản dùng để **tạo thu nhập thụ động khi nghỉ hưu**. Chỉ tài sản tick mới cộng vào tiến độ "
             "FIRE. Thường bỏ tick: quỹ khẩn cấp, tiền cho mục tiêu ngắn hạn, nhà đang ở.",
             "Kế hoạch FIRE: tiến độ, mốc thành tựu", "✓ (quỹ CP) ✗ (QKC)",
             "Tick = cộng vào tài sản tính FIRE (tạo thu nhập thụ động)"),
            ("Lợi suất KV (%/năm)", "Số %, gõ 10 = 10%", "Nên có",
             "Giả định lợi suất dài hạn **danh nghĩa** (chưa trừ lạm phát). Khi bật *Lợi suất tự tính*, app lấy bình quân "
             "gia quyền theo giá trị các tài sản Tính FIRE.", "Kế hoạch FIRE → Giả định", "10",
             "Giả định lợi suất dài hạn, gõ 10 = 10%/năm – không phải cam kết"),
            ("Tỷ lệ mục tiêu (%)", "Số %, gõ 40 = 40%", "Không",
             "Tỷ lệ **bạn muốn** cho tài sản này trong nhóm tái cân bằng. Chỉ điền cho các tài sản muốn tái cân bằng; "
             "tổng nhóm nên = 100. App tính *Cần bổ sung* theo cách **chỉ mua thêm** (không bán).",
             "Tài sản → Tái cân bằng", "40", "Tỷ lệ bạn muốn (gõ 40 = 40%) – để trống nếu không tái cân bằng"),
            ("Cách định giá", "Thị trường / Khai báo / Sổ tiết kiệm", "Có",
             "**Thị trường**: giá tự cập nhật theo Nguồn giá. **Khai báo**: bạn tự nhập giá ở trang Giá (BĐS, bảo hiểm, "
             "khoản góp vốn…). **Sổ tiết kiệm**: giá trị = tổng các sổ cùng mã. Hai cách đầu: giá trị = Số lượng (từ "
             "Giao dịch) × Giá mới nhất.", "Trang Giá; tab Sổ tiết kiệm", "Thị trường",
             "Thị trường (giá tự động) · Khai báo (giá nhập tay) · Sổ tiết kiệm (cộng các sổ)"),
            ("Nguồn giá", "Cú pháp nguồn:mã", "Khi định giá Thị trường",
             "`fmarket` (NAV quỹ mở) · `vndirect` (cổ phiếu/ETF) · `pnj:SJC:mua` hoặc `pnj:N24K:mua` (vàng, giá mua "
             "vào/chỉ). Để trống = nhập giá tay. Có thể ghi mã khác mã app, VD `vndirect:FPT`.", "Trang Giá",
             "fmarket", "fmarket · vndirect · pnj:SJC:mua – để trống = nhập tay"),
            ("Đơn vị", "Chữ", "Không", "Đơn vị số lượng để bạn đọc cho dễ.", "", "CCQ; cổ phiếu; chỉ",
             "Đơn vị số lượng (CCQ, cổ phiếu, chỉ…)"),
            ("Ghi chú", "Chữ", "Không", "Ghi chú tuỳ ý.", "", "Mua qua Fmarket", "Ghi chú tuỳ ý"),
            ("Thứ tự", "Số nguyên", "Không", "Thứ tự sắp xếp trong các bảng (nhỏ đứng trước).", "", "10",
             "Thứ tự hiển thị (nhỏ đứng trước)"),
        ],
        "computed": [],
        "example": [
            "Quỹ cổ phiếu: DCDS · Quỹ cổ phiếu DCDS · Quỹ mở cổ phiếu · Tăng trưởng · ✓ · 12 · 40 · Thị trường · fmarket · CCQ",
            "Quỹ khẩn cấp: QKC · Quỹ khẩn cấp · Tiết kiệm · Phòng thủ · ✗ · 5 · (trống) · Sổ tiết kiệm · (trống)",
            "Căn hộ cho thuê: CANHO · Căn hộ Q7 · Bất động sản · Thu nhập · ✓ · 6 · (trống) · Khai báo · (trống) · căn "
            "→ ghi Vốn đầu kỳ số lượng 1, giá vốn = giá mua; cập nhật giá trị ở trang Giá.",
        ],
        "tips": [
            "Gõ % theo số nguyên: 10 nghĩa là 10% (đừng gõ 0,1).",
            "Tài sản đã có giao dịch/sổ thì không xoá được – xoá giao dịch trước.",
            "Định giá Khai báo mà chưa nhập giá ở trang Giá → giá trị = 0 và có cảnh báo *Chưa có giá*.",
        ],
    },
    # ------------------------------------------------------------------ Giao dịch: khai lần đầu
    "opening": {
        "title": "Tài sản đang có (khai lần đầu)",
        "intro": "Dành cho tài sản đã mua từ trước, **không muốn nhập lại từng lệnh**. Mỗi mã lưu thành **1 giao dịch "
                 "Vốn đầu kỳ**; sau này mua thêm thì ghi ở tab *Mua CCQ nhanh*.",
        "cols": [
            ("Số lượng đang có", "Số, 2 chữ số lẻ", "Có",
             "Số CCQ / cổ phiếu / chỉ vàng đang nắm giữ. Để trống = bỏ qua mã đó.", "Giao dịch: Vốn đầu kỳ (cột Số lượng)",
             "1234,56", "Số đơn vị đang nắm giữ (CCQ ghi đủ 2 số lẻ)"),
            ("Giá vốn BQ (₫)", "Số ₫ mỗi đơn vị", "Có (hoặc Tổng vốn)",
             "Giá vốn bình quân mỗi đơn vị – xem trong app quỹ/chứng khoán. Vốn = Số lượng × Giá vốn BQ.",
             "Giao dịch: Vốn đầu kỳ (cột Giá)", "24500", "Giá vốn bình quân mỗi CCQ/cổ phiếu"),
            ("hoặc Tổng vốn (₫)", "Số ₫", "Có (hoặc Giá vốn BQ)",
             "Điền nếu không biết giá vốn BQ – app tự chia: Giá vốn BQ = Tổng vốn ÷ Số lượng.", "", "30246720",
             "Tổng tiền đã bỏ ra – app tự chia ra giá vốn BQ"),
            ("Ngày khai", "Ngày dd/mm/yyyy", "Có",
             "Thường là hôm nay. XIRR của mã tính **từ ngày này** (hiện sau 30 ngày), dùng giá thị trường quanh ngày khai.",
             "", "20/11/2026", "Thường là hôm nay – XIRR tính từ ngày này"),
        ],
        "computed": [("Giá hiện tại", "Giá mới nhất trên bảng giá – để đối chiếu lãi/lỗ.")],
        "example": ["DCDS · 1.234,56 · 24.500 · (trống) · 20/11/2026 → vốn 30.246.720 ₫; hoặc để trống Giá vốn BQ và "
                    "điền Tổng vốn 30.246.720."],
        "tips": ["Lưu xong mã rời khỏi bảng này. Sửa số dư đã khai ở tab *Lịch sử & sửa* (dòng Vốn đầu kỳ)."],
    },
    # ------------------------------------------------------------------ Giao dịch: lịch sử
    "transactions": {
        "title": "Giao dịch",
        "intro": "Mỗi dòng là **một lần mua, bán, nhận cổ tức hoặc khai số dư**. Số lượng nắm giữ, giá vốn, lãi/lỗ và "
                 "XIRR của từng tài sản đều cộng từ bảng này. Cột cần điền **tuỳ Loại GD** – xem bảng ngay dưới.",
        "cols": [
            ("Ngày", "Ngày dd/mm/yyyy", "Có", "Ngày giao dịch (ngày khớp lệnh / ngày nhận tiền).",
             "Bảng giá: tra giá đúng ngày này nếu để trống Giá", "18/11/2026", "Ngày khớp lệnh / nhận tiền"),
            ("Mã", "Chọn mã tài sản", "Có", "Tài sản của giao dịch.", "Trang Tài sản (cột Mã)", "DCDS",
             "Mã tài sản (tạo ở trang Tài sản)"),
            ("Loại GD", "Mua / Bán / Cổ tức TM / Cổ tức CP/Thưởng / Vốn đầu kỳ", "Có",
             "Quyết định cột nào được dùng và dấu của dòng tiền (xem bảng theo loại).", "", "Mua",
             "Mua · Bán · Cổ tức TM · Cổ tức CP/Thưởng · Vốn đầu kỳ"),
            ("Số tiền", "Số ₫", "Tuỳ loại",
             "**Mua theo số tiền** (quỹ mở): số tiền bỏ ra. **Cổ tức TM**: tiền cổ tức nhận được. "
             "Có Giá thì app tính lại giá trị = Số lượng × Giá.", "", "3000000",
             "Mua quỹ theo số tiền / tiền cổ tức nhận được"),
            ("Giá", "Số ₫ mỗi đơn vị", "Tuỳ loại",
             "Giá khớp / NAV. **Để trống** → app tra giá **đúng ngày** trên bảng giá (ngày nghỉ không có giá → "
             "không tính được số lượng, nên điền).", "Trang Giá", "25000",
             "Giá khớp/NAV – trống thì app tra giá đúng ngày"),
            ("Số lượng", "Số, 2 chữ số lẻ", "Tuỳ loại",
             "Số đơn vị. **Mua** để trống → app tính = Số tiền ÷ Giá (cắt 2 số lẻ). **Bán, Cổ tức CP** bắt buộc.", "",
             "120", "Số đơn vị – Mua để trống thì app tính = Số tiền ÷ Giá"),
            ("Phí", "Số ₫", "Không",
             "Phí giao dịch. **Mua**: cộng vào giá vốn. **Bán**: trừ vào tiền nhận.", "", "15000",
             "Phí giao dịch – mua cộng vào vốn, bán trừ vào tiền nhận"),
            ("Thuế", "Số ₫", "Không", "Thuế khi **Bán** (0,1% giá trị bán) – trừ vào tiền nhận.", "", "4700",
             "Thuế bán (0,1%) – trừ vào tiền nhận"),
            ("Ghi chú", "Chữ", "Không",
             "Ghi chú. Có chữ **XÁC NHẬN** thì app nhắc ở Việc cần chú ý (VD cổ tức chưa chắc ngày nhận).", "",
             "Cổ tức 2025", "Ghi chú – có chữ XÁC NHẬN sẽ được nhắc"),
        ],
        "by_type": """
| Loại GD | Số tiền | Giá | Số lượng | Phí / Thuế | App tính |
|---|---|---|---|---|---|
| **Mua** quỹ theo tiền | ✔ số tiền | ✔ NAV (hoặc trống: tra theo ngày) | trống | Phí nếu có | SL = Số tiền ÷ Giá; vốn += SL × Giá + Phí |
| **Mua** cổ phiếu | trống | ✔ giá khớp | ✔ | Phí | vốn += SL × Giá + Phí |
| **Bán** | trống | ✔ giá khớp | ✔ (≤ đang có) | Phí + Thuế | SL giảm; tiền nhận = SL × Giá − Phí − Thuế |
| **Cổ tức TM** | ✔ tiền nhận | trống | trống | – | cộng vào cổ tức, lãi/lỗ, XIRR |
| **Cổ tức CP/Thưởng** | trống | trống | ✔ số CP nhận | – | SL tăng, vốn không đổi |
| **Vốn đầu kỳ** | (tự tính) | ✔ giá vốn BQ | ✔ đang có | – | số dư ban đầu; XIRR tính từ ngày khai |
""",
        "computed": [("SL tính", "Số lượng app dùng (điền tay hoặc Số tiền ÷ Giá)."),
                     ("Dòng tiền", "Âm khi Mua (tiền ra), dương khi Bán/Cổ tức TM (tiền về) – dùng để tính XIRR.")],
        "example": [
            "Mua quỹ: 18/11/2026 · DCDS · Mua · 3.000.000 · 25.000 · (trống) → SL tính 120,00; Dòng tiền −3.000.000",
            "Mua cổ phiếu: 18/11/2026 · FPT · Mua · (trống) · 120.000 · 100 · Phí 18.000 → vốn 12.018.000",
            "Bán: 20/11/2026 · FPT · Bán · (trống) · 125.000 · 100 · Phí 18.750 · Thuế 12.500 → nhận 12.468.750",
            "Cổ tức: 25/11/2026 · FPT · Cổ tức TM · 200.000",
        ],
        "tips": [
            "Bán nhiều hơn số đang có sẽ làm số lượng âm – kiểm tra cột Số lượng ở trang Tài sản.",
            "Tiền dùng dấu chấm phân cách hàng nghìn khi hiển thị; khi gõ chỉ cần gõ số liền (3000000).",
            "Xoá dòng: chọn dòng → biểu tượng thùng rác → Lưu thay đổi (app sao lưu tự động mỗi ngày).",
        ],
    },
}

_HEAD = "| Cột | Loại & định dạng | Bắt buộc | Ý nghĩa & cách app dùng | Liên kết | Ví dụ |\n|---|---|---|---|---|---|\n"


def tip(key: str, label: str) -> str:
    """Câu ngắn cho tooltip tiêu đề cột."""
    for c in GUIDES[key]["cols"]:
        if c[0] == label:
            return c[6]
    raise KeyError(f"{key}: chưa có giải thích cho cột {label!r}")


def table_md(key: str) -> str:
    rows = "".join(f"| **{c[0]}** | {c[1]} | {c[2]} | {c[3]} | {c[4] or '–'} | {c[5]} |\n" for c in GUIDES[key]["cols"])
    return _HEAD + rows


_CSS = f"""<style>
.fg{{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:10px;margin:6px 0 10px}}
@media (max-width:900px){{.fg{{grid-template-columns:1fr}}}}
.fg .c{{background:{style.CARD};border:1px solid #2C2C2C;border-radius:14px;padding:12px 14px}}
.fg .h{{display:flex;flex-wrap:wrap;align-items:center;gap:6px 8px;margin-bottom:6px}}
.fg .n{{font-weight:700;color:{style.TEXT}}}
.fg .k{{font-size:.72rem;border-radius:999px;padding:2px 9px;background:#1C1C1C;border:1px solid #333;color:#CFCFCF}}
.fg .k.req{{border-color:rgba(182,243,106,.45);color:{style.LIME}}}
.fg .d{{color:#CFCFCF;font-size:.86rem;line-height:1.5}}
.fg .d b{{color:{style.TEXT}}}
.fg .m{{color:{style.MUTED};font-size:.8rem;margin-top:6px;line-height:1.45}}
.fg .m b{{color:#DADADA;font-weight:600}}
.fg code{{background:#1C1C1C;border-radius:6px;padding:1px 5px;color:{style.LIME};font-size:.8rem}}
</style>"""


def _md(s: str) -> str:
    """Markdown tối giản (`code`, **đậm**, *nghiêng*) → HTML cho thẻ."""
    s = re.sub(r"`([^`]+)`", r"<code>\1</code>", s)
    s = re.sub(r"\*\*(.+?)\*\*", r"<b>\1</b>", s)
    return re.sub(r"\*(.+?)\*", r"<i>\1</i>", s)


def cards_html(key: str) -> str:
    """Mỗi cột một thẻ: tên + loại + bắt buộc, ý nghĩa, liên kết, ví dụ (dễ đọc hơn bảng 6 cột trên màn hẹp)."""
    out = []
    for name, kind, req, meaning, link, ex, _ in GUIDES[key]["cols"]:
        tag_req = f'<span class="k{" req" if req.startswith("Có") else ""}">{_md({"Có": "Bắt buộc", "Không": "Tuỳ chọn"}.get(req, req))}</span>'
        meta = (f'<div class="m"><b>Liên kết:</b> {_md(link)}</div>' if link else "") + \
               f'<div class="m"><b>Ví dụ:</b> {_md(ex)}</div>'
        out.append(f'<div class="c"><div class="h"><span class="n">{name}</span><span class="k">{_md(kind)}</span>'
                   f'{tag_req}</div><div class="d">{_md(meaning)}</div>{meta}</div>')
    return _CSS + f'<div class="fg">{"".join(out)}</div>'


def render(key: str, label: str = "Cách điền bảng này", ident: str = "") -> None:
    """ident: phân biệt khi cùng một hướng dẫn hiện 2 lần trên một trang (khoá phần tử không được trùng)."""
    g = GUIDES[key]
    with st.expander(f"{label} – {g['title']}", key=style.ic("help-circle", f"fg_{key}{ident}")):
        st.markdown(g["intro"])
        st.html(cards_html(key))
        if g.get("by_type"):
            st.markdown("**Điền cột nào theo Loại GD**")
            st.markdown(g["by_type"])
        if g.get("computed"):
            st.markdown("**Cột app tự tính (không sửa được)**")
            st.markdown("\n".join(f"- **{n}**: {d}" for n, d in g["computed"]))
        if g.get("example"):
            st.markdown("**Ví dụ điền**")
            st.markdown("\n".join(f"- {x}" for x in g["example"]))
        if g.get("tips"):
            st.html(style.tip("<b>Lỗi hay gặp:</b> " + " · ".join(_md_b(x) for x in g["tips"])))


def _md_b(s: str) -> str:
    """**đậm** markdown → <b> cho khung tip HTML."""
    out, on = [], False
    for i, part in enumerate(s.split("**")):
        out.append(("<b>" if on else "</b>") if i else "")
        out.append(part.replace("*", ""))
        on = not on
    return "".join(out)

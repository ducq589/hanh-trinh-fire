"""Tạo file mẫu trống Investment_tracking_v4.xlsx từ v3 (v3 chỉ được ĐỌC, không bị sửa).

- Giữ nguyên cấu trúc: các sheet, bảng (Excel Table), công thức, biểu đồ, dropdown, ghi chú hướng dẫn.
- Xoá toàn bộ số liệu cá nhân: tài sản, giao dịch, sổ tiết kiệm, mục tiêu, nợ, giá, snapshot, số tiền thu chi, tuổi.
- Bỏ kết nối Power Query (trỏ tới đường dẫn gia.csv trên máy người tạo) – giá do app tự cập nhật.

Chạy:  .venv/bin/python scripts/tao_mau_v4.py
Kết quả: mau/Investment_tracking_v4.xlsx (app cho tải về) và ../Investment_tracking_v4.xlsx
"""
from __future__ import annotations

import re
import shutil
import sys
import zipfile
from pathlib import Path

import openpyxl

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT.parent / "Investment_tracking_v3.xlsx"
OUT = ROOT / "mau" / "Investment_tracking_v4.xlsx"
COPY = ROOT.parent / "Investment_tracking_v4.xlsx"

# bảng → các cột NHẬP (giữ cột công thức ở dòng dữ liệu đầu tiên)
TABLES = {
    "tblTaiSan": "DM_TaiSan", "tblGD": "GiaoDich", "tblSTK": "SoTietKiem", "tblMucTieu": "MucTieu",
    "tblNo": "No", "tblGiaTay": "Gia", "tblGiaAuto": "Gia_Auto", "tblSnapshot": "Snapshot",
}

HUONG_DAN = [
    "HƯỚNG DẪN SỬ DỤNG – Investment_tracking v4 (mẫu trống)",
    "Điền thông tin của bạn vào các BẢNG (ô chữ xanh / nền vàng) → DanhMuc, FI_Plan, Dashboard tự tính. "
    "Sau đó tải file lên app Hành trình FIRE (trang Sao lưu & Cài đặt) để giá được tự cập nhật hằng ngày.",
    None,
    "1. THU CHI (sheet Profile) – khai 1 lần",
    "• Điền cột Số tiền theo số tiền ĐIỂN HÌNH và chọn Tần suất (Tháng/Quý/Năm). File tự quy đổi về mỗi tháng.",
    "• Khoản không có: để trống. Thêm khoản mới = gõ vào dòng ngay dưới bảng. Ghi Ngày cập nhật ở ô B3.",
    None,
    "2. TÀI SẢN (sheet DM_TaiSan)",
    "• Mỗi tài sản 1 dòng: Mã (ngắn, không dấu cách, không trùng), Tên, Loại, Tầng, Tính FI?, Lợi suất KV, Cách định giá.",
    "• Để app TỰ LẤY GIÁ, ghi Mã đúng mã giao dịch: quỹ mở theo mã Fmarket (DCDS, VESAF, VNDBF…), "
    "cổ phiếu/ETF theo mã sàn (FPT, MBB, E1VFVN30…).",
    "• Vàng, bảo hiểm, BĐS: giá nhập tay ở sheet Gia (hoặc chọn nguồn giá vàng PNJ trong app sau khi tải lên).",
    "• Tiết kiệm: Cách định giá = Sổ tiết kiệm, rồi nhập từng sổ ở sheet SoTietKiem với cùng Mã.",
    None,
    "3. GIAO DỊCH (sheet GiaoDich)",
    "• Mua quỹ mở: Ngày, Mã, Loại GD = Mua, Số tiền (để trống Giá & Số lượng nếu chưa biết – app tự tra NAV).",
    "• Mua cổ phiếu: Giá (VND/CP), Số lượng, Phí. Bán: Loại GD = Bán, Giá, Số lượng, Phí, Thuế.",
    "• Cổ tức tiền mặt: Loại GD = Cổ tức TM, Số tiền. Cổ tức cổ phiếu/thưởng: Loại GD = Cổ tức CP/Thưởng, Số lượng.",
    "• Tài sản có từ trước, không rõ ngày mua (vàng, bảo hiểm…): Loại GD = Vốn đầu kỳ.",
    "• Các cột từ 'Giá dùng' trở sang phải tự tính – không nhập.",
    None,
    "4. SỔ TIẾT KIỆM, MỤC TIÊU, NỢ",
    "• SoTietKiem: mỗi sổ 1 dòng (Gói, Mã TS, Ngày đáo hạn, Gốc, Gửi đầu kỳ, Lãi trước thuế).",
    "• MucTieu: khoản cần tiền trong tương lai (học phí…). Cột 'Mục tiêu' ở SoTietKiem ghi ĐÚNG tên mục tiêu.",
    "• No: các khoản vay (nhà, xe, thẻ tín dụng…). Để trống nếu không có nợ.",
    None,
    "5. GIẢ ĐỊNH FIRE (sheet FI_Plan, ô B4:B10)",
    "• Tuổi hiện tại, tuổi muốn đạt FIRE, lạm phát, lợi suất kỳ vọng, tỷ lệ rút an toàn (SWR), số tháng quỹ khẩn cấp.",
    None,
    "6. ĐƯA LÊN APP",
    "• Mở app Hành trình FIRE → Sao lưu & Cài đặt → Nhập dữ liệu từ Excel → chọn file này → tick xác nhận → Nhập.",
    "• Sau khi nhập, giá quỹ/cổ phiếu tự cập nhật mỗi ngày; giao dịch mới ghi thẳng trên app.",
    None,
    "QUY ƯỚC",
    "• Chữ xanh dương / ô vàng = dữ liệu nhập. Chữ đen = công thức. Mọi giá tính bằng VND (VD cổ phiếu 18.800).",
    "• Sheet Gia_Auto dành cho giá tự động (app ghi vào khi xuất) – không cần nhập tay.",
    "• Yêu cầu Excel 365 nếu muốn xem các trang tính toán trong Excel.",
]


def _shrink(ws, tname: str) -> None:
    """Thu bảng về 1 dòng dữ liệu trống: xoá giá trị nhập dòng 2, xoá hẳn các dòng sau, giữ công thức cột tính."""
    t = ws.tables[tname]
    (c1, r1), (c2, r2) = [openpyxl.utils.cell.coordinate_from_string(x) for x in t.ref.split(":")]
    first, last = openpyxl.utils.column_index_from_string(c1), openpyxl.utils.column_index_from_string(c2)
    calc = {i for i, tc in enumerate(t.tableColumns) if tc.calculatedColumnFormula is not None}
    data_row = r1 + 1
    for row in range(data_row, r2 + 1):
        for j, col in enumerate(range(first, last + 1)):
            cell = ws.cell(row, col)
            keep_formula = (row == data_row and isinstance(cell.value, str) and cell.value.startswith("=")
                            and (j in calc or tname == "tblSnapshot"))
            if not keep_formula:
                cell.value = None
    t.ref = f"{c1}{r1}:{c2}{data_row}"
    if t.autoFilter is not None:
        t.autoFilter.ref = t.ref


def _strip_chart_cache(src: Path, dst: Path) -> None:
    """Biểu đồ lưu sẵn số liệu cũ (numCache/strCache) → xoá để không lộ dữ liệu; Excel tự vẽ lại khi mở."""
    cache = re.compile(r"<(?:c:)?(numCache|strCache)>.*?</(?:c:)?\1>", re.S)
    with zipfile.ZipFile(src) as zin, zipfile.ZipFile(dst, "w", zipfile.ZIP_DEFLATED) as zout:
        for item in zin.infolist():
            data = zin.read(item.filename)
            if item.filename.startswith("xl/charts/"):
                data = cache.sub("", data.decode("utf-8")).encode("utf-8")
            zout.writestr(item, data)


def build() -> Path:
    if not SRC.exists():
        sys.exit(f"Không thấy {SRC}")
    wb = openpyxl.load_workbook(SRC)          # chỉ đọc v3; lưu ra file khác

    for tname, sheet in TABLES.items():
        _shrink(wb[sheet], tname)

    # tblGiaAuto từng là bảng Power Query: bỏ dấu queryTable (phần kết nối không còn → Excel báo lỗi nếu giữ)
    ga = wb["Gia_Auto"].tables["tblGiaAuto"]
    ga.tableType = None
    for tc in ga.tableColumns:
        tc.queryTableFieldId = None
        tc.uniqueName = None

    # Thu chi: giữ danh sách khoản mục gợi ý, xoá số tiền / thành viên / ghi chú cá nhân
    p = wb["Profile"]
    t = p.tables["tblThuChi"]
    r2 = int(t.ref.split(":")[1].lstrip("ABCDEFGHIJKLMNOPQRSTUVWXYZ"))
    p["B3"] = None
    for row in range(6, r2 + 1):
        p.cell(row, 3).value = None                                   # Thành viên
        p.cell(row, 4).value = None                                   # Số tiền
        if row != 10:                                                 # G10 là hướng dẫn chung
            p.cell(row, 7).value = None

    # Giả định FIRE: bỏ tuổi cá nhân, để mặc định hợp lý
    f = wb["FI_Plan"]
    f["B4"], f["B5"] = None, 50

    # Hướng dẫn mới cho mẫu v4 (không còn Power Query)
    h = wb["HuongDan"]
    for row in range(1, h.max_row + 1):
        h.cell(row, 1).value = None
    for i, line in enumerate(HUONG_DAN, start=1):
        h.cell(i, 1).value = line

    # Bỏ tên vùng của Power Query + thông tin tác giả
    for ws in wb.worksheets:
        for name in [n for n in ws.defined_names if n.startswith("ExternalData")]:
            del ws.defined_names[name]
    wb.properties.creator = wb.properties.lastModifiedBy = "Hành trình FIRE"
    wb.properties.title = "Investment_tracking_v4 – mẫu trống"
    for ws in wb.worksheets:
        ws.sheet_view.tabSelected = ws.title == "HuongDan"
    wb.active = wb.sheetnames.index("HuongDan")

    # Ghi chú nhắc tới sổ tiết kiệm cụ thể → thay bằng hướng dẫn chung
    from openpyxl.comments import Comment
    wb["SoTietKiem"]["G1"].comment = Comment(
        "Tiền gốc nộp thêm sau ngày gửi ban đầu (nếu có), để % tăng trưởng tính đúng.", "Hành trình FIRE")

    OUT.parent.mkdir(parents=True, exist_ok=True)
    tmp = OUT.with_suffix(".tmp.xlsx")
    wb.save(tmp)
    _strip_chart_cache(tmp, OUT)
    tmp.unlink()
    shutil.copyfile(OUT, COPY)
    return OUT


if __name__ == "__main__":
    print(build())

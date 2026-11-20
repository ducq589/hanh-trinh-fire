"""Chính sách quyền riêng tư & Điều khoản sử dụng – trang công khai (không cần đăng nhập).

Địa chỉ:  <app>/?doc=privacy · <app>/?doc=terms · <app>/?doc=delete (hướng dẫn xoá tài khoản – Google Play yêu cầu)
Email liên hệ lấy từ secrets [supabase] contact_email (không ghi vào code).
"""
from __future__ import annotations

import streamlit as st

from . import intro, style

UPDATED = "20/11/2026"
DOCS = ("privacy", "terms", "delete")


def _cfg() -> dict:
    try:
        return dict(st.secrets.get("supabase") or {})
    except Exception:
        return {}


def base() -> str:
    """Địa chỉ gốc của app (secrets site_url) – link tuyệt đối mở ở cửa sổ chính (app trên Streamlit Cloud nằm trong iframe)."""
    return str(_cfg().get("site_url") or "").rstrip("/")


def url(doc: str | None = None) -> str:
    return f"{base()}/?doc={doc}" if doc else (base() or "/")


def _a(href: str, text: str) -> str:
    return f'<a href="{href}" target="_top">{text}</a>'


def contact() -> str:
    email = _cfg().get("contact_email") or ""
    return f"**{email}**" if email else "người quản trị app (qua kênh bạn nhận được đường link app)"


def _privacy(c: str) -> str:
    return f"""
**Hành trình FIRE** là công cụ giúp bạn lập kế hoạch và theo dõi hành trình tới tự do tài chính. Trang này giải thích
app thu thập dữ liệu gì, dùng để làm gì và bạn có những quyền gì.

#### 1. Dữ liệu app thu thập
- **Thông tin tài khoản:** địa chỉ email và mã người dùng do hệ thống đăng nhập (Supabase Auth) cấp.
- **Khi đăng nhập bằng Google:** app chỉ nhận **email và thông tin hồ sơ cơ bản** (tên, ảnh đại diện) mà Google
  cung cấp. App **không** đọc Gmail, Google Drive, danh bạ hay bất kỳ dữ liệu nào khác trong tài khoản Google của bạn.
- **Dữ liệu tài chính do bạn tự nhập:** danh mục tài sản, giao dịch, số dư đầu kỳ, hồ sơ thu chi, sổ tiết kiệm,
  mục tiêu, khoản nợ và các giả định lập kế hoạch FIRE.
- App **không** thu thập số tài khoản ngân hàng, mật khẩu, thông tin thẻ, giấy tờ tuỳ thân, và không kết nối với tài
  khoản ngân hàng hay chứng khoán của bạn.

#### 2. Mục đích sử dụng
- Hiển thị bức tranh tài sản, tính lãi/lỗ, tiến độ và kế hoạch tự do tài chính **cho chính bạn**.
- Gửi mã đăng nhập vào email của bạn.
- App **không** dùng dữ liệu để quảng cáo, **không bán** và **không chia sẻ** dữ liệu của bạn cho bên thứ ba.

#### 3. Lưu trữ và bảo mật
- Dữ liệu được lưu trên cơ sở dữ liệu **Supabase**; mỗi tài khoản được **tách riêng bằng phân quyền theo từng dòng dữ liệu**
  – tài khoản khác không thể đọc hay sửa dữ liệu của bạn. Kết nối được mã hoá (HTTPS/TLS).
- Giao diện app chạy trên **Streamlit Community Cloud**.
- Trên trình duyệt, app chỉ lưu **mã ghi nhớ đăng nhập** (trong localStorage) để bạn không phải nhập mã mỗi lần; mã này
  bị thu hồi và xoá khi bạn bấm **Đăng xuất**.
- Giá chứng chỉ quỹ, cổ phiếu, vàng được tải từ các nguồn công khai (Fmarket, VNDirect, PNJ). App chỉ tải giá về,
  **không gửi** dữ liệu của bạn tới các nguồn này.

#### 4. Quyền của bạn
- Xem, sửa, xoá dữ liệu của mình bất cứ lúc nào ngay trong app.
- Tải toàn bộ dữ liệu ra file Excel tại **Sao lưu & Cài đặt → Tạo báo cáo Excel**.
- **Tự xoá tài khoản và toàn bộ dữ liệu ngay trong app**: **Sao lưu & Cài đặt → Xoá tài khoản**. Việc xoá diễn ra
  ngay lập tức và không thể hoàn tác (xem trang **Xoá tài khoản**).
- Không đăng nhập được? Gửi yêu cầu xoá tới {c} từ chính email của tài khoản; yêu cầu được xử lý trong vòng 30 ngày.

#### 5. Thay đổi chính sách
Khi chính sách thay đổi, nội dung mới được cập nhật tại trang này kèm ngày cập nhật.

#### 6. Liên hệ
Mọi câu hỏi về quyền riêng tư, vui lòng liên hệ {c}.
"""


def _terms(c: str) -> str:
    no = "\n".join(f"- {x.replace('<b>', '**').replace('</b>', '**')}" for x in intro.APP_DOES_NOT)
    return f"""
Khi sử dụng **Hành trình FIRE**, bạn đồng ý với các điều khoản dưới đây.

#### 1. App là gì
Hành trình FIRE là công cụ **lập kế hoạch và theo dõi** tài chính cá nhân: ghi nhận tài sản, thu chi, giao dịch do bạn
khai báo và tính toán tiến độ tới tự do tài chính.

#### 2. App không làm gì
{no}

Mọi quyết định đầu tư và giao dịch do **bạn tự thực hiện** tại nơi bạn mở tài khoản và **tự chịu trách nhiệm**.

#### 3. Số liệu và dự phóng
- Giá lấy từ nguồn công khai có thể chậm hoặc sai lệch; hãy đối chiếu với nơi bạn giao dịch khi cần con số chính xác.
- Các con số dự phóng (lợi suất kỳ vọng, năm đạt FIRE…) dựa trên **giả định do bạn đặt**, chỉ để tham khảo, không phải
  cam kết lợi nhuận hay khuyến nghị.

#### 4. Tài khoản của bạn
- Bạn chịu trách nhiệm giữ an toàn email (và tài khoản Google nếu đăng nhập bằng Google) dùng để đăng nhập.
- Không dùng app cho mục đích trái pháp luật hoặc gây ảnh hưởng tới hệ thống và người dùng khác.

#### 5. Dịch vụ
- App được cung cấp **miễn phí, "như hiện có"**; có thể được thay đổi, tạm ngừng hoặc dừng mà không cần báo trước.
- Hãy tự sao lưu định kỳ bằng **Sao lưu & Cài đặt → Tạo báo cáo Excel**. Trong phạm vi pháp luật cho phép, app không
  chịu trách nhiệm về thiệt hại phát sinh từ việc sử dụng số liệu trong app.
- **Ủng hộ tự nguyện:** bạn có thể ủng hộ tác giả bằng chuyển khoản (mã VietQR ở trang Giới thiệu). Khoản ủng hộ hoàn toàn
  tự nguyện, **không phải phí dịch vụ**, không đổi lấy quyền lợi hay tính năng nào và không được hoàn lại. Không ủng hộ
  bạn vẫn dùng đầy đủ app. Giao dịch diễn ra trực tiếp giữa ngân hàng của bạn và tài khoản nhận; app không xử lý thanh toán.

#### 6. Quyền riêng tư
Cách app thu thập và bảo vệ dữ liệu được mô tả tại trang **Chính sách quyền riêng tư** (link cuối trang).

#### 7. Luật áp dụng và liên hệ
Điều khoản này được điều chỉnh theo pháp luật Việt Nam. Liên hệ: {c}.
"""


def _delete(c: str) -> str:
    return f"""
Bạn có thể **tự xoá tài khoản Hành trình FIRE và toàn bộ dữ liệu** bất cứ lúc nào, ngay trong app.

#### Cách xoá trong app
1. Đăng nhập vào app.
2. Mở trang **Sao lưu & Cài đặt** (menu bên trái, mục *Hệ thống*).
3. Kéo xuống mục **Xoá tài khoản** → mở khung **Xoá tài khoản và toàn bộ dữ liệu**.
4. Gõ đúng email tài khoản, tick ô xác nhận, rồi bấm **Xoá vĩnh viễn tài khoản**.

Muốn giữ lại số liệu? Trước khi xoá, bấm **Tạo báo cáo Excel** ở cùng trang để tải toàn bộ dữ liệu về máy.

#### Dữ liệu bị xoá
- Tài khoản đăng nhập (email, liên kết đăng nhập Google nếu có).
- Toàn bộ dữ liệu bạn đã nhập: tài sản, giao dịch, giá nhập tay, hồ sơ thu chi, sổ tiết kiệm, mục tiêu, khoản nợ,
  giả định kế hoạch, cài đặt, lịch sử snapshot và thành tựu.

Dữ liệu bị xoá khỏi cơ sở dữ liệu của app **ngay lập tức và vĩnh viễn**, không thể khôi phục. File Excel bạn đã tải
về máy (nếu có) vẫn thuộc về bạn. Giá thị trường dùng chung (NAV quỹ, giá cổ phiếu, vàng) không phải dữ liệu cá nhân nên không bị ảnh hưởng.

#### Không đăng nhập được?
Gửi yêu cầu xoá tới {c} **từ chính email của tài khoản** cần xoá. Yêu cầu được xử lý trong vòng 30 ngày và bạn sẽ
nhận được email xác nhận khi hoàn tất.
"""


TITLES = {"privacy": ("Chính sách quyền riêng tư", _privacy), "terms": ("Điều khoản sử dụng", _terms),
          "delete": ("Xoá tài khoản", _delete)}


def links_html() -> str:
    return ('<div style="text-align:center;font-size:.82rem;color:#8A8A8A;margin-top:10px">'
            f'{_a(url("privacy"), "Chính sách quyền riêng tư")} · {_a(url("terms"), "Điều khoản sử dụng")} · '
            f'{_a(url("delete"), "Xoá tài khoản")}</div>')


def render(doc: str) -> None:
    """Vẽ trang chính sách (gọi trước bước đăng nhập, rồi st.stop())."""
    title, body = TITLES[doc]
    st.markdown("<style>[data-testid='stSidebar'],[data-testid='stSidebarCollapsedControl']{display:none}</style>",
                unsafe_allow_html=True)
    _, mid, _ = st.columns([1, 3, 1])
    with mid:
        style.title("info-circle", title, f"Hành trình FIRE · cập nhật {UPDATED}")
        st.markdown(body(contact()))
        others = " &nbsp;·&nbsp; ".join(_a(url(d), TITLES[d][0]) for d in DOCS if d != doc)
        st.html(f'<div style="margin-top:18px;font-size:.9rem">{_a(url(), "← Về trang chủ")} &nbsp;·&nbsp; {others}</div>')

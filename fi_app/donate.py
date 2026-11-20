"""Ủng hộ tác giả bằng mã VietQR – hoàn toàn tự nguyện, app vẫn miễn phí.

Thông tin tài khoản nhận tiền đọc từ secrets mục [donate] (KHÔNG ghi vào code):
    bank_name, account_no, account_name, message, (bank_bin – chỉ cần khi ngân hàng không có trong BANKS)
Ngân hàng có trong BANKS → mã BIN lấy theo tên (tránh gõ nhầm BIN). Thiếu account_no hoặc không xác định được BIN → ẩn.

Mã QR tạo ngay trong app theo chuẩn NAPAS VietQR (EMVCo) và vẽ bằng segno – không gửi số tài khoản ra dịch vụ ngoài.
"""
from __future__ import annotations

import unicodedata

import streamlit as st

from . import style

AMOUNTS = {"20.000 ₫": 20_000, "50.000 ₫": 50_000, "100.000 ₫": 100_000, "Tự nhập": None}
DEFAULT_MESSAGE = "Ung ho Hanh trinh FIRE"
INTRO = ("Hành trình FIRE **miễn phí** và sẽ tiếp tục miễn phí. Nếu app giúp ích cho hành trình của bạn, bạn có thể "
         "ủng hộ tác giả một ly cà phê để trả chi phí máy chủ và duy trì phát triển. Ủng hộ **hoàn toàn tự nguyện**, "
         "không đổi lấy quyền lợi nào – cảm ơn bạn rất nhiều!")


# Mã BIN (NAPAS) theo tên ngân hàng – khoá đã chuẩn hoá: chữ thường, bỏ dấu và khoảng trắng.
BANKS = {
    "vietcombank": "970436", "vcb": "970436", "vietinbank": "970415", "ctg": "970415", "bidv": "970418",
    "agribank": "970405", "techcombank": "970407", "tcb": "970407", "mbbank": "970422", "mb": "970422",
    "acb": "970416", "vpbank": "970432", "tpbank": "970423", "sacombank": "970403", "vib": "970441",
    "shb": "970443", "hdbank": "970437", "msb": "970426",
}


def _norm(name: str) -> str:
    return ascii_text(name).lower().replace(" ", "")


def resolve_bin(bank_name: str, bank_bin: str = "") -> tuple[str, str]:
    """(BIN dùng cho QR, cảnh báo). Tên ngân hàng có trong BANKS → dùng BIN theo tên; BIN khai khác → cảnh báo."""
    known = BANKS.get(_norm(bank_name or ""))
    bank_bin = (bank_bin or "").strip()
    if known:
        warn = (f"bank_bin {bank_bin} không khớp {bank_name} ({known}) – app dùng {known}"
                if bank_bin and bank_bin != known else "")
        return known, warn
    return bank_bin, ""


def cfg() -> dict | None:
    try:
        d = {k: str(v).strip() for k, v in dict(st.secrets.get("donate") or {}).items()}
    except Exception:  # noqa: BLE001 – không có file secrets
        return None
    d["bank_bin"], d["warning"] = resolve_bin(d.get("bank_name", ""), d.get("bank_bin", ""))
    if not d["bank_bin"] or not d.get("account_no"):
        return None
    return d


# ---------------------------------------------------------------- VietQR (EMVCo)
def _tlv(tag: str, value: str) -> str:
    return f"{tag}{len(value):02d}{value}"


def crc16(data: str) -> str:
    """CRC16-CCITT (poly 0x1021, init 0xFFFF) – chuẩn EMVCo, 4 ký tự hex in hoa."""
    crc = 0xFFFF
    for b in data.encode("utf-8"):
        crc ^= b << 8
        for _ in range(8):
            crc = ((crc << 1) ^ 0x1021) if crc & 0x8000 else (crc << 1)
            crc &= 0xFFFF
    return f"{crc:04X}"


def ascii_text(s: str, limit: int = 50) -> str:
    """Bỏ dấu tiếng Việt, chỉ giữ chữ/số/khoảng trắng (nội dung chuyển khoản an toàn với mọi ngân hàng)."""
    s = unicodedata.normalize("NFD", s.replace("đ", "d").replace("Đ", "D"))
    s = "".join(ch for ch in s if unicodedata.category(ch) != "Mn")
    kept = "".join(ch for ch in s if ch.isascii() and (ch.isalnum() or ch == " "))
    return " ".join(kept.split())[:limit].strip()


def vietqr_payload(bank_bin: str, account_no: str, amount: int | None = None, message: str = "") -> str:
    """Chuỗi QR chuyển khoản nhanh NAPAS 247 tới tài khoản (có số tiền → QR động 12, không → QR tĩnh 11)."""
    beneficiary = _tlv("00", bank_bin) + _tlv("01", account_no)
    merchant = _tlv("00", "A000000727") + _tlv("01", beneficiary) + _tlv("02", "QRIBFTTA")
    parts = [_tlv("00", "01"), _tlv("01", "12" if amount else "11"), _tlv("38", merchant), _tlv("53", "704")]
    if amount:
        parts.append(_tlv("54", str(int(amount))))
    parts.append(_tlv("58", "VN"))
    msg = ascii_text(message)
    if msg:
        parts.append(_tlv("62", _tlv("08", msg)))
    body = "".join(parts) + "6304"
    return body + crc16(body)


def qr_png(payload: str, scale: int = 4) -> bytes:
    """Ảnh QR dạng PNG (nền trắng, viền đủ rộng để app ngân hàng quét dễ). segno ghi PNG không cần Pillow."""
    import io

    import segno
    buf = io.BytesIO()
    segno.make_qr(payload, error="m").save(buf, kind="png", scale=scale, border=4, dark="#111111", light="#FFFFFF")
    return buf.getvalue()


# ---------------------------------------------------------------- giao diện
def invite_line() -> str:
    """Dòng mời nhẹ nhàng (rỗng nếu chưa cấu hình)."""
    return "App miễn phí – nếu thấy hữu ích, bạn có thể ủng hộ tác giả ở trang **Ủng hộ**." if cfg() else ""


def render(key: str = "donate", heading: bool = True) -> None:
    c = cfg()
    if not c:
        return
    if c.get("warning"):
        import logging
        logging.getLogger(__name__).warning("[donate] %s", c["warning"])
    with st.container(border=True):
        if heading:
            st.markdown("#### Ủng hộ tác giả")
        st.markdown(INTRO)
        pick = st.radio("Mức ủng hộ", list(AMOUNTS), horizontal=True, index=1, key=f"{key}_amt")
        amount = AMOUNTS[pick]
        message = c.get("message") or DEFAULT_MESSAGE
        payload = vietqr_payload(c["bank_bin"], c["account_no"], amount, message)
        q1, q2 = st.columns([1, 1.8], vertical_alignment="center", gap="medium")
        with q1:
            # ~200 px trên màn rộng (bằng 1/2 trước đây), tự co lại khi cột hẹp
            st.image(qr_png(payload), width="content", caption="Quét bằng app ngân hàng")
        with q2:
            st.markdown(f"**Ngân hàng:** {c.get('bank_name') or c['bank_bin']}")
            if c.get("account_name"):
                st.markdown(f"**Chủ tài khoản:** {c['account_name']}")
            st.markdown("**Số tài khoản** (bấm biểu tượng để sao chép):")
            st.code(c["account_no"], language=None)
            st.markdown(f"**Nội dung:** {ascii_text(message)}"
                        + (f" · **Số tiền:** {pick}" if amount else " · **Số tiền:** bạn tự nhập trong app ngân hàng"))
        st.html(style.tip("Mở <b>app ngân hàng</b> → <b>Quét QR</b> → kiểm tra tên chủ tài khoản → xác nhận. "
                          "App Hành trình FIRE không nhận, không giữ và không xử lý giao dịch này."))

"""Ủng hộ VietQR: chuỗi QR đúng chuẩn EMVCo (CRC16), bỏ dấu nội dung, ảnh PNG hợp lệ, ẩn khi chưa cấu hình."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from fi_app import donate  # noqa: E402


def _fields(payload):
    """Tách TLV cấp 1 → dict tag → value."""
    out, i = {}, 0
    while i < len(payload):
        tag, n = payload[i:i + 2], int(payload[i + 2:i + 4])
        out[tag] = payload[i + 4:i + 4 + n]
        i += 4 + n
    return out


def test_crc16_ccitt_check_value():
    assert donate.crc16("123456789") == "29B1"          # giá trị kiểm tra chuẩn của CRC-16/CCITT-FALSE


def test_payload_with_amount_and_message():
    p = donate.vietqr_payload("970436", "0123456789", 50000, "Ủng hộ Hành trình FIRE")
    f = _fields(p)
    assert f["00"] == "01" and f["01"] == "12" and f["53"] == "704" and f["58"] == "VN" and f["54"] == "50000"
    m = _fields(f["38"])
    assert m["00"] == "A000000727" and m["02"] == "QRIBFTTA"
    assert _fields(m["01"]) == {"00": "970436", "01": "0123456789"}
    assert _fields(f["62"])["08"] == "Ung ho Hanh trinh FIRE"
    assert p[-8:-4] == "6304" and donate.crc16(p[:-4]) == p[-4:]


def test_payload_static_without_amount():
    f = _fields(donate.vietqr_payload("970418", "123", None, ""))
    assert f["01"] == "11" and "54" not in f and "62" not in f


def test_ascii_text_strips_vietnamese_and_symbols():
    assert donate.ascii_text("Đóng góp: cà phê ☕ #1") == "Dong gop ca phe 1"


def test_svg_and_cfg_absent():
    assert donate.qr_png(donate.vietqr_payload("970436", "1", 1000)).startswith(b"\x89PNG")
    assert donate.cfg() is None and donate.invite_line() == ""          # không có secrets [donate] trong test


def test_bin_resolved_from_bank_name():
    assert donate.resolve_bin("Vietinbank", "970416") == (
        "970415", "bank_bin 970416 không khớp Vietinbank (970415) – app dùng 970415")   # BIN gõ nhầm (ACB) được sửa
    assert donate.resolve_bin("VietinBank", "")[0] == "970415"
    assert donate.resolve_bin("Vietcombank", "")[0] == "970436"
    assert donate.resolve_bin("MB Bank", "")[0] == "970422"
    assert donate.resolve_bin("Ngân hàng lạ", "970999") == ("970999", "")    # không có trong bảng → dùng BIN khai
    assert donate.resolve_bin("Ngân hàng lạ", "") == ("", "")

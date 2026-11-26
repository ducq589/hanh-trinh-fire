from fi_app import style


def _lv(no, label, color, assets):
    return {"no": no, "label": label, "color": color, "pct": "10,0%", "value": "1,0 tr", "assets": assets}


def test_pyramid_order_assets_and_empty_tier():
    out = style.pyramid([
        _lv(4, "Tầng tăng trưởng", "#B6F36A", [("Quỹ A <x>", "5,0 tr", "50,0%")]),
        _lv(3, "Tầng thu nhập", "#5DC23A", []),
        _lv(2, "Tầng bảo vệ", "#2F7A2A", []),
        _lv(1, "Tầng phòng thủ", "#E8F9D2", [("Vàng", "5,0 tr", "50,0%")]),
    ])
    assert out.index("Tầng tăng trưởng") < out.index("Tầng thu nhập") < out.index("Tầng bảo vệ") < out.index("Tầng phòng thủ")
    assert "Quỹ A &lt;x&gt;" in out                          # tên tài sản được escape
    assert out.count("Chưa có tài sản ở tầng này") == 2
    assert out.count('class="pyr-row"') == 4


def test_ink_contrast():
    assert style._ink("#E8F9D2") == "#111"
    assert style._ink("#2F7A2A") == style.TEXT

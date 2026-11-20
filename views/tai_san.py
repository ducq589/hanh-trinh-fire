import pandas as pd
import streamlit as st

from fi_app import catalog, db, style, ui

c, data, h, fp = ui.state()
style.title("briefcase", "Danh mục tài sản", "Chọn tài sản bạn đầu tư – quỹ, cổ phiếu, vàng được tự cập nhật giá mỗi ngày.")


_funds = ui.funds


def _add(asset: dict):
    ui.add_asset(c, asset, hint=" Đã mua từ trước? Khai số lượng & giá vốn ở Giao dịch → Tài sản đang có.")


existing = {a["code"] for a in data["assets"]}
if data["assets"] and not data["transactions"]:
    with st.container(key=style.ic("wallet", "lk_sodu")):
        st.page_link("views/giao_dich.py", label="Đã có sẵn CCQ/cổ phiếu? Khai số lượng & giá vốn – không cần nhập lịch sử lệnh")
with st.container(border=True, key="them_ts"):
    st.subheader("Thêm tài sản")
    st.caption("Chọn từ danh mục có sẵn → app tự điền loại, tầng, lợi suất kỳ vọng và **nguồn giá tự động**. "
               "Bạn sửa lại được ở bảng bên dưới.")
    t_q, t_cp, t_v, t_k = st.tabs(["Chứng chỉ quỹ", "Cổ phiếu / ETF", "Vàng", "Khác"], key="tabs_them")
    style.tab_icons("tabs_them", ["chart-pie", "chart-candle", "coin", "edit"])

    with t_q:
        try:
            funds = [f for f in _funds() if f["code"] not in existing]
        except Exception:  # noqa: BLE001
            funds = None
            st.warning("Không tải được danh sách quỹ từ Fmarket lúc này. Thử lại sau, hoặc dùng tab **Khác**.")
        if funds is not None:
            groups = sorted({f["group"] for f in funds if f["group"]})
            grp = st.pills("Nhóm quỹ", ["Tất cả", *groups], default="Tất cả", key="nhom_quy")
            shown = [f for f in funds if grp in (None, "Tất cả") or f["group"] == grp]
            fund = st.selectbox(f"Chọn quỹ ({len(shown)} quỹ)", shown, index=None, placeholder="Gõ mã hoặc tên quỹ…",
                                format_func=lambda f: f"{f['code']} – {f['name']}", key="chon_quy")
            if fund:
                typ = catalog.fund_type(fund["group"])
                st.caption(f"{fund['group']} · NAV hiện tại **{ui.vnd(fund['nav'])} ₫** · Loại: {typ} · "
                           f"Tầng: {catalog._DEFAULTS[typ]['tier']}")
                if st.button(f"Thêm {fund['code']}", type="primary", key=style.ic("plus", "them_quy")):
                    _add(catalog.build("fund", fund["code"], f"{typ} {fund['code']}", asset_type=typ))

    with t_cp:
        a1, a2 = st.columns([1, 2])
        sym = a1.text_input("Mã chứng khoán", max_chars=10, placeholder="VD: FPT, E1VFVN30",
                            key="ma_cp").strip().upper()
        kind = a2.radio("Loại", ["Cổ phiếu", "ETF"], horizontal=True, key="loai_cp")
        if sym:
            if sym in existing:
                st.info(f"{sym} đã có trong danh mục.")
            elif st.button(f"Kiểm tra & thêm {sym}", type="primary", key=style.ic("plus", "them_cp")):
                q = catalog.stock_quote(sym)
                if not q:
                    st.error(f"Không tìm thấy giá của mã {sym} trên VNDirect. Kiểm tra lại mã.")
                else:
                    _add(catalog.build("stock", sym, f"{kind} {sym}", asset_type=kind))

    with t_v:
        g1, g2 = st.columns([2, 1])
        prod = g1.selectbox("Loại vàng (giá mua vào của PNJ, theo chỉ)", list(catalog.GOLD_PRODUCTS),
                            format_func=lambda k: catalog.GOLD_PRODUCTS[k], key="loai_vang")
        default_code = "VANG" if "VANG" not in existing else f"VANG{prod}"[:12]
        gcode = g2.text_input("Mã trong app", value=default_code, max_chars=12, key="ma_vang").strip().upper()
        st.caption("Ghi số lượng theo **chỉ** khi nhập giao dịch (1 lượng = 10 chỉ).")
        if st.button("Thêm vàng", type="primary", key=style.ic("plus", "them_vang")):
            try:
                _add(catalog.build("gold", gcode, catalog.GOLD_PRODUCTS[prod], gold_product=prod))
            except ValueError as e:
                st.error(str(e))

    with t_k:
        st.markdown("Tiết kiệm, bảo hiểm, bất động sản, tiền mặt… **không có giá thị trường**: thêm 1 dòng ở cuối "
                    "**bảng Danh sách tài sản** bên dưới, để trống cột *Nguồn giá* và chọn *Cách định giá* "
                    "(Sổ tiết kiệm / Khai báo).")

st.subheader("Danh sách tài sản")
st.caption("Sửa trực tiếp trong bảng rồi bấm **Lưu danh mục**. Thêm dòng ở cuối bảng cho tài sản tự khai báo. "
           "**Mã** ngắn, không dấu cách, không trùng.")
df = pd.DataFrame(data["assets"], columns=["code", "name", "type", "tier", "fire_include", "exp_return",
                                           "target_weight", "valuation", "price_source", "unit", "note", "sort_order"])
df["fire_include"] = df["fire_include"].astype(bool)
df["exp_return"] = df["exp_return"] * 100
df["target_weight"] = df["target_weight"] * 100
st.data_editor(df, key="assets_ed", hide_index=True, width="stretch", num_rows="dynamic", column_config={
    "code": st.column_config.TextColumn("Mã", required=True, max_chars=12),
    "name": st.column_config.TextColumn("Tên", required=True),
    "type": st.column_config.SelectboxColumn("Loại", options=db.ASSET_TYPES),
    "tier": st.column_config.SelectboxColumn("Tầng", options=db.TIERS, required=True),
    "fire_include": st.column_config.CheckboxColumn("Tính FIRE?", help="Tài sản dùng để tạo thu nhập thụ động"),
    "exp_return": st.column_config.NumberColumn("Lợi suất KV (%/năm)", format="%.1f",
                                                help="Giả định dài hạn để dự phóng FIRE – không phải cam kết"),
    "target_weight": st.column_config.NumberColumn("Tỷ lệ mục tiêu (%)", format="%.0f",
                                                   help="Chỉ điền cho nhóm tài sản muốn tái cân bằng"),
    "valuation": st.column_config.SelectboxColumn("Cách định giá", options=db.VALUATIONS, required=True),
    "price_source": st.column_config.TextColumn(
        "Nguồn giá", help="Để trống = nhập tay. fmarket (quỹ mở) · vndirect (cổ phiếu/ETF) · "
                          "pnj:SJC:mua hoặc pnj:N24K:mua (vàng, giá mua vào/chỉ). Có thể ghi mã khác, VD vndirect:FPT"),
    "unit": st.column_config.TextColumn("Đơn vị"),
    "note": st.column_config.TextColumn("Ghi chú"),
    "sort_order": st.column_config.NumberColumn("Thứ tự", format="%d"),
})


def _tx(r):
    if "code" in r and r["code"]:
        r["code"] = str(r["code"]).strip().upper()
    if "price_source" in r:
        r["price_source"] = (r["price_source"] or "").strip() or None
    if "fire_include" in r:
        r["fire_include"] = 1 if r["fire_include"] else 0
    for k in ("exp_return", "target_weight"):
        if k in r and r[k] is not None:
            r[k] = r[k] / 100
    return r


if ui.has_changes("assets_ed"):
    ch = st.session_state["assets_ed"]
    blocked = []
    for i in ch.get("deleted_rows", []):
        code = df.iloc[int(i)]["code"]
        if any(t["code"] == code for t in data["transactions"]) or any(s["code"] == code for s in data["savings"]):
            blocked.append(code)
    dup = [r.get("code", "").strip().upper() for r in ch.get("added_rows", [])
           if r.get("code", "").strip().upper() in set(df["code"])]
    if blocked:
        st.error(f"Không xoá được {', '.join(blocked)}: đã có giao dịch/sổ tiết kiệm. Hãy xoá các giao dịch trước.")
    elif dup:
        st.error(f"Mã đã tồn tại: {', '.join(dup)}")
    elif st.button("Lưu danh mục", type="primary", key=style.ic("device-floppy", "luudm")):
        e, a, x = ui.save_editor(c, "assets", "code", df, "assets_ed",
                                 ["name", "type", "tier", "fire_include", "exp_return", "target_weight",
                                  "valuation", "price_source", "unit", "note", "sort_order"], transform=_tx)
        ui.flash(f"Danh mục: sửa {e}, thêm {a}, xoá {x}")
        st.rerun()

st.subheader("Chi tiết nắm giữ")
rows = pd.DataFrame(h["rows"])
st.dataframe(pd.DataFrame({
    "Mã": rows["code"], "Số lượng": rows["qty"], "Vốn thuần": rows["cost"], "Cổ tức": rows["dividends"],
    "Ngày giá": rows["price_date"], "Giá mới nhất": rows["price"], "Giá trị": rows["value"],
    "Lãi/lỗ": rows["pnl"], "% Lãi/lỗ": rows["pnl_pct"] * 100, "XIRR": [ui.xirr_label(r) for r in h["rows"]],
    "Tính FIRE": rows["fire_value"],
}), hide_index=True, width="stretch", column_config={
    "Số lượng": st.column_config.NumberColumn(format="%.2f"),
    **{k: st.column_config.NumberColumn(format="localized")
       for k in ("Vốn thuần", "Cổ tức", "Giá mới nhất", "Giá trị", "Lãi/lỗ", "Tính FIRE")},
    "Ngày giá": st.column_config.DateColumn(format="DD/MM/YYYY"),
    "% Lãi/lỗ": st.column_config.NumberColumn(format="%.1f%%"),
})
st.caption("Vốn thuần = tiền mua (gồm phí) − tiền bán thu về. Lãi/lỗ = Giá trị − Vốn thuần + Cổ tức tiền mặt. "
           "Tài sản khai số dư đầu kỳ: XIRR tính từ ngày khai (sau 30 ngày), đánh dấu *.")

st.subheader("Tái cân bằng")
tg = [r for r in h["rows"] if r["target_weight"]]
if tg:
    st.caption("Số tiền nên mua thêm cho từng tài sản để về đúng tỷ lệ mục tiêu mà không phải bán tài sản nào.")
    st.dataframe(pd.DataFrame([{
        "Mã": r["code"], "Giá trị": ui.vnd(r["value"]), "Tỷ lệ hiện tại": ui.pct(r["current_weight"]),
        "Tỷ lệ mục tiêu": ui.pct(r["target_weight"], 0), "Cần bổ sung": ui.vnd(r["rebalance_need"]),
    } for r in tg]), hide_index=True, width="stretch")
    total_need = sum(r["rebalance_need"] for r in tg)
    if total_need > 0:
        st.info("Gợi ý chia khoản mua tiếp theo: " + " · ".join(
            f"**{r['code']}** {ui.pct(r['rebalance_need'] / total_need, 0)}" for r in tg if r["rebalance_need"] > 0))
else:
    st.info("Chưa có tài sản nào có Tỷ lệ mục tiêu.")

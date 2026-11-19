import pandas as pd
import streamlit as st

from fi_app import db, ui

c, data, h, fp = ui.state()
st.title("🗂️ Danh mục tài sản")

st.subheader("Danh sách tài sản")
st.caption("Thêm tài sản mới = thêm 1 dòng ở cuối bảng. **Mã** ngắn, không dấu cách, không trùng (VD: DCBF, FPT, VANGNHAN). "
           "Sau đó nhập giao dịch và giá – tài sản tự xuất hiện ở Tổng quan và Kế hoạch FIRE.")
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
    elif st.button("💾 Lưu danh mục", type="primary"):
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
    "Lãi/lỗ": rows["pnl"], "% Lãi/lỗ": rows["pnl_pct"] * 100, "XIRR (%)": pd.to_numeric(rows["xirr"], errors="coerce") * 100,
    "Tính FIRE": rows["fire_value"],
}), hide_index=True, width="stretch", column_config={
    "Số lượng": st.column_config.NumberColumn(format="%.2f"),
    **{k: st.column_config.NumberColumn(format="localized")
       for k in ("Vốn thuần", "Cổ tức", "Giá mới nhất", "Giá trị", "Lãi/lỗ", "Tính FIRE")},
    "Ngày giá": st.column_config.DateColumn(format="DD/MM/YYYY"),
    "% Lãi/lỗ": st.column_config.NumberColumn(format="%.1f%%"),
    "XIRR (%)": st.column_config.NumberColumn(format="%.2f%%"),
})
st.caption("Vốn thuần = tiền mua (gồm phí) − tiền bán thu về. Lãi/lỗ = Giá trị − Vốn thuần + Cổ tức tiền mặt. "
           "XIRR không tính cho tài sản có dòng 'Vốn đầu kỳ'.")

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

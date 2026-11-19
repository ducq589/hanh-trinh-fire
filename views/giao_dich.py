import datetime as dt

import pandas as pd
import streamlit as st

from fi_app import db, engine, style, ui

c, data, h, fp = ui.state()
style.title("receipt", "Giao dịch")

market = [a for a in data["assets"] if a["valuation"] != "Sổ tiết kiệm"]
codes = [a["code"] for a in market]
names = {a["code"]: f"{a['code']} – {a['name']}" for a in market}
book = h["book"]

tab_dca, tab_other, tab_hist = st.tabs(["Mua DCA nhanh", "Giao dịch khác", "Lịch sử & sửa"], key="tabs_gd")
style.tab_icons("tabs_gd", ["bolt", "plus", "history"])

# --------------------------------------------------------------- DCA
with tab_dca:
    st.caption("Mua quỹ mở theo số tiền: app tự tra NAV đúng ngày và tính số CCQ = TRUNC(Số tiền / NAV, 2).")
    col = st.columns([2, 1.2, 1.5, 1.5])
    code = col[0].selectbox("Tài sản", codes, format_func=names.get, key="dca_code")
    day = col[1].date_input("Ngày", dt.date.today(), format="DD/MM/YYYY", key="dca_day")
    amount = col[2].number_input("Số tiền (₫)", min_value=0, step=100_000, value=0, key="dca_amt")
    nav_found = book.on(code, day)
    price = col[3].number_input("Giá/NAV (₫) – để 0 nếu tự tra", min_value=0.0, step=10.0,
                                value=0.0, format="%.2f", key="dca_price")
    use_price = price or nav_found
    if use_price and amount:
        qty = engine.trunc2(amount / use_price)
        st.info(f"Giá dùng: **{ui.num(use_price)} ₫** {'(tra từ bảng giá)' if not price else '(nhập tay)'} → "
                f"số lượng **{ui.num(qty)}**, giá trị {ui.vnd(qty * use_price)}")
    elif amount and not use_price:
        st.warning(f"Chưa có giá {code} ngày {day:%d/%m/%Y}. Nhập giá/NAV ở ô bên cạnh, "
                   "hoặc cập nhật giá ở trang **Giá** trước.")
    if st.button("Lưu giao dịch mua", type="primary", disabled=not (amount and use_price), key=style.ic("device-floppy", "luudca")):
        db.add_transaction(c, day, code, "Mua", amount=amount, price=price or None)
        if price and not nav_found:
            db.upsert_price(c, day, code, price, "Nhập khi mua (app)", is_manual=1)
        ui.flash(f"Đã lưu: mua {code} {ui.vnd(amount)} ngày {day:%d/%m/%Y}")
        st.rerun()

# --------------------------------------------------------------- other types
with tab_other:
    with st.form("tx_full", clear_on_submit=True):
        c1, c2, c3 = st.columns(3)
        t_code = c1.selectbox("Tài sản", codes, format_func=names.get)
        t_type = c2.selectbox("Loại giao dịch", db.TX_TYPES)
        t_day = c3.date_input("Ngày", dt.date.today(), format="DD/MM/YYYY")
        c4, c5, c6 = st.columns(3)
        t_amount = c4.number_input("Số tiền (₫)", min_value=0.0, step=100_000.0, format="%.0f",
                                   help="Mua quỹ theo tiền / cổ tức tiền mặt")
        t_price = c5.number_input("Giá (₫/đơn vị)", min_value=0.0, step=100.0, format="%.2f",
                                  help="Cổ phiếu: giá khớp, ví dụ 18800")
        t_qty = c6.number_input("Số lượng", min_value=0.0, step=1.0, format="%.2f",
                                help="Để 0 khi mua quỹ theo số tiền")
        c7, c8, c9 = st.columns(3)
        t_fee = c7.number_input("Phí (₫)", min_value=0.0, step=1000.0, format="%.0f")
        t_tax = c8.number_input("Thuế (₫)", min_value=0.0, step=1000.0, format="%.0f")
        t_note = c9.text_input("Ghi chú")
        st.caption("Mua/Bán cổ phiếu: nhập Giá + Số lượng (+ Phí, Thuế khi bán). · Cổ tức TM: Số tiền. · "
                   "Cổ tức CP/Thưởng: Số lượng. · Vốn đầu kỳ: tài sản có sẵn, không rõ ngày mua (không tính XIRR).")
        if st.form_submit_button("Lưu giao dịch", type="primary", key=style.ic("device-floppy", "luukhac")):
            held = next((r["qty"] for r in h["rows"] if r["code"] == t_code), 0) or 0
            err = None
            if not (t_amount or t_qty):
                err = "Cần nhập Số tiền hoặc Số lượng."
            elif t_type == "Bán" and t_qty > held + 1e-9:
                err = f"Không thể bán {ui.num(t_qty)} – đang nắm giữ {ui.num(held)}."
            elif t_type == "Bán" and not t_price:
                err = "Giao dịch Bán cần nhập Giá."
            if err:
                st.error(err)
            else:
                db.add_transaction(c, t_day, t_code, t_type, amount=t_amount or None, price=t_price or None,
                                   qty=t_qty or None, fee=t_fee or None, tax=t_tax or None, note=t_note or None)
                ui.flash(f"Đã lưu: {t_type} {t_code} ngày {t_day:%d/%m/%Y}")
                st.rerun()

# --------------------------------------------------------------- history
with tab_hist:
    f1, f2, f3 = st.columns([2, 1, 1])
    sel = f1.multiselect("Lọc theo mã", sorted({t["code"] for t in data["transactions"]}))
    start = f2.date_input("Từ ngày", dt.date.today() - dt.timedelta(days=365), format="DD/MM/YYYY")
    end = f3.date_input("Đến ngày", dt.date.today(), format="DD/MM/YYYY")
    derived = {t["id"]: t for t in h["transactions"]}
    txs = [t for t in data["transactions"]
           if (not sel or t["code"] in sel) and start <= engine.to_date(t["date"]) <= end]
    df = pd.DataFrame([{
        "id": t["id"], "date": engine.to_date(t["date"]), "code": t["code"], "type": t["type"],
        "amount": t["amount"], "price": t["price"], "qty": t["qty"], "fee": t["fee"], "tax": t["tax"],
        "note": t["note"], "SL tính": derived[t["id"]]["qty_calc"], "Dòng tiền": derived[t["id"]]["cashflow"],
    } for t in reversed(txs)], columns=["id", "date", "code", "type", "amount", "price", "qty", "fee", "tax",
                                        "note", "SL tính", "Dòng tiền"])
    st.caption(f"{len(df)} giao dịch. Sửa trực tiếp trong bảng; chọn dòng rồi bấm biểu tượng thùng rác để xoá; bấm **Lưu thay đổi** để ghi.")
    st.data_editor(df, key="tx_editor", hide_index=True, width="stretch", num_rows="dynamic",
                   disabled=["id", "SL tính", "Dòng tiền"], column_config={
                       "id": None,
                       "date": st.column_config.DateColumn("Ngày", format="DD/MM/YYYY", required=True),
                       "code": st.column_config.SelectboxColumn("Mã", options=codes, required=True),
                       "type": st.column_config.SelectboxColumn("Loại GD", options=db.TX_TYPES, required=True),
                       "amount": st.column_config.NumberColumn("Số tiền", format="localized"),
                       "price": st.column_config.NumberColumn("Giá", format="localized"),
                       "qty": st.column_config.NumberColumn("Số lượng", format="%.2f"),
                       "fee": st.column_config.NumberColumn("Phí", format="localized"),
                       "tax": st.column_config.NumberColumn("Thuế", format="localized"),
                       "note": st.column_config.TextColumn("Ghi chú"),
                       "SL tính": st.column_config.NumberColumn(format="%.2f"),
                       "Dòng tiền": st.column_config.NumberColumn(format="localized"),
                   })
    if ui.has_changes("tx_editor"):
        n_del = len(st.session_state["tx_editor"].get("deleted_rows", []))
        ok = True
        if n_del:
            ok = st.checkbox(f"Tôi xác nhận xoá {n_del} giao dịch (đã có bản sao lưu tự động hằng ngày)")
        if st.button("Lưu thay đổi", type="primary", disabled=not ok, key=style.ic("device-floppy", "luugd")):
            e, a, x = ui.save_editor(c, "transactions", "id", df, "tx_editor",
                                     ["date", "code", "type", "amount", "price", "qty", "fee", "tax", "note"])
            ui.flash(f"Đã lưu: sửa {e}, thêm {a}, xoá {x} giao dịch")
            st.rerun()

import datetime as dt

import pandas as pd
import streamlit as st

from fi_app import catalog, db, engine, style, ui

c, data, h, fp = ui.state()
style.title("receipt", "Giao dịch")

market = [a for a in data["assets"] if a["valuation"] != "Sổ tiết kiệm"]
codes = [a["code"] for a in market]
names = {a["code"]: f"{a['code']} – {a['name']}" for a in market}
book = h["book"]

tab_open, tab_dca, tab_other, tab_hist = st.tabs(["Tài sản đang có", "Mua DCA nhanh", "Giao dịch khác", "Lịch sử & sửa"],
                                                 key="tabs_gd")
style.tab_icons("tabs_gd", ["wallet", "bolt", "plus", "history"])

# --------------------------------------------------------------- opening balances
with tab_open:
    st.caption("Đã mua CCQ/cổ phiếu từ trước và **không muốn nhập lại từng lệnh**? Chỉ cần chép 2 con số cho mỗi tài sản: "
               "**Số lượng đang có** và **Giá vốn bình quân** (hoặc Tổng vốn). Từ nay mua thêm thì ghi ở tab *Mua DCA nhanh*.")
    st.html(style.tip("Lấy số ở đâu? App Fmarket / app quỹ: <b>Tài sản</b> → Số CCQ, Giá vốn BQ. "
                      "App chứng khoán: <b>Danh mục</b> → Khối lượng, Giá vốn. Số lượng CCQ ghi đủ 2 số lẻ."))
    # ---- thêm / bỏ mã ngay tại đây
    with st.form("them_ma", clear_on_submit=True, border=False):
        a1, a2, a3 = st.columns([3, 1.2, 2], vertical_alignment="bottom")
        new_code = a1.text_input("Chưa có mã trong bảng? Gõ mã quỹ / cổ phiếu để thêm",
                                 placeholder="VD: DCBF, FPT, E1VFVN30", max_chars=12)
        submitted = a2.form_submit_button("Thêm", type="primary", width="stretch",
                                          key=style.ic("plus", "them_ma_open"))
    with a3.container(key=style.ic("coin", "lk_vang_open")):
        st.page_link("views/tai_san.py", label="Vàng, BĐS…", width="stretch")
    if submitted and new_code.strip():
        code_u = new_code.strip().upper()
        if any(a["code"] == code_u for a in data["assets"]):
            st.info(f"{code_u} đã có trong bảng bên dưới.")
        else:
            with st.spinner(f"Đang tìm {code_u}…"):
                try:
                    asset = catalog.detect(code_u, ui.funds_or_none())
                except ValueError as e:
                    asset = None
                    st.error(f"{e}. Vàng, bảo hiểm, BĐS… thêm ở trang **Tài sản**.")
            if asset:
                ui.add_asset(c, asset, hint=" Điền Số lượng đang có và Giá vốn BQ ở bảng bên dưới.")

    rows_by = {r["code"]: r for r in h["rows"]}
    op_rows = []
    for a in market:
        mine = [t for t in data["transactions"] if t["code"] == a["code"] and t["type"] == db.OPENING]
        q = sum(engine.n(t["qty"]) for t in mine)
        cost = sum(engine.n(t["qty"]) * engine.n(t["price"]) or engine.n(t["amount"]) for t in mine)
        r = rows_by.get(a["code"], {})
        n_orders = sum(1 for t in data["transactions"] if t["code"] == a["code"] and t["type"] != db.OPENING)
        op_rows.append({"code": a["code"], "name": a["name"], "orders": n_orders, "qty": q or None,
                        "avg": round(cost / q, 2) if q else None, "total": round(cost) if q else None,
                        "day": min((engine.to_date(t["date"]) for t in mine), default=dt.date.today()),
                        "price": r.get("price"), "pnl": (r.get("pnl") if q else None)})
    op_df = pd.DataFrame(op_rows, columns=["code", "name", "orders", "qty", "avg", "total", "day", "price", "pnl"])
    num_cols = ["qty", "avg", "total", "price", "pnl"]
    op_df[num_cols] = op_df[num_cols].astype(float)            # ô trống hiển thị trống thay vì "None"
    if op_df.empty:
        st.info("Chưa có tài sản nào. Gõ mã quỹ / cổ phiếu ở ô phía trên rồi bấm **Thêm**.")
    else:
        edited = st.data_editor(op_df, key="open_ed", hide_index=True, width="stretch", disabled=["code", "name", "orders", "price", "pnl"],
                                column_config={
            "code": st.column_config.TextColumn("Mã"), "name": st.column_config.TextColumn("Tên"),
            "orders": st.column_config.NumberColumn("Lệnh đã ghi", format="%d",
                                                    help="Số giao dịch Mua/Bán/Cổ tức đã nhập cho mã này"),
            "qty": st.column_config.NumberColumn("Số lượng đang có", min_value=0.0, format="%.2f"),
            "avg": st.column_config.NumberColumn("Giá vốn BQ (₫)", min_value=0.0, format="localized",
                                                 help="Giá vốn bình quân mỗi CCQ/cổ phiếu"),
            "total": st.column_config.NumberColumn("hoặc Tổng vốn (₫)", min_value=0.0, format="localized",
                                                   help="Điền nếu không biết giá vốn BQ – app tự chia ra"),
            "day": st.column_config.DateColumn("Ngày khai", format="DD/MM/YYYY",
                                               help="Thường là hôm nay. XIRR sẽ tính từ ngày này."),
            "price": st.column_config.NumberColumn("Giá hiện tại", format="localized"),
            "pnl": st.column_config.NumberColumn("Lãi/lỗ tạm tính", format="localized"),
        })
        changes = []
        for (_, old_r), (_, new_r) in zip(op_df.iterrows(), edited.iterrows()):
            def val(x):
                return None if pd.isna(x) else x
            o = (val(old_r["qty"]), val(old_r["avg"]), val(old_r["total"]), val(old_r["day"]))
            nw = (val(new_r["qty"]), val(new_r["avg"]), val(new_r["total"]), val(new_r["day"]))
            if o != nw:
                q, avg, tot = nw[0] or 0, nw[1], nw[2]
                if q and avg in (None, 0) and tot:
                    avg = tot / q                       # chỉ có tổng vốn → suy ra giá vốn BQ
                elif q and avg and tot and o[1] == avg:  # người dùng sửa Tổng vốn, giữ giá cũ → ưu tiên tổng vốn
                    avg = tot / q
                changes.append((new_r["code"], q, avg, nw[3] or dt.date.today()))
        missing = [code for code, q, avg, _ in changes if q and not avg]
        orders = dict(zip(op_df["code"], op_df["orders"]))
        dup = [code for code, q, _, day in changes if q and any(
            t["code"] == code and t["type"] != db.OPENING and engine.to_date(t["date"]) <= day for t in data["transactions"])]
        if dup:
            st.warning(f"{', '.join(dup)} đã có lệnh mua/bán trước ngày khai ({', '.join(str(orders[x]) + ' lệnh' for x in dup)}). "
                       "Số lượng đang có đã gồm các lệnh đó → khai thêm sẽ bị **tính trùng**. Hãy chọn một trong hai: "
                       "xoá các lệnh cũ ở tab *Lịch sử & sửa*, hoặc không khai số dư cho mã này.")
        if missing:
            st.warning(f"Cần Giá vốn BQ hoặc Tổng vốn cho: {', '.join(missing)}")
        if st.button(f"Lưu khai báo ({len(changes)} thay đổi)", type="primary", disabled=not changes or bool(missing),
                     key=style.ic("device-floppy", "luusodu")):
            res = [f"{code} {db.set_opening(c, code, q, avg, day)}" for code, q, avg, day in changes]
            words = {"added": "đã thêm", "updated": "đã cập nhật", "deleted": "đã xoá", "none": "không đổi"}
            ui.flash("Số dư đầu kỳ: " + ", ".join(f"{x.split()[0]} {words[x.split()[1]]}" for x in res))
            st.rerun()
        can_remove = [a["code"] for a in market if catalog.removable(c, a["code"])]
        with st.expander("Bỏ mã khỏi danh mục", key=style.ic("trash", "bo_ma")):
            if not can_remove:
                st.caption("Không có mã nào bỏ được. Mã đã có lệnh giao dịch: xoá lệnh ở tab *Lịch sử & sửa* trước.")
            else:
                st.caption("Chỉ bỏ được mã **chưa có lệnh Mua/Bán/Cổ tức** (số dư đầu kỳ của mã cũng bị xoá theo). "
                           "Mã đã có lệnh: xoá lệnh ở tab *Lịch sử & sửa* trước.")
                rm = st.multiselect("Chọn mã", can_remove, format_func=names.get, key="rm_codes")
                sure = st.checkbox("Tôi muốn bỏ các mã đã chọn", key="rm_sure")
                if st.button("Bỏ", disabled=not (rm and sure), key=style.ic("trash", "bo_ma_btn")):
                    for code_rm in rm:
                        catalog.remove(c, code_rm)
                    ui.flash(f"Đã bỏ khỏi danh mục: {', '.join(rm)}")
                    st.rerun()
        st.caption("Lãi/lỗ = (Giá hiện tại − Giá vốn) × Số lượng. XIRR của các mã này tính **từ ngày khai**, "
                   "hiện sau 30 ngày. Ô mờ ghi None = chưa khai. Xoá trắng Số lượng để bỏ số dư đầu kỳ của mã đó.")

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
                   "Cổ tức CP/Thưởng: Số lượng. · Vốn đầu kỳ: Số lượng đang có + Giá vốn bình quân (dễ hơn: tab *Tài sản đang có*); "
                   "XIRR tính từ ngày khai.")
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

import datetime as dt

import pandas as pd
import streamlit as st

from fi_app import catalog, db, engine, field_guide, style, ui

c, data, h, fp = ui.state()
style.title("receipt", "Giao dịch")

market = [a for a in data["assets"] if a["valuation"] != "Sổ tiết kiệm"]
codes = [a["code"] for a in market]
names = {a["code"]: f"{a['code']} – {a['name']}" for a in market}
book = h["book"]

tab_dca, tab_other, tab_open, tab_hist = st.tabs(["Mua CCQ nhanh", "Giao dịch khác", "Tài sản đang có", "Lịch sử & sửa"],
                                                 key="tabs_gd")
style.tab_icons("tabs_gd", ["bolt", "plus", "wallet", "history"])

# --------------------------------------------------------------- opening balances
with tab_open:
    st.caption("**Khai báo lần đầu** – chỉ hiện tài sản **chưa có dữ liệu**. Đã mua CCQ/cổ phiếu từ trước và **không muốn "
               "nhập lại từng lệnh**? Chỉ cần chép 2 con số cho mỗi tài sản: "
               "**Số lượng đang có** và **Giá vốn bình quân** (hoặc Tổng vốn). Từ nay mua thêm thì ghi ở tab *Mua CCQ nhanh*.")
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

    # Chỉ tài sản CHƯA có dữ liệu (khai lần đầu). Đã có lệnh/số dư → sửa ở tab Lịch sử & sửa, không hiện ở đây.
    used = {t["code"] for t in data["transactions"]} | {sv["code"] for sv in data["savings"]}
    fresh = [a for a in market if a["code"] not in used]
    rows_by = {r["code"]: r for r in h["rows"]}
    op_df = pd.DataFrame([{"code": a["code"], "name": a["name"], "qty": None, "avg": None, "total": None,
                           "day": dt.date.today(), "price": rows_by.get(a["code"], {}).get("price")} for a in fresh],
                         columns=["code", "name", "qty", "avg", "total", "day", "price"])
    num_cols = ["qty", "avg", "total", "price"]
    op_df[num_cols] = op_df[num_cols].astype(float)            # ô trống hiển thị trống thay vì "None"
    if op_df.empty:
        st.info("Mọi tài sản trong danh mục đã có dữ liệu. Có tài sản mới mua từ trước? Gõ mã ở ô **Thêm** phía trên. "
                "Sửa số dư đã khai ở tab *Lịch sử & sửa* (dòng Vốn đầu kỳ).")
    else:
        field_guide.render("opening")
        edited = st.data_editor(op_df, key="open_ed", hide_index=True, width="stretch", disabled=["code", "name", "price"],
                                column_config={
            "code": st.column_config.TextColumn("Mã"), "name": st.column_config.TextColumn("Tên"),
            "qty": st.column_config.NumberColumn("Số lượng đang có", min_value=0.0, format="%.2f", help=field_guide.tip("opening", "Số lượng đang có")),
            "avg": st.column_config.NumberColumn("Giá vốn BQ (₫)", min_value=0.0, format="localized", help=field_guide.tip("opening", "Giá vốn BQ (₫)")),
            "total": st.column_config.NumberColumn("hoặc Tổng vốn (₫)", min_value=0.0, format="localized", help=field_guide.tip("opening", "hoặc Tổng vốn (₫)")),
            "day": st.column_config.DateColumn("Ngày khai", format="DD/MM/YYYY", help=field_guide.tip("opening", "Ngày khai")),
            "price": st.column_config.NumberColumn("Giá hiện tại", format="localized"),
        })
        todo = []
        for _, r in edited.iterrows():
            q = 0 if pd.isna(r["qty"]) else float(r["qty"])
            if not q:
                continue
            avg = None if pd.isna(r["avg"]) or not r["avg"] else float(r["avg"])
            tot = None if pd.isna(r["total"]) or not r["total"] else float(r["total"])
            if avg is None and tot:
                avg = tot / q                            # chỉ có tổng vốn → suy ra giá vốn BQ
            day = pd.Timestamp(r["day"]).date() if not pd.isna(r["day"]) else dt.date.today()
            todo.append((r["code"], q, avg, day))
        missing = [code for code, q, avg, _ in todo if not avg]
        if missing:
            st.warning(f"Cần Giá vốn BQ hoặc Tổng vốn cho: {', '.join(missing)}")
        if st.button(f"Lưu khai báo ({len(todo)} mã)", type="primary", disabled=not todo or bool(missing),
                     key=style.ic("device-floppy", "luusodu")):
            for code, q, avg, day in todo:
                db.set_opening(c, code, q, avg, day)
            ui.flash(f"Đã lưu số dư: {', '.join(x[0] for x in todo)}. Muốn sửa: tab Lịch sử & sửa (dòng Vốn đầu kỳ).")
            st.rerun()
        st.caption("Lãi/lỗ = (Giá hiện tại − Giá vốn) × Số lượng. XIRR của các mã này tính **từ ngày khai**, hiện sau 30 ngày. "
                   "Ô mờ ghi None = chưa khai. Lưu xong, mã chuyển sang Tổng quan; sửa/xoá số dư ở tab *Lịch sử & sửa*.")
        with st.expander("Bỏ mã thêm nhầm", key=style.ic("trash", "bo_ma")):
            st.caption("Chỉ bỏ được mã **chưa có dữ liệu** (đang hiện trong bảng trên). Tài sản đã có lệnh/số dư không bị ảnh hưởng.")
            rm = st.multiselect("Chọn mã", [a["code"] for a in fresh], format_func=names.get, key="rm_codes")
            if st.button("Bỏ", disabled=not rm, key=style.ic("trash", "bo_ma_btn")):
                for code_rm in rm:
                    catalog.remove(c, code_rm)
                ui.flash(f"Đã bỏ khỏi danh mục: {', '.join(rm)}")
                st.rerun()

# --------------------------------------------------------------- DCA
with tab_dca:
    st.caption("Mua quỹ mở theo số tiền: app tự tra NAV **ngày phân bổ** và tính số CCQ = TRUNC(Số tiền / NAV, 2). "
               "Đặt mua hôm nay mà quỹ chưa có NAV? Chọn ngày phân bổ (thường là phiên kế tiếp) và lưu luôn – "
               "app tự tính số CCQ khi NAV ngày đó được cập nhật.")
    col = st.columns([2, 1.2, 1.5, 1.5])
    code = col[0].selectbox("Tài sản", codes, format_func=names.get, key="dca_code")
    day = col[1].date_input("Ngày phân bổ CCQ", dt.date.today(), format="DD/MM/YYYY", key="dca_day",
                            help="Ngày quỹ ghi NAV cho lệnh của bạn (xem trong app quỹ/sao kê). Có thể chọn ngày mai.")
    amount = col[2].number_input("Số tiền (₫)", min_value=0, step=100_000, value=0, key="dca_amt")
    nav_found = book.on(code, day)
    price = col[3].number_input("Giá/NAV (₫) – để 0 nếu tự tra", min_value=0.0, step=10.0,
                                value=0.0, format="%.2f", key="dca_price")
    use_price = price or nav_found
    pending = bool(amount) and not use_price
    if use_price and amount:
        qty = engine.trunc2(amount / use_price)
        st.info(f"Giá dùng: **{ui.num(use_price)} ₫** {'(tra từ bảng giá)' if not price else '(nhập tay)'} → "
                f"số lượng **{ui.num(qty)}**, giá trị {ui.vnd(qty * use_price)}")
    elif pending:
        st.warning(f"Chưa có NAV {code} ngày {day:%d/%m/%Y} → lưu dạng **chờ phân bổ**: số tiền được ghi ngay, "
                   "số CCQ tự tính khi giá ngày đó có ở trang **Giá**. Trong lúc chờ, tài sản tính theo số tiền đã mua.")
    label = "Lưu – chờ NAV" if pending else "Lưu giao dịch mua"
    if st.button(label, type="primary", disabled=not amount, key=style.ic("device-floppy", "luudca")):
        note = f"Đặt mua {dt.date.today():%d/%m/%Y}" if pending else None
        db.add_transaction(c, day, code, "Mua", amount=amount, price=price or None, note=note)
        if price and not nav_found:
            db.upsert_price(c, day, code, price, "Nhập khi mua (app)", is_manual=1)
        ui.flash(f"Đã lưu: mua {code} {ui.vnd(amount)} – phân bổ ngày {day:%d/%m/%Y}"
                 + (" (chờ NAV)" if pending else ""))
        st.rerun()

# --------------------------------------------------------------- other types
with tab_other:
    field_guide.render("transactions", "Điền cột nào theo loại giao dịch", ident="_form")
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
    last_tx = max((engine.to_date(t["date"]) for t in data["transactions"]), default=dt.date.today())
    end = f3.date_input("Đến ngày", max(dt.date.today(), last_tx), format="DD/MM/YYYY")   # gồm lệnh chờ phân bổ
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
    field_guide.render("transactions")
    st.data_editor(df, key="tx_editor", hide_index=True, width="stretch", num_rows="dynamic",
                   disabled=["id", "SL tính", "Dòng tiền"], column_config={
                       "id": None,
                       "date": st.column_config.DateColumn("Ngày", format="DD/MM/YYYY", required=True, help=field_guide.tip("transactions", "Ngày")),
                       "code": st.column_config.SelectboxColumn("Mã", options=codes, required=True, help=field_guide.tip("transactions", "Mã")),
                       "type": st.column_config.SelectboxColumn("Loại GD", options=db.TX_TYPES, required=True, help=field_guide.tip("transactions", "Loại GD")),
                       "amount": st.column_config.NumberColumn("Số tiền", format="localized", help=field_guide.tip("transactions", "Số tiền")),
                       "price": st.column_config.NumberColumn("Giá", format="localized", help=field_guide.tip("transactions", "Giá")),
                       "qty": st.column_config.NumberColumn("Số lượng", format="%.2f", help=field_guide.tip("transactions", "Số lượng")),
                       "fee": st.column_config.NumberColumn("Phí", format="localized", help=field_guide.tip("transactions", "Phí")),
                       "tax": st.column_config.NumberColumn("Thuế", format="localized", help=field_guide.tip("transactions", "Thuế")),
                       "note": st.column_config.TextColumn("Ghi chú", help=field_guide.tip("transactions", "Ghi chú")),
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

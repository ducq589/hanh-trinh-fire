import datetime as dt

import pandas as pd
import streamlit as st

from fi_app import db, engine, field_guide, lessons, style, ui

c, data, h, fp = ui.state()
style.title("building-bank", "Tiết kiệm, Mục tiêu & Nợ")

sav_codes = [a["code"] for a in data["assets"] if a["valuation"] == "Sổ tiết kiệm"]
goal_names = [g["name"] for g in data["goals"]]
tab_s, tab_g, tab_n = st.tabs(["Sổ tiết kiệm", "Mục tiêu (Sinking Fund)", "Nợ phải trả"], key="tabs_tk")
style.tab_icons("tabs_tk", ["pig-money", "target", "coin"])

# --------------------------------------------------------------- savings
with tab_s:
    tax = engine.n(data["settings"].get("tax_interest", 0.05))
    st.caption(f"Nhận cuối kỳ = Gửi đầu kỳ + Lãi trước thuế × (1 − {ui.pct(tax, 0)}). "
               "**Nạp thêm** = tiền gốc nộp thêm sau ngày gửi (không phải lãi). Khi tái tục: sửa Ngày đáo hạn, "
               "Gửi đầu kỳ, Lãi trước thuế của dòng đó.")
    derived = {s["id"]: s for s in h["savings"]}

    # ---- tổng quan: tô màu cả dòng theo trạng thái, sắp theo ngày đáo hạn
    STATUS = {  # trạng thái → (biểu tượng, nền dòng, màu chữ)
        "Quá hạn xử lý": ("●", "rgba(255,122,107,0.20)", "#FF8A7A"),
        "Sắp đáo hạn": ("●", "rgba(255,209,102,0.17)", "#FFD166"),
        "Đang sinh lời": ("●", "rgba(182,243,106,0.07)", "#B6F36A"),
        "": ("●", "transparent", "#D9D9D9"),
    }
    today = dt.date.today()
    sv = sorted(h["savings"], key=lambda s: (s["maturity_d"] is None, s["maturity_d"] or today))
    counts = {k: sum(1 for s in sv if s["status"] == k) for k in ("Quá hạn xử lý", "Sắp đáo hạn", "Đang sinh lời")}
    st.html('<div style="display:flex;gap:8px;flex-wrap:wrap;margin:2px 0 10px">' + "".join(
        f'<span class="pill" style="background:{STATUS[k][1]};color:{STATUS[k][2]};border-color:transparent">'
        f'{STATUS[k][0]} {k}: <b>{n}</b></span>' for k, n in counts.items()) + "</div>")
    if sv:
        ov = pd.DataFrame([{
            "Trạng thái": f"{STATUS[s['status']][0]} {s['status'] or '–'}",
            "Gói": s["name"], "Nhóm": s["code"], "Đáo hạn": ui.d(s["maturity"]),
            "Còn": (f"{(s['maturity_d'] - today).days} ngày" if s["maturity_d"] and s["maturity_d"] >= today
                    else ("quá {} ngày".format((today - s["maturity_d"]).days) if s["maturity_d"] else "–")),
            "Gốc + nạp": ui.vnd(s["base"]), "Nhận cuối kỳ": ui.vnd(s["received"]),
            "Tăng trưởng": ui.pct(s["growth"]), "Mục đích": s.get("purpose") or "",
            "_st": s["status"],
        } for s in sv])

        def _row(r):
            _, bg, fg = STATUS.get(r["_st"], STATUS[""])
            return [f"background-color:{bg};color:{fg}"] * len(r)

        st.dataframe(ov.style.apply(_row, axis=1), hide_index=True, width="stretch",
                     column_order=[c for c in ov.columns if c != "_st"], column_config={
                         "Trạng thái": st.column_config.TextColumn(width=150),
                         "Gói": st.column_config.TextColumn(width=170),
                         "Nhóm": st.column_config.TextColumn(width=60),
                         "Đáo hạn": st.column_config.TextColumn(width=95),
                         "Còn": st.column_config.TextColumn(width=85),
                         "Gốc + nạp": st.column_config.TextColumn(width=115),
                         "Nhận cuối kỳ": st.column_config.TextColumn(width=120),
                         "Tăng trưởng": st.column_config.TextColumn(width=90),
                     })

    st.caption(" · ".join(f"**{k}**: {ui.vnd(v)}" for k, v in
                          (pd.DataFrame(h["savings"]).groupby("code")["received"].sum().items()
                           if h["savings"] else [])))

    with st.expander("Sửa / thêm / xoá sổ tiết kiệm", key=style.ic("edit", "suaso")):
        df = pd.DataFrame([{
            "id": s["id"], "name": s["name"], "code": s["code"], "goal": s["goal"] or "", "purpose": s["purpose"] or "",
            "maturity": engine.to_date(s["maturity"]), "principal": s["principal"], "topup": s["topup"],
            "start_balance": s["start_balance"], "interest_gross": s["interest_gross"],
            "Nhận cuối kỳ": derived[s["id"]]["received"], "Tăng trưởng": derived[s["id"]]["growth"] * 100,
            "Trạng thái": f'{STATUS[derived[s["id"]]["status"]][0]} {derived[s["id"]]["status"]}',
        } for s in data["savings"]], columns=["id", "name", "code", "goal", "purpose", "maturity", "principal", "topup",
                                              "start_balance", "interest_gross", "Nhận cuối kỳ", "Tăng trưởng", "Trạng thái"])
        def _cell(v):
            st_ = str(v)[2:]
            return f"background-color:{STATUS[st_][1]};color:{STATUS[st_][2]}" if st_ in STATUS else ""
        styled = df.style.map(_cell, subset=["Trạng thái"])
        field_guide.render("savings")
        st.data_editor(styled, key="sav_ed", hide_index=True, width="stretch", num_rows="dynamic",
                       disabled=["id", "Nhận cuối kỳ", "Tăng trưởng", "Trạng thái"], column_config={
                           "id": None,
                           "name": st.column_config.TextColumn("Gói", required=True, help=field_guide.tip("savings", "Gói")),
                           "code": st.column_config.SelectboxColumn("Nhóm (Mã TS)", options=sav_codes, required=True, help=field_guide.tip("savings", "Nhóm (Mã TS)")),
                           "goal": st.column_config.SelectboxColumn("Mục tiêu", options=[""] + goal_names, help=field_guide.tip("savings", "Mục tiêu")),
                           "purpose": st.column_config.TextColumn("Mục đích", help=field_guide.tip("savings", "Mục đích")),
                           "maturity": st.column_config.DateColumn("Ngày đáo hạn", format="DD/MM/YYYY", help=field_guide.tip("savings", "Ngày đáo hạn")),
                           "principal": st.column_config.NumberColumn("Gốc", format="localized", help=field_guide.tip("savings", "Gốc")),
                           "topup": st.column_config.NumberColumn("Nạp thêm", format="localized", help=field_guide.tip("savings", "Nạp thêm")),
                           "start_balance": st.column_config.NumberColumn("Gửi đầu kỳ", format="localized", help=field_guide.tip("savings", "Gửi đầu kỳ")),
                           "interest_gross": st.column_config.NumberColumn("Lãi trước thuế", format="localized", help=field_guide.tip("savings", "Lãi trước thuế")),
                           "Nhận cuối kỳ": st.column_config.NumberColumn(format="localized"),
                           "Tăng trưởng": st.column_config.NumberColumn(format="%.1f%%"),
                       })
        if ui.has_changes("sav_ed"):
            n_del = len(st.session_state["sav_ed"].get("deleted_rows", []))
            ok = st.checkbox(f"Xác nhận xoá {n_del} sổ") if n_del else True
            if st.button("Lưu sổ tiết kiệm", type="primary", disabled=not ok, key=style.ic("device-floppy", "luuso")):
                e, a, x = ui.save_editor(c, "savings", "id", df, "sav_ed",
                                         ["name", "code", "goal", "purpose", "maturity", "principal", "topup",
                                          "start_balance", "interest_gross"])
                ui.flash(f"Sổ tiết kiệm: sửa {e}, thêm {a}, xoá {x}")
                st.rerun()

# --------------------------------------------------------------- goals
with tab_g:
    st.caption("Liên kết sổ tiết kiệm với mục tiêu bằng cột **Mục tiêu** ở tab Sổ tiết kiệm.")
    gd = {g["id"]: g for g in h["goals"]}
    gdf = pd.DataFrame([{
        "id": g["id"], "name": g["name"], "target": g["target"], "due_date": engine.to_date(g["due_date"]),
        "Đã có": gd[g["id"]]["have"], "Còn lại": gd[g["id"]]["remaining"],
        "Số tháng còn": gd[g["id"]]["months_left"], "Cần góp/tháng": gd[g["id"]]["need_monthly"],
        "Trạng thái": gd[g["id"]]["status"],
    } for g in data["goals"]], columns=["id", "name", "target", "due_date", "Đã có", "Còn lại", "Số tháng còn",
                                        "Cần góp/tháng", "Trạng thái"])
    field_guide.render("goals")
    st.data_editor(gdf, key="goal_ed", hide_index=True, width="stretch", num_rows="dynamic",
                   disabled=["id", "Đã có", "Còn lại", "Số tháng còn", "Cần góp/tháng", "Trạng thái"],
                   column_config={
                       "id": None,
                       "name": st.column_config.TextColumn("Mục tiêu", required=True, help=field_guide.tip("goals", "Mục tiêu")),
                       "target": st.column_config.NumberColumn("Số tiền mục tiêu", format="localized", help=field_guide.tip("goals", "Số tiền mục tiêu")),
                       "due_date": st.column_config.DateColumn("Ngày hoàn thành", format="DD/MM/YYYY", help=field_guide.tip("goals", "Ngày hoàn thành")),
                       **{k: st.column_config.NumberColumn(format="localized")
                          for k in ("Đã có", "Còn lại", "Cần góp/tháng")},
                   })
    for g in h["goals"]:
        if engine.n(g["target"]):
            st.progress(min(1.0, g["have"] / g["target"]), text=f"{g['name']}: {ui.pct(g['have'] / g['target'])}")
    if ui.has_changes("goal_ed") and st.button("Lưu mục tiêu", type="primary", key=style.ic("device-floppy", "luumt")):
        e, a, x = ui.save_editor(c, "goals", "id", gdf, "goal_ed", ["name", "target", "due_date"])
        ui.flash(f"Mục tiêu: sửa {e}, thêm {a}, xoá {x}")
        st.rerun()
    no_goal = [s["name"] for s in h["savings"] if s["code"] == "SF" and not s.get("goal")]
    if no_goal:
        st.info(f"{len(no_goal)} sổ Sinking Fund chưa gán mục tiêu: {', '.join(no_goal)}")

# --------------------------------------------------------------- liabilities
with tab_n:
    st.caption("Tổng nợ được trừ khỏi tài sản tính FIRE và tài sản ròng. Trả nợ hằng tháng nên khai cả ở trang Thu chi.")
    ndf = pd.DataFrame(data["liabilities"], columns=["id", "name", "balance", "rate", "monthly_payment", "end_date", "note"])
    ndf["end_date"] = ndf["end_date"].map(lambda x: engine.to_date(x) if x else None)
    ndf["rate"] = ndf["rate"] * 100
    field_guide.render("debts")
    st.data_editor(ndf, key="debt_ed", hide_index=True, width="stretch", num_rows="dynamic", column_config={
        "id": None,
        "name": st.column_config.TextColumn("Khoản nợ", required=True, help=field_guide.tip("debts", "Khoản nợ")),
        "balance": st.column_config.NumberColumn("Dư nợ", format="localized", help=field_guide.tip("debts", "Dư nợ")),
        "rate": st.column_config.NumberColumn("Lãi suất (%/năm)", format="%.2f", help=field_guide.tip("debts", "Lãi suất (%/năm)")),
        "monthly_payment": st.column_config.NumberColumn("Trả hằng tháng", format="localized", help=field_guide.tip("debts", "Trả hằng tháng")),
        "end_date": st.column_config.DateColumn("Ngày tất toán", format="DD/MM/YYYY", help=field_guide.tip("debts", "Ngày tất toán")),
        "note": st.column_config.TextColumn("Ghi chú", help=field_guide.tip("debts", "Ghi chú")),
    })
    st.metric("Tổng nợ", ui.vnd(fp["debt"]))

    def _rate(r):
        if r.get("rate") is not None:
            r["rate"] = r["rate"] / 100
        return r

    if ui.has_changes("debt_ed") and st.button("Lưu khoản nợ", type="primary", key=style.ic("device-floppy", "luuno")):
        e, a, x = ui.save_editor(c, "liabilities", "id", ndf, "debt_ed",
                                 ["name", "balance", "rate", "monthly_payment", "end_date", "note"], transform=_rate)
        ui.flash(f"Nợ: sửa {e}, thêm {a}, xoá {x}")
        st.rerun()

st.write("")
lessons.render_emergency(c, data, fp)

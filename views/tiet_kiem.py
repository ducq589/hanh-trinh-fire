import pandas as pd
import streamlit as st

from fi_app import db, engine, ui

c, data, h, fp = ui.state()
st.title("🏦 Tiết kiệm, Mục tiêu & Nợ")

sav_codes = [a["code"] for a in data["assets"] if a["valuation"] == "Sổ tiết kiệm"]
goal_names = [g["name"] for g in data["goals"]]
tab_s, tab_g, tab_n = st.tabs(["Sổ tiết kiệm", "Mục tiêu (Sinking Fund)", "Nợ phải trả"])

# --------------------------------------------------------------- savings
with tab_s:
    tax = engine.n(data["settings"].get("tax_interest", 0.05))
    st.caption(f"Nhận cuối kỳ = Gửi đầu kỳ + Lãi trước thuế × (1 − {ui.pct(tax, 0)}). "
               "**Nạp thêm** = tiền gốc nộp thêm sau ngày gửi (không phải lãi). Khi tái tục: sửa Ngày đáo hạn, "
               "Gửi đầu kỳ, Lãi trước thuế của dòng đó.")
    derived = {s["id"]: s for s in h["savings"]}
    df = pd.DataFrame([{
        "id": s["id"], "name": s["name"], "code": s["code"], "goal": s["goal"], "purpose": s["purpose"],
        "maturity": engine.to_date(s["maturity"]), "principal": s["principal"], "topup": s["topup"],
        "start_balance": s["start_balance"], "interest_gross": s["interest_gross"],
        "Nhận cuối kỳ": derived[s["id"]]["received"], "Tăng trưởng": derived[s["id"]]["growth"] * 100,
        "Trạng thái": derived[s["id"]]["status"],
    } for s in data["savings"]], columns=["id", "name", "code", "goal", "purpose", "maturity", "principal", "topup",
                                          "start_balance", "interest_gross", "Nhận cuối kỳ", "Tăng trưởng", "Trạng thái"])
    st.data_editor(df, key="sav_ed", hide_index=True, width="stretch", num_rows="dynamic",
                   disabled=["id", "Nhận cuối kỳ", "Tăng trưởng", "Trạng thái"], column_config={
                       "id": None,
                       "name": st.column_config.TextColumn("Gói", required=True),
                       "code": st.column_config.SelectboxColumn("Nhóm (Mã TS)", options=sav_codes, required=True),
                       "goal": st.column_config.SelectboxColumn("Mục tiêu", options=goal_names),
                       "purpose": st.column_config.TextColumn("Mục đích"),
                       "maturity": st.column_config.DateColumn("Ngày đáo hạn", format="DD/MM/YYYY"),
                       "principal": st.column_config.NumberColumn("Gốc", format="localized"),
                       "topup": st.column_config.NumberColumn("Nạp thêm", format="localized"),
                       "start_balance": st.column_config.NumberColumn("Gửi đầu kỳ", format="localized"),
                       "interest_gross": st.column_config.NumberColumn("Lãi trước thuế", format="localized"),
                       "Nhận cuối kỳ": st.column_config.NumberColumn(format="localized"),
                       "Tăng trưởng": st.column_config.NumberColumn(format="%.1f%%"),
                   })
    if ui.has_changes("sav_ed"):
        n_del = len(st.session_state["sav_ed"].get("deleted_rows", []))
        ok = st.checkbox(f"Xác nhận xoá {n_del} sổ") if n_del else True
        if st.button("💾 Lưu sổ tiết kiệm", type="primary", disabled=not ok):
            e, a, x = ui.save_editor(c, "savings", "id", df, "sav_ed",
                                     ["name", "code", "goal", "purpose", "maturity", "principal", "topup",
                                      "start_balance", "interest_gross"])
            ui.flash(f"Sổ tiết kiệm: sửa {e}, thêm {a}, xoá {x}")
            st.rerun()
    tot = pd.DataFrame(h["savings"]).groupby("code")["received"].sum() if h["savings"] else pd.Series(dtype=float)
    st.caption(" · ".join(f"**{k}**: {ui.vnd(v)}" for k, v in tot.items()))

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
    st.data_editor(gdf, key="goal_ed", hide_index=True, width="stretch", num_rows="dynamic",
                   disabled=["id", "Đã có", "Còn lại", "Số tháng còn", "Cần góp/tháng", "Trạng thái"],
                   column_config={
                       "id": None,
                       "name": st.column_config.TextColumn("Mục tiêu", required=True),
                       "target": st.column_config.NumberColumn("Số tiền mục tiêu", format="localized"),
                       "due_date": st.column_config.DateColumn("Ngày hoàn thành", format="DD/MM/YYYY"),
                       **{k: st.column_config.NumberColumn(format="localized")
                          for k in ("Đã có", "Còn lại", "Cần góp/tháng")},
                   })
    for g in h["goals"]:
        if engine.n(g["target"]):
            st.progress(min(1.0, g["have"] / g["target"]), text=f"{g['name']}: {ui.pct(g['have'] / g['target'])}")
    if ui.has_changes("goal_ed") and st.button("💾 Lưu mục tiêu", type="primary"):
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
    st.data_editor(ndf, key="debt_ed", hide_index=True, width="stretch", num_rows="dynamic", column_config={
        "id": None,
        "name": st.column_config.TextColumn("Khoản nợ", required=True),
        "balance": st.column_config.NumberColumn("Dư nợ", format="localized"),
        "rate": st.column_config.NumberColumn("Lãi suất (%/năm)", format="%.2f"),
        "monthly_payment": st.column_config.NumberColumn("Trả hằng tháng", format="localized"),
        "end_date": st.column_config.DateColumn("Ngày tất toán", format="DD/MM/YYYY"),
        "note": st.column_config.TextColumn("Ghi chú"),
    })
    st.metric("Tổng nợ", ui.vnd(fp["debt"]))

    def _rate(r):
        if r.get("rate") is not None:
            r["rate"] = r["rate"] / 100
        return r

    if ui.has_changes("debt_ed") and st.button("💾 Lưu khoản nợ", type="primary"):
        e, a, x = ui.save_editor(c, "liabilities", "id", ndf, "debt_ed",
                                 ["name", "balance", "rate", "monthly_payment", "end_date", "note"], transform=_rate)
        ui.flash(f"Nợ: sửa {e}, thêm {a}, xoá {x}")
        st.rerun()

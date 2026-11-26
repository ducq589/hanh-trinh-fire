import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from fi_app import db, engine, style, ui

c, data, h, fp = ui.state()
style.title("chart-line", "Lịch sử")

tab_nw, tab_ccq, tab_nav = st.tabs(["Tài sản ròng", "CCQ theo tháng", "Biểu đồ NAV & ngày mua"], key="tabs_ls")
style.tab_icons("tabs_ls", ["chart-line", "stack-2", "chart-candle"])

# --------------------------------------------------------------- tài sản ròng (Snapshot)
with tab_nw:
    st.caption("App tự chụp 1 Snapshot mỗi tháng khi mở lần đầu trong tháng. Có thể chụp thêm bất cứ lúc nào.")
    col1, col2 = st.columns([1, 3])
    note = col2.text_input("Ghi chú cho lần chụp", placeholder="VD: sau khi nhận thưởng Tết")
    if col1.button("Chụp ngay", type="primary", key=style.ic("camera", "chup")):
        db.save_snapshot(c, engine.snapshot(data, h, fp, note=note or "Chụp thủ công"))
        ui.flash("Đã lưu Snapshot hôm nay")
        st.rerun()

    snaps = pd.DataFrame(data["snapshots"])
    if snaps.empty:
        st.info("Chưa có Snapshot.")
    else:
        snaps["date"] = pd.to_datetime(snaps["date"])
        fig = go.Figure()
        fig.add_trace(go.Scatter(x=snaps["date"], y=snaps["net_worth"], name="Tài sản ròng", mode="lines+markers",
                                 line=dict(color=style.TEXT, width=3)))
        fig.add_trace(go.Scatter(x=snaps["date"], y=snaps["fire_assets"], name="Tài sản tính FIRE", mode="lines+markers",
                                 line=dict(color=style.LIME, width=3)))
        if snaps["fire_number"].notna().any():
            fig.add_trace(go.Scatter(x=snaps["date"], y=snaps["fire_number"], name="Số FIRE", line=dict(color=style.TARGET_FULL, dash="dash")))
        fig.update_layout(height=400, margin=dict(t=10, b=10), hovermode="x unified", yaxis_tickformat=",.0f",
                          legend=dict(orientation="h", y=-0.15))
        st.plotly_chart(style.fig(fig), width="stretch")
        if len(snaps) == 1:
            st.caption("Mới có 1 điểm dữ liệu – biểu đồ sẽ rõ dần sau mỗi tháng.")

        view = snaps.sort_values("date", ascending=False)
        st.dataframe(pd.DataFrame({
            "Ngày": view["date"].dt.strftime("%d/%m/%Y"), "Tổng tài sản": view["total_assets"].map(ui.vnd),
            "Nợ": view["liabilities"].map(ui.vnd), "Tài sản ròng": view["net_worth"].map(ui.vnd),
            "Tài sản FIRE": view["fire_assets"].map(ui.vnd), "Số FIRE": view["fire_number"].map(ui.vnd),
            "% Full FIRE": view["fire_progress"].map(ui.pct), "Tỷ lệ tiết kiệm": view["savings_rate"].map(ui.pct),
            "Ghi chú": view["note"]}), hide_index=True, width="stretch")

# --------------------------------------------------------------- lô CCQ theo tháng
funds = [a for a in data["assets"] if a.get("type") in engine.FUND_TYPES
         and any(t["code"] == a["code"] for t in data["transactions"])]
fund_names = {a["code"]: f"{a['code']} – {a['name']}" for a in funds}


def _m(x) -> str:
    """Số tiền gọn cho bảng: 1.234.567 (âm có dấu −)."""
    return "" if x is None or pd.isna(x) else f"{x:,.0f}".replace(",", ".")


def _p(x) -> str:
    return "" if x is None or pd.isna(x) else f"{x * 100:.2f}%".replace(".", ",")


def _q(x) -> str:
    return "" if not x else f"{x:,.2f}".replace(",", "§").replace(".", ",").replace("§", ".")


def _color(v: str) -> str:
    if not isinstance(v, str) or not v.endswith("%"):
        return ""
    return "color:#FF8A80" if v.startswith("-") else "color:#B6F36A"


with tab_ccq:
    if not funds:
        st.info("Chưa có giao dịch quỹ mở/ETF nào. Ghi lệnh mua ở trang **Giao dịch → Mua CCQ nhanh**.")
    else:
        st.caption("Mỗi tháng mua là **một lô**. Khi bán, CCQ được trừ vào **lô mua sớm nhất trước** (mua trước bán trước). "
                   "Lãi/lỗ của lô = (Giá hiện tại × CCQ còn lại) − Vốn của phần còn lại.")
        pick = st.multiselect("Quỹ", list(fund_names), default=list(fund_names), format_func=fund_names.get, key="lot_codes")
        results = [engine.fund_lots(h["transactions"], h["book"], code) for code in pick]
        months = engine.monthly_lots(results)
        if not months:
            st.info("Chọn ít nhất 1 quỹ.")
        else:
            mode = st.segmented_control("Kiểu xem", ["Theo năm", "Chi tiết từng lô", "Các lần bán"], default="Theo năm",
                                        key="lot_mode") or "Theo năm"
            if mode == "Theo năm":
                years = sorted({m["year"] for m in months})
                st.markdown("**Tổng tiền đầu tư và lợi nhuận theo tháng**" + (f" ({', '.join(pick)})" if pick else ""))
                rows = []
                for mo in range(1, 13):
                    r = {"Tháng": str(mo)}
                    for y in years:
                        ms = [m for m in months if m["year"] == y and m["month"] == mo]
                        cost = sum(m["cost"] for m in ms)
                        rc, pnl = sum(m["remaining_cost"] for m in ms), sum(m["pnl"] for m in ms)
                        r[f"Tiền mua {y}"] = _m(cost) if ms else ""
                        r[f"Lãi/lỗ {y}"] = _p(pnl / rc) if rc else ("Đã bán hết" if ms else "")
                    rows.append(r)
                tot = {"Tháng": "Tổng"}
                prof = {"Tháng": "Lợi nhuận"}
                for y in years:
                    ms = [m for m in months if m["year"] == y]
                    rc, pnl = sum(m["remaining_cost"] for m in ms), sum(m["pnl"] for m in ms)
                    tot[f"Tiền mua {y}"], tot[f"Lãi/lỗ {y}"] = _m(sum(m["cost"] for m in ms)), _p(pnl / rc) if rc else ""
                    prof[f"Tiền mua {y}"], prof[f"Lãi/lỗ {y}"] = _m(pnl), ""
                df = pd.DataFrame(rows + [tot, prof])
                st.dataframe(df.style.map(_color), hide_index=True, width="stretch", height=(len(df) + 1) * 35 + 3)

                st.markdown("**Số lượng CCQ mua theo tháng**")
                qrows = []
                for mo in list(range(1, 13)) + ["Tổng"]:
                    r = {"Tháng": str(mo)}
                    for y in years:
                        for code in pick:
                            ms = [m for m in months if m["year"] == y and m["code"] == code and (mo == "Tổng" or m["month"] == mo)]
                            r[f"{code} {y}"] = _q(sum(m["qty"] for m in ms))
                    qrows.append(r)
                qdf = pd.DataFrame(qrows)
                st.dataframe(qdf, hide_index=True, width="stretch", height=(len(qdf) + 1) * 35 + 3)
                st.caption("Lãi/lỗ theo tháng tính trên **phần CCQ còn giữ** của lô tháng đó, theo giá mới nhất. "
                           "Dòng Lợi nhuận = tổng lãi/lỗ chưa chốt của các lô trong năm. Vốn đầu kỳ được tính là 1 lô "
                           "ở tháng khai báo.")

            elif mode == "Chi tiết từng lô":
                lot_rows = [{"Mã": res["code"], "Ngày mua": lot["date"].strftime("%d/%m/%Y"), "Loại": lot["kind"],
                             "Giá mua": _m(lot["price"]), "CCQ mua": _q(lot["qty"]), "Tiền mua": _m(lot["cost"]),
                             "CCQ còn lại": _q(lot["remaining"]) or "0", "Giá trị hiện tại": _m(lot["value"]),
                             "Lãi/lỗ": _m(lot["pnl"]), "% Lãi/lỗ": _p(lot["pct"])}
                            for res in results for lot in res["lots"]]
                lot_rows.sort(key=lambda r: pd.to_datetime(r["Ngày mua"], dayfirst=True), reverse=True)
                st.dataframe(pd.DataFrame(lot_rows).style.map(_color), hide_index=True, width="stretch")
                st.caption(" · ".join(f"Giá {res['code']} mới nhất: {_m(res['price'])} ₫ ({ui.d(res['price_date'])})"
                                      for res in results))

            else:
                sale_rows = [{"Mã": res["code"], "Ngày bán": s["date"].strftime("%d/%m/%Y"), "CCQ bán": _q(s["qty"]),
                              "Giá bán": _m(s["price"]), "Tiền nhận (sau phí, thuế)": _m(s["proceeds"]),
                              "Giá vốn (lô cũ trước)": _m(s["cost"]), "Lãi/lỗ đã chốt": _m(s["pnl"]), "%": _p(s["pct"]),
                              "Lấy từ lô": "; ".join(f"{d:%d/%m/%Y}: {_q(q)}" for d, q in s["sources"])}
                             for res in results for s in res["sales"]]
                if not sale_rows:
                    st.info("Chưa có lần bán nào.")
                else:
                    st.dataframe(pd.DataFrame(sale_rows).style.map(_color), hide_index=True, width="stretch")
                    total = sum(s["pnl"] for res in results for s in res["sales"])
                    st.markdown(f"Tổng lãi/lỗ đã chốt: **{ui.vnd(total)}**")
                if any(s["short"] for res in results for s in res["sales"]):
                    st.warning("Có lần bán nhiều CCQ hơn số đang giữ theo các lô đã ghi – kiểm tra lại lệnh mua/bán "
                               "ở trang Giao dịch → Lịch sử & sửa.")

# --------------------------------------------------------------- biểu đồ NAV + ngày mua
LINE = ["#6FA8DC", "#FF9F68", style.LIME, "#C39BD3", "#FFD166"]
MARK = ["#FF4D4D", "#2BB3A3", "#FFFFFF", "#F7DC6F", "#5DADE2"]
with tab_nav:
    nav_codes = [a["code"] for a in funds]
    if not nav_codes:
        st.info("Chưa có giao dịch quỹ mở/ETF nào.")
    else:
        sel = st.multiselect("Quỹ", nav_codes, default=nav_codes[:2], format_func=fund_names.get, key="nav_codes")
        hist = {code: h["book"].history(code) for code in sel}
        meds = {code: sorted(p for _, p in hs)[len(hs) // 2] for code, hs in hist.items() if hs}
        dual = len(meds) == 2 and max(meds.values()) / max(min(meds.values()), 1) > 1.5
        fig = go.Figure()
        for i, code in enumerate(sel):
            if not hist.get(code):
                continue
            ax = "y2" if dual and i == 1 else "y"
            ds, ps = zip(*hist[code])
            fig.add_trace(go.Scatter(x=ds, y=ps, name=f"NAV {code}", mode="lines", yaxis=ax,
                                     line=dict(color=LINE[i % len(LINE)], width=2),
                                     hovertemplate="%{x|%d/%m/%Y}: %{y:,.0f} ₫<extra>" + code + "</extra>"))
            mine = [t for t in h["transactions"] if t["code"] == code and t["price_used"] > 0]
            for typ, sym, label in (("Mua", "star", "Mua"), ("Bán", "triangle-down", "Bán")):
                pts = [t for t in mine if t["type"] == typ]
                if not pts:
                    continue
                fig.add_trace(go.Scatter(
                    x=[t["d"] for t in pts], y=[t["price_used"] for t in pts], mode="markers", yaxis=ax,
                    name=f"{label} {code}", marker=dict(symbol=sym, size=12, color=MARK[i % len(MARK)],
                                                        line=dict(color="#111", width=1)),
                    customdata=[[_m(t["value"] + (t.get("fee") or 0) if typ == "Mua" else t["value"]),
                                 _q(t["qty_calc"])] for t in pts],
                    hovertemplate=(f"{label} {code} %{{x|%d/%m/%Y}}<br>Giá %{{y:,.0f}} ₫<br>"
                                   "Số tiền %{customdata[0]} ₫ · %{customdata[1]} CCQ<extra></extra>")))
        layout = dict(height=480, margin=dict(t=10, b=10), hovermode="closest", yaxis=dict(tickformat=",.0f", title="NAV (₫)"),
                      legend=dict(orientation="h", y=-0.18),
                      xaxis=dict(rangeselector=dict(buttons=[
                          dict(count=6, label="6 tháng", step="month", stepmode="backward"),
                          dict(count=1, label="1 năm", step="year", stepmode="backward"),
                          dict(step="all", label="Tất cả")], bgcolor="#2A2A2A", activecolor="#3A3A3A",
                          font=dict(color=style.TEXT))))
        if dual:
            layout["yaxis2"] = dict(overlaying="y", side="right", tickformat=",.0f", showgrid=False,
                                    title=f"NAV {sel[1]} (₫)")
        fig.update_layout(**layout)
        st.plotly_chart(style.fig(fig), width="stretch")
        st.caption("★ = ngày mua (đặt tại giá mua thực tế), ▼ = ngày bán. Lệnh chờ NAV và Vốn đầu kỳ không hiện trên biểu đồ."
                   + (f" Hai quỹ chênh giá nhiều nên {sel[1]} dùng trục bên phải." if dual else ""))

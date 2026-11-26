"""Lõi tính toán – hàm Python thuần, không phụ thuộc giao diện hay cơ sở dữ liệu.

Mọi công thức được chuyển nguyên từ Investment_tracking_v3.xlsx (đã kiểm chứng bằng Excel):
- cột tính của tblGD (Giá dùng, SL tính, GT giao dịch, ΔSL, Tiền vào ròng, Cổ tức nhận, Dòng tiền)
- sheet DanhMuc (giá mới nhất, giá trị, lãi/lỗ, XIRR, tái cân bằng)
- sheet FI_Plan → "Kế hoạch FIRE" (Số FIRE, Lean/Coast/Full FIRE, NPER, dự phóng FV)
"""
from __future__ import annotations

import datetime as dt
import math
from collections import defaultdict

BUY_LIKE = ("Mua", "Vốn đầu kỳ")
XIRR_MIN_DAYS = 30          # số dư đầu kỳ: cần tối thiểu 30 ngày theo dõi mới hiện XIRR (ngắn hơn thì dao động quá mạnh)


# ================================================================ helpers
def to_date(v) -> dt.date | None:
    if v in (None, ""):
        return None
    if isinstance(v, dt.datetime):
        return v.date()
    if isinstance(v, dt.date):
        return v
    return dt.date.fromisoformat(str(v)[:10])


def n(v) -> float:
    """Giống hàm N() của Excel: None/'' → 0."""
    if v in (None, ""):
        return 0.0
    try:
        f = float(v)
    except (TypeError, ValueError):
        return 0.0
    return 0.0 if math.isnan(f) else f


def trunc2(x: float) -> float:
    """TRUNC(x, 2) – cách quỹ mở phân bổ chứng chỉ quỹ."""
    return math.trunc(round(x * 100, 8)) / 100


def months_between(start: dt.date, end: dt.date) -> int:
    """DATEDIF(start, end, "m") – số tháng tròn."""
    m = (end.year - start.year) * 12 + (end.month - start.month)
    if end.day < start.day:
        m -= 1
    return max(m, 0)


def vnd(x: float) -> str:
    """Định dạng tiền kiểu Việt Nam: 4.150.000 ₫."""
    return f"{x:,.0f}".replace(",", ".") + " ₫"


def monthly(amount, freq: str) -> float:
    a = n(amount)
    return a / 12 if freq == "Năm" else a / 3 if freq == "Quý" else a


# ================================================================ finance functions (Excel semantics)
def xirr(values: list[float], dates: list[dt.date], guesses=(-0.05, 0.05, 0.1, -0.5)) -> float | None:
    if len(values) < 2 or not any(v > 0 for v in values) or not any(v < 0 for v in values):
        return None
    d0 = dates[0]
    t = [(d - d0).days / 365.0 for d in dates]

    def f(r):
        return sum(v / (1 + r) ** ti for v, ti in zip(values, t))

    def df(r):
        return sum(-ti * v / (1 + r) ** (ti + 1) for v, ti in zip(values, t))

    for g in guesses:
        r = g
        try:
            for _ in range(100):
                fv, dfv = f(r), df(r)
                if dfv == 0:
                    break
                nr = r - fv / dfv
                if nr <= -1:
                    nr = (r - 1) / 2
                if abs(nr - r) < 1e-12:
                    return nr
                r = nr
            if abs(f(r)) < 1e-6:
                return r
        except (OverflowError, ZeroDivisionError):
            continue
    lo, hi = -0.9999, 10.0  # bisection fallback
    try:
        flo, fhi = f(lo), f(hi)
    except OverflowError:
        return None
    if flo * fhi > 0:
        return None
    for _ in range(300):
        mid = (lo + hi) / 2
        fm = f(mid)
        if flo * fm <= 0:
            hi = mid
        else:
            lo, flo = mid, fm
    return (lo + hi) / 2


def nper(rate: float, pmt: float, pv: float, fv: float) -> float | None:
    """NPER(rate, pmt, pv, fv) của Excel (type = 0). None nếu không có nghiệm."""
    if rate == 0:
        return None if pmt == 0 else -(pv + fv) / pmt
    num = pmt - fv * rate
    den = pmt + pv * rate
    if den == 0 or num / den <= 0:
        return None
    return math.log(num / den) / math.log(1 + rate)


def fv(rate: float, periods: int, pmt: float, pv: float) -> float:
    """FV(rate, nper, pmt, pv) của Excel (type = 0)."""
    if rate == 0:
        return -(pv + pmt * periods)
    g = (1 + rate) ** periods
    return -(pv * g + pmt * (g - 1) / rate)


# ================================================================ prices
class PriceBook:
    """Tra giá: cùng ngày ưu tiên giá nhập tay > giá người dùng > giá thị trường; trùng dòng thì lấy trung bình."""

    def __init__(self, prices: list[dict]):
        acc: dict[tuple, list] = defaultdict(list)
        for p in prices:
            acc[(p["code"], to_date(p["date"]), int(p.get("is_manual") or 0))].append(float(p["price"]))
        self._px = {k: sum(v) / len(v) for k, v in acc.items()}
        self._dates: dict[str, set] = defaultdict(set)
        for code, d, _ in self._px:
            self._dates[code].add(d)

    def on(self, code: str, d: dt.date) -> float | None:
        # 1 = nhập tay, 0 = giá của người dùng (gia.csv/v3), -1 = giá thị trường dùng chung
        for manual in (1, 0, -1):
            if (code, d, manual) in self._px:
                return self._px[(code, d, manual)]
        return None

    def latest(self, code: str) -> tuple[dt.date | None, float | None]:
        ds = self._dates.get(code)
        if not ds:
            return None, None
        d = max(ds)
        return d, self.on(code, d)

    def at_or_before(self, code: str, d: dt.date, max_days: int = 7) -> float | None:
        """Giá thị trường gần nhất trong vòng max_days ngày tính tới ngày d (ngày nghỉ lễ, cuối tuần)."""
        ds = [x for x in self._dates.get(code, ()) if x <= d and (d - x).days <= max_days]
        return self.on(code, max(ds)) if ds else None

    def history(self, code: str) -> list[tuple[dt.date, float]]:
        return sorted((d, self.on(code, d)) for d in self._dates.get(code, ()))


# ================================================================ transactions
def derive_tx(tx: dict, book: PriceBook) -> dict:
    """Các cột tính của tblGD."""
    t = tx["type"]
    d = to_date(tx["date"])
    price_used = n(tx.get("price")) if n(tx.get("price")) > 0 else n(book.on(tx["code"], d))
    if tx.get("qty") not in (None, ""):
        qty = n(tx["qty"])
    elif t in BUY_LIKE and price_used > 0:
        qty = trunc2(n(tx.get("amount")) / price_used)
    else:
        qty = 0.0
    gt = qty * price_used if price_used > 0 else n(tx.get("amount"))
    fee, tax = n(tx.get("fee")), n(tx.get("tax"))
    dqty = qty if t in BUY_LIKE + ("Cổ tức CP/Thưởng",) else -qty if t == "Bán" else 0.0
    net_in = gt + fee if t in BUY_LIKE else -(gt - fee - tax) if t == "Bán" else 0.0
    dividend = n(tx.get("amount")) if t == "Cổ tức TM" else 0.0
    cash = -(gt + fee) if t == "Mua" else (gt - fee - tax) if t == "Bán" else dividend
    # Mua theo số tiền nhưng chưa có NAV ngày phân bổ → "chờ phân bổ": tiền đã ghi, số CCQ tính khi có NAV
    pending = t == "Mua" and tx.get("qty") in (None, "") and price_used <= 0 and n(tx.get("amount")) > 0
    return {**tx, "d": d, "price_used": price_used, "qty_calc": qty, "value": gt, "dqty": dqty,
            "net_in": net_in, "dividend": dividend, "cashflow": cash, "pending": pending}


# ================================================================ savings & goals
def derive_savings(s: dict, tax: float, today: dt.date, maturity_days: float) -> dict:
    received = n(s.get("start_balance")) + n(s.get("interest_gross")) * (1 - tax)
    base = n(s.get("principal")) + n(s.get("topup"))
    m = to_date(s.get("maturity"))
    if m is None:
        status = ""
    elif m < today:
        status = "Quá hạn xử lý"
    elif (m - today).days <= maturity_days:
        status = "Sắp đáo hạn"
    else:
        status = "Đang sinh lời"
    return {**s, "received": received, "base": base, "growth": (received - base) / base if base else 0.0,
            "status": status, "maturity_d": m}


def derive_goals(goals: list[dict], savings: list[dict], today: dt.date) -> list[dict]:
    out = []
    for g in goals:
        have = sum(s["received"] for s in savings if (s.get("goal") or "") == g["name"])
        remaining = max(0.0, n(g.get("target")) - have)
        due = to_date(g.get("due_date"))
        months = (months_between(today, max(today, due)) + 1) if due else None
        if months is not None and due < today:
            months = 0
        need = 0.0 if remaining <= 0 else (remaining if not months else remaining / months)
        status = "Done" if remaining <= 0 else ("Quá hạn" if not months else "Đang góp")
        out.append({**g, "have": have, "remaining": remaining, "months_left": months, "need_monthly": need,
                    "status": status})
    return out


# ================================================================ holdings (sheet DanhMuc)
def holdings(data: dict, today: dt.date | None = None) -> dict:
    today = today or dt.date.today()
    st = data["settings"]
    tax, stale_days, mat_days = n(st.get("tax_interest", 0.05)), n(st.get("stale_days", 7)), n(st.get("maturity_days", 15))
    book = PriceBook(data["prices"])
    txs = [derive_tx(t, book) for t in data["transactions"]]
    by_code: dict[str, list] = defaultdict(list)
    for t in txs:
        by_code[t["code"]].append(t)
    savs = [derive_savings(s, tax, today, mat_days) for s in data["savings"]]

    rows = []
    for a in data["assets"]:
        code, val = a["code"], a.get("valuation") or "Thị trường"
        r = {**a, "qty": None, "cost": 0.0, "dividends": 0.0, "price_date": None, "price": None,
             "value": 0.0, "xirr": None, "xirr_since": None, "warning": ""}
        if val == "Sổ tiết kiệm":
            mine = [s for s in savs if s["code"] == code]
            r["cost"] = sum(s["base"] for s in mine)
            r["value"] = sum(s["received"] for s in mine)
        else:
            mine = by_code.get(code, [])
            r["qty"] = sum(t["dqty"] for t in mine)
            r["cost"] = sum(t["net_in"] for t in mine)
            r["dividends"] = sum(t["dividend"] for t in mine)
            r["price_date"], r["price"] = book.latest(code)
            r["value"] = n(r["qty"]) * n(r["price"])
            if r["price_date"] is None:
                r["warning"] = "Chưa có giá" if mine else ""
            elif (today - r["price_date"]).days > stale_days:
                r["warning"] = f"Giá cũ {(today - r['price_date']).days} ngày"
            waiting = [t for t in mine if t["pending"]]
            mine = [t for t in mine if not t["pending"]]           # XIRR chỉ tính lệnh đã có NAV
            opening = [t for t in mine if t["type"] == "Vốn đầu kỳ"]
            if not opening:
                flows = [(t["d"], t["cashflow"]) for t in mine if t["cashflow"] != 0]
            else:
                # Có số dư đầu kỳ (không nhập lịch sử lệnh): XIRR tính TỪ NGÀY KHAI BÁO, coi số dư như được
                # "mua" theo giá thị trường ngày đó. Không có giá thị trường quanh ngày khai → không tính.
                since = min(t["d"] for t in opening)
                r["xirr_since"] = since
                flows = []
                for t in opening:
                    mkt = book.at_or_before(code, t["d"])
                    if mkt is None:
                        flows = None
                        break
                    flows.append((t["d"], -t["qty_calc"] * mkt))
                if flows is not None:
                    flows += [(t["d"], t["cashflow"]) for t in mine
                              if t["type"] != "Vốn đầu kỳ" and t["cashflow"] != 0 and t["d"] >= since]
                    if r["price_date"] is None or (r["price_date"] - since).days < XIRR_MIN_DAYS:
                        flows = None
            if r["price_date"] and flows:
                r["xirr"] = xirr([v for _, v in flows] + [r["value"]], [d for d, _ in flows] + [r["price_date"]])
            if waiting:   # tiền chờ phân bổ tính theo giá vốn, tránh hiện lỗ giả
                r["pending_amount"] = sum(n(t.get("amount")) for t in waiting)
                r["value"] += r["pending_amount"]
                ds = ", ".join(sorted({t["d"].strftime("%d/%m") for t in waiting}))
                r["warning"] = "; ".join(x for x in (r["warning"], f"Chờ NAV ngày {ds}") if x)
        r["pnl"] = r["value"] - r["cost"] + r["dividends"]
        r["pnl_pct"] = r["pnl"] / r["cost"] if r["cost"] else 0.0
        r["fire_value"] = r["value"] if a.get("fire_include") else 0.0
        rows.append(r)

    total = sum(r["value"] for r in rows)
    targeted = [r for r in rows if n(r.get("target_weight")) > 0]
    tgt_total = sum(r["value"] for r in targeted)
    anchor = max((r["value"] / n(r["target_weight"]) for r in targeted), default=0.0)
    for r in rows:
        r["weight"] = r["value"] / total if total else 0.0
        if n(r.get("target_weight")) > 0:
            r["current_weight"] = r["value"] / tgt_total if tgt_total else 0.0
            r["rebalance_need"] = anchor * n(r["target_weight"]) - r["value"]
        else:
            r["current_weight"] = r["rebalance_need"] = None

    tiers = []
    from .db import TIERS  # nhãn tầng
    for tier in TIERS:
        tr = [r for r in rows if r.get("tier") == tier]
        cost, value = sum(r["cost"] for r in tr), sum(r["value"] for r in tr)
        pnl = sum(r["pnl"] for r in tr)
        tiers.append({"tier": tier, "cost": cost, "value": value, "pnl": pnl,
                      "pnl_pct": pnl / cost if cost else 0.0, "weight": value / total if total else 0.0,
                      "fire_value": sum(r["fire_value"] for r in tr)})

    cost_total = sum(r["cost"] for r in rows)
    pnl_total = sum(r["pnl"] for r in rows)
    return {"rows": rows, "tiers": tiers, "transactions": txs, "savings": savs,
            "goals": derive_goals(data["goals"], savs, today), "book": book,
            "total_value": total, "total_cost": cost_total, "total_pnl": pnl_total,
            "total_pnl_pct": pnl_total / cost_total if cost_total else 0.0,
            "total_dividends": sum(r["dividends"] for r in rows),
            "fire_value_gross": sum(r["fire_value"] for r in rows)}


# ================================================================ cash-flow profile (sheet Profile)
def cashflow_summary(items: list[dict]) -> dict:
    g = defaultdict(float)
    for it in items:
        g[it["grp"]] += monthly(it.get("amount"), it.get("freq") or "Tháng")
    active, passive = g["Thu nhập chủ động"], g["Thu nhập thụ động"]
    essential, flexible, invest = g["Chi thiết yếu"], g["Chi linh hoạt"], g["Đầu tư định kỳ"]
    income, expense = active + passive, essential + flexible
    surplus = income - expense
    return {"active": active, "passive": passive, "income": income, "essential": essential,
            "flexible": flexible, "expense": expense, "surplus": surplus, "invest": invest,
            "after_invest": surplus - invest,
            "savings_rate": surplus / income if income else 0.0,
            "essential_ratio": essential / income if income else 0.0}


# ================================================================ FIRE plan (sheet FI_Plan)
def fire_plan(data: dict, h: dict, today: dt.date | None = None, extra_invest: float = 0.0,
              expense_factor: float = 1.0, years: int = 40) -> dict:
    today = today or dt.date.today()
    a = data["assumptions"]
    cf = cashflow_summary(data["cashflow"])
    age = int(n(a.get("current_age"))) or None
    target_age = int(n(a.get("target_age"))) or None
    infl = n(a.get("inflation"))
    swr = n(a.get("swr")) or 0.04
    em_target = n(a.get("emergency_months")) or 6
    rows = h["rows"]
    fire_gross = sum(r["fire_value"] for r in rows)
    ret_auto = (sum(r["fire_value"] * n(r.get("exp_return")) for r in rows) / fire_gross) if fire_gross else 0.08
    nominal = n(a.get("return_nominal")) if a.get("return_nominal") not in (None, "") else ret_auto
    real = (1 + nominal) / (1 + infl) - 1
    debt = sum(n(l.get("balance")) for l in data["liabilities"])
    assets = max(0.0, fire_gross - debt)

    expense = cf["expense"] * expense_factor
    essential = cf["essential"]  # kịch bản "Nếu…" chỉ thay đổi tổng chi tiêu, không đổi mức chi thiết yếu
    invest = cf["invest"] + extra_invest
    fire_number = expense * 12 / swr if expense else None
    lean = essential * 12 / swr if essential else None
    coast = (fire_number / (1 + real) ** max(0.0, target_age - age)) if (fire_number and age and target_age) else None

    def years_to(target):
        if not target:
            return None
        if assets >= target:
            return 0.0
        k = nper(real / 12, -invest, -assets, target)
        return k / 12 if k is not None else None

    y_full, y_lean = years_to(fire_number), years_to(lean)
    passive_sust = assets * swr / 12
    em_value = sum(r["value"] for r in rows if r["code"] == a.get("emergency_code", "QKC"))
    em_months = em_value / cf["essential"] if cf["essential"] else None

    proj, d = [], assets
    for k in range(years):
        if k > 0:
            d = fv(real / 12, 12, -invest, -d)
        label = ""
        if fire_number:
            label = "Full FIRE" if d >= fire_number else ("Lean FIRE" if lean and d >= lean else "")
        proj.append({"k": k, "year": today.year + k, "age": (age + k) if age else None, "assets": d,
                     "full": fire_number or 0.0, "lean": lean or 0.0,
                     "full_nominal": (fire_number or 0.0) * (1 + infl) ** k,
                     "pct": d / fire_number if fire_number else None, "milestone": label})

    return {
        "cf": cf, "age": age, "target_age": target_age, "inflation": infl, "swr": swr,
        "return_auto": ret_auto, "return_nominal": nominal, "return_is_auto": a.get("return_nominal") in (None, ""),
        "real": real, "debt": debt, "fire_gross": fire_gross, "assets": assets,
        "expense": expense, "essential": essential, "invest": invest,
        "fire_number": fire_number, "lean": lean, "coast": coast,
        "progress": assets / fire_number if fire_number else None,
        "lean_progress": assets / lean if lean else None,
        "passive_sustainable": passive_sust, "passive_declared": cf["passive"],
        "passive_ratio": (passive_sust + cf["passive"]) / expense if expense else None,
        "years_full": y_full, "years_lean": y_lean,
        "year_full": today.year + math.ceil(y_full) if y_full is not None else None,
        "age_full": age + math.ceil(y_full) if (y_full is not None and age) else None,
        "coast_reached": (assets >= coast) if coast else None,
        "coast_gap": (coast - assets) if coast else None,
        "emergency_value": em_value, "emergency_months": em_months, "emergency_target": em_target,
        "emergency_gap": (em_target - em_months) * cf["essential"] if em_months is not None and em_months < em_target else 0.0,
        "projection": proj,
    }


# ================================================================ snapshot & reminders
def snapshot(data: dict, h: dict, fp: dict, today: dt.date | None = None, note: str = "") -> dict:
    today = today or dt.date.today()
    return {"date": today.isoformat(), "total_assets": h["total_value"], "liabilities": fp["debt"],
            "net_worth": h["total_value"] - fp["debt"], "fire_assets": fp["assets"],
            "fire_number": fp["fire_number"], "fire_progress": fp["progress"],
            "savings_rate": fp["cf"]["savings_rate"], "note": note}


def needs_monthly_snapshot(snapshots: list[dict], today: dt.date | None = None) -> bool:
    today = today or dt.date.today()
    return not any(str(s["date"])[:7] == today.strftime("%Y-%m") for s in snapshots)


def reminders(data: dict, h: dict, fp: dict, today: dt.date | None = None) -> list[tuple[str, str]]:
    """Danh sách (mức độ, nội dung): 'error' | 'warning' | 'info'."""
    today = today or dt.date.today()
    out: list[tuple[str, str]] = []
    for r in h["rows"]:
        if r["warning"]:
            out.append(("warning", f"**{r['code']}**: {r['warning']} – cập nhật ở trang Giá."))
    for s in h["savings"]:
        if s["status"] == "Quá hạn xử lý":
            out.append(("error", f"Sổ **{s['name']}** đã đáo hạn {s['maturity_d']:%d/%m/%Y} – cần tất toán/tái tục."))
        elif s["status"] == "Sắp đáo hạn":
            out.append(("warning", f"Sổ **{s['name']}** sắp đáo hạn {s['maturity_d']:%d/%m/%Y} "
                                   f"({(s['maturity_d'] - today).days} ngày)."))
        if s["base"] and (n(s.get("start_balance")) - s["base"]) / s["base"] > 0.15:
            out.append(("info", f"Sổ **{s['name']}**: gửi đầu kỳ lớn hơn gốc + nạp thêm "
                                f"{(n(s.get('start_balance')) - s['base']) / s['base']:.0%} – kiểm tra cột Nạp thêm."))
        if s["code"] == "SF" and not s.get("goal"):
            out.append(("info", f"Sổ **{s['name']}** thuộc Sinking Fund nhưng chưa gán mục tiêu."))
    for g in h["goals"]:
        if g["status"] == "Quá hạn":
            out.append(("error", f"Mục tiêu **{g['name']}** đã quá hạn, còn thiếu {vnd(g['remaining'])}."))
        elif g["remaining"] > 0:
            out.append(("info", f"Mục tiêu **{g['name']}**: còn thiếu {vnd(g['remaining'])}, "
                                f"cần góp {vnd(g['need_monthly'])}/tháng."))
    pu = to_date(data["assumptions"].get("profile_updated"))
    if not pu:
        out.append(("warning", "Chưa có ngày rà soát hồ sơ thu chi – cập nhật ở trang Thu chi."))
    elif (today - pu).days > 90:
        out.append(("warning", f"Hồ sơ thu chi đã {(today - pu).days} ngày chưa rà soát (nên rà mỗi quý)."))
    if fp["cf"]["income"] and fp["cf"]["after_invest"] < 0:
        out.append(("warning", f"Cam kết đầu tư vượt dòng tiền dư {vnd(-fp['cf']['after_invest'])}/tháng."))
    if fp["emergency_gap"] > 0:
        out.append(("warning", f"Quỹ khẩn cấp đủ {fp['emergency_months']:.1f}/{fp['emergency_target']:.0f} tháng "
                               f"chi thiết yếu – thiếu {vnd(fp['emergency_gap'])}."))
    for t in data["transactions"]:
        if t.get("note") and "XÁC NHẬN" in str(t["note"]).upper():
            out.append(("info", f"Giao dịch {t['code']} ngày {to_date(t['date']):%d/%m/%Y}: {t['note']}"))
    return out


# ================================================================ hướng dẫn thiết lập từng bước
def onboarding(data: dict, fp: dict) -> list[dict]:
    """5 bước thiết lập lần đầu; mỗi bước tự đánh dấu xong dựa trên dữ liệu thật."""
    cf = fp["cf"]
    steps = [
        {"key": "thu_chi", "page": "thu_chi", "title": "Khai hồ sơ thu chi",
         "desc": "Thu nhập và chi tiêu <b>điển hình</b> theo tháng/quý/năm – chỉ khai 1 lần, rà soát mỗi quý.",
         "done": cf["income"] > 0 and cf["expense"] > 0},
        {"key": "ca_nhan", "page": "ke_hoach_fire", "title": "Thông tin cá nhân & mục tiêu",
         "desc": "Trang <b>Kế hoạch FIRE</b> → mở <b>Giả định</b>: tuổi hiện tại, tuổi muốn đạt FIRE.",
         "done": bool(n(data["assumptions"].get("current_age")))},
        {"key": "tai_san", "page": "tai_san", "title": "Chọn tài sản đầu tư",
         "desc": "Chọn quỹ, cổ phiếu, vàng từ danh mục – giá tự cập nhật hằng ngày.",
         "done": bool(data["assets"])},
        {"key": "dang_co", "page": "giao_dich", "title": "Khai tài sản đang có",
         "desc": "Đã mua từ trước? Chỉ cần <b>số lượng + giá vốn bình quân</b> (tab <b>Tài sản đang có</b>), "
                 "hoặc nhập giao dịch / sổ tiết kiệm đầu tiên.",
         "done": bool(data["transactions"] or data["savings"])},
    ]
    steps.append({"key": "ke_hoach", "page": "ke_hoach_fire", "title": "Xem kế hoạch FIRE",
                  "desc": "Số FIRE, tiến độ, năm dự kiến đạt và <b>sức khoẻ tài chính</b> của bạn.",
                  "done": bool(fp["fire_number"]) and all(s["done"] for s in steps)})
    return steps


# ================================================================ sức khoẻ tài chính
# Mốc tham khảo phổ biến trong tài chính cá nhân – không phải khuyến nghị. (tốt, tạm) theo chiều của chỉ số.
HEALTH_REF = {
    "savings_rate": (0.20, 0.10),       # ≥ 20% tốt · ≥ 10% tạm
    "essential_ratio": (0.50, 0.70),    # ≤ 50% tốt · ≤ 70% tạm
    "debt_ratio": (0.20, 0.35),         # ≤ 20% tốt · ≤ 35% tạm
    "invest_ratio": (0.15, 0.0),        # ≥ 15% tốt · > 0 tạm
    "emergency_min": 3.0,               # ≥ 3 tháng: tạm (đủ = mục tiêu trong Giả định)
}


def _grade(x: float, good: float, ok: float, higher_better: bool = True) -> str:
    if higher_better:
        return "good" if x >= good else ("warn" if (x > ok if ok == 0 else x >= ok) else "bad")
    return "good" if x <= good else ("warn" if x <= ok else "bad")


def health(data: dict, h: dict, fp: dict) -> list[dict]:
    """Các chỉ số 'nền móng' tài chính. status: good | warn | bad | na (thiếu dữ liệu)."""
    R, cf = HEALTH_REF, fp["cf"]
    inc = cf["income"]
    out: list[dict] = []

    def add(key, label, status, display, ref, hint="", page="thu_chi", value=None):
        out.append({"key": key, "label": label, "status": status, "display": display, "value": value,
                    "ref": ref, "hint": hint if status != "good" else "", "page": page})

    no_cf = "Chưa khai thu nhập ở trang Thu chi"
    # 1. Quỹ khẩn cấp
    code = data["assumptions"].get("emergency_code") or "QKC"
    tgt = fp["emergency_target"]
    ref = f"Đủ ≥ {tgt:.0f} tháng chi thiết yếu (mục tiêu trong Giả định)"
    if not any(r["code"] == code for r in h["rows"]):
        add("emergency", "Quỹ khẩn cấp", "na", "–", ref,
            f"Tạo một tài sản mã <b>{code}</b> (tiền gửi, quỹ trái phiếu…) dùng làm quỹ khẩn cấp ở trang Tài sản",
            "tai_san")
    elif fp["emergency_months"] is None:
        add("emergency", "Quỹ khẩn cấp", "na", "–", ref, "Khai khoản <b>Chi thiết yếu</b> ở trang Thu chi")
    else:
        m = fp["emergency_months"]
        st_ = "good" if m >= tgt else ("warn" if m >= R["emergency_min"] else "bad")
        add("emergency", "Quỹ khẩn cấp", st_, f"{m:.1f} tháng".replace(".", ","), ref,
            f"Còn thiếu {vnd(fp['emergency_gap'])} để đủ {tgt:.0f} tháng", "tai_san", m)

    if not inc:
        for key, label in (("savings_rate", "Tỷ lệ tiết kiệm"), ("essential_ratio", "Tỷ lệ chi thiết yếu"),
                           ("debt_ratio", "Trả nợ / thu nhập"), ("invest_ratio", "Đầu tư định kỳ / thu nhập")):
            add(key, label, "na", "–", "", no_cf)
    else:
        g, o = R["savings_rate"]
        x = cf["savings_rate"]
        add("savings_rate", "Tỷ lệ tiết kiệm", _grade(x, g, o), f"{x:.0%}",
            f"≥ {g:.0%} tốt · {o:.0%}–{g:.0%} tạm", "Rà lại chi linh hoạt ở trang Thu chi", value=x)
        g, o = R["essential_ratio"]
        x = cf["essential_ratio"]
        add("essential_ratio", "Tỷ lệ chi thiết yếu", _grade(x, g, o, False), f"{x:.0%}",
            f"≤ {g:.0%} tốt · {g:.0%}–{o:.0%} tạm", "Chi thiết yếu chiếm phần lớn thu nhập – xem lại các khoản cố định",
            value=x)
        g, o = R["debt_ratio"]
        pay = sum(n(l.get("monthly_payment")) for l in data["liabilities"])
        x = pay / inc
        add("debt_ratio", "Trả nợ / thu nhập", _grade(x, g, o, False),
            f"{x:.0%}" if data["liabilities"] else "Không có nợ",
            f"≤ {g:.0%} tốt · {g:.0%}–{o:.0%} tạm", "Ưu tiên trả bớt khoản nợ lãi cao (trang Tiết kiệm, Mục tiêu & Nợ)",
            "tiet_kiem", x)
        g, o = R["invest_ratio"]
        x = cf["invest"] / inc
        add("invest_ratio", "Đầu tư định kỳ / thu nhập", _grade(x, g, o), f"{x:.0%}",
            f"≥ {g:.0%} tốt · > 0% tạm", "Khai khoản <b>Đầu tư định kỳ</b> ở trang Thu chi", value=x)

    has_ins = any(a.get("type") == "Bảo hiểm" for a in data["assets"])
    add("insurance", "Bảo vệ rủi ro (bảo hiểm)", "good" if has_ins else "warn", "Đã có" if has_ins else "Chưa khai",
        "Có bảo hiểm sức khoẻ/nhân thọ phù hợp",
        "Cân nhắc bảo hiểm sức khoẻ/nhân thọ; nếu đã có, khai ở trang Tài sản (loại Bảo hiểm)", "tai_san")
    return out


# ================================================================ thành tựu (mốc để động viên)
FIRE_STEPS = (0.01, 0.05, 0.10, 0.25, 0.50, 0.75, 1.0)
STREAK_TARGET = 6


def _short(x: float) -> str:
    return (f"{x / 1e9:,.2f} tỷ" if abs(x) >= 1e9 else f"{x / 1e6:,.1f} tr").replace(".", ",")


def snapshot_streak(snapshots: list[dict], today: dt.date | None = None) -> int:
    """Số tháng Snapshot liên tiếp tính tới tháng này (tháng này chưa chụp thì tính tới tháng trước)."""
    today = today or dt.date.today()
    months = {str(s["date"])[:7] for s in snapshots}
    y, m = today.year, today.month
    if f"{y:04d}-{m:02d}" not in months:
        y, m = (y - 1, 12) if m == 1 else (y, m - 1)
    k = 0
    while f"{y:04d}-{m:02d}" in months:
        k += 1
        y, m = (y - 1, 12) if m == 1 else (y, m - 1)
    return k


def milestones(data: dict, h: dict, fp: dict, today: dt.date | None = None) -> list[dict]:
    """Các mốc theo thứ tự tăng dần trong từng nhóm. Mỗi mốc: key, group, reached, progress (0–1), gap (chuỗi)."""
    out: list[dict] = []

    def add(key, group, reached, progress=None, gap=""):
        out.append({"key": key, "group": group, "reached": bool(reached),
                    "progress": 1.0 if reached else max(0.0, min(1.0, progress or 0.0)), "gap": "" if reached else gap})

    steps = onboarding(data, fp)
    done = sum(s["done"] for s in steps)
    add("setup_cf", "Thiết lập", steps[0]["done"], 0, "Khai thu nhập và chi tiêu ở trang Thu chi")
    add("setup_asset", "Thiết lập", bool(data["assets"]), 0, "Thêm tài sản đầu tiên ở trang Tài sản")
    add("setup_done", "Thiết lập", done == len(steps), done / len(steps), f"Còn {len(steps) - done} bước thiết lập")

    target, assets = fp["fire_number"], fp["assets"]
    for p in FIRE_STEPS:
        reached = bool(target) and assets >= target * p
        gap = (f"Còn {_short(target * p - assets)} để chạm {p:.0%} Số FIRE" if target
               else "Khai thu chi để app tính Số FIRE")
        add(f"fire_{round(p * 100)}", "Hành trình FIRE", reached, (assets / (target * p)) if target else 0, gap)

    em, tgt = fp["emergency_months"], fp["emergency_target"]
    add("em_full", "Nền móng", em is not None and em >= tgt, (em or 0) / tgt if tgt else 0,
        f"Còn {_short(fp['emergency_gap'])} để quỹ khẩn cấp đủ {tgt:.0f} tháng" if em is not None
        else "Tạo tài sản quỹ khẩn cấp (mã QKC) và khai chi thiết yếu")
    sr = fp["cf"]["savings_rate"] if fp["cf"]["income"] else 0.0
    add("save_20", "Nền móng", fp["cf"]["income"] > 0 and sr >= 0.20, sr / 0.20,
        f"Tỷ lệ tiết kiệm hiện {sr:.0%}, mục tiêu 20%" if fp["cf"]["income"] else "Khai thu chi để tính tỷ lệ tiết kiệm")
    k = snapshot_streak(data["snapshots"], today)
    add("streak_6", "Nền móng", k >= STREAK_TARGET, k / STREAK_TARGET,
        f"Đã {k} tháng liên tiếp – còn {STREAK_TARGET - k} tháng")
    return out


def next_milestone(ms: list[dict]) -> dict | None:
    """Mốc chưa đạt gần nhất: ưu tiên thiết lập → hành trình FIRE → nền móng; trong nhóm lấy mốc đầu tiên."""
    return next((m for m in ms if not m["reached"]), None)


def new_milestones(ms: list[dict], seen: dict) -> list[dict]:
    """Mốc đã đạt nhưng chưa ghi nhận. Thứ tự: mốc 'cao nhất' (đứng sau cùng trong danh sách) lên đầu."""
    fresh = [m for m in ms if m["reached"] and m["key"] not in seen]
    rank = {"Hành trình FIRE": 0, "Thiết lập": 1, "Nền móng": 2}
    return sorted(fresh, key=lambda m: (rank[m["group"]], -ms.index(m)))


# ================================================================ ngân sách so với các quy tắc (bài học Thu chi)
def budget_check(cf: dict) -> dict | None:
    """Tỷ lệ theo hồ sơ thu chi để so với 50/30/20 và 'trả cho mình trước'. None khi chưa có thu nhập."""
    inc = cf["income"]
    if not inc:
        return None
    save = cf["invest"] + max(0.0, cf["after_invest"])
    return {"essential": cf["essential"] / inc, "flexible": cf["flexible"] / inc, "save": save / inc,
            "pay_first": cf["invest"] / inc,
            "buffer_low": cf["expense"] * 0.05, "buffer_high": cf["expense"] * 0.10}


# ================================================================ quỹ khẩn cấp (bài học Tiết kiệm)
HOUSEHOLDS = ("Độc thân", "Vợ chồng đều có thu nhập")
DEPENDENTS = ("Không ai", "1–2 người", "3–4 người")
EMERGENCY_MONTHS = {("Độc thân", "Không ai"): 6, ("Độc thân", "1–2 người"): 12, ("Độc thân", "3–4 người"): 18,
                    ("Vợ chồng đều có thu nhập", "Không ai"): 3, ("Vợ chồng đều có thu nhập", "1–2 người"): 6,
                    ("Vợ chồng đều có thu nhập", "3–4 người"): 12}
FREELANCE_EXTRA = 3            # thu nhập tự do / tự kinh doanh: gợi ý để thêm 3 tháng
LADDERS = {
    "50/50": [("Dài hạn (8–13 tháng)", .5), ("Ngắn hạn (2 tuần – 1 tháng)", .5)],
    "50/30/20": [("Dài hạn (8–13 tháng)", .5), ("Trung hạn (3–5 tháng)", .3), ("Ngắn hạn (1 tháng)", .2)],
    "40/30/20/10": [("Dài hạn (8–13 tháng)", .4), ("Trung hạn (3–5 tháng)", .3), ("Ngắn hạn (1 tháng)", .2),
                    ("Rút ngay / 2 tuần", .1)],
}


def emergency_plan(essential: float, current: float, household: str, dependents: str, freelance: bool,
                   monthly_save: float) -> dict:
    """Quỹ khẩn cấp gợi ý theo hoàn cảnh: số tháng, số tiền, còn thiếu, số tháng để đủ với mức để dành mỗi tháng."""
    months = EMERGENCY_MONTHS[(household, dependents)] + (FREELANCE_EXTRA if freelance else 0)
    target = months * essential
    gap = max(0.0, target - current)
    return {"months": months, "target": target, "current": current, "gap": gap,
            "progress": min(1.0, current / target) if target else None,
            "months_to_goal": (0 if gap == 0 else math.ceil(gap / monthly_save)) if monthly_save > 0 else None}


def ladder(amount: float, scheme: str) -> list[tuple[str, float, float]]:
    """Chia quỹ thành nhiều sổ: (kỳ hạn, tỷ lệ, số tiền)."""
    return [(lb, p, amount * p) for lb, p in LADDERS[scheme]]


# ================================================================ lô CCQ (mua trước bán trước)
FUND_TYPES = ("Quỹ mở cổ phiếu", "Quỹ mở trái phiếu", "ETF")


def fund_lots(txs: list[dict], book: PriceBook, code: str) -> dict:
    """Lô CCQ của 1 mã: mỗi lệnh mua là 1 lô; lệnh bán trừ vào lô cũ nhất trước (FIFO).

    txs: giao dịch đã qua derive_tx (h["transactions"]). Chỉ để xem – không đổi cách tính ở holdings().
    Trả về lots (mỗi lô: date, kind, qty, cost, remaining, remaining_cost, value, pnl, pct, pending)
    và sales (mỗi lần bán: date, qty, proceeds, cost, pnl, pct, sources=[(ngày lô, số CCQ)], short).
    """
    mine = sorted((t for t in txs if t["code"] == code), key=lambda t: (t["d"], n(t.get("id"))))
    price_date, price = book.latest(code)
    lots, sales = [], []
    for t in mine:
        typ = t["type"]
        if t.get("pending"):
            lots.append({"date": t["d"], "kind": "Chờ NAV", "qty": 0.0, "cost": n(t.get("amount")), "remaining": 0.0,
                         "pending": True, "price": None})
        elif typ in BUY_LIKE + ("Cổ tức CP/Thưởng",) and t["qty_calc"] > 0:
            cost = t["net_in"] if typ in BUY_LIKE else 0.0
            lots.append({"date": t["d"], "kind": {"Mua": "Mua", "Vốn đầu kỳ": "Vốn đầu kỳ"}.get(typ, "Thưởng"),
                         "qty": t["qty_calc"], "cost": cost, "remaining": t["qty_calc"], "pending": False,
                         "price": t["price_used"] or None})
        elif typ == "Bán" and t["qty_calc"] > 0:
            need, basis, sources = t["qty_calc"], 0.0, []
            for lot in lots:
                if need <= 1e-9:
                    break
                if lot["pending"] or lot["remaining"] <= 1e-9:
                    continue
                take = min(need, lot["remaining"])
                basis += take * lot["cost"] / lot["qty"]
                lot["remaining"] -= take
                need -= take
                sources.append((lot["date"], take))
            proceeds = t["value"] - n(t.get("fee")) - n(t.get("tax"))
            sales.append({"date": t["d"], "qty": t["qty_calc"], "price": t["price_used"], "proceeds": proceeds,
                          "cost": basis, "pnl": proceeds - basis, "pct": (proceeds - basis) / basis if basis else None,
                          "sources": sources, "short": need > 1e-9})
    for lot in lots:
        if lot["pending"]:
            lot.update(remaining_cost=lot["cost"], value=lot["cost"], pnl=0.0, pct=None)
            continue
        lot["remaining"] = trunc2(lot["remaining"] + 1e-9) if lot["remaining"] > 1e-9 else 0.0
        rc = lot["remaining"] * lot["cost"] / lot["qty"]
        val = lot["remaining"] * n(price)
        lot.update(remaining_cost=rc, value=val, pnl=val - rc, pct=(val - rc) / rc if rc else None)
    return {"code": code, "lots": lots, "sales": sales, "price": price, "price_date": price_date}


def monthly_lots(results: list[dict]) -> list[dict]:
    """Gộp lô theo (mã, năm, tháng) – giống bảng 'Tổng tiền đầu tư và lợi nhuận' theo tháng."""
    acc: dict[tuple, dict] = {}
    for res in results:
        for lot in res["lots"]:
            k = (res["code"], lot["date"].year, lot["date"].month)
            m = acc.setdefault(k, {"code": k[0], "year": k[1], "month": k[2], "cost": 0.0, "qty": 0.0,
                                   "remaining": 0.0, "remaining_cost": 0.0, "value": 0.0, "pending": 0.0})
            m["cost"] += lot["cost"]
            m["qty"] += lot["qty"]
            m["remaining"] += lot["remaining"]
            m["remaining_cost"] += lot["remaining_cost"]
            m["value"] += lot["value"]
            m["pending"] += lot["cost"] if lot["pending"] else 0.0
    out = []
    for m in sorted(acc.values(), key=lambda x: (x["year"], x["month"], x["code"])):
        m["pnl"] = m["value"] - m["remaining_cost"]
        m["pct"] = m["pnl"] / m["remaining_cost"] if m["remaining_cost"] else None
        out.append(m)
    return out

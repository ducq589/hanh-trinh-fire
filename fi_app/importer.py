"""Import dữ liệu từ Investment_tracking_v3.xlsx (CHỈ ĐỌC – không bao giờ ghi vào file Excel)."""
from __future__ import annotations

import datetime as dt
from pathlib import Path

import openpyxl

from . import db

V3_PATH = db.PROJECT_DIR / "Investment_tracking_v3.xlsx"


def _table(wb, name: str) -> list[dict]:
    for ws in wb.worksheets:
        if name in ws.tables:
            cells = list(ws[ws.tables[name].ref])
            header = [c.value for c in cells[0]]
            out = []
            for row in cells[1:]:
                rec = {h: c.value for h, c in zip(header, row)}
                if any(v not in (None, "") for v in rec.values()):
                    out.append(rec)
            return out
    raise KeyError(f"Không tìm thấy bảng {name} trong file Excel")


def _num(v):
    if v in (None, ""):
        return None
    try:
        return float(v)
    except (TypeError, ValueError):
        return None


def _date(v):
    if isinstance(v, (dt.datetime, dt.date)):
        return db._d(v)
    if isinstance(v, str) and v.strip():
        for fmt in ("%Y-%m-%d", "%d/%m/%Y"):
            try:
                return dt.datetime.strptime(v.strip()[:10], fmt).date().isoformat()
            except ValueError:
                pass
    return None


def _first_col(rec: dict, *names):
    for n in names:
        if n in rec:
            return rec[n]
    return None


def import_v3(store: db.Store, path=V3_PATH) -> dict:
    """Xoá dữ liệu hiện có (của người dùng hiện tại) và nạp lại toàn bộ từ v3.

    path: đường dẫn hoặc file-like (file tải lên). Trả về số dòng mỗi bảng."""
    raw = path.read() if hasattr(path, "read") else None
    src = (lambda: __import__("io").BytesIO(raw)) if raw is not None else (lambda: path)
    wb = openpyxl.load_workbook(src(), data_only=True, read_only=False)
    wf = openpyxl.load_workbook(src(), data_only=False, read_only=False)
    conn = store
    counts = {}
    with store.tx():
        for t in ("assets", "transactions", "prices", "savings", "goals", "liabilities", "cashflow_items", "snapshots"):
            conn.x(f"DELETE FROM {t}")

        for i, r in enumerate(_table(wb, "tblTaiSan")):
            fire = _first_col(r, "Tính FIRE?", "Tính FI?")
            conn.x(
                "INSERT INTO assets(code,name,type,tier,fire_include,exp_return,target_weight,valuation,unit,note,"
                "sort_order,price_source) VALUES (?,?,?,?,?,?,?,?,?,?,?,?)",
                (str(r["Mã"]).strip().upper(), r["Tên"], r["Loại"], r["Tầng"], 1 if fire == "Có" else 0,
                 _num(r["Lợi suất KV"]), _num(r["Tỷ lệ mục tiêu"]), r["Cách định giá"] or "Thị trường",
                 r.get("Đơn vị"), r.get("Ghi chú"), i,
                 db.DEFAULT_PRICE_SOURCE.get(r["Loại"]) if (r["Cách định giá"] or "Thị trường") == "Thị trường" else None))
        counts["assets"] = i + 1

        batch = [(_date(r["Ngày"]), str(r["Mã"]).strip().upper(), r["Loại GD"], _num(r["Số tiền"]), _num(r["Giá"]),
                  _num(r["Số lượng"]), _num(r["Phí"]), _num(r["Thuế"]), r.get("Ghi chú"))
                 for r in _table(wb, "tblGD") if r.get("Mã") and r.get("Ngày")]
        n = conn.many("INSERT INTO transactions(date,code,type,amount,price,qty,fee,tax,note) VALUES (?,?,?,?,?,?,?,?,?)",
                      batch)
        counts["transactions"] = n

        batch = []
        for tname, manual in (("tblGiaAuto", 0), ("tblGiaTay", 1)):
            for r in _table(wb, tname):
                d, code, p = _date(r.get("Ngày")), r.get("Mã"), _num(r.get("Giá"))
                if d and code and p:
                    batch.append((d, str(code).strip().upper(), p, r.get("Nguồn"), manual))
        n = conn.many("INSERT INTO prices(date,code,price,source,is_manual) VALUES (?,?,?,?,?) "
                      "ON CONFLICT(date, code, is_manual) DO UPDATE SET price=excluded.price, source=excluded.source",
                      batch)
        counts["prices"] = n

        n = 0
        for r in _table(wb, "tblSTK"):
            conn.x("INSERT INTO savings(name,code,goal,purpose,maturity,principal,topup,start_balance,interest_gross) "
                         "VALUES (?,?,?,?,?,?,?,?,?)",
                         (r["Gói"], r["Mã TS"], r.get("Mục tiêu"), r.get("Mục đích"), _date(r.get("Ngày đáo hạn")),
                          _num(r["Gốc"]), _num(r.get("Nạp thêm")), _num(r["Gửi đầu kỳ"]), _num(r["Lãi trước thuế"])))
            n += 1
        counts["savings"] = n

        n = 0
        for r in _table(wb, "tblMucTieu"):
            if r.get("Mục tiêu"):
                conn.x("INSERT INTO goals(name,target,due_date) VALUES (?,?,?)",
                             (r["Mục tiêu"], _num(r["Số tiền mục tiêu"]), _date(r.get("Ngày hoàn thành"))))
                n += 1
        counts["goals"] = n

        n = 0
        for r in _table(wb, "tblNo"):
            if r.get("Khoản nợ") or _num(r.get("Dư nợ")):
                conn.x("INSERT INTO liabilities(name,balance,rate,monthly_payment,end_date,note) VALUES (?,?,?,?,?,?)",
                             (r.get("Khoản nợ") or "Khoản nợ", _num(r.get("Dư nợ")), _num(r.get("Lãi suất/năm")),
                              _num(r.get("Trả hằng tháng")), _date(r.get("Ngày tất toán")), r.get("Ghi chú")))
                n += 1
        counts["liabilities"] = n

        n = 0
        for i, r in enumerate(_table(wb, "tblThuChi")):
            if r.get("Khoản mục") and r.get("Nhóm"):
                conn.x("INSERT INTO cashflow_items(name,grp,member,amount,freq,note,sort_order) VALUES (?,?,?,?,?,?,?)",
                             (r["Khoản mục"], r["Nhóm"], r.get("Thành viên"), _num(r.get("Số tiền")),
                              r.get("Tần suất") or "Tháng", r.get("Ghi chú"), i))
                n += 1
        counts["cashflow_items"] = n

        n = 0
        for r in _table(wb, "tblSnapshot"):
            d = _date(r.get("Ngày"))
            if d:
                conn.x("INSERT INTO snapshots(date,total_assets,liabilities,net_worth,fire_assets,"
                       "fire_number,fire_progress,savings_rate,note) VALUES (?,?,?,?,?,?,?,?,?) ON CONFLICT(date) DO NOTHING",
                             (d, _num(r.get("Tổng tài sản")), _num(r.get("Tổng nợ")), _num(r.get("Tài sản ròng")),
                              _num(_first_col(r, "Tài sản tính FIRE", "Tài sản tính FI")),
                              _num(_first_col(r, "Số FIRE", "Số FI")),
                              _num(_first_col(r, "% Full FIRE", "% Full FI")), _num(r.get("Tỷ lệ tiết kiệm")),
                              r.get("Ghi chú")))
                n += 1
        counts["snapshots"] = n

    # Giả định FIRE (FI_Plan B4:B10) – ô lợi suất danh nghĩa: nếu là công thức thì để "tự tính"
    fi_v, fi_f = wb["FI_Plan"], wf["FI_Plan"]
    ret_formula = isinstance(fi_f["B7"].value, str) and str(fi_f["B7"].value).startswith("=")
    prof = wb["Profile"]["B3"].value
    db.set_kv(conn, "assumptions", {
        "current_age": _num(fi_v["B4"].value) or "",
        "target_age": _num(fi_v["B5"].value) or 50,
        "inflation": _num(fi_v["B6"].value) or 0.035,
        "return_nominal": "" if ret_formula else (_num(fi_v["B7"].value) or ""),
        "swr": _num(fi_v["B9"].value) or 0.04,
        "emergency_months": _num(fi_v["B10"].value) or 6,
        "profile_updated": _date(prof) or "",
    })
    cd = wb["CaiDat"]
    db.set_kv(conn, "settings", {
        "tax_interest": _num(cd["B4"].value) if _num(cd["B4"].value) is not None else 0.05,
        "stale_days": _num(cd["B5"].value) or 7,
        "maturity_days": _num(cd["B6"].value) or 15,
    })
    db.set_kv(conn, "meta", {"imported_from": getattr(path, "name", str(path)).split("/")[-1], "imported_at": dt.datetime.now().isoformat(timespec="seconds")})
    return counts

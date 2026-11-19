"""Chuyển toàn bộ dữ liệu app trên máy (webapp/data/fi.db) lên Supabase cho MỘT tài khoản email.

Điều kiện: tài khoản email đã tồn tại trong Supabase (đã đăng nhập app cloud 1 lần, hoặc được
thêm ở Supabase ▸ Authentication ▸ Users ▸ Add user).

Chạy (từ thư mục webapp):
    .venv/bin/python scripts/len_cloud.py ban@example.com
Chuỗi kết nối lấy từ .streamlit/secrets.toml ([supabase] db_url) hoặc biến môi trường DATABASE_URL.

Dữ liệu cloud hiện có của tài khoản đó sẽ bị XOÁ và thay bằng dữ liệu trên máy (có hỏi xác nhận).
"""
import os
import sys
import tomllib
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

import psycopg  # noqa: E402

from fi_app import db  # noqa: E402

TABLES = {  # bảng → cột (không gồm id / user_id)
    "assets": ["code", "name", "type", "tier", "fire_include", "exp_return", "target_weight", "valuation", "unit",
               "note", "active", "sort_order", "price_source"],
    "transactions": ["date", "code", "type", "amount", "price", "qty", "fee", "tax", "note"],
    "prices": ["date", "code", "price", "source", "is_manual"],
    "savings": ["name", "code", "goal", "purpose", "maturity", "principal", "topup", "start_balance",
                "interest_gross", "note"],
    "goals": ["name", "target", "due_date"],
    "liabilities": ["name", "balance", "rate", "monthly_payment", "end_date", "note"],
    "cashflow_items": ["name", "grp", "member", "amount", "freq", "note", "sort_order"],
    "assumptions": ["key", "value"],
    "settings": ["key", "value"],
    "snapshots": ["date", "total_assets", "liabilities", "net_worth", "fire_assets", "fire_number", "fire_progress",
                  "savings_rate", "note"],
    "meta": ["key", "value"],
}


def dsn() -> str:
    if os.environ.get("DATABASE_URL"):
        return os.environ["DATABASE_URL"]
    sec = ROOT / ".streamlit" / "secrets.toml"
    if sec.exists():
        return tomllib.loads(sec.read_text())["supabase"]["db_url"]
    sys.exit("Không tìm thấy DATABASE_URL hoặc .streamlit/secrets.toml")


def main(email: str) -> None:
    url = dsn()
    with psycopg.connect(url, prepare_threshold=None) as c:
        row = c.execute("SELECT id FROM auth.users WHERE lower(email) = lower(%s)", (email,)).fetchone()
    if not row:
        sys.exit(f"Chưa có tài khoản {email} trên Supabase. Hãy đăng nhập app cloud 1 lần hoặc tạo ở "
                 "Authentication ▸ Users ▸ Add user.")
    uid = str(row[0])
    local = db.connect_local()
    counts = {t: len(local.q(f"SELECT 1 FROM {t}")) for t in TABLES}
    print("Dữ liệu trên máy:", ", ".join(f"{t} {n}" for t, n in counts.items()))
    if input(f"XOÁ dữ liệu cloud hiện có của {email} và thay bằng dữ liệu trên máy? Gõ 'co' để tiếp tục: ").strip() != "co":
        sys.exit("Đã huỷ.")
    cloud = db.connect_cloud(url, uid, email)
    with cloud.tx():
        for t, cols in TABLES.items():
            cloud.x(f"DELETE FROM {t}")
            rows = [tuple(r[c] for c in cols) for r in local.q(f"SELECT {', '.join(cols)} FROM {t}")]
            cloud.many(f"INSERT INTO {t}({', '.join(cols)}) VALUES ({', '.join('?' * len(cols))})", rows)
    market = [(r["symbol"], r["date"], r["price"], r["source"]) for r in local.q("SELECT * FROM market_prices")]
    cloud.market_upsert(market)
    check = {t: cloud.q(f"SELECT COUNT(*) AS n FROM {t}")[0]["n"] for t in TABLES}
    print("Đã chuyển lên cloud:", ", ".join(f"{t} {n}" for t, n in check.items()), f"| giá thị trường {len(market)}")
    bad = [t for t in TABLES if check[t] != counts[t]]
    if bad:
        sys.exit(f"CẢNH BÁO: số dòng không khớp ở {bad}")
    print("Hoàn tất – số dòng khớp 100%.")
    cloud.close(); local.close()


if __name__ == "__main__":
    if len(sys.argv) != 2:
        sys.exit("Cách dùng: .venv/bin/python scripts/len_cloud.py ban@example.com")
    main(sys.argv[1])

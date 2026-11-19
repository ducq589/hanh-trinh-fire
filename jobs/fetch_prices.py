"""Job lấy giá hằng ngày cho chế độ cloud (chạy bởi GitHub Actions – xem .github/workflows/fetch_prices.yml).

Đọc mọi nguồn giá (price_source) của mọi người dùng, lấy giá, ghi vào bảng market_prices dùng chung.
Biến môi trường: DATABASE_URL = chuỗi kết nối Postgres của Supabase (Session pooler).
Chạy thử trên máy:  DATABASE_URL="postgresql://..." .venv/bin/python jobs/fetch_prices.py
"""
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import psycopg  # noqa: E402
from psycopg.rows import dict_row  # noqa: E402

from fi_app import db, prices  # noqa: E402


def main() -> int:
    dsn = os.environ.get("DATABASE_URL")
    if not dsn:
        print("Thiếu biến môi trường DATABASE_URL", file=sys.stderr)
        return 2
    conn = psycopg.connect(dsn, row_factory=dict_row, autocommit=False, prepare_threshold=None, connect_timeout=20)
    store = db.Store("pg", conn)            # quyền hệ thống: đọc nguồn giá của mọi người dùng
    try:
        res = prices.fetch_auto(store)
    finally:
        store.close()
    print("\n".join(res["log"]))
    print(f"Đã lưu {res['saved']} giá.")
    failed = sum(1 for line in res["log"] if line.startswith("✗"))
    return 1 if failed and failed == len(res["log"]) else 0   # chỉ báo lỗi khi MỌI nguồn đều hỏng


if __name__ == "__main__":
    sys.exit(main())

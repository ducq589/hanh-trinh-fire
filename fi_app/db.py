"""Lớp lưu trữ: cùng một API cho 2 chế độ.

- **local**  : SQLite (`webapp/data/fi.db`) – chạy trên máy, 1 người dùng.
- **cloud**  : Postgres trên Supabase – nhiều người dùng. Mỗi bảng có cột `user_id`
               (mặc định = auth.uid()) và Row Level Security: phiên làm việc chạy với
               role `authenticated` + claims của người dùng đăng nhập, nên Postgres tự
               chặn mọi truy cập vào dữ liệu của người khác (xem supabase/schema.sql).

Code nghiệp vụ viết SQL kiểu SQLite (tham số `?`); Store tự chuyển sang Postgres.
Nhãn nghiệp vụ (Tầng, Loại GD…) giữ nguyên tiếng Việt như file Excel v3.
"""
from __future__ import annotations

import contextlib
import datetime as dt
import json
import re
import sqlite3
from pathlib import Path

APP_DIR = Path(__file__).resolve().parent.parent          # webapp/
PROJECT_DIR = APP_DIR.parent                              # thư mục dự án
DATA_DIR = APP_DIR / "data"
DB_PATH = DATA_DIR / "fi.db"
BACKUP_DIR = DATA_DIR / "backups"
EXPORT_DIR = APP_DIR / "xuat"

SQLITE_SCHEMA = """
CREATE TABLE IF NOT EXISTS assets (
    code TEXT PRIMARY KEY, name TEXT NOT NULL, type TEXT, tier TEXT NOT NULL,
    fire_include INTEGER NOT NULL DEFAULT 0, exp_return REAL, target_weight REAL,
    valuation TEXT NOT NULL DEFAULT 'Thị trường', unit TEXT, note TEXT,
    active INTEGER NOT NULL DEFAULT 1, sort_order INTEGER NOT NULL DEFAULT 0, price_source TEXT
);
CREATE TABLE IF NOT EXISTS transactions (
    id INTEGER PRIMARY KEY AUTOINCREMENT, date TEXT NOT NULL, code TEXT NOT NULL, type TEXT NOT NULL,
    amount REAL, price REAL, qty REAL, fee REAL, tax REAL, note TEXT,
    created_at TEXT DEFAULT (datetime('now','localtime'))
);
CREATE INDEX IF NOT EXISTS ix_tx_code_date ON transactions(code, date);
CREATE TABLE IF NOT EXISTS prices (
    date TEXT NOT NULL, code TEXT NOT NULL, price REAL NOT NULL, source TEXT,
    is_manual INTEGER NOT NULL DEFAULT 0, PRIMARY KEY (date, code, is_manual)
);
CREATE TABLE IF NOT EXISTS market_prices (
    symbol TEXT NOT NULL, date TEXT NOT NULL, price REAL NOT NULL, source TEXT,
    fetched_at TEXT, PRIMARY KEY (symbol, date)
);
CREATE TABLE IF NOT EXISTS savings (
    id INTEGER PRIMARY KEY AUTOINCREMENT, name TEXT NOT NULL, code TEXT NOT NULL, goal TEXT, purpose TEXT,
    maturity TEXT, principal REAL, topup REAL, start_balance REAL, interest_gross REAL, note TEXT
);
CREATE TABLE IF NOT EXISTS goals (
    id INTEGER PRIMARY KEY AUTOINCREMENT, name TEXT NOT NULL UNIQUE, target REAL, due_date TEXT
);
CREATE TABLE IF NOT EXISTS liabilities (
    id INTEGER PRIMARY KEY AUTOINCREMENT, name TEXT NOT NULL, balance REAL, rate REAL,
    monthly_payment REAL, end_date TEXT, note TEXT
);
CREATE TABLE IF NOT EXISTS cashflow_items (
    id INTEGER PRIMARY KEY AUTOINCREMENT, name TEXT NOT NULL, grp TEXT NOT NULL, member TEXT, amount REAL,
    freq TEXT NOT NULL DEFAULT 'Tháng', note TEXT, sort_order INTEGER NOT NULL DEFAULT 0
);
CREATE TABLE IF NOT EXISTS assumptions (key TEXT PRIMARY KEY, value TEXT);
CREATE TABLE IF NOT EXISTS settings (key TEXT PRIMARY KEY, value TEXT);
CREATE TABLE IF NOT EXISTS snapshots (
    date TEXT PRIMARY KEY, total_assets REAL, liabilities REAL, net_worth REAL, fire_assets REAL,
    fire_number REAL, fire_progress REAL, savings_rate REAL, note TEXT
);
CREATE TABLE IF NOT EXISTS meta (key TEXT PRIMARY KEY, value TEXT);
"""

DEFAULT_SETTINGS = {"tax_interest": "0.05", "stale_days": "7", "maturity_days": "15", "auto_fetch": "1"}
DEFAULT_ASSUMPTIONS = {
    "current_age": "", "target_age": "50", "inflation": "0.035", "return_nominal": "",
    "swr": "0.04", "emergency_months": "6", "profile_updated": "",
}
# Nguồn giá gợi ý khi import (xem fi_app/sources.py)
DEFAULT_PRICE_SOURCE = {"Quỹ mở cổ phiếu": "fmarket", "Quỹ mở trái phiếu": "fmarket", "Cổ phiếu": "vndirect",
                        "ETF": "vndirect"}
BENCHMARKS = {"VNINDEX": "vndirect_index:VNINDEX"}   # chỉ số so sánh, không phải tài sản

TIERS = ["Tăng trưởng", "Thu nhập", "Bảo vệ", "Phòng thủ"]
ASSET_TYPES = ["Quỹ mở cổ phiếu", "Quỹ mở trái phiếu", "Cổ phiếu", "ETF", "Tiết kiệm", "Vàng",
               "Bảo hiểm", "Bất động sản", "Tiền mặt", "Khác"]
VALUATIONS = ["Thị trường", "Khai báo", "Sổ tiết kiệm"]
TX_TYPES = ["Mua", "Bán", "Cổ tức TM", "Cổ tức CP/Thưởng", "Vốn đầu kỳ"]
CF_GROUPS = ["Thu nhập chủ động", "Thu nhập thụ động", "Chi thiết yếu", "Chi linh hoạt", "Đầu tư định kỳ"]
FREQS = ["Tháng", "Quý", "Năm"]

# Bảng thuộc về từng người dùng (cloud: có cột user_id + RLS)
USER_TABLES = ("assets", "transactions", "prices", "savings", "goals", "liabilities", "cashflow_items",
               "assumptions", "settings", "snapshots", "meta")
# Khoá ON CONFLICT: cloud thêm user_id vào trước
_CONFLICT_KEYS = {"(key)": "(user_id, key)", "(date, code, is_manual)": "(user_id, date, code, is_manual)",
                  "(date)": "(user_id, date)", "(code)": "(user_id, code)", "(name)": "(user_id, name)"}


# =====================================================================
class Store:
    """Kết nối + chuyển đổi SQL giữa SQLite và Postgres. kind = 'sqlite' | 'pg'."""

    def __init__(self, kind: str, conn, user_id: str | None = None, email: str | None = None):
        self.kind, self.conn, self.user_id, self.email = kind, conn, user_id, email
        self._depth = 0

    @property
    def is_cloud(self) -> bool:
        return self.kind == "pg"

    def _sql(self, sql: str) -> str:
        if self.kind != "pg":
            return sql
        sql = sql.replace("?", "%s")
        for k, v in _CONFLICT_KEYS.items():
            sql = re.sub(r"ON CONFLICT\s*" + re.escape(k), "ON CONFLICT" + v, sql, flags=re.I)
        return sql

    def q(self, sql: str, params=()) -> list[dict]:
        cur = self.conn.execute(self._sql(sql), params)
        rows = [dict(r) for r in cur.fetchall()]
        if self.kind == "pg" and self._depth == 0:
            self.conn.commit()          # không giữ giao dịch mở khi chỉ đọc
        return rows

    def one(self, sql: str, params=()):
        r = self.q(sql, params)
        return next(iter(r[0].values())) if r else None

    def x(self, sql: str, params=()) -> int:
        cur = self.conn.execute(self._sql(sql), params)
        if self._depth == 0:
            self.conn.commit()
        return cur.rowcount

    def many(self, sql: str, seq) -> int:
        seq = list(seq)
        if not seq:
            return 0
        if self.kind == "pg":
            with self.conn.cursor() as cur:
                cur.executemany(self._sql(sql), seq)
        else:
            self.conn.executemany(sql, seq)
        if self._depth == 0:
            self.conn.commit()
        return len(seq)

    def insert_id(self, sql: str, params=()) -> int:
        if self.kind == "pg":
            cur = self.conn.execute(self._sql(sql) + " RETURNING id", params)
            new_id = cur.fetchone()["id"]
        else:
            new_id = self.conn.execute(sql, params).lastrowid
        if self._depth == 0:
            self.conn.commit()
        return new_id

    @contextlib.contextmanager
    def tx(self):
        """Gom nhiều lệnh thành 1 giao dịch (rollback nếu lỗi)."""
        self._depth += 1
        try:
            yield self
            self._depth -= 1
            if self._depth == 0:
                self.conn.commit()
        except Exception:
            self._depth = 0
            self.conn.rollback()
            raise

    # ---- giá thị trường dùng chung: chỉ code lấy giá của app được ghi (cloud: tạm bỏ role authenticated)
    def market_upsert(self, rows: list[tuple]) -> int:
        """rows: (symbol, date_iso, price, source)."""
        if not rows:
            return 0
        now = dt.datetime.now().isoformat(timespec="seconds")
        sql = ("INSERT INTO market_prices(symbol, date, price, source, fetched_at) VALUES (?,?,?,?,?) "
               "ON CONFLICT(symbol, date) DO UPDATE SET price=excluded.price, source=excluded.source, "
               "fetched_at=excluded.fetched_at")
        elevated = self.kind == "pg" and self.user_id is not None
        with self.tx():
            if elevated:
                self.conn.execute("RESET ROLE")
            try:
                for r in rows:
                    self.conn.execute(self._sql(sql), (*r, now))
            finally:
                if elevated:
                    self._set_user_role()
        return len(rows)

    def _set_user_role(self):
        claims = json.dumps({"sub": self.user_id, "role": "authenticated", "email": self.email or ""})
        self.conn.execute("SELECT set_config('request.jwt.claims', %s, false), "
                          "set_config('request.jwt.claim.sub', %s, false)", (claims, self.user_id))
        self.conn.execute("SET ROLE authenticated")

    def close(self):
        with contextlib.suppress(Exception):
            self.conn.close()


# =====================================================================
def _init_defaults(store: Store) -> None:
    with store.tx():
        for k, v in DEFAULT_SETTINGS.items():
            store.x("INSERT INTO settings(key, value) VALUES (?, ?) ON CONFLICT(key) DO NOTHING", (k, v))
        for k, v in DEFAULT_ASSUMPTIONS.items():
            store.x("INSERT INTO assumptions(key, value) VALUES (?, ?) ON CONFLICT(key) DO NOTHING", (k, v))


def connect_local(path: Path = DB_PATH) -> Store:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(path, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    conn.executescript(SQLITE_SCHEMA)
    cols = {r[1] for r in conn.execute("PRAGMA table_info(assets)")}
    if "price_source" not in cols:            # nâng cấp DB tạo từ phiên bản trước + gán nguồn giá gợi ý
        conn.execute("ALTER TABLE assets ADD COLUMN price_source TEXT")
        for typ, src in DEFAULT_PRICE_SOURCE.items():
            conn.execute("UPDATE assets SET price_source = ? WHERE type = ? AND valuation = 'Thị trường'", (src, typ))
    conn.commit()
    store = Store("sqlite", conn)
    _init_defaults(store)
    return store


connect = connect_local  # tương thích code cũ


def connect_cloud(dsn: str, user_id: str, email: str | None = None) -> Store:
    import psycopg
    from psycopg.rows import dict_row
    conn = psycopg.connect(dsn, row_factory=dict_row, autocommit=False, prepare_threshold=None,
                           connect_timeout=15)
    store = Store("pg", conn, user_id=user_id, email=email)
    store._set_user_role()
    conn.commit()
    _init_defaults(store)
    return store


# =====================================================================
def is_empty(s: Store) -> bool:
    return (s.one("SELECT COUNT(*) AS n FROM assets") or 0) == 0


def rows(s: Store, sql: str, params=()) -> list[dict]:
    return s.q(sql, params)


def kv(s: Store, table: str) -> dict[str, str]:
    return {r["key"]: r["value"] for r in s.q(f"SELECT key, value FROM {table}")}


def set_kv(s: Store, table: str, values: dict) -> None:
    with s.tx():
        for k, v in values.items():
            s.x(f"INSERT INTO {table}(key, value) VALUES (?, ?) "
                "ON CONFLICT(key) DO UPDATE SET value = excluded.value", (k, "" if v is None else str(v)))


def asset_symbol(a: dict) -> str | None:
    """Khoá giá thị trường của tài sản, VD 'fmarket:DCDS' (chuẩn hoá từ price_source)."""
    from .sources import parse_spec
    spec = parse_spec(a.get("price_source"), a["code"])
    return ":".join([spec[0], *[x.upper() for x in spec[1]]]) if spec else None


def load_all(s: Store) -> dict:
    assets = s.q("SELECT * FROM assets ORDER BY sort_order, code")
    user_prices = s.q("SELECT date, code, price, source, is_manual FROM prices")
    # Giá thị trường dùng chung → gán vào mã tài sản; ưu tiên thấp nhất (is_manual = -1)
    sym_to_codes: dict[str, list[str]] = {}
    for a in assets:
        sym = asset_symbol(a)
        if sym:
            sym_to_codes.setdefault(sym, []).append(a["code"])
    for code, spec in BENCHMARKS.items():
        sym_to_codes.setdefault(asset_symbol({"code": code, "price_source": spec}), []).append(code)
    market = []
    if sym_to_codes:
        marks = ",".join("?" * len(sym_to_codes))
        for r in s.q(f"SELECT symbol, date, price, source FROM market_prices WHERE symbol IN ({marks})",
                     tuple(sym_to_codes)):
            for code in sym_to_codes[r["symbol"]]:
                market.append({"date": r["date"], "code": code, "price": r["price"], "source": r["source"],
                               "is_manual": -1})
    return {
        "assets": assets,
        "transactions": s.q("SELECT * FROM transactions ORDER BY date, id"),
        "prices": user_prices + market,
        "savings": s.q("SELECT * FROM savings ORDER BY id"),
        "goals": s.q("SELECT * FROM goals ORDER BY id"),
        "liabilities": s.q("SELECT * FROM liabilities ORDER BY id"),
        "cashflow": s.q("SELECT * FROM cashflow_items ORDER BY sort_order, id"),
        "assumptions": kv(s, "assumptions"),
        "settings": kv(s, "settings"),
        "snapshots": s.q("SELECT * FROM snapshots ORDER BY date"),
    }


# ---------------------------------------------------------------- writes
def add_transaction(s: Store, date, code, type_, amount=None, price=None, qty=None, fee=None, tax=None,
                    note=None) -> int:
    return s.insert_id("INSERT INTO transactions(date, code, type, amount, price, qty, fee, tax, note) "
                       "VALUES (?,?,?,?,?,?,?,?,?)", (_d(date), code, type_, amount, price, qty, fee, tax, note))


def upsert_price(s: Store, date, code, price, source="", is_manual=1) -> None:
    s.x("INSERT INTO prices(date, code, price, source, is_manual) VALUES (?,?,?,?,?) "
        "ON CONFLICT(date, code, is_manual) DO UPDATE SET price = excluded.price, source = excluded.source",
        (_d(date), code, float(price), source, int(is_manual)))


def save_snapshot(s: Store, snap: dict) -> None:
    cols = ["date", "total_assets", "liabilities", "net_worth", "fire_assets", "fire_number",
            "fire_progress", "savings_rate", "note"]
    s.x(f"INSERT INTO snapshots({','.join(cols)}) VALUES ({','.join('?' * len(cols))}) "
        "ON CONFLICT(date) DO UPDATE SET " + ",".join(f"{c}=excluded.{c}" for c in cols[1:]),
        [snap.get(c) for c in cols])


def _d(v) -> str | None:
    if v is None or v == "":
        return None
    if isinstance(v, dt.datetime):
        return v.date().isoformat()
    if isinstance(v, dt.date):
        return v.isoformat()
    return str(v)[:10]


# ---------------------------------------------------------------- backup (chỉ chế độ local)
def backup(store: Store | None = None, tag: str = "") -> Path:
    BACKUP_DIR.mkdir(parents=True, exist_ok=True)
    stamp = dt.datetime.now().strftime("%Y%m%d_%H%M%S")
    dest = BACKUP_DIR / f"fi_{stamp}{('_' + tag) if tag else ''}.db"
    src = sqlite3.connect(DB_PATH)
    dst = sqlite3.connect(dest)
    with dst:
        src.backup(dst)
    src.close(); dst.close()
    return dest


def daily_backup(keep: int = 30) -> Path | None:
    """Sao lưu tự động 1 lần/ngày; giữ `keep` bản gần nhất."""
    if not DB_PATH.exists():
        return None
    BACKUP_DIR.mkdir(parents=True, exist_ok=True)
    today = dt.date.today().strftime("%Y%m%d")
    if any(p.name.startswith(f"fi_{today}") for p in BACKUP_DIR.glob("fi_*.db")):
        return None
    dest = backup(tag="auto")
    for old in sorted(BACKUP_DIR.glob("fi_*_auto.db"))[:-keep]:
        old.unlink(missing_ok=True)
    return dest


def list_backups() -> list[Path]:
    return sorted(BACKUP_DIR.glob("fi_*.db"), reverse=True) if BACKUP_DIR.exists() else []


def restore(path: Path) -> None:
    """Khôi phục từ bản sao lưu (tự sao lưu dữ liệu hiện tại trước)."""
    backup(tag="truoc_khoi_phuc")
    src = sqlite3.connect(path)
    dst = sqlite3.connect(DB_PATH)
    with dst:
        src.backup(dst)
    src.close(); dst.close()

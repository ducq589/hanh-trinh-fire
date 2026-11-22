"""Giữ app trên Streamlit Community Cloud luôn thức (GitHub Actions chạy 6 giờ/lần).

Streamlit Cloud cho app ngủ sau 12 giờ không có ai truy cập. Script mở app bằng Chromium chạy ngầm;
nếu app đã ngủ thì bấm nút đánh thức; chờ app hiện ra rồi giữ trang mở một lúc để được tính là có truy cập.
Không đăng nhập, không bấm gì trong app, không gửi dữ liệu nào.

Chạy:  python scripts/giu_app_thuc.py          (cần: pip install playwright && playwright install chromium)
Biến môi trường: APP_URL (mặc định https://fire-travel.streamlit.app)
"""
from __future__ import annotations

import os
import sys
import time

from playwright.sync_api import TimeoutError as PWTimeout
from playwright.sync_api import sync_playwright

APP_URL = os.environ.get("APP_URL", "https://fire-travel.streamlit.app").rstrip("/")
WAKE_TEXT = "get this app back up"   # nút trên trang "app đang ngủ" của Streamlit Cloud
WAIT_APP_MS = 180_000                # chờ app khởi động tối đa 3 phút
STAY_S = 20                          # giữ trang mở để Streamlit ghi nhận truy cập


def app_ready(page) -> bool:
    """App đã hiện: có nội dung Streamlit trong iframe của Cloud (hoặc ngay trên trang khi chạy ngoài Cloud)."""
    for frame in page.frames:
        try:
            if frame.locator('[data-testid="stApp"]').count() and frame.locator(
                    '[data-testid="stMain"], [data-testid="stAppViewContainer"]').count():
                return True
        except Exception:  # noqa: BLE001 – frame đang tải lại
            continue
    return False


def wait_ready(page, timeout_ms: int) -> bool:
    end = time.monotonic() + timeout_ms / 1000
    while time.monotonic() < end:
        if app_ready(page):
            return True
        page.wait_for_timeout(2000)
    return False


def main() -> int:
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()
        page.goto(APP_URL, wait_until="domcontentloaded", timeout=60_000)
        page.wait_for_timeout(5000)

        status = "app đang thức"
        wake = page.get_by_role("button", name=WAKE_TEXT, exact=False)
        try:
            if wake.count():
                wake.first.click(timeout=10_000)
                status = "đã đánh thức app"
                print("App đang ngủ – đã bấm nút đánh thức, chờ khởi động…", flush=True)
        except PWTimeout:
            pass

        if not wait_ready(page, WAIT_APP_MS):
            print(f"KHÔNG mở được app tại {APP_URL} sau {WAIT_APP_MS // 1000} giây.", file=sys.stderr)
            browser.close()
            return 1

        page.wait_for_timeout(STAY_S * 1000)
        browser.close()
    print(f"OK – {status}: {APP_URL}")
    return 0


if __name__ == "__main__":
    sys.exit(main())

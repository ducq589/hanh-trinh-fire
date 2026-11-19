# Hành trình FIRE

Webapp theo dõi tài sản tích sản và kế hoạch FIRE (Financial Independence, Retire Early).
Streamlit + SQLite (chạy trên máy) hoặc Supabase Postgres (cloud, đăng nhập email, nhiều người dùng, Row Level Security).

- `app.py`, `views/` – giao diện
- `fi_app/engine.py` – lõi tính toán (XIRR, tháp tài sản, tái cân bằng, Lean/Coast/Full FIRE)
- `fi_app/sources.py` – lấy giá tự động (Fmarket, VNDirect, PNJ)
- `supabase/schema.sql` – schema + RLS cho Supabase
- `jobs/fetch_prices.py` + `.github/workflows/fetch_prices.yml` – job lấy giá hằng ngày
- `scripts/len_cloud.py` – chuyển dữ liệu từ máy lên Supabase
- `tests/` – `python -m pytest tests -q`

Không có dữ liệu cá nhân trong repo (xem `.gitignore`). Công cụ lập kế hoạch cá nhân, không phải tư vấn đầu tư.

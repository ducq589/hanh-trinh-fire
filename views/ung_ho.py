"""Trang Ủng hộ tác giả (chỉ có trong menu khi secrets có mục [donate])."""
import streamlit as st

from fi_app import donate, intro, style

intro.css()
style.title("heart", "Ủng hộ tác giả", "Hoàn toàn tự nguyện – app vẫn miễn phí đầy đủ tính năng")
if donate.cfg():
    donate.render(heading=False)
else:
    st.info("Tính năng ủng hộ chưa được bật.")
st.caption("Khoản ủng hộ giúp trả chi phí máy chủ, cơ sở dữ liệu và thời gian phát triển thêm bài học, tính năng mới. "
           "Xem điều khoản ở trang **Điều khoản sử dụng** (mục Ủng hộ tự nguyện).")

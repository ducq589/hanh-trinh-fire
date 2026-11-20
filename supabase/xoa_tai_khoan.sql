-- Hành trình FIRE – cho người dùng tự xoá tài khoản ngay trong app (App Store 5.1.1(v), Google Play).
-- Chạy MỘT LẦN: Supabase → SQL Editor → New query → dán toàn bộ file này → Run.
--
-- Hàm chỉ xoá CHÍNH người đang đăng nhập (auth.uid()). Mọi bảng dữ liệu có
-- "references auth.users(id) on delete cascade" nên toàn bộ dữ liệu của người đó bị xoá theo.
-- Không cần (và không dùng) service key trong app.

create or replace function public.delete_my_account() returns void
language plpgsql security definer set search_path = '' as $$
begin
  if auth.uid() is null then
    raise exception 'not authenticated';
  end if;
  delete from auth.users where id = auth.uid();
end $$;

revoke all on function public.delete_my_account() from public, anon;
grant execute on function public.delete_my_account() to authenticated;

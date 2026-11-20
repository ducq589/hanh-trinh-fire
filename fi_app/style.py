"""Giao diện: nền tối, thẻ bo tròn, điểm nhấn xanh chanh (theo mẫu dashboard). Màu gốc ở .streamlit/config.toml."""
from __future__ import annotations

import html
from urllib.parse import quote

import plotly.graph_objects as go
import streamlit as st

from .icons import ICONS

LIME = "#B6F36A"
CARD = "#242424"
MUTED = "#9A9A9A"
TEXT = "#F2F2F2"
GRID = "#2E2E2E"
TIER_COLORS = {"Tăng trưởng": "#B6F36A", "Thu nhập": "#5DC23A", "Bảo vệ": "#2F7A2A", "Phòng thủ": "#E8F9D2"}
SERIES = ["#B6F36A", "#5DC23A", "#E8F9D2", "#2F7A2A", "#8FD96B", "#4C9F38"]
TARGET_FULL = "#FF9F68"     # đường mục tiêu Full FIRE
TARGET_LEAN = "#FFD166"     # đường mục tiêu Lean FIRE

_CSS = f"""
<style>
/* ---- khung chung ---- */
.block-container {{ padding-top: 4.6rem; max-width: 1280px; }}
.st-key-fire_auth_bridge_box {{ display: none; }}
h1, h2, h3 {{ letter-spacing: -0.01em; }}
[data-testid="stCaptionContainer"], .stCaption {{ color: {MUTED} !important; }}

/* ---- thẻ: mọi container có viền (st.container(border=True)) ---- */
[data-testid="stVerticalBlockBorderWrapper"]:has(> div > [data-testid="stVerticalBlock"]) {{
  background: {CARD}; border: 1px solid #2C2C2C !important; border-radius: 20px !important;
}}
[data-testid="stExpander"] details {{ background: {CARD}; border: 1px solid #2C2C2C; border-radius: 18px; }}

/* ---- chỉ số (st.metric) dạng thẻ ---- */
[data-testid="stMetric"] {{ background: {CARD}; border: 1px solid #2C2C2C; border-radius: 18px; padding: 16px 20px; }}
[data-testid="stMetricLabel"] p {{ color: {MUTED}; font-size: .86rem; }}

/* ---- nút: chữ tối trên nền xanh chanh ---- */
button[kind="primary"], button[data-testid="stBaseButton-primary"],
button[data-testid="stBaseButton-primaryFormSubmit"] {{ color: #111 !important; font-weight: 600; }}

/* ---- thanh bên ---- */
[data-testid="stSidebarNav"] a[aria-current="page"] {{ background: {LIME} !important; border-radius: 999px; }}
[data-testid="stSidebarNav"] a[aria-current="page"] span {{ color: #111 !important; font-weight: 600; }}
[data-testid="stSidebarNav"] a {{ border-radius: 999px; }}
[data-testid="stSidebarNavSeparator"] {{ border-color: #2A2A2A; }}

/* ---- thẻ KPI tự vẽ ---- */
.kpi {{ background: {CARD}; border: 1px solid #2C2C2C; border-radius: 20px; padding: 18px 22px; min-height: 150px;
        box-sizing: border-box; }}
.kpi .lb {{ color: {MUTED}; font-size: .9rem; margin-bottom: 6px; }}
.kpi .v {{ font-size: 2rem; font-weight: 700; line-height: 1.15; color: {TEXT}; }}
.kpi .v.lime {{ color: {LIME}; }}
.kpi .sub {{ color: {MUTED}; font-size: .8rem; margin-top: 6px; }}
.kpi .up {{ color: {LIME}; }} .kpi .down {{ color: #FF7A6B; }}
.kpi .bar {{ height: 8px; background: #333; border-radius: 99px; margin-top: 10px; overflow: hidden; }}
.kpi .bar > div {{ height: 100%; background: {LIME}; border-radius: 99px; }}

/* ---- chào hỏi + danh sách chú thích ---- */
.hello {{ display:flex; align-items:center; gap:12px; margin: 4px 0 14px; }}
.hello .av {{ width:42px; height:42px; border-radius:50%; background:{LIME}; color:#111; display:flex;
             align-items:center; justify-content:center; font-weight:700; font-size:1.1rem; }}
.hello .t1 {{ color:{MUTED}; font-size:.8rem; }} .hello .t2 {{ color:{TEXT}; font-weight:600; font-size:.95rem; }}
.legend {{ list-style:none; padding:0; margin:0; }}
.legend li {{ display:flex; align-items:center; gap:10px; padding:7px 0; color:#DADADA; font-size:.9rem; }}
.legend .dot {{ width:10px; height:10px; border-radius:50%; flex:none; }}
.legend .val {{ margin-left:auto; color:{MUTED}; font-variant-numeric: tabular-nums; }}
.big-total .lb {{ color:{MUTED}; font-size:.85rem; }} .big-total .v {{ color:{LIME}; font-size:1.7rem; font-weight:700; }}
.pill {{ display:inline-block; background:#1C1C1C; border:1px solid #333; color:#DADADA; border-radius:999px;
        padding:3px 12px; font-size:.78rem; }}
/* ---- tiêu đề trang + icon ---- */
.pt {{ display:flex; align-items:center; gap:14px; margin: 0 0 4px; }}
.pt h1 {{ margin:0; padding:0; font-size:2.2rem; font-weight:700; color:{TEXT}; line-height:1.2; }}
.pt-ic {{ width:46px; height:46px; border-radius:14px; background:{LIME}; display:flex; align-items:center;
          justify-content:center; flex:none; }}
.pt-cap {{ color:{MUTED}; font-size:.88rem; margin: 2px 0 14px; }}
.kpi {{ position:relative; }}
.kpi .ki {{ position:absolute; top:14px; right:14px; width:34px; height:34px; border-radius:50%; background:#1C1C1C;
           border:1px solid #333; display:flex; align-items:center; justify-content:center; }}
.kpi .ki.lime {{ background:{LIME}; border-color:{LIME}; }}
@media (max-width: 640px) {{ .pt h1 {{ font-size:1.5rem; }} .pt-ic {{ width:38px; height:38px; border-radius:12px; }}
  .kpi .ki {{ width:28px; height:28px; top:10px; right:10px; }} }}

/* ---- các bước hướng dẫn ---- */
.steps {{ display:flex; flex-direction:column; gap:10px; }}
.step {{ display:flex; gap:14px; align-items:flex-start; background:{CARD}; border:1px solid #2C2C2C;
        border-radius:16px; padding:14px 16px; }}
.step .n {{ flex:none; width:30px; height:30px; border-radius:50%; background:{LIME}; color:#111;
           font-weight:700; display:flex; align-items:center; justify-content:center; }}
.step .t {{ font-weight:600; color:{TEXT}; margin-bottom:2px; }}
.step .d {{ color:#BDBDBD; font-size:.9rem; line-height:1.5; }}
.step .d b {{ color:{LIME}; font-weight:600; }}
/* ---- tiến độ thiết lập ---- */
.step.done {{ opacity:.6; }} .step.done .n {{ background:#2F7A2A; color:{TEXT}; }}
.step.next {{ border-color:{LIME}; box-shadow:0 0 0 1px {LIME} inset; }}
.step.todo .n {{ background:#1C1C1C; color:{MUTED}; border:1px solid #3A3A3A; }}
.obar {{ display:flex; align-items:center; gap:12px; margin:2px 0 12px; color:{MUTED}; font-size:.88rem; }}
.obar .track {{ flex:1; height:8px; background:#333; border-radius:99px; overflow:hidden; }}
.obar .track > div {{ height:100%; background:{LIME}; border-radius:99px; }}
/* ---- sức khoẻ tài chính ---- */
.hgrid {{ display:grid; grid-template-columns:repeat(3,minmax(0,1fr)); gap:12px; }}
@media (max-width: 900px) {{ .hgrid {{ grid-template-columns:repeat(2,minmax(0,1fr)); }} }}
@media (max-width: 560px) {{ .hgrid {{ grid-template-columns:1fr; }} }}
.hc {{ background:{CARD}; border:1px solid #2C2C2C; border-left:4px solid #555; border-radius:16px; padding:14px 16px; }}
.hc.good {{ border-left-color:{LIME}; }} .hc.warn {{ border-left-color:{TARGET_LEAN}; }}
.hc.bad {{ border-left-color:#FF7A6B; }} .hc.na {{ border-left-color:#555; }}
.hc .top {{ display:flex; flex-wrap:wrap; justify-content:space-between; align-items:center; gap:4px 8px; }}
.hc .lb {{ color:{MUTED}; font-size:.88rem; }}
.hc .tag {{ font-size:.72rem; border-radius:999px; padding:2px 10px; font-weight:600; white-space:nowrap; }}
.hc.good .tag {{ background:rgba(182,243,106,.15); color:{LIME}; }}
.hc.warn .tag {{ background:rgba(255,209,102,.15); color:{TARGET_LEAN}; }}
.hc.bad .tag {{ background:rgba(255,122,107,.15); color:#FF7A6B; }}
.hc.na .tag {{ background:#1C1C1C; color:{MUTED}; }}
.hc .v {{ font-size:1.5rem; font-weight:700; color:{TEXT}; margin:6px 0 2px; }}
.hc .ref {{ color:{MUTED}; font-size:.78rem; }}
.hc .hint {{ color:#DADADA; font-size:.84rem; margin-top:8px; line-height:1.45; }}
.hc .hint b {{ color:{LIME}; font-weight:600; }}
/* ---- thành tựu ---- */
.cele {{ display:flex; gap:16px; align-items:center; background:linear-gradient(120deg,rgba(182,243,106,.18),rgba(182,243,106,.04));
        border:1px solid {LIME}; border-radius:20px; padding:16px 20px; }}
.cele .ico {{ flex:none; width:52px; height:52px; border-radius:16px; background:{LIME}; display:flex;
             align-items:center; justify-content:center; }}
.cele .k {{ color:{LIME}; font-size:.78rem; font-weight:700; letter-spacing:.04em; text-transform:uppercase; }}
.cele .t {{ color:{TEXT}; font-size:1.25rem; font-weight:700; margin:2px 0; }}
.cele .m {{ color:#DDF5BF; font-size:.95rem; line-height:1.5; }}
.cele .also {{ color:{MUTED}; font-size:.82rem; margin-top:6px; }}
.badges {{ display:flex; flex-wrap:wrap; gap:8px; margin:4px 0 6px; }}
.badge {{ display:inline-flex; align-items:center; gap:6px; border-radius:999px; padding:5px 12px; font-size:.8rem;
         border:1px solid #333; background:#1C1C1C; color:#6E6E6E; }}
.badge.on {{ background:rgba(182,243,106,.12); border-color:rgba(182,243,106,.45); color:{LIME}; font-weight:600; }}
.badge .dt {{ color:{MUTED}; font-weight:400; font-size:.72rem; }}
.bgroup {{ color:{MUTED}; font-size:.8rem; margin-top:8px; }}
.hc.next {{ border-left-color:{LIME}; }} .hc.next .v {{ font-size:1.15rem; }}
.hc .bar {{ height:8px; background:#333; border-radius:99px; margin:8px 0 6px; overflow:hidden; }}
.hc .bar > div {{ height:100%; background:{LIME}; border-radius:99px; }}
.tip {{ background:rgba(182,243,106,.08); border:1px solid rgba(182,243,106,.25); color:#DDF5BF;
       border-radius:14px; padding:10px 14px; font-size:.88rem; margin:8px 0; }}
.cal {{ display:grid; grid-template-columns: repeat(4, minmax(0,1fr)); gap:12px; }}
.cal .c {{ background:{CARD}; border:1px solid #2C2C2C; border-radius:16px; padding:14px; }}
.cal .h {{ color:{LIME}; font-weight:700; margin-bottom:6px; }}
.cal ul {{ margin:0; padding-left:18px; color:#CFCFCF; font-size:.88rem; line-height:1.6; }}
@media (max-width: 900px) {{ .cal {{ grid-template-columns: repeat(2, minmax(0,1fr)); }} }}

/* ---- nút liên kết (st.page_link) dạng viên thuốc ---- */
[data-testid="stPageLink"] a {{ background: #1C1C1C; border: 1px solid #333; border-radius: 999px;
  justify-content: center; padding: 6px 14px; }}
[data-testid="stPageLink"] a:hover {{ border-color: {LIME}; }}
[data-testid="stPageLink"] a p {{ color: {LIME} !important; font-weight: 600; }}
.kpis {{ display:grid; grid-template-columns: repeat(4, minmax(0,1fr)); gap: 14px; margin-bottom: 6px; }}
.kpis .kpi {{ min-height: 0; }}
@media (max-width: 900px) {{ .kpis {{ grid-template-columns: repeat(2, minmax(0,1fr)); }} }}
@media (max-width: 640px) {{
  .block-container {{ padding-top: 3.8rem; }}
  h1 {{ font-size: 1.7rem !important; }} h2, h3 {{ font-size: 1.25rem !important; }}
  .kpis {{ gap: 10px; }} .kpi {{ padding: 14px 14px; border-radius: 16px; }}
  .kpi .v {{ font-size: 1.35rem; }} .kpi .lb {{ font-size: .78rem; }} .kpi .sub {{ font-size: .72rem; }}
}}
</style>
"""


# ---------------------------------------------------------------- icon Tabler
# Trang (đường dẫn URL) → icon ở menu thanh bên
NAV_ICONS = {"": "home", "ke_hoach_fire": "flame", "lich_su": "chart-line", "giao_dich": "receipt",
             "gia": "chart-candle", "tai_san": "briefcase", "tiet_kiem": "building-bank", "thu_chi": "cash",
             "gioi_thieu": "info-circle", "huong_dan": "book", "ung_ho": "heart", "sao_luu": "settings"}


def svg(name: str, size: int = 18, color: str = "currentColor", stroke: float = 2, cls: str = "") -> str:
    """Icon Tabler chèn vào HTML (st.html lọc bỏ thẻ <svg>, nên vẽ bằng CSS mask từ biến --ti-<tên>)."""
    assert name in ICONS, name
    return (f'<span class="tic ti-{name} {cls}" style="width:{size}px;height:{size}px;color:{color}" '
            f'aria-hidden="true"></span>')


def _var(name: str) -> str:
    return "--ti-" + name


_MASK_BASE = ("content:'';display:inline-block;width:1.15em;height:1.15em;margin-right:.45em;vertical-align:-.2em;"
              "background-color:currentColor;-webkit-mask-repeat:no-repeat;mask-repeat:no-repeat;"
              "-webkit-mask-position:center;mask-position:center;-webkit-mask-size:contain;mask-size:contain;")


def _mask(name: str) -> str:
    return f"-webkit-mask-image:var({_var(name)});mask-image:var({_var(name)});"


def _icon_css() -> str:
    defs = []
    for name, inner in ICONS.items():
        raw = (f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="black" '
               f'stroke-width="2" stroke-linecap="round" stroke-linejoin="round">{inner}</svg>')
        defs.append(f'{_var(name)}:url("data:image/svg+xml,{quote(raw)}");')
    rules = [":root{" + "".join(defs) + "}"]
    rules.append(".tic{display:inline-block;flex:none;vertical-align:-.2em;background-color:currentColor;"
                 "-webkit-mask-repeat:no-repeat;mask-repeat:no-repeat;-webkit-mask-position:center;"
                 "mask-position:center;-webkit-mask-size:contain;mask-size:contain;}")
    for name in ICONS:
        rules.append(f".ti-{name}{{{_mask(name)}}}")
    nav = 'a[data-testid="stSidebarNavLink"]'
    rules.append(f'{nav} p::before{{{_MASK_BASE}margin-right:.6em;}}')
    for path, name in NAV_ICONS.items():
        rules.append(f'{nav}[href$="/{path}"] p::before{{{_mask(name)}}}')
    targets = ('.stElementContainer{k} button p::before', '{k} summary p::before',
               '{k} [data-testid="stPageLink"] p::before')
    rules.append(",".join(t.format(k='[class*="st-key-ic-"]') for t in targets) + "{" + _MASK_BASE + "}")
    for name in ICONS:
        k = f'[class*="st-key-ic-{name}-"]'
        rules.append(",".join(t.format(k=k) for t in targets) + "{" + _mask(name) + "}")
    return "<style>" + "\n".join(rules) + "</style>"


def ic(name: str, ident: str) -> str:
    """Key cho nút / mục mở rộng / khung để gắn icon Tabler: st.button("Lưu", key=style.ic("device-floppy", "luu_gd"))."""
    assert name in ICONS, name
    return f"ic-{name}-{ident}"


def tab_icons(key: str, names: list[str]) -> None:
    """Gắn icon cho các tab của st.tabs(..., key=key) theo thứ tự."""
    rules = [f'.st-key-{key} [role="tab"]:nth-of-type({i}) p::before{{{_MASK_BASE}{_mask(n)}}}'
             for i, n in enumerate(names, 1)]
    st.html("<style>" + "".join(rules) + "</style>")


def title(icon: str, text: str, caption: str | None = None) -> None:
    """Tiêu đề trang kèm icon Tabler trong ô tròn xanh chanh."""
    cap = f'<div class="pt-cap">{caption}</div>' if caption else ""
    st.html(f'<div class="pt"><span class="pt-ic">{svg(icon, 26, "#111", 2)}</span><h1>{esc(text)}</h1></div>{cap}')


def apply() -> None:
    """Gọi 1 lần mỗi lượt chạy, ngay sau set_page_config."""
    st.html(_CSS)
    st.html(_icon_css())


def esc(x) -> str:
    return html.escape(str(x))


def kpi(label: str, value: str, sub: str = "", lime: bool = False, progress: float | None = None,
        trend: str | None = None, icon: str | None = None) -> str:
    """HTML một thẻ KPI. trend: 'up' | 'down' để tô màu dòng phụ."""
    bar = (f'<div class="bar"><div style="width:{max(0.0, min(1.0, progress)) * 100:.1f}%"></div></div>'
           if progress is not None else "")
    sub_html = f'<div class="sub {trend or ""}">{esc(sub)}</div>' if sub else ""
    ico = (f'<div class="ki{" lime" if lime else ""}">{svg(icon, 18, "#111" if lime else LIME)}</div>'
           if icon else "")
    return (f'<div class="kpi">{ico}<div class="lb">{esc(label)}</div>'
            f'<div class="v{" lime" if lime else ""}">{esc(value)}</div>{bar}{sub_html}</div>')


def kpi_grid(cards: list[str]) -> str:
    """Lưới thẻ KPI: 4 cột trên máy tính, 2 cột trên điện thoại."""
    return f'<div class="kpis">{"".join(cards)}</div>'


def steps(items: list[tuple[str, str]], start: int = 1) -> str:
    """Danh sách bước đánh số. items: (tiêu đề, mô tả – cho phép <b>…</b>)."""
    out = "".join(f'<div class="step"><div class="n">{i}</div><div><div class="t">{esc(t)}</div>'
                  f'<div class="d">{d}</div></div></div>' for i, (t, d) in enumerate(items, start))
    return f'<div class="steps">{out}</div>'


def progress_steps(items: list[dict]) -> str:
    """Danh sách bước có trạng thái. items: dict có title, desc (cho phép <b>), done. Bước chưa xong đầu tiên nổi bật."""
    nxt = next((i for i, x in enumerate(items) if not x["done"]), None)
    done = sum(x["done"] for x in items)
    bar = (f'<div class="obar"><span>Đã xong <b style="color:{LIME}">{done}/{len(items)}</b> bước</span>'
           f'<div class="track"><div style="width:{done / len(items) * 100:.0f}%"></div></div></div>')
    rows = []
    for i, x in enumerate(items):
        cls = "done" if x["done"] else ("next" if i == nxt else "todo")
        mark = "✓" if x["done"] else str(i + 1)
        rows.append(f'<div class="step {cls}"><div class="n">{mark}</div><div><div class="t">{esc(x["title"])}</div>'
                    f'<div class="d">{x["desc"]}</div></div></div>')
    return bar + f'<div class="steps">{"".join(rows)}</div>'


HEALTH_TAG = {"good": "Tốt", "warn": "Cần chú ý", "bad": "Cần cải thiện", "na": "Chưa đủ dữ liệu"}


def health_grid(items: list[dict]) -> str:
    """Lưới thẻ sức khoẻ tài chính; viền trái + nhãn màu theo trạng thái."""
    cards = []
    for x in items:
        hint = f'<div class="hint">{x["hint"]}</div>' if x.get("hint") else ""
        ref = f'<div class="ref">Mốc tham khảo: {esc(x["ref"])}</div>' if x.get("ref") else ""
        cards.append(f'<div class="hc {x["status"]}"><div class="top"><div class="lb">{esc(x["label"])}</div>'
                     f'<span class="tag">{HEALTH_TAG[x["status"]]}</span></div>'
                     f'<div class="v">{esc(x["display"])}</div>{ref}{hint}</div>')
    return f'<div class="hgrid">{"".join(cards)}</div>'


def celebration(title: str, message: str, also: list[str] | None = None) -> str:
    extra = f'<div class="also">Bạn cũng vừa đạt: {esc(" · ".join(also))}</div>' if also else ""
    return (f'<div class="cele"><div class="ico">{svg("trophy", 28, "#111")}</div><div>'
            f'<div class="k">Chúc mừng – mốc mới!</div><div class="t">{esc(title)}</div>'
            f'<div class="m">{esc(message)}</div>{extra}</div></div>')


def badges(groups: list[tuple[str, list[tuple[str, bool, str]]]]) -> str:
    """groups: (tên nhóm, [(nhãn, đã đạt, ngày đạt)])."""
    out = []
    for g, items in groups:
        b = "".join(f'<span class="badge{" on" if on else ""}">{"✓ " if on else ""}{esc(lb)}'
                    f'{f" <span class=dt>{esc(d)}</span>" if on and d else ""}</span>' for lb, on, d in items)
        out.append(f'<div class="bgroup">{esc(g)}</div><div class="badges">{b}</div>')
    return "".join(out)


def next_cards(items: list[dict]) -> str:
    """Thẻ 'mốc kế tiếp': nhóm, tên mốc, thanh tiến độ, còn thiếu."""
    cards = "".join(
        f'<div class="hc next"><div class="top"><div class="lb">{esc(m["group"])}</div></div>'
        f'<div class="v">{esc(m["title"])}</div><div class="bar"><div style="width:{m["progress"] * 100:.0f}%"></div>'
        f'</div><div class="ref">{esc(m["gap"])}</div></div>' for m in items)
    return f'<div class="hgrid">{cards}</div>'


def tip(text: str) -> str:
    return f'<div class="tip">{svg("bulb", 16, LIME)} {text}</div>'


def flow(nodes: list[tuple[str, str]], edges: list[tuple[str, str, str]] | None = None, rankdir: str = "LR",
         highlight: tuple[str, ...] = ()) -> str:
    """Sơ đồ quy trình Graphviz (DOT) tông tối. nodes: (id, nhãn); edges: (từ, tới, nhãn).
    Mặc định nối tuần tự các node nếu không truyền edges."""
    edges = edges if edges is not None else [(a[0], b[0], "") for a, b in zip(nodes, nodes[1:])]
    font = 'fontname="Be Vietnam Pro,Helvetica,Arial"'
    lines = [f'digraph G {{ rankdir={rankdir}; bgcolor="transparent"; pad=0.2; nodesep=0.35; ranksep=0.45;',
             f'node [shape=box, style="rounded,filled", fillcolor="{CARD}", color="#3A3A3A", fontcolor="{TEXT}", '
             f'{font}, fontsize=12, margin="0.18,0.10", penwidth=1.2];',
             f'edge [color="{LIME}", fontcolor="#BDBDBD", {font}, fontsize=10, arrowsize=0.7, penwidth=1.3];']
    for nid, label in nodes:
        extra = f', fillcolor="{LIME}", fontcolor="#111111", color="{LIME}"' if nid in highlight else ""
        lines.append(f'{nid} [label="{label}"{extra}];')
    for a, b, lbl in edges:
        lines.append(f'{a} -> {b}' + (f' [label=" {lbl} "]' if lbl else "") + ";")
    return "\n".join(lines) + "}"


def legend(items: list[tuple[str, str, str]]) -> str:
    """items: (màu, nhãn, giá trị)."""
    lis = "".join(f'<li><span class="dot" style="background:{c}"></span>{esc(lbl)}<span class="val">{esc(v)}</span></li>'
                  for c, lbl, v in items)
    return f'<ul class="legend">{lis}</ul>'


def hello(name: str, subtitle: str = "Xin chào!") -> str:
    initial = (name.strip()[:1] or "?").upper()
    return (f'<div class="hello"><div class="av">{esc(initial)}</div>'
            f'<div><div class="t1">{esc(subtitle)}</div><div class="t2">{esc(name)}</div></div></div>')


def fig(f: go.Figure, height: int | None = None, legend_bottom: bool = True) -> go.Figure:
    """Áp phong cách tối cho biểu đồ Plotly."""
    f.update_layout(
        paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
        font=dict(family="Be Vietnam Pro, sans-serif", color="#D9D9D9", size=12),
        colorway=SERIES, margin=dict(t=10, b=10, l=10, r=10),
        hoverlabel=dict(bgcolor="#1C1C1C", bordercolor="#333", font=dict(color=TEXT)),
    )
    f.update_xaxes(gridcolor=GRID, zerolinecolor=GRID, linecolor=GRID)
    f.update_yaxes(gridcolor=GRID, zerolinecolor=GRID, linecolor=GRID)
    if legend_bottom:
        f.update_layout(legend=dict(orientation="h", y=-0.18, bgcolor="rgba(0,0,0,0)"))
    if height:
        f.update_layout(height=height)
    return f

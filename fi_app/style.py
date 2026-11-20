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
             "huong_dan": "book", "sao_luu": "settings"}


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

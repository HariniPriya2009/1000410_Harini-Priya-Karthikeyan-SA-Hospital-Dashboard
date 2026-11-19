"""Look and feel for the MediScope dashboard: palette, CSS, icons, mascot and page banners.

Everything here is plain CSS and inline SVG. Only transform and opacity are animated,
so the page stays smooth. Motion switches off for visitors who prefer reduced motion.
"""
from __future__ import annotations

# ---- hospital light palette (blue, green, white, red, plus the teal/lime of the reference swatch) ----
BLUE = "#1E6FD9"
DEEP = "#0B4F9C"
NAVY = "#0E2A47"
SKY = "#7FB2F0"
GREEN = "#1DB98A"
TEAL = "#79C1B9"
MINT = "#A9D188"
LIME = "#CFCE5D"
RED = "#E5384F"
CORAL = "#F0766B"
BG = "#F4F9FC"
CARD = "#FFFFFF"
MUTED = "#5F7690"
LINE = "#DDEBF5"

PALETTE = [BLUE, GREEN, SKY, TEAL, DEEP, LIME, MINT, RED]
SEVERITY_COLORS = {"Minor": GREEN, "Moderate": "#C6CB45", "Major": CORAL, "Extreme": "#D7263D", "Unknown": "#B7C7DA"}
HEAT_SCALE = [[0, "#EAF4FF"], [0.5, "#5BA3F0"], [1, DEEP]]

ICONS = {
    "records": '<rect x="9" y="2" width="6" height="4" rx="1"/><path d="M16 4h2a2 2 0 0 1 2 2v14a2 2 0 0 1-2 2H6a2 2 0 0 1-2-2V6a2 2 0 0 1 2-2h2"/><path d="M9 13h6M9 17h4"/>',
    "clock": '<circle cx="12" cy="12" r="10"/><polyline points="12 6 12 12 16 14"/>',
    "money": '<rect x="1" y="4" width="22" height="16" rx="2"/><line x1="1" y1="10" x2="23" y2="10"/>',
    "hospital": '<rect x="3" y="3" width="18" height="18" rx="3"/><line x1="12" y1="8" x2="12" y2="16"/><line x1="8" y1="12" x2="16" y2="12"/>',
    "layers": '<polygon points="12 2 2 7 12 12 22 7 12 2"/><polyline points="2 17 12 22 22 17"/><polyline points="2 12 12 17 22 12"/>',
    "help": '<circle cx="12" cy="12" r="10"/><path d="M9.09 9a3 3 0 0 1 5.83 1c0 2-3 3-3 3"/><line x1="12" y1="17" x2="12.01" y2="17"/>',
    "copy": '<rect x="9" y="9" width="13" height="13" rx="2"/><path d="M5 15H4a2 2 0 0 1-2-2V4a2 2 0 0 1 2-2h9a2 2 0 0 1 2 2v1"/>',
    "alert": '<path d="M10.29 3.86L1.82 18a2 2 0 0 0 1.71 3h16.94a2 2 0 0 0 1.71-3L13.71 3.86a2 2 0 0 0-3.42 0z"/><line x1="12" y1="9" x2="12" y2="13"/><line x1="12" y1="17" x2="12.01" y2="17"/>',
    "pulse": '<polyline points="22 12 18 12 15 21 9 3 6 12 2 12"/>',
    "users": '<path d="M17 21v-2a4 4 0 0 0-4-4H5a4 4 0 0 0-4 4v2"/><circle cx="9" cy="7" r="4"/><path d="M23 21v-2a4 4 0 0 0-3-3.87"/><path d="M16 3.13a4 4 0 0 1 0 7.75"/>',
}
# the old emoji keys used by the pages map onto the icons above
ICON_ALIASES = {"📋": "records", "⏱️": "clock", "💳": "money", "🏥": "hospital", "🧾": "records",
                "🧱": "layers", "❓": "help", "♊": "copy", "⚠️": "alert"}

SCENES = {
    "Summary": ("Hospital Exterior", "Click the right side of the window for a fact from Jabby"),
    "Patient Analysis": ("Scanner Room", "The scanner runs while you read the patient charts"),
    "Cost Analysis": ("Reception and Billing", "Charges, costs and payers, one counter at a time"),
    "Hospital Analysis": ("Hospital Globe", "Drag to spin the globe. Red pins are New York counties"),
    "Data Quality": ("Clean Wards", "Every record checked, every outlier kept"),
}

PAGE_TIPS = {
    "Summary": "Hi, I'm Syro! Start here for the big picture, then pick a page.",
    "Patient Analysis": "Raise the minimum records slider to hide diagnoses with only a few cases.",
    "Cost Analysis": "Charges are what hospitals bill. Costs are what the care takes to deliver.",
    "Hospital Analysis": "A long average stay is not always bad. Case mix changes the picture.",
    "Data Quality": "Outliers stay in the data. Only the charts can hide them.",
}

_CSS = """
<style>
:root{--blue:@@BLUE@@;--deep:@@DEEP@@;--navy:@@NAVY@@;--green:@@GREEN@@;--teal:@@TEAL@@;--lime:@@LIME@@;--red:@@RED@@;--muted:@@MUTED@@;--line:@@LINE@@}
.stApp{background:linear-gradient(180deg,#F8FCFE 0%,#EDF6FA 100%);color:var(--navy)}
.stApp::before{content:"";position:fixed;inset:0;z-index:0;pointer-events:none;background:
 radial-gradient(900px 520px at 6% -4%,rgba(30,111,217,.15),transparent 62%),
 radial-gradient(800px 560px at 104% 8%,rgba(29,185,138,.14),transparent 60%),
 radial-gradient(700px 500px at 96% 104%,rgba(207,206,93,.18),transparent 60%),
 radial-gradient(520px 420px at 0% 100%,rgba(229,56,79,.06),transparent 62%)}
[data-testid="stHeader"]{background:transparent}
[data-testid="stAppViewContainer"],[data-testid="stMain"]{background:transparent}
.block-container{position:relative;z-index:1;padding-top:1.4rem;padding-bottom:3rem;max-width:1500px}
@keyframes rise{from{opacity:0;transform:translate3d(0,14px,0)}to{opacity:1;transform:none}}
@keyframes fxFloat{0%,100%{transform:translate3d(0,0,0) rotate(0)}50%{transform:translate3d(0,-26px,0) rotate(14deg)}}
@keyframes fxFloat2{0%,100%{transform:translate3d(0,0,0) rotate(0)}50%{transform:translate3d(14px,20px,0) rotate(-16deg)}}

/* floating background shapes (5 elements, transform only) */
.fx{position:fixed;z-index:0;pointer-events:none;opacity:.5;will-change:transform}
.fx svg{display:block}
.fx.f1{left:2%;top:22%;animation:fxFloat 9s ease-in-out infinite}
.fx.f2{right:3%;top:14%;animation:fxFloat2 11s ease-in-out infinite}
.fx.f3{left:6%;bottom:8%;animation:fxFloat2 13s ease-in-out infinite}
.fx.f4{right:6%;bottom:12%;animation:fxFloat 10s ease-in-out infinite}
.fx.f5{left:48%;top:3%;animation:fxFloat 14s ease-in-out infinite}

/* page banner */
.banner{position:relative;overflow:hidden;border-radius:24px;padding:22px 28px;margin:0 0 18px;color:#fff;display:flex;align-items:center;gap:18px;
 background:linear-gradient(120deg,var(--deep) 0%,var(--blue) 50%,var(--green) 115%);box-shadow:0 14px 34px rgba(30,111,217,.22);animation:rise .55s cubic-bezier(.2,.8,.2,1) both}
.banner::after{content:"";position:absolute;top:0;bottom:0;left:0;width:34%;background:linear-gradient(100deg,transparent,rgba(255,255,255,.24),transparent);transform:translateX(-130%) skewX(-18deg);animation:shine 7s ease-in-out infinite}
@keyframes shine{0%,55%{transform:translateX(-130%) skewX(-18deg)}100%{transform:translateX(420%) skewX(-18deg)}}
.banner-ico{flex:none;width:58px;height:58px;border-radius:18px;background:rgba(255,255,255,.18);display:flex;align-items:center;justify-content:center;font-size:28px;border:1px solid rgba(255,255,255,.35)}
.banner-title{font-size:1.75rem;font-weight:800;line-height:1.15;letter-spacing:-.01em}
.banner-sub{opacity:.93;font-size:.98rem;margin-top:.25rem;max-width:760px}
.banner-ecg{position:absolute;right:10px;bottom:6px;width:42%;height:64%;opacity:.45;pointer-events:none}
.banner-ecg path{fill:none;stroke:#fff;stroke-width:3;stroke-linecap:round;stroke-linejoin:round;stroke-dasharray:420;animation:ecg 3.4s linear infinite}
@keyframes ecg{from{stroke-dashoffset:840}to{stroke-dashoffset:0}}

.section-title{font-size:1.15rem;font-weight:800;color:var(--deep);margin:1.5rem 0 .7rem;display:flex;align-items:center;gap:10px}
.section-title::before{content:"";width:6px;height:22px;border-radius:4px;background:linear-gradient(var(--blue),var(--green))}

/* KPI cards */
.kpi{position:relative;background:#fff;border:1px solid var(--line);border-radius:18px;padding:16px 18px 16px 22px;display:flex;gap:14px;align-items:center;
 box-shadow:0 6px 20px rgba(14,42,71,.06);min-height:86px;overflow:hidden;transition:box-shadow .25s ease,border-color .25s ease;animation:rise .6s cubic-bezier(.2,.8,.2,1) both}
.kpi::before{content:"";position:absolute;left:0;top:0;bottom:0;width:5px;background:var(--tone)}
.kpi:hover{box-shadow:0 14px 32px rgba(30,111,217,.16);border-color:var(--tone)}
.kpi-icon{width:46px;height:46px;border-radius:14px;display:flex;align-items:center;justify-content:center;flex:none;background:var(--soft);color:var(--tone);transition:transform .35s cubic-bezier(.2,1.4,.4,1)}
.kpi:hover .kpi-icon{transform:rotate(-8deg) scale(1.1)}
.kpi-icon svg{width:24px;height:24px;stroke:currentColor;fill:none;stroke-width:2;stroke-linecap:round;stroke-linejoin:round}
.kpi-label{font-size:.78rem;color:var(--muted);font-weight:700;letter-spacing:.02em}
.kpi-value{font-size:1.45rem;font-weight:800;color:var(--navy);line-height:1.2}
.kpi.t0{--tone:var(--blue);--soft:#E4F0FF}
.kpi.t1{--tone:var(--green);--soft:#DDF6EE}
.kpi.t2{--tone:var(--red);--soft:#FFE6EA}
.kpi.t3{--tone:#A3A72A;--soft:#F5F6CF}
.kpi.t4{--tone:#3E9D95;--soft:#DDF1EF}

/* chart cards: shadow change only (no movement, so no hover flicker) */
div[class*="st-key-card_"]{background:#fff;border:1px solid var(--line);border-radius:20px;padding:16px 20px 10px;box-shadow:0 8px 26px rgba(14,42,71,.06);margin-bottom:.8rem;
 transition:box-shadow .25s ease,border-color .25s ease;animation:rise .6s cubic-bezier(.2,.8,.2,1) both}
div[class*="st-key-card_"]:hover{box-shadow:0 16px 38px rgba(30,111,217,.14);border-color:#BBD6F3}
.st-key-hero{border-radius:26px;overflow:hidden;box-shadow:0 18px 44px rgba(30,111,217,.18);border:1px solid var(--line);margin-bottom:1.1rem;background:#fff;animation:rise .6s cubic-bezier(.2,.8,.2,1) both}
.st-key-hero iframe{display:block;border:0}
div[data-testid="stAlert"]{border-radius:14px;border:1px solid var(--line)}
details{border-radius:14px!important}

/* sidebar (light) */
section[data-testid="stSidebar"]{background:linear-gradient(180deg,#FFFFFF 0%,#F0F7FE 62%,#EAF8F2 100%);border-right:1px solid var(--line)}
section[data-testid="stSidebar"] h3{color:var(--deep);font-size:1.05rem;margin-top:.6rem}
section[data-testid="stSidebar"] [data-testid="stWidgetLabel"] p{color:var(--navy);font-weight:600}
section[data-testid="stSidebar"] [data-testid="stCaptionContainer"]{color:var(--muted)}
.brand{display:flex;align-items:center;gap:12px;margin:.2rem 0 1rem}
.brand-logo{width:46px;height:46px;border-radius:14px;background:linear-gradient(135deg,var(--blue),var(--green));color:#fff;display:flex;align-items:center;justify-content:center;font-size:24px;font-weight:800;animation:pulse 2.4s ease-in-out infinite}
@keyframes pulse{0%{box-shadow:0 0 0 0 rgba(29,185,138,.5)}70%{box-shadow:0 0 0 13px rgba(29,185,138,0)}100%{box-shadow:0 0 0 0 rgba(29,185,138,0)}}
.brand-name{color:var(--deep);font-weight:800;font-size:1.08rem;line-height:1.2}
.brand-name small{display:block;color:var(--muted);font-weight:600;font-size:.72rem;letter-spacing:.08em}
section[data-testid="stSidebar"] div[role="radiogroup"] label{padding:9px 12px;border-radius:12px;width:100%;transition:background .2s ease,box-shadow .2s ease}
section[data-testid="stSidebar"] div[role="radiogroup"] label>div:first-child{display:none}
section[data-testid="stSidebar"] div[role="radiogroup"] label p{color:var(--navy)!important;font-weight:600}
section[data-testid="stSidebar"] div[role="radiogroup"] label:hover{background:#E4F0FF}
section[data-testid="stSidebar"] div[role="radiogroup"] label:has(input:checked){background:linear-gradient(100deg,var(--blue),var(--green));box-shadow:0 8px 18px rgba(30,111,217,.28)}
section[data-testid="stSidebar"] div[role="radiogroup"] label:has(input:checked) p{color:#fff!important}
section[data-testid="stSidebar"] .stButton button{background:#fff;color:var(--deep);border:1.5px solid #BBD6F3;border-radius:12px;font-weight:700;transition:background .2s,color .2s,box-shadow .2s}
section[data-testid="stSidebar"] .stButton button:hover{background:linear-gradient(100deg,var(--blue),var(--green));color:#fff;border-color:transparent;box-shadow:0 8px 18px rgba(30,111,217,.25)}
section[data-testid="stSidebar"] [data-baseweb="tag"]{background:#E4F0FF!important}
section[data-testid="stSidebar"] [data-baseweb="tag"] span{color:var(--deep)!important}
section[data-testid="stSidebar"] details{background:#fff;border:1px solid var(--line)}
.stDownloadButton button{background:linear-gradient(100deg,var(--blue),var(--green));color:#fff;border:none;border-radius:12px;font-weight:700;transition:box-shadow .2s,filter .2s}
.stDownloadButton button:hover{color:#fff;box-shadow:0 10px 22px rgba(30,111,217,.3);filter:brightness(1.05)}
::-webkit-scrollbar{width:10px;height:10px}::-webkit-scrollbar-thumb{background:#BBD6F3;border-radius:8px}::-webkit-scrollbar-track{background:transparent}

/* Syro the syrup bottle */
.syro{display:flex;gap:8px;align-items:flex-end;margin:.9rem 0 .4rem}
.syro-svg{width:86px;height:124px;flex:none;overflow:visible;animation:bob 3.4s ease-in-out infinite;transform-origin:50% 100%}
@keyframes bob{0%,100%{transform:translateY(0) rotate(-1.5deg)}50%{transform:translateY(-6px) rotate(1.5deg)}}
.syro-bubble{position:relative;background:#fff;border:1px solid var(--line);border-radius:16px;padding:10px 12px;font-size:.8rem;line-height:1.4;color:var(--navy);box-shadow:0 8px 20px rgba(14,42,71,.08);animation:pop .6s cubic-bezier(.2,1.4,.4,1) both;margin-bottom:34px}
.syro-bubble::before{content:"";position:absolute;left:-7px;bottom:16px;width:12px;height:12px;background:#fff;border-left:1px solid var(--line);border-bottom:1px solid var(--line);transform:rotate(45deg)}
@keyframes pop{from{opacity:0;transform:scale(.8)}to{opacity:1;transform:scale(1)}}
.syro .eye{transform-box:fill-box;transform-origin:center;animation:blink 4.2s infinite}
@keyframes blink{0%,92%,100%{transform:scaleY(1)}95%{transform:scaleY(.08)}}
.syro .wave{animation:waveX 2.4s linear infinite}
@keyframes waveX{to{transform:translateX(60px)}}
.syro .arm{transform-box:view-box;transform-origin:88px 112px;animation:wave 1.1s ease-in-out infinite}
@keyframes wave{0%,100%{transform:rotate(-8deg)}50%{transform:rotate(22deg)}}
.syro .bub{animation:bubUp 3.2s ease-in infinite;opacity:0}
.syro .bub.b2{animation-delay:1.1s}.syro .bub.b3{animation-delay:2.1s}
@keyframes bubUp{0%{transform:translateY(0);opacity:0}15%{opacity:.85}100%{transform:translateY(-46px);opacity:0}}
.syro .shadow{transform-box:fill-box;transform-origin:center;animation:shadow 3.4s ease-in-out infinite}
@keyframes shadow{0%,100%{transform:scaleX(1)}50%{transform:scaleX(.82)}}


/* 3D world layer: full-screen, click-through, behind the page. It only draws inside #scene-window. */
.st-key-world{position:fixed!important;inset:0;z-index:-1;pointer-events:none;margin:0!important;padding:0!important;width:100vw!important;height:100vh!important;overflow:hidden}
.st-key-world>div,.st-key-world iframe{width:100vw!important;height:100vh!important;border:0;display:block}
#page-marker{display:none}
.scene-window{position:relative;height:300px;margin:0 0 18px;border-radius:24px;overflow:hidden;box-shadow:0 18px 44px rgba(30,111,217,.2),inset 0 0 0 1.5px rgba(255,255,255,.9);border:1px solid #CFE3F5}
.sw-chip{position:absolute;left:16px;top:14px;display:flex;gap:9px;align-items:center;background:rgba(255,255,255,.88);border:1px solid rgba(255,255,255,.95);border-radius:999px;padding:7px 15px;font-weight:800;color:var(--deep);font-size:.85rem;box-shadow:0 6px 18px rgba(14,42,71,.12);z-index:2}
.sw-chip i{width:9px;height:9px;border-radius:50%;background:var(--red);animation:blip 1.4s infinite}
@keyframes blip{0%,100%{box-shadow:0 0 0 0 rgba(229,56,79,.55)}70%{box-shadow:0 0 0 8px rgba(229,56,79,0)}}
.sw-hint{position:absolute;left:16px;bottom:12px;background:rgba(14,42,71,.62);color:#fff;border-radius:999px;padding:5px 12px;font-size:.74rem;font-weight:600;z-index:2;max-width:70%}
@media (max-width:640px){.scene-window{height:240px}.sw-hint{display:none}}

@media (prefers-reduced-motion:reduce){*,*::before,*::after{animation:none!important;transition:none!important}}
</style>
"""

_FX = """
<div class="fx f1"><svg width="46" height="46" viewBox="0 0 24 24"><path d="M9 3h6v6h6v6h-6v6H9v-6H3V9h6z" fill="#E5384F" opacity=".75"/></svg></div>
<div class="fx f2"><svg width="40" height="40" viewBox="0 0 24 24"><path d="M9 3h6v6h6v6h-6v6H9v-6H3V9h6z" fill="#1DB98A" opacity=".75"/></svg></div>
<div class="fx f3"><svg width="64" height="30" viewBox="0 0 64 30"><rect width="64" height="30" rx="15" fill="#fff"/><path d="M32 0h17a15 15 0 0 1 0 30H32z" fill="#1E6FD9"/></svg></div>
<div class="fx f4"><svg width="38" height="38" viewBox="0 0 38 38"><circle cx="19" cy="19" r="15" fill="none" stroke="#CFCE5D" stroke-width="6"/></svg></div>
<div class="fx f5"><svg width="30" height="30" viewBox="0 0 30 30"><circle cx="15" cy="15" r="9" fill="#79C1B9" opacity=".8"/></svg></div>
"""

BRAND = ('<div class="brand"><div class="brand-logo">✚</div>'
         '<div class="brand-name">MediScope<small>HEALTH ANALYTICS</small></div></div>')


def css() -> str:
    out = _CSS
    for key, value in {"BLUE": BLUE, "DEEP": DEEP, "NAVY": NAVY, "GREEN": GREEN, "TEAL": TEAL, "LIME": LIME,
                       "RED": RED, "MUTED": MUTED, "LINE": LINE}.items():
        out = out.replace(f"@@{key}@@", value)
    return out + _FX


def icon_svg(name: str) -> str:
    name = ICON_ALIASES.get(name, name)
    body = ICONS.get(name)
    if body is None:
        return f"<span>{name}</span>"
    return f'<svg viewBox="0 0 24 24">{body}</svg>'


def kpi_html(items: list) -> list[str]:
    out = []
    for i, (icon, label, value) in enumerate(items):
        out.append(f'<div class="kpi t{i % 5}" style="animation-delay:{i * 0.08:.2f}s"><div class="kpi-icon">{icon_svg(icon)}</div>'
                   f'<div><div class="kpi-label">{label}</div><div class="kpi-value">{value}</div></div></div>')
    return out


def banner_html(title: str, subtitle: str, icon: str = "✚") -> str:
    ecg = ('<svg class="banner-ecg" viewBox="0 0 420 80" preserveAspectRatio="none"><path d="M0 44 H110 L128 44 L142 18 L160 70 L176 8 L192 44 H300 L314 44 L326 30 L340 54 L352 44 H420"/></svg>')
    return (f'<div class="banner"><div class="banner-ico">{icon}</div><div><div class="banner-title">{title}</div>'
            f'<div class="banner-sub">{subtitle}</div></div>{ecg}</div>')


def mascot_html(page: str) -> str:
    """Syro, a syrup bottle that waves and gives a short tip for each page."""
    tip = PAGE_TIPS.get(page, PAGE_TIPS["Summary"])
    body = "M32 66 Q32 54 44 50 L44 40 H76 V50 Q88 54 88 66 V142 Q88 156 74 156 H46 Q32 156 32 142 Z"
    wave = "M-60 88 q15 -7 30 0 t30 0 t30 0 t30 0 t30 0 t30 0 t30 0 t30 0 V110 H-60 Z"
    svg = f"""<svg class="syro-svg" viewBox="0 0 120 170" xmlns="http://www.w3.org/2000/svg" role="img" aria-label="Syro the syrup bottle mascot">
<defs><clipPath id="syroBody"><path d="{body}"/></clipPath>
<linearGradient id="syroLiq" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="#5BDDB0"/><stop offset="1" stop-color="#1DB98A"/></linearGradient>
<linearGradient id="syroCap" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="#F2566B"/><stop offset="1" stop-color="#C92A40"/></linearGradient></defs>
<ellipse class="shadow" cx="60" cy="164" rx="28" ry="5" fill="#0E2A47" opacity=".13"/>
<path d="M32 112 q-12 2 -17 14" stroke="#CFE3F7" stroke-width="6" fill="none" stroke-linecap="round"/><circle cx="14" cy="128" r="6.5" fill="#fff" stroke="#B9D4EE" stroke-width="2"/>
<g class="arm"><path d="M88 112 q15 -2 20 -18" stroke="#CFE3F7" stroke-width="6" fill="none" stroke-linecap="round"/><circle cx="109" cy="92" r="6.5" fill="#fff" stroke="#B9D4EE" stroke-width="2"/></g>
<path d="{body}" fill="#F7FBFF" stroke="#B9D4EE" stroke-width="2.5"/>
<g clip-path="url(#syroBody)"><rect x="20" y="96" width="100" height="70" fill="url(#syroLiq)"/>
<g class="wave"><path d="{wave}" fill="#5BDDB0"/></g>
<circle class="bub" cx="44" cy="150" r="2.4" fill="#fff"/><circle class="bub b2" cx="72" cy="146" r="2" fill="#fff"/><circle class="bub b3" cx="58" cy="152" r="2.8" fill="#fff"/></g>
<path d="M38 72 Q36 104 38 138" stroke="#fff" stroke-width="4" opacity=".75" fill="none" stroke-linecap="round"/>
<circle cx="60" cy="70" r="11" fill="#fff" stroke="#F4C3CB" stroke-width="1.5"/><path d="M60 63v14M53 70h14" stroke="#E5384F" stroke-width="4.5" stroke-linecap="round"/>
<rect x="40" y="24" width="40" height="18" rx="5" fill="url(#syroCap)"/><path d="M48 27v12M56 27v12M64 27v12M72 27v12" stroke="#fff" stroke-opacity=".35" stroke-width="2" stroke-linecap="round"/>
<rect x="43" y="40" width="34" height="6" rx="3" fill="#D6E7F7"/>
<g class="eye"><ellipse cx="50" cy="108" rx="6" ry="7.2" fill="#fff"/><circle cx="51" cy="109" r="3.2" fill="#0E2A47"/><circle cx="52" cy="107.5" r="1.1" fill="#fff"/></g>
<g class="eye"><ellipse cx="70" cy="108" rx="6" ry="7.2" fill="#fff"/><circle cx="71" cy="109" r="3.2" fill="#0E2A47"/><circle cx="72" cy="107.5" r="1.1" fill="#fff"/></g>
<path d="M53 123 q7 8 14 0" stroke="#7A1A2B" stroke-width="2.6" fill="none" stroke-linecap="round"/>
<circle cx="43" cy="119" r="4" fill="#FF8FA3" opacity=".6"/><circle cx="77" cy="119" r="4" fill="#FF8FA3" opacity=".6"/>
</svg>"""
    return f'<div class="syro">{svg}<div class="syro-bubble">{tip}</div></div>'


def scene_window(scene: str | None) -> str:
    """Transparent hole in the page. The 3D world draws itself inside this rectangle."""
    if scene not in SCENES:
        return ""
    name, hint = SCENES[scene]
    return (f'<div class="scene-window" id="scene-window"><div class="sw-chip"><i></i>{name}</div>'
            f'<div class="sw-hint">{hint}</div></div>')


def page_marker(page: str) -> str:
    return f'<div id="page-marker" data-page="{page}"></div>'

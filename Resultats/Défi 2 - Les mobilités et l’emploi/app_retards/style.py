"""Habillage Streamlit calqué sur les maquettes Hackaviz (palette, polices, navigation, en-têtes)."""
import re

import streamlit as st

CSS = """<style>
@import url('https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@400;500;600;700;800&family=Outfit:wght@700;800&display=swap');
html, body, .stApp, button, input, textarea {font-family:'Plus Jakarta Sans',sans-serif}
.stApp {background:#F6F7F4;color:#1B1F2A}
.stApp::before {content:"";position:fixed;left:0;top:0;bottom:0;width:6px;background:#E4572E;z-index:1000}
[data-testid="stSidebar"] {background:#ECEEE9}
h1,h2,h3,h4 {font-family:'Outfit',sans-serif!important;font-weight:800!important;color:#1B1F2A}
.block-container {padding-top:2rem;max-width:1280px}
[data-baseweb="tab-list"] {gap:8px;flex-wrap:wrap}
button[data-baseweb="tab"] {border-radius:999px;background:#fff;border:2px solid #1B1F2A;padding:6px 16px;min-height:44px}
button[data-baseweb="tab"] p {font-weight:700;margin:0;color:#1B1F2A}
button[data-baseweb="tab"][aria-selected="true"] {background:#1B1F2A}
button[data-baseweb="tab"][aria-selected="true"] p {color:#fff}
[data-baseweb="tab-highlight"], [data-baseweb="tab-border"] {display:none}
[data-testid="stMetric"] {background:#fff;border:1px solid #E3E6E0;border-radius:16px;padding:16px 18px}
.hk-hero {background:#141A2E;color:#F1F2F6;border-radius:16px;padding:34px 40px;margin-bottom:22px}
.hk-hero h1 {color:#F1F2F6;font-size:42px;line-height:1.12;margin:10px 0 12px}
.hk-hero p {color:#C9CDD8;font-size:17px;line-height:1.6;margin:0;max-width:720px}
.hk-kicker {display:flex;align-items:center;gap:10px;font-size:14px;font-weight:700;letter-spacing:.08em;text-transform:uppercase}
.hk-dot {width:26px;height:26px;border-radius:50%;display:inline-flex;align-items:center;justify-content:center;color:#fff;font-size:13px}
.hk-head h1 {font-size:36px;line-height:1.15;margin:8px 0 8px}
.hk-head p {font-size:17px;line-height:1.55;color:#4E5466;margin:0 0 14px;max-width:760px}
.hk-card {background:#fff;border:1px solid #E3E6E0;border-radius:16px;padding:20px 22px;height:100%}
.hk-card h4 {margin:0 0 12px;font-size:18px}
.hk-chip {display:inline-block;border-radius:999px;background:#ECEEE9;color:#1B1F2A;font-size:14px;font-weight:600;padding:5px 12px;margin:0 6px 8px 0}
.hk-brand {display:flex;align-items:center;gap:12px;margin-bottom:18px}
.hk-logo {width:42px;height:42px;border-radius:12px;background:#1B1F2A;color:#fff;display:flex;align-items:center;justify-content:center;font-weight:800}
.hk-brand b {font-family:'Outfit',sans-serif;font-size:16px;line-height:1.2;display:block}
.hk-brand span {font-size:14px;color:#5E6475}
</style>"""


def apply():
    st.markdown(CSS, unsafe_allow_html=True)


def brand():
    st.markdown('<div class="hk-brand"><div class="hk-logo">R</div><div><b>Sur place, loin du réseau</b>'
                '<span>Hackaviz IDFM 2026 · Défi 2</span></div></div>', unsafe_allow_html=True)


def _accent(t, color):
    return re.sub(r"\*(.+?)\*", rf'<span style="color:{color}">\1</span>', t)


def hero():
    st.markdown('<div class="hk-hero"><div class="hk-kicker" style="color:#F28B6B"><span class="hk-dot" '
                'style="background:#E4572E">●</span>Mobilités et emploi en Île-de-France</div>'
                + _accent("<h1>Combien coûtent les *retards* de transport à un salarié ?</h1>", "#F28B6B")
                + "<p>Une simulation à partir de la ponctualité réelle des lignes, de l'historique des perturbations "
                  "et des habitudes de déplacement des actifs.</p></div>", unsafe_allow_html=True)


def head(n, total, label, title, lead):
    st.markdown(f'<div class="hk-head"><div class="hk-kicker" style="color:#C0401A"><span class="hk-dot" '
                f'style="background:#C0401A">{n}</span>{label} · {n} / {total}</div>'
                + _accent(f"<h1>{title}</h1>", "#C0401A") + f"<p>{lead}</p></div>", unsafe_allow_html=True)


def cards(blocks):
    """blocks : liste de (titre, [puces]) affichée en colonnes."""
    cols = st.columns(len(blocks))
    for c, (t, chips) in zip(cols, blocks):
        c.markdown(f'<div class="hk-card"><h4>{t}</h4>' + "".join(f'<span class="hk-chip">{x}</span>' for x in chips)
                   + "</div>", unsafe_allow_html=True)

VERDICT = {"ok": ("Vérifiée", "#1F6A8C"), "ko": ("Réfutée", "#B23A86"),
           "nc": ("Non concluante", "#8A8F9C"), "nt": ("Pas encore testable", "#8A8F9C")}


def verdict(code, question, chiffre, detail):
    """Carte d'hypothèse : pastille de verdict, question, gros chiffre, détail."""
    lab, col = VERDICT[code]
    st.markdown(f'<div class="hk-card" style="border-top:6px solid {col}">'
                f'<span class="hk-chip" style="background:{col};color:#fff">{lab}</span>'
                f'<h4 style="margin-top:6px">{question}</h4>'
                f'<div style="font-family:Outfit,sans-serif;font-size:34px;font-weight:800;color:{col};line-height:1.1">{chiffre}</div>'
                f'<div style="font-size:14px;color:#4E5466;margin-top:6px">{detail}</div></div>', unsafe_allow_html=True)
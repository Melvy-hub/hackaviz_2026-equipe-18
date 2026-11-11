"""Visualisations Altair (incluses avec Streamlit) : heatmaps, bump chart, horloge radiale, waffle, calendrier."""
import altair as alt
import numpy as np
import pandas as pd
import streamlit as st

PAL = ["#E4572E", "#1F6A8C", "#B23A86", "#3A8FB7", "#C0401A", "#E58BC4"]
DIV = ["#C0401A", "#F3E7DA", "#1F6A8C"]  # mauvais -> neutre -> bon (orange / bleu, lisible par tous)


def _theme():
    return {"config": {"background": "transparent", "font": "Plus Jakarta Sans", "view": {"stroke": "transparent"},
            "axis": {"labelColor": "#4E5466", "titleColor": "#1B1F2A", "gridColor": "#E3E6E0", "domainColor": "#C9CDD8",
                     "tickColor": "#C9CDD8", "labelFontSize": 12, "titleFontSize": 12, "titleFontWeight": 600},
            "legend": {"labelColor": "#4E5466", "titleColor": "#1B1F2A", "labelFontSize": 12},
            "title": {"color": "#1B1F2A", "font": "Outfit", "fontWeight": 800},
            "text": {"color": "#1B1F2A"}, "range": {"category": PAL}}}


alt.themes.register("hackaviz", _theme)
alt.themes.enable("hackaviz")


def show(container, chart, **kw):
    """Affiche un graphique avec le thème des maquettes (et non celui de Streamlit)."""
    kw.setdefault("theme", None)
    if kw.pop("use_container_width", False):
        try:
            return container.altair_chart(chart, width="stretch", **kw)
        except TypeError:  # Streamlit plus ancien
            return container.altair_chart(chart, use_container_width=True, **kw)
    return container.altair_chart(chart, **kw)


def _div(s):
    lo, hi = s.quantile([0.02, 0.98])
    return alt.Scale(domain=[lo, (lo + hi) / 2, hi], range=DIV, clamp=True)


MOIS = ["janv", "févr", "mars", "avr", "mai", "juin", "juil", "août", "sept", "oct", "nov", "déc"]
JOURS = "['lun','mar','mer','jeu','ven','sam','dim'][datum.value]"


def heatmap_lines(h):
    """Ligne × mois : chaque case est un mois, rouge = mauvaise ponctualité."""
    lo, hi = h["taux"].quantile([0.02, 0.98])
    return alt.Chart(h).mark_rect().encode(
        x=alt.X("date:T", timeUnit="yearmonth", title=None),
        y=alt.Y("ligne:N", title=None, sort=alt.EncodingSortField("taux", op="mean", order="ascending")),
        color=alt.Color("mean(taux):Q", title="Ponctualité %",
                        scale=_div(h["taux"])),
        tooltip=[alt.Tooltip("date:T", timeUnit="yearmonth", title="Mois"), "ligne:N",
                 alt.Tooltip("mean(taux):Q", title="Ponctualité %", format=".1f")],
    ).properties(height=max(120, 26 * h["ligne"].nunique()))


def bump(h):
    """Course des lignes : rang annuel de ponctualité (1 = la plus ponctuelle)."""
    y = h.assign(an=h["date"].dt.year).groupby(["an", "ligne"], as_index=False)["taux"].mean()
    y["rang"] = y.groupby("an")["taux"].rank(ascending=False, method="first")
    base = alt.Chart(y).encode(x=alt.X("an:O", title=None), y=alt.Y("rang:O", title="Rang"),
                               color=alt.Color("ligne:N", legend=None, scale=alt.Scale(range=PAL)))
    last = base.transform_filter(alt.datum.an == int(y["an"].max()))
    return (base.mark_line(strokeWidth=3, interpolate="monotone")
            + base.mark_circle(size=200).encode(tooltip=["an:O", "ligne:N", alt.Tooltip("taux:Q", format=".1f")])
            + last.mark_text(align="left", dx=14, fontSize=11).encode(text="ligne:N")
            ).properties(height=320, padding={"left": 5, "right": 90, "top": 5, "bottom": 5})


def radial_months(h):
    """Horloge des retards : un secteur par mois, plus il est grand et sombre, plus le mois est en retard."""
    m = h.groupby(h["date"].dt.month, as_index=False)["taux"].mean().rename(columns={"date": "m"})
    m["retard"] = 100 - m["taux"]
    m["mois"] = m["m"].map(lambda i: MOIS[i - 1])
    m["un"] = 1
    base = alt.Chart(m).encode(
        theta=alt.Theta("un:Q", stack=True),
        radius=alt.Radius("retard:Q", scale=alt.Scale(type="sqrt", zero=True, rangeMin=25)),
        order=alt.Order("m:O"),
        color=alt.Color("retard:Q", scale=alt.Scale(range=["#FBE3DA", "#C0401A"]), legend=None),
        tooltip=["mois:N", alt.Tooltip("taux:Q", title="Ponctualité %", format=".1f")])
    return (base.mark_arc(innerRadius=25, stroke="white")
            + base.mark_text(radiusOffset=14, fontSize=11).encode(text="mois:N")).properties(height=330)


def small_multiples(h, ncol=3):
    """Une courbe par ligne, pire mois marqué en rouge."""
    base = alt.Chart(h).encode(x=alt.X("date:T", title=None),
                               y=alt.Y("taux:Q", scale=alt.Scale(zero=False), title="%"))
    worst = (base.transform_window(rk="rank()", sort=[alt.SortField("taux", "ascending")], groupby=["ligne"])
             .transform_filter("datum.rk == 1")
             .mark_point(color="#C0401A", filled=True, size=70)
             .encode(tooltip=["date:T", alt.Tooltip("taux:Q", format=".1f")]))
    return (base.mark_area(opacity=0.25, line=True, color="#1F6A8C") + worst).properties(
        width=210, height=110).facet(alt.Facet("ligne:N", title=None), columns=ncol)


def waffle(n, n_late, cols=20, seed=3):
    """Un carré par matin de travail ; rouge = arrivée en retard (positions tirées au hasard)."""
    n, n_late = int(n), int(min(max(n_late, 0), n))
    flags = np.zeros(n, bool)
    flags[np.random.default_rng(seed).choice(n, n_late, replace=False)] = True
    g = pd.DataFrame({"i": range(n)})
    g["x"], g["y"] = g["i"] % cols, g["i"] // cols
    g["Matin"] = np.where(flags, "En retard", "À l'heure")
    return alt.Chart(g).mark_square(size=170).encode(
        x=alt.X("x:O", axis=None), y=alt.Y("y:O", axis=None),
        color=alt.Color("Matin:N", scale=alt.Scale(domain=["À l'heure", "En retard"], range=["#D9DDD3", "#E4572E"]),
                        legend=alt.Legend(orient="bottom", title=None)),
        tooltip=["Matin:N"]).properties(width=cols * 16, height=(n // cols + 1) * 16)


def calendar_heatmap(z, year):
    """Calendrier façon GitHub : semaine × jour, couleur = régularité du jour."""
    c = z[z["date"].dt.year == year].groupby("date", as_index=False)["regularite"].mean()
    c["sem"] = c["date"].dt.isocalendar().week.astype(int)
    c["jour"] = c["date"].dt.dayofweek
    return alt.Chart(c).mark_rect(stroke="white").encode(
        x=alt.X("sem:O", title="Semaine"), y=alt.Y("jour:O", title=None, axis=alt.Axis(labelExpr=JOURS)),
        color=alt.Color("regularite:Q", title="Régularité %", scale=_div(c["regularite"])),
        tooltip=["date:T", alt.Tooltip("regularite:Q", format=".1f")]).properties(height=170)


def hour_week_heatmap(d):
    """Quand les perturbations commencent : jour de semaine × heure."""
    g = (d.assign(h=d["begin"].dt.hour, j=d["begin"].dt.dayofweek)
         .groupby(["j", "h"]).size().reset_index(name="n"))
    return alt.Chart(g).mark_rect().encode(
        x=alt.X("h:O", title="Heure de début"), y=alt.Y("j:O", title=None, axis=alt.Axis(labelExpr=JOURS)),
        color=alt.Color("n:Q", scale=alt.Scale(domain=[0, g["n"].max() / 2, g["n"].max()], range=["#F3F4F0", "#E4572E", "#7A2410"]), title="Perturbations"),
        tooltip=["j:O", "h:O", "n:Q"]).properties(height=200)


def dots100(pct, headline, lines, color):
    """Pictogramme « X personnes sur 100 » avec gros chiffre et source en sous-titre."""
    g = pd.DataFrame({"i": range(100)})
    g["x"], g["y"] = g["i"] % 10, g["i"] // 10
    g["on"] = np.where(g["i"] < pct, "oui", "non")
    return alt.Chart(g).mark_circle(size=130).encode(
        x=alt.X("x:O", axis=None), y=alt.Y("y:O", axis=None),
        color=alt.Color("on:N", scale=alt.Scale(domain=["oui", "non"], range=[color, "#E3E6E0"]), legend=None),
    ).properties(width=190, height=190, title=alt.TitleParams(
        text=headline, subtitle=lines, anchor="start", fontSize=34, subtitleFontSize=12, subtitleColor="gray"))


def dumbbell(rows):
    """Comparaison de deux groupes par question : deux points reliés (haltère)."""
    d = pd.DataFrame(rows, columns=["question", "groupe", "valeur"])
    d["etiquette"] = d["groupe"] + " : " + d["valeur"].astype(int).astype(str) + " %"
    base = alt.Chart(d).encode(y=alt.Y("question:N", title=None, sort=None, axis=alt.Axis(labelLimit=320, labelFontSize=13)))
    x = alt.X("valeur:Q", title="%", scale=alt.Scale(domain=[0, 50]))
    rule = base.mark_rule(color="#b0bec5", strokeWidth=5).encode(x=alt.X("min(valeur):Q", scale=alt.Scale(domain=[0, 50]), title="%"),
                                                                 x2="max(valeur):Q")
    pts = base.mark_circle(size=520, opacity=1).encode(x=x, color=alt.Color("groupe:N", legend=None,
                                                                            scale=alt.Scale(domain=list(d["groupe"]), range=["#3A8FB7", "#1F6A8C", "#F28B6B", "#C0401A"])))
    txt = base.mark_text(dy=-26, fontWeight="bold", fontSize=12).encode(x=x, text="etiquette:N")
    return (rule + pts + txt).properties(height=70 * d["question"].nunique() + 30)



def lollipop(d, cat, val, unit=""):
    """Classement en sucettes : les 3 premiers en orange, les autres en bleu."""
    d = d.sort_values(val, ascending=False).copy()
    d["rang"] = np.where(np.arange(len(d)) < 3, "top", "autre")
    base = alt.Chart(d).encode(y=alt.Y(f"{cat}:N", sort=None, title=None, axis=alt.Axis(labelLimit=260)),
                               x=alt.X(f"{val}:Q", title=unit))
    col = alt.Color("rang:N", legend=None, scale=alt.Scale(domain=["top", "autre"], range=["#E4572E", "#1F6A8C"]))
    return (base.mark_rule(strokeWidth=3, color="#C9CDD8").encode(x2=alt.value(0))
            + base.mark_circle(size=170, opacity=1).encode(color=col)
            + base.mark_text(align="left", dx=14, fontSize=12, fontWeight="bold").encode(
                text=alt.Text(f"{val}:Q", format=",.1f"))).properties(height=26 * len(d) + 40)


def bubble(r):
    """Nuage de bulles : perturbation moyenne (x) × actifs (y), taille = score d'exposition."""
    base = alt.Chart(r).encode(
        x=alt.X("heures_moy:Q", title="Perturbation moyenne des lignes (heures pondérées)"),
        y=alt.Y("actifs:Q", title="Actifs concernés"))
    dots = base.mark_circle(opacity=0.7, color="#1F6A8C").encode(
        size=alt.Size("score:Q", legend=None, scale=alt.Scale(range=[60, 1400])),
        tooltip=["commune:N", alt.Tooltip("actifs:Q", format=",.0f"), alt.Tooltip("heures_moy:Q", format=".1f"),
                 alt.Tooltip("score:Q", format=",.0f")])
    names = (base.transform_window(rk="rank()", sort=[alt.SortField("score", "descending")])
             .transform_filter("datum.rk <= 5").mark_text(dy=-16, fontWeight="bold", fontSize=12)
             .encode(text="commune:N"))
    return (dots + names).properties(height=340)


def histo(tot, margin):
    """Distribution du retard cumulé par trajet, avec la marge de l'employé en trait orange."""
    d = pd.DataFrame({"retard": np.clip(tot, 0, 60)})
    bars = alt.Chart(d).mark_bar(color="#1F6A8C", cornerRadiusTopLeft=3, cornerRadiusTopRight=3).encode(
        x=alt.X("retard:Q", bin=alt.Bin(step=5, extent=[0, 60]), title="Minutes de retard cumulées sur le trajet"),
        y=alt.Y("count():Q", title="Trajets simulés"))
    rule = alt.Chart(pd.DataFrame({"m": [margin]})).mark_rule(color="#E4572E", strokeWidth=3, strokeDash=[6, 4]).encode(x="m:Q")
    return (bars + rule).properties(height=260)


def lines_year(d):
    """Heures perdues par an, une courbe par ligne."""
    base = alt.Chart(d).encode(x=alt.X("annee:O", title=None, axis=alt.Axis(labelAngle=0)),
                               y=alt.Y("heures:Q", title="Heures perdues par an"),
                               color=alt.Color("ligne:N", legend=alt.Legend(orient="bottom", title=None)))
    return (base.mark_line(strokeWidth=3) + base.mark_circle(size=70, opacity=1)).properties(height=300)

# ---------------------------------------------------------------- onglet Résultats
def month_bars(pm):
    """H1 : ponctualité moyenne par mois, mois d'hiver en orange."""
    lo = float(pm["taux"].min()) - 1.5
    base = alt.Chart(pm).encode(x=alt.X("nom:N", sort=MOIS, title=None, axis=alt.Axis(labelAngle=0)))
    bars = base.mark_bar(cornerRadiusTopLeft=6, cornerRadiusTopRight=6).encode(
        y=alt.Y("taux:Q", title="Ponctualité %", scale=alt.Scale(domain=[lo, 100], clamp=True)),
        color=alt.Color("saison:N", scale=alt.Scale(domain=["Hiver", "Reste de l'année"], range=["#E4572E", "#1F6A8C"]),
                        legend=alt.Legend(orient="bottom", title=None)),
        tooltip=["nom:N", alt.Tooltip("taux:Q", title="Ponctualité %", format=".1f")])
    txt = base.mark_text(dy=-8, fontSize=11, fontWeight="bold").encode(y="taux:Q", text=alt.Text("taux:Q", format=".1f"))
    return (bars + txt).properties(height=280)


def trend(an):
    """H2 : ponctualité annuelle et droite de tendance."""
    base = alt.Chart(an).encode(x=alt.X("annee:O", title=None, axis=alt.Axis(labelAngle=0)))
    pts = base.mark_line(color="#1F6A8C", strokeWidth=3, point=alt.OverlayMarkDef(size=80, filled=True, color="#1F6A8C")).encode(
        y=alt.Y("taux:Q", title="Ponctualité moyenne %", scale=alt.Scale(zero=False)),
        tooltip=["annee:O", alt.Tooltip("taux:Q", format=".2f")])
    tr = base.mark_line(color="#E4572E", strokeDash=[6, 4], strokeWidth=2).encode(y="tendance:Q")
    return (pts + tr).properties(height=280)


def late_dots(m):
    """H3 : voyageurs en retard sur 100, une ligne par rangée (pictogramme)."""
    rows = []
    for _, r in m.iterrows():
        k = int(round(r["en_retard"]))
        for i in range(100):
            rows.append({"ligne": r["ligne"], "i": i, "etat": "En retard (≥ 5 min)" if i < k else "À l'heure",
                         "val": f"{r['en_retard']:.1f} sur 100"})
    g = pd.DataFrame(rows)
    return alt.Chart(g).mark_circle(size=34).encode(
        x=alt.X("i:O", axis=None),
        y=alt.Y("ligne:N", sort=list(m["ligne"]), title=None, axis=alt.Axis(labelLimit=260)),
        color=alt.Color("etat:N", scale=alt.Scale(domain=["En retard (≥ 5 min)", "À l'heure"], range=["#E4572E", "#E3E6E0"]),
                        legend=alt.Legend(orient="bottom", title=None)),
        tooltip=["ligne:N", alt.Tooltip("val:N", title="Voyageurs en retard")]).properties(height=24 * len(m) + 30)


def hour_profile(prof):
    """H4 : nombre d'incidents par heure de début, heures de pointe en orange."""
    return alt.Chart(prof).mark_bar(cornerRadiusTopLeft=4, cornerRadiusTopRight=4).encode(
        x=alt.X("heure:O", title="Heure de début", axis=alt.Axis(labelAngle=0)),
        y=alt.Y("n:Q", title="Incidents"),
        color=alt.Color("pointe:N", scale=alt.Scale(domain=["Heure de pointe", "Autre"], range=["#E4572E", "#1F6A8C"]),
                        legend=alt.Legend(orient="bottom", title=None)),
        tooltip=["heure:O", "n:Q"]).properties(height=260)


def month_risk(n, p, thr):
    """Probabilité d'avoir k matins en retard dans un mois (loi binomiale), seuil en orange."""
    from math import comb
    k = np.arange(0, n + 1)
    pr = np.array([comb(n, i) * p**i * (1 - p) ** (n - i) for i in k])
    d = pd.DataFrame({"k": k, "proba": pr})
    d = d[(d["k"] <= max(thr + 4, int(n * p * 3) + 2))]
    d["zone"] = np.where(d["k"] >= thr, f"{thr} retards ou plus", "Moins")
    return alt.Chart(d).mark_bar(cornerRadiusTopLeft=4, cornerRadiusTopRight=4).encode(
        x=alt.X("k:O", title="Matins en retard dans le mois", axis=alt.Axis(labelAngle=0)),
        y=alt.Y("proba:Q", title="Probabilité", axis=alt.Axis(format="%")),
        color=alt.Color("zone:N", scale=alt.Scale(domain=[f"{thr} retards ou plus", "Moins"], range=["#E4572E", "#1F6A8C"]),
                        legend=alt.Legend(orient="bottom", title=None)),
        tooltip=["k:O", alt.Tooltip("proba:Q", format=".1%")]).properties(height=240)


# ---------------------------------------------------------------- foule de 100 personnes
PERSON = ("M -0.28,-0.62 A 0.28,0.28 0 1,0 0.28,-0.62 A 0.28,0.28 0 1,0 -0.28,-0.62 Z "
          "M -0.48,1 L -0.48,0.08 Q -0.48,-0.24 0,-0.24 Q 0.48,-0.24 0.48,0.08 L 0.48,1 Z")


def crowd(groups, color):
    """Une foule de 100 silhouettes par groupe ; les personnes concernées sont colorées.
    groups : liste de (libellé, pourcentage)."""
    charts = []
    for i, (lab, pct) in enumerate(groups):
        g = pd.DataFrame({"k": range(100)})
        g["x"], g["y"] = g["k"] % 10, g["k"] // 10
        g["etat"] = np.where(g["k"] < round(pct), "Concerné", "Non concerné")
        g["groupe"] = lab
        c = alt.Chart(g).mark_point(shape=PERSON, filled=True, size=420, opacity=1).encode(
            x=alt.X("x:O", axis=None), y=alt.Y("y:O", axis=None),
            color=alt.Color("etat:N", legend=None,
                            scale=alt.Scale(domain=["Concerné", "Non concerné"],
                                            range=[color, "#DADDD6"])),
            tooltip=[alt.Tooltip("groupe:N", title="Groupe"), alt.Tooltip("etat:N", title=" ")],
        ).properties(width=250, height=270, title=alt.TitleParams(
            text=f"{pct} %", subtitle=f"{lab} · {round(pct)} personnes sur 100", anchor="start",
            fontSize=40, color=color, subtitleFontSize=14, subtitleColor="#1B1F2A", subtitleFontWeight=600))
        charts.append(c)
    return alt.hconcat(*charts, spacing=60).configure_view(stroke=None)


def _soft(hexc, i):
    """Teinte plus claire pour le groupe de comparaison."""
    r, g, b = (int(hexc[j:j + 2], 16) for j in (1, 3, 5))
    t = 0.45 if i == 1 else 0.65
    return "#%02X%02X%02X" % tuple(int(v + (255 - v) * t) for v in (r, g, b))
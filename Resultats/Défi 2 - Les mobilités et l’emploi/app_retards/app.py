"""Retards de transport : impact sur le travail et le quotidien (Île-de-France).
Uniquement des données réelles : aucune valeur de démonstration."""
import io
from math import comb
from pathlib import Path

import numpy as np
import pandas as pd
import streamlit as st

import analyses as an
import style
import viz
from parse_archive import line_stats, load_archive

st.set_page_config(page_title="Retards & vie de salarié", layout="wide")
style.apply()


def first_csv(dirname, contains=""):
    for f in sorted((Path("data/history") / dirname).glob("*.csv")):
        if contains in f.name:
            return f.read_bytes()
    return None


@st.cache_data
def get_transilien(raw):
    return an.load_transilien(raw)


@st.cache_data
def get_sncf(raw):
    return an.load_sncf(raw)


@st.cache_data
def get_archive(raw):
    return load_archive(io.BytesIO(raw))


@st.cache_data
def get_results(raw_tr, raw_arch):
    h = an.load_transilien(raw_tr)
    inc = an.incidents(load_archive(io.BytesIO(raw_arch))) if raw_arch else None
    return an.h1_hiver(h), an.h2_tendance(h), an.h3_ecarts(h), an.h4_pointe(inc)


def fr(x, d=0):
    return f"{x:,.{d}f}".replace(",", " ").replace(".", ",")


# ---------------- Données réelles ----------------
raw_tr = first_csv("regularite-mensuelle-transilien")
ARCHIVE = Path("disruptions.jsonl.gz")  # écrit par collector.py
raw_arch = ARCHIVE.read_bytes() if ARCHIVE.exists() else None

with st.sidebar:
    style.brand()
    st.header("Données réelles")
    if raw_tr is None:
        st.error("Ponctualité Transilien absente.")
    up_arch = st.file_uploader("Archive PRIM (.jsonl.gz de collector.py)", type="gz")
    if up_arch is not None:
        raw_arch = up_arch.getvalue()
    st.header("Votre situation")
    days = st.slider("Jours travaillés par semaine", 1, 7, 5)
    weeks = st.slider("Semaines travaillées par an", 30, 52, 45)
    diag = st.checkbox("Mode diagnostic (données brutes)", value=False)

style.hero()

if raw_tr is None:
    st.error("Aucune donnée réelle trouvée. Dans le dossier du projet, lancez `python backfill.py`, "
             "puis rechargez la page (touche R).")
    st.stop()

hist = get_transilien(raw_tr)
arch = get_archive(raw_arch) if raw_arch else None
if arch is not None and arch.empty:
    arch = None
mornings = days * weeks

with st.sidebar:
    st.caption(f"Ponctualité : {hist['date'].min():%m/%Y} → {hist['date'].max():%m/%Y} · "
               f"{hist['ligne'].nunique()} lignes")
    if arch is not None:
        st.caption(f"Archive PRIM : {str(arch['fetched_at'].min())[:16]} → {str(arch['fetched_at'].max())[:16]}")
    else:
        st.caption("Archive PRIM : pas encore de fichier `disruptions.jsonl.gz`.")

T = 8
tabs = st.tabs(["1 · Résultats", "2 · Mon trajet", "3 · Classement des lignes", "4 · Historique",
                "5 · Archive PRIM", "6 · Communes exposées", "7 · Santé & emploi", "8 · Sources"])

# ---------------- 1. Résultats ----------------
with tabs[0]:
    style.head(1, T, "Résultats", "Ce que disent les *vraies* données",
               "Quatre hypothèses testées sur la ponctualité SNCF et sur l'archive PRIM, avec un test statistique.")
    r1, r2, r3, r4 = get_results(raw_tr, raw_arch)
    c = st.columns(4)
    with c[0]:
        style.verdict(r1["v"], "Plus de retards en hiver ?", f"{r1['diff']:+.1f} pt".replace(".", ","),
                      f"Déc.–févr. : {fr(r1['hiver'], 1)} % à l'heure, contre {fr(r1['autre'], 1)} % le reste de l'année "
                      f"(p = {r1['p']:.3f})")
    with c[1]:
        style.verdict(r2["v"], f"Dégradation depuis {r2['debut']} ?", f"{r2['pente']:+.2f} pt/an".replace(".", ","),
                      f"IC 95 % : {r2['lo']:+.2f} à {r2['hi']:+.2f} pt/an, années complètes {r2['debut']}–{r2['fin']}".replace(".", ","))
    with c[2]:
        style.verdict(r3["v"], "De gros écarts entre lignes ?", f"× {fr(r3['ratio'], 1)}",
                      f"Risque de retard sur {r3['worst']} par rapport à {r3['best']} ({r3['periode']}, p = {r3['p']:.3f})")
    with c[3]:
        if r4["v"] == "nt":
            style.verdict("nt", "Plus d'incidents aux heures de pointe ?", f"{r4['n']} incidents",
                          "Il en faut au moins 30 : laissez tourner collector.py plusieurs jours.")
        else:
            style.verdict(r4["v"], "Plus d'incidents aux heures de pointe ?", f"{r4['part']:.0%}",
                          f"des incidents commencent entre 6–10 h ou 16–20 h, contre {r4['att']:.0%} si c'était au hasard "
                          f"(n = {r4['n']}, p = {r4['p']:.3f})")
    st.markdown("### H1 · Le calendrier des retards")
    viz.show(st, viz.month_bars(r1["mois"]), use_container_width=True)
    a, b = st.columns(2)
    a.markdown("### H2 · Quinze ans de ponctualité")
    viz.show(a, viz.trend(r2["annuel"]), use_container_width=True)
    b.markdown("### H3 · Sur 100 voyageurs, combien en retard ?")
    viz.show(b, viz.late_dots(r3["lignes"]), use_container_width=True)
    if r4["v"] != "nt":
        st.markdown("### H4 · À quelle heure le réseau déraille")
        viz.show(st, viz.hour_profile(r4["profil"]), use_container_width=True)
    st.caption("Ponctualité = part des voyageurs arrivés avec moins de 5 min de retard (SNCF Transilien et RER). "
               "Tests de permutation (H1, H3), bootstrap sur la pente (H2), test binomial (H4) ; seuil 5 %. "
               "Associations observées, pas des liens de cause à effet.")

# ---------------- 2. Mon trajet ----------------
with tabs[1]:
    style.head(2, T, "Mon trajet", "Vos *retards*, matin après matin",
               "Ponctualité réelle de vos lignes sur les 12 derniers mois.")
    p12 = an.last12(hist).groupby("ligne")["taux"].mean()
    c1, c2 = st.columns(2)
    mes = c1.multiselect("Les lignes de mon trajet (dans l'ordre)", list(p12.index),
                         default=[p12.idxmin()], max_selections=3)
    wage = c2.number_input("Salaire net horaire (€)", 8.0, 100.0, 14.0)
    thr = c2.slider("Nombre de retards par mois à surveiller", 1, 10, 3)
    if not mes:
        st.info("Choisissez au moins une ligne.")
    else:
        pl = [1 - p12[l] / 100 for l in mes]
        p_any = 1 - np.prod([1 - p for p in pl])
        late_am = p_any * mornings
        min_lost = 2 * mornings * sum(pl) * 5
        n_month = round(mornings / 12)
        p_month = 1 - sum(comb(n_month, i) * p_any**i * (1 - p_any) ** (n_month - i) for i in range(min(thr, n_month + 1)))
        m = st.columns(4)
        m[0].metric("Matins avec ≥ 5 min de retard / an", fr(late_am), f"{p_any:.1%} des trajets")
        m[1].metric("Temps perdu par an, au minimum", f"{fr(min_lost / 60, 1)} h", "aller + retour", delta_color="off")
        m[2].metric(f"Risque d'avoir ≥ {thr} retards dans un mois", f"{p_month:.0%}")
        m[3].metric("Retenue possible / an, au minimum", f"{fr(min_lost / 2 / 60 * wage)} €",
                    "si les retards du matin sont retenus", delta_color="off")
        st.subheader(f"Vos {mornings} matins de l'année")
        viz.show(st, viz.waffle(mornings, round(late_am)))
        st.caption("Un carré = un matin ; orange = arrivée avec au moins 5 min de retard. "
                   "Le nombre de carrés orange vient de la ponctualité réelle, leur place est tirée au hasard.")
        st.subheader("Combien de matins en retard dans un mois ?")
        viz.show(st, viz.month_risk(n_month, p_any, thr), use_container_width=True)
        st.caption("Minimum = chaque retard compté pour 5 min : la SNCF publie la part de voyageurs en retard, "
                   "pas la durée des retards. Lignes supposées indépendantes, correspondances ratées non comptées.")

# ---------------- 3. Classement ----------------
with tabs[2]:
    style.head(3, T, "Classement", "Les lignes qui vous mettent le plus en *retard*",
               "Voyageurs arrivés avec au moins 5 min de retard, sur 100, 12 derniers mois.")
    d = (100 - an.last12(hist).groupby("ligne")["taux"].mean()).rename("sur 100").reset_index()
    d["heures"] = d["sur 100"] / 100 * 5 * 2 * mornings / 60
    a, b = st.columns(2)
    a.markdown("**Voyageurs en retard sur 100**")
    viz.show(a, viz.lollipop(d, "ligne", "sur 100", "sur 100 voyageurs"), use_container_width=True)
    b.markdown("**Heures perdues par an pour un navetteur, au minimum**")
    viz.show(b, viz.lollipop(d, "ligne", "heures", "heures / an"), use_container_width=True)

# ---------------- 4. Historique ----------------
with tabs[3]:
    style.head(4, T, "Historique", "Des années de *retards* en un coup d'œil",
               "Ponctualité mensuelle des lignes Transilien et RER, mois après mois.")
    if diag:
        st.dataframe(hist.head(20))
    lignes = sorted(hist["ligne"].unique())
    rer = [l for l in lignes if l.startswith("RER")]
    sel = st.multiselect("Lignes", lignes, default=rer or lignes[:6])
    h = hist[hist["ligne"].isin(sel)]
    if h.empty:
        st.warning("Sélectionnez au moins une ligne.")
    else:
        st.markdown("### La carte de chaleur des retards")
        st.caption("Chaque case est un mois : orange = mois difficile, bleu = mois fiable.")
        viz.show(st, viz.heatmap_lines(h), use_container_width=True)
        c1, c2 = st.columns(2)
        c1.markdown("### La course des lignes")
        c1.caption("Rang annuel de ponctualité : qui monte, qui décroche.")
        viz.show(c1, viz.bump(h), use_container_width=True)
        c2.markdown("### L'horloge des retards")
        c2.caption("Plus le secteur est grand et foncé, plus ce mois est en retard.")
        viz.show(c2, viz.radial_months(h), use_container_width=True)
        st.markdown("### Chaque ligne en détail")
        st.caption("Le point marque le pire mois de la ligne.")
        viz.show(st, viz.small_multiples(h))
        st.markdown("### Heures perdues par an pour un navetteur, au minimum")
        yr = h.groupby(["annee", "ligne"])["taux"].mean().reset_index()
        yr["heures"] = (1 - yr["taux"] / 100) * 5 * 2 * mornings / 60
        viz.show(st, viz.lines_year(yr), use_container_width=True)
    reg = first_csv("regularite-quotidienne-lignes-sncf", "regularite")
    if reg is not None:
        with st.expander("Calendrier de régularité SNCF (archive, s'arrête fin 2023)"):
            sn = get_sncf(reg)
            cc1, cc2 = st.columns(2)
            lg = cc1.selectbox("Ligne SNCF", sorted(sn["ligne"].dropna().unique()), key="sncf")
            yan = cc2.selectbox("Année", sorted(sn["date"].dt.year.unique(), reverse=True), key="sncf_an")
            z = sn[sn["ligne"] == lg]
            if z[z["date"].dt.year == yan].empty:
                st.info("Pas de données pour cette ligne cette année-là.")
            else:
                viz.show(st, viz.calendar_heatmap(z, yan), use_container_width=True)

# ---------------- 5. Archive PRIM ----------------
stats = None
with tabs[4]:
    style.head(5, T, "Archive PRIM", "Quand le réseau *déraille*",
               "Les perturbations relevées toutes les 5 minutes sur l'API PRIM d'Île-de-France Mobilités.")
    if arch is None:
        st.info("Pas encore d'archive : lancez `python collector.py` dans le dossier du projet. "
                "Le fichier `disruptions.jsonl.gz` apparaît au premier appel réussi.")
    else:
        if diag:
            st.dataframe(arch.head(20))
        opts = sorted(arch["cause"].dropna().unique())
        f1, f2 = st.columns(2)
        causes = f1.multiselect("Causes retenues", opts, default=[c for c in ["PERTURBATION"] if c in opts])
        max_h = f2.slider("Durée maximale retenue (h)", 1, 24 * 30, 72,
                          help="Écarte les messages de long terme (travaux jusqu'en 2027, réorganisations).")
        refu = st.file_uploader("Référentiel des lignes IDFM (CSV) : remplace les identifiants par les noms",
                                type="csv", key="ref")
        a2 = arch.copy()
        if refu is not None:
            ref = pd.read_csv(io.BytesIO(refu.getvalue()), sep=None, engine="python", dtype=str)
            rc = list(ref.columns)
            k1, k2 = st.columns(2)
            cid = k1.selectbox("Colonne identifiant de ligne", rc, key="rid")
            cnm = k2.selectbox("Colonne nom court", rc, index=min(1, len(rc) - 1), key="rnm")
            mp = {}
            for i, n in zip(ref[cid], ref[cnm]):
                mp[str(i).replace("line:", "")] = n
                mp[str(i).split(":")[-1]] = n
            key = a2["line_id"].astype(str).str.replace("line:", "", regex=False)
            a2["line"] = key.map(mp).fillna(key.str.split(":").str[-1].map(mp)).fillna(a2["line"])
        d = a2[a2["cause"].isin(causes)] if causes else a2
        d = d[(d["end"] - d["begin"]).dt.total_seconds() / 3600 <= max_h]
        d = (d.dropna(subset=["begin"]).sort_values("last_update")
             .groupby(["disruption_id", "line", "begin"], as_index=False)
             .agg(end=("end", "max"), cause=("cause", "last"), severity=("severity", "last")))
        stats = line_stats(d)
        if stats.empty:
            st.warning("Aucune perturbation ne correspond à ces filtres.")
            stats = None
        else:
            k = st.columns(3)
            k[0].metric("Perturbations distinctes", fr(d["disruption_id"].nunique()))
            k[1].metric("Heures cumulées", fr(stats["heures"].sum()))
            k[2].metric("Ligne la plus touchée", str(stats.index[0]))
            st.markdown("**Heures de perturbation pondérées par ligne** (bloquante = 1, perturbée = 0,5) · 15 premières")
            viz.show(st, viz.lollipop(stats.head(15).reset_index(), "line", "heures_ponderees", "heures pondérées"),
                     use_container_width=True)
            st.markdown("**Quand les perturbations commencent (jour × heure)**")
            viz.show(st, viz.hour_week_heatmap(d), use_container_width=True)
            st.caption(f"Période couverte : {str(arch['fetched_at'].min())[:16]} → {str(arch['fetched_at'].max())[:16]}. "
                       "Les chiffres ne valent que pour cette période de collecte.")

# ---------------- 6. Communes ----------------
with tabs[5]:
    style.head(6, T, "Communes", "Où les actifs sont le plus *exposés*",
               "Actifs en transports en commun × perturbations des lignes qui desservent leur commune.")
    up_lc = st.file_uploader("Lien ligne → commune (CSV avec colonnes ligne, code_insee), "
                             "construit depuis « Arrêts et lignes associées » d'IDFM", type="csv", key="lc")
    up_nav = st.file_uploader("Actifs par commune (INSEE, flux domicile-travail ou NAV2)", type="csv", key="nav")
    if stats is None or up_lc is None or up_nav is None:
        st.info("Cet onglet a besoin de trois fichiers réels : l'archive PRIM (onglet 5), le lien ligne → commune "
                "et les actifs par commune de l'INSEE. Aucun calcul n'est affiché sans eux.")
    else:
        lc = pd.read_csv(io.BytesIO(up_lc.getvalue()), sep=None, engine="python", dtype=str)
        nav = pd.read_csv(io.BytesIO(up_nav.getvalue()), sep=None, engine="python", dtype=str)
        if not {"ligne", "code_insee"}.issubset(lc.columns):
            st.error("Le lien ligne → commune doit avoir les colonnes ligne et code_insee.")
        else:
            cols = list(nav.columns)
            a, b, c = st.columns(3)
            ccom = a.selectbox("Colonne commune", cols, index=0)
            ceff = b.selectbox("Colonne effectif", cols, index=len(cols) - 1)
            cmode = c.selectbox("Colonne mode (optionnel)", ["(aucune)"] + cols)
            if cmode != "(aucune)":
                vals = sorted(nav[cmode].dropna().unique())
                keep = st.multiselect("Modes exposés aux retards", vals,
                                      default=[v for v in vals if "commun" in v.lower()] or vals[:1])
                nav = nav[nav[cmode].isin(keep)]
            nav[ceff] = pd.to_numeric(nav[ceff], errors="coerce")
            actifs = nav.groupby(ccom)[ceff].sum().rename("actifs")
            expo = (lc.merge(stats[["heures_ponderees"]], left_on="ligne", right_index=True)
                    .groupby("code_insee").agg(lignes=("ligne", "nunique"), heures_moy=("heures_ponderees", "mean")))
            res = actifs.to_frame().join(expo, how="inner")
            res["score"] = res["actifs"] * res["heures_moy"]
            res = res.sort_values("score", ascending=False)
            if res.empty:
                st.warning("Aucune commune en commun : vérifiez les codes INSEE (5 caractères, en texte).")
            else:
                r = res.rename_axis("commune").reset_index()
                viz.show(st, viz.bubble(r), use_container_width=True)
                viz.show(st, viz.lollipop(r.head(15), "commune", "score", "score d'exposition"), use_container_width=True)

# ---------------- 7. Santé & emploi (enquêtes publiées) ----------------
THEMES = {
    "Fatigue et santé": dict(
        q="Les trajets fatiguent-ils ?", color="#1F6A8C",
        groups=[("Étudiants et actifs", 30)],
        msg="**3 personnes sur 10** disent que leurs trajets les fatiguent ou abîment leur santé.",
        src="Terram / Alliance pour la santé mentale (Ifop), 2025 · 3 300 personnes"),
    "Anxiété": dict(
        q="Les trajets rendent-ils anxieux ?", color="#B23A86",
        groups=[("Urbains", 39), ("Ruraux", 30)],
        msg="En ville, **9 personnes de plus sur 100** citent leurs trajets comme source d'anxiété.",
        src="Terram / Alliance pour la santé mentale (Ifop), 2025 · 3 300 personnes"),
    "Emploi refusé": dict(
        q="Le transport fait-il perdre des emplois ?", color="#E4572E",
        groups=[("Sans permis B", 37), ("Ensemble", 23), ("Avec permis B", 17)],
        msg="Sans permis, on refuse **2 fois plus souvent** un emploi faute de transport.",
        src="Elabe / Laboratoire de la mobilité inclusive, 2017 · 1 003 personnes"),
}

with tabs[6]:
    style.head(7, T, "Santé & emploi", "Ce que les trajets font à la *santé* et à l'emploi",
               "Chaque foule représente 100 personnes interrogées : en couleur, celles qui sont concernées.")
    choix = st.radio("Thème", list(THEMES), horizontal=True, label_visibility="collapsed")
    th = THEMES[choix]
    st.markdown(f"### {th['q']}")
    viz.show(st, viz.crowd(th["groups"], th["color"]))
    st.markdown(f"<div style='font-size:20px;margin:6px 0 2px'>{th['msg'].replace('**', '<b>', 1).replace('**', '</b>', 1)}</div>"
                f"<div style='font-size:12px;color:#8A8F9C'>Source : {th['src']}</div>", unsafe_allow_html=True)
    st.markdown(
        """<div style="padding:22px 28px;border-radius:16px;background:#141A2E;color:white;margin-top:26px;display:flex;gap:28px;align-items:center">
        <div style="font-family:Outfit,sans-serif;font-size:64px;font-weight:800;color:#F28B6B;line-height:1">69</div>
        <div><div style="font-size:19px;font-weight:700;line-height:1.35">études : retards et embouteillages vont de pair avec un moins bon bien-être mental.</div>
        <div style="opacity:.7;font-size:12px;margin-top:8px">Revue systématique · Transport Reviews, 2022</div></div></div>""",
        unsafe_allow_html=True)

# ---------------- 8. Sources ----------------
with tabs[7]:
    style.head(8, T, "Sources", "D'où viennent les *données*", "Ce qui est branché, et ce qui reste à brancher.")
    style.cards([
        ("Branché", ["Ponctualité mensuelle Transilien (SNCF)", "Régularité quotidienne SNCF (jusqu'en 2023)",
                     "API PRIM : perturbations (collecte)"]),
        ("À brancher", ["Arrêts et lignes associées (IDFM)", "INSEE flux domicile-travail", "Validations réseau ferré",
                        "Référentiel des lignes IDFM"]),
        ("Enquêtes citées", ["Terram / Ifop 2025", "Elabe / LMI 2017", "Transport Reviews 2022"])])
    with st.expander("Mettre à jour les données"):
        st.code("python backfill.py      # ponctualité SNCF\npython collector.py     # perturbations PRIM, toutes les 5 min\n"
                "python -m streamlit run app.py", language="bash")
"""Chargement des données RÉELLES et tests d'hypothèses (aucune valeur inventée)."""
import io

import numpy as np
import pandas as pd

HIVER = [12, 1, 2]
MOIS = ["janv", "févr", "mars", "avr", "mai", "juin", "juil", "août", "sept", "oct", "nov", "déc"]


# ---------------------------------------------------------------- chargement
def _read(raw, sep):
    for enc in ("utf-8-sig", "latin-1"):
        try:
            return pd.read_csv(io.BytesIO(raw), sep=sep, dtype=str, encoding=enc)
        except UnicodeDecodeError:
            continue
    raise ValueError("Encodage du fichier non reconnu")


def _num(s):
    return pd.to_numeric(s.astype(str).str.replace(",", ".", regex=False)
                         .str.replace("%", "", regex=False).str.strip(), errors="coerce")


def load_transilien(raw: bytes) -> pd.DataFrame:
    """Ponctualité mensuelle Transilien (SNCF) : Date;Service;Ligne;Nom de la ligne;Taux de ponctualité;..."""
    df = _read(raw, ";")
    df.columns = [c.strip() for c in df.columns]
    taux_col = next(c for c in df.columns if c.lower().startswith("taux"))
    df["taux"] = _num(df[taux_col])
    if df["taux"].dropna().max() <= 1.5:
        df["taux"] *= 100
    df["date"] = pd.to_datetime(df["Date"].str.strip(), format="%Y-%m", errors="coerce")
    if df["date"].isna().all():
        df["date"] = pd.to_datetime(df["Date"].str.strip(), errors="coerce")
    svc = df["Service"].fillna("").str.strip()
    code = df["Ligne"].fillna("").str.strip()
    nom = df["Nom de la ligne"].fillna("").str.strip()
    df["ligne"] = np.where(svc.str.upper() == "RER", "RER " + code, "Ligne " + code + " · " + nom)
    df["service"] = svc
    df = df.dropna(subset=["taux", "date"])
    df["annee"] = df["date"].dt.year
    df["mois"] = df["date"].dt.month
    return df[["date", "annee", "mois", "service", "ligne", "taux"]].sort_values("date")


def load_sncf(raw: bytes) -> pd.DataFrame:
    df = _read(raw, ",")
    df["date"] = pd.to_datetime(df["date"], errors="coerce")
    df["regularite"] = _num(df["regularite"])
    if df["regularite"].dropna().max() <= 1.5:
        df["regularite"] *= 100
    return df.dropna(subset=["date", "regularite"])


def last12(df):
    return df[df["date"] > df["date"].max() - pd.DateOffset(months=12)]


def incidents(arch: pd.DataFrame, max_h=72, causes=("PERTURBATION",)) -> pd.DataFrame:
    """Incidents distincts (une ligne par perturbation et par période), hors travaux longs."""
    d = arch.dropna(subset=["begin", "end"])
    if causes:
        d = d[d["cause"].isin(causes)]
    d = d[(d["end"] - d["begin"]).dt.total_seconds() / 3600 <= max_h]
    return d.drop_duplicates(["disruption_id", "begin"])


# ---------------------------------------------------------------- tests
_rng = np.random.default_rng(42)


def _perm(a, b, n=10000):
    a, b = np.asarray(a, float), np.asarray(b, float)
    obs = a.mean() - b.mean()
    pool = np.concatenate([a, b])
    c = 0
    for _ in range(n):
        _rng.shuffle(pool)
        if abs(pool[:len(a)].mean() - pool[len(a):].mean()) >= abs(obs):
            c += 1
    return obs, (c + 1) / (n + 1)


def _verdict(p, sens_attendu):
    if p >= 0.05:
        return "nc"
    return "ok" if sens_attendu else "ko"


def h1_hiver(df):
    hiver, autre = df[df["mois"].isin(HIVER)]["taux"], df[~df["mois"].isin(HIVER)]["taux"]
    diff, p = _perm(hiver, autre)
    pm = df.groupby("mois", as_index=False)["taux"].mean()
    pm["nom"] = pm["mois"].map(lambda i: MOIS[i - 1])
    pm["saison"] = np.where(pm["mois"].isin(HIVER), "Hiver", "Reste de l'année")
    return dict(hiver=hiver.mean(), autre=autre.mean(), diff=diff, p=p, v=_verdict(p, diff < 0), mois=pm)


def h2_tendance(df):
    ok = df.groupby("annee")["mois"].nunique()
    an = df[df["annee"].isin(ok[ok >= 12].index)].groupby("annee", as_index=False)["taux"].mean()
    x, y = an["annee"].values.astype(float), an["taux"].values
    pente, b0 = np.polyfit(x, y, 1)
    boots = []
    for _ in range(5000):
        i = _rng.integers(0, len(x), len(x))
        if len(set(x[i])) > 2:
            boots.append(np.polyfit(x[i], y[i], 1)[0])
    lo, hi = np.percentile(boots, [2.5, 97.5])
    v = "ok" if hi < 0 else "ko" if lo > 0 else "nc"
    an["tendance"] = pente * x + b0
    return dict(annuel=an, pente=pente, lo=lo, hi=hi, v=v,
                debut=int(x.min()), fin=int(x.max()))


def h3_ecarts(df):
    r = last12(df)
    m = r.groupby("ligne", as_index=False)["taux"].mean().sort_values("taux")
    m["en_retard"] = 100 - m["taux"]
    worst, best = m.iloc[0], m.iloc[-1]
    diff, p = _perm(r[r["ligne"] == best["ligne"]]["taux"], r[r["ligne"] == worst["ligne"]]["taux"])
    return dict(lignes=m, worst=worst["ligne"], best=best["ligne"], diff=diff, p=p, v=_verdict(p, diff > 0),
                ratio=worst["en_retard"] / max(best["en_retard"], 0.01),
                periode=f"{r['date'].min():%m/%Y} – {r['date'].max():%m/%Y}")


def h4_pointe(inc):
    if inc is None or len(inc) < 30:
        return dict(v="nt", n=0 if inc is None else len(inc))
    h = inc["begin"].dt.hour
    pointe = (h.between(6, 9) | h.between(16, 19))
    k, n, att = int(pointe.sum()), len(h), 8 / 24
    sims = _rng.binomial(n, att, 20000)
    p = (np.sum(np.abs(sims - n * att) >= abs(k - n * att)) + 1) / 20001
    prof = h.value_counts().reindex(range(24), fill_value=0).rename_axis("heure").reset_index(name="n")
    prof["pointe"] = np.where(prof["heure"].between(6, 9) | prof["heure"].between(16, 19), "Heure de pointe", "Autre")
    return dict(v=_verdict(p, k / n > att), n=n, part=k / n, att=att, p=p, profil=prof)
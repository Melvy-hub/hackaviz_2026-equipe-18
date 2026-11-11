"""Lecture de l'archive PRIM (jsonl.gz de collector.py) -> tableau à plat.
Format réel observé : disruption = {id, applicationPeriods[{begin,end}], lastUpdate, cause (TRAVAUX|PERTURBATION),
severity (BLOQUANTE|PERTURBEE|...), title, impactedSections[{lineId, from, to}]}.
Les noms de lignes viennent de payload["lines"] s'il existe, sinon l'identifiant (ex. line:IDFM:C02437)
est conservé : l'app permet de le traduire avec le référentiel des lignes."""
import gzip
import json
import re

import pandas as pd

COLS = ["fetched_at", "disruption_id", "line_id", "line", "mode", "cause", "severity",
        "begin", "end", "last_update"]
WEIGHT = {"BLOQUANTE": 1.0, "BLOCKING": 1.0, "PERTURBEE": 0.5, "DISTURBED": 0.5}
TITLE_LINE = re.compile(r"\b(RER\s?[A-E]|Lignes?\s+\w+|Bus\s?\d+\w*|M[ée]tro\s?\d+\w*|Tram(?:way)?\s?T?\d+\w*)\b")


def _ts(s):
    return pd.to_datetime(s, format="%Y%m%dT%H%M%S", errors="coerce")


def _up(x):
    x = x.get("name") if isinstance(x, dict) else x
    return str(x).upper() if x else None


def _from_title(title):
    m = TITLE_LINE.search(title or "")
    return m.group(0).replace("Lignes", "Ligne") if m else "?"


def load_archive(fileobj) -> pd.DataFrame:
    rows = []
    with gzip.open(fileobj, "rt", encoding="utf-8") as f:
        for raw in f:
            snap = json.loads(raw)
            p = snap.get("payload", {})
            names, link = {}, {}
            for ln in p.get("lines", []):
                lid = ln.get("id")
                names[lid] = (ln.get("shortName") or ln.get("name") or lid, ln.get("mode"))
                for o in ln.get("impactedObjects", []):
                    for d in o.get("disruptionIds", []):
                        link.setdefault(d, set()).add(lid)
                for d in ln.get("disruptionIds", []):
                    link.setdefault(d, set()).add(lid)
            for d in p.get("disruptions", []):
                ids = {s.get("lineId") for s in d.get("impactedSections", []) if s.get("lineId")}
                ids |= link.get(d.get("id"), set())
                targets = [(i, *names.get(i, (i, None))) for i in sorted(ids)] or \
                          [(None, _from_title(d.get("title")), None)]
                for per in d.get("applicationPeriods") or [{}]:
                    for lid, lname, mode in targets:
                        rows.append({"fetched_at": snap.get("fetched_at"), "disruption_id": d.get("id"),
                                     "line_id": lid, "line": lname, "mode": mode,
                                     "cause": _up(d.get("cause")), "severity": _up(d.get("severity")),
                                     "begin": _ts(per.get("begin")), "end": _ts(per.get("end")),
                                     "last_update": _ts(d.get("lastUpdate"))})
    return pd.DataFrame(rows, columns=COLS)


def line_stats(d: pd.DataFrame) -> pd.DataFrame:
    """Par ligne : nb de perturbations, heures cumulées, heures pondérées (bloquante=1, perturbée=0,5)."""
    d = d.dropna(subset=["begin", "end"]).copy()
    d["heures"] = (d["end"] - d["begin"]).dt.total_seconds() / 3600
    d["hp"] = d["heures"] * d["severity"].map(WEIGHT).fillna(0.0)
    return (d.groupby("line").agg(perturbations=("disruption_id", "nunique"),
                                  heures=("heures", "sum"), heures_ponderees=("hp", "sum"))
            .sort_values("heures_ponderees", ascending=False))
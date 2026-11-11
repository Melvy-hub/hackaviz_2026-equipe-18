"""Télécharge l'HISTORIQUE de ponctualité publié sur data.gouv.fr dans data/history/.
Usage : python backfill.py
Affiche pour chaque fichier son nom, son nombre de lignes et ses colonnes : collez-moi
ces en-têtes pour que j'écrive le parseur et branche l'historique dans l'app."""
import re
from pathlib import Path

import requests

SLUGS = [
    "regularite-mensuelle-transilien",      # ponctualité mensuelle Transilien (depuis 2013)
    "regularite-quotidienne-lignes-sncf",   # archive quotidienne SNCF (arrêtée début 2024)
]
OUT = Path("data/history")

for slug in SLUGS:
    try:
        ds = requests.get(f"https://www.data.gouv.fr/api/1/datasets/{slug}/", timeout=30).json()
    except Exception as e:
        print(f"[{slug}] erreur API : {e}")
        continue
    print(f"\n== {ds.get('title', slug)} (maj : {ds.get('last_modified', '?')})")
    for res in ds.get("resources", []):
        if str(res.get("format", "")).lower() not in ("csv", "tsv"):
            continue
        name = re.sub(r"[^\w.-]+", "_", res.get("title") or res["id"]) + ".csv"
        path = OUT / slug / name
        path.parent.mkdir(parents=True, exist_ok=True)
        try:
            r = requests.get(res["url"], timeout=120)
            r.raise_for_status()
            path.write_bytes(r.content)
            lines = r.content.decode("utf-8", errors="replace").splitlines()
            print(f"- {path} : {len(lines) - 1} lignes\n  colonnes : {lines[0][:300] if lines else '(vide)'}")
        except Exception as e:
            print(f"- {name} : échec ({e})")

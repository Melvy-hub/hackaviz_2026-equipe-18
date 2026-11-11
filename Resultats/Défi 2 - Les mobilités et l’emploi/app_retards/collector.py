"""Archive l'API PRIM des perturbations (IDFM) dans un fichier JSONL compressé.

Usage : PRIM_API_KEY=xxx python collector.py
Quota par défaut : 1 000 requêtes/jour -> un appel toutes les 5 min (288/jour) suffit.
À VÉRIFIER : l'URL exacte sur https://prim.iledefrance-mobilites.fr/fr/apis/idfm-disruptions_bulk
"""
import datetime as dt
import gzip
import json
import os
import time

import requests

URL = os.getenv(
    "PRIM_DISRUPTIONS_URL",
    "https://prim.iledefrance-mobilites.fr/marketplace/disruptions_bulk/disruptions/v2",
)


def load_env(path=".env"):
    """Lit KEY=valeur dans .env (sans dépendance) sans écraser les variables déjà définies."""
    if os.path.exists(path):
        for line in open(path, encoding="utf-8"):
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                k, v = line.split("=", 1)
                os.environ.setdefault(k.strip(), v.strip().strip('"').strip("'"))


load_env()
KEY = os.environ.get("PRIM_API_KEY", "")
if not KEY or KEY == "votre_cle":
    raise SystemExit("PRIM_API_KEY manquante : créez un fichier .env (voir .env.example).")
EVERY = int(os.getenv("POLL_SECONDS", "300"))
OUT = os.getenv("OUT_FILE", "disruptions.jsonl.gz")

while True:
    now = dt.datetime.now(dt.timezone.utc).isoformat()
    try:
        r = requests.get(URL, headers={"apikey": KEY, "Accept": "application/json"}, timeout=30)
        r.raise_for_status()
        with gzip.open(OUT, "at", encoding="utf-8") as f:
            f.write(json.dumps({"fetched_at": now, "payload": r.json()}, ensure_ascii=False) + "\n")
        print(now, "ok")
    except Exception as e:  # on garde la boucle en vie
        print(now, "erreur :", e)
    time.sleep(EVERY)
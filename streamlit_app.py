"""
streamlit_app.py : lanceur pour Streamlit Community Cloud (branche de déploiement seulement, hors Pull Request).

Pourquoi ce fichier : le dossier imposé par les organisateurs (« Défi 2 - Les mobilités et l'emploi ») contient des
espaces. Streamlit Cloud installe les dépendances avec ce chemin sans guillemets : il est coupé aux espaces et
l'installation échoue (« Failed to parse: `-` », 2026-11-12). À la racine du dépôt, le chemin n'a plus d'espace.

Ce lanceur ne contient aucune logique : il exécute l'application réelle, sans la copier.
"""

import runpy
import sys
from pathlib import Path

# Dossier de l'application réelle (le seul endroit où le code est maintenu)
APPLICATION = (Path(__file__).parent / "Resultats" / "Défi 2 - Les mobilités et l’emploi" / "defi-2_equipe-18"
               / "production" / "application")
# utils.py et pages/ sont importés depuis ce dossier (une seule fois dans le chemin de recherche)
if str(APPLICATION) not in sys.path:
    sys.path.insert(0, str(APPLICATION))
# Modules de l'application oubliés avant chaque affichage : Python les relit, donc toujours à jour. Sans cela, après une
# mise à jour du dépôt, Streamlit Cloud gardait l'ancien utils.py en mémoire (constaté le 2026-11-12 : pages à jour,
# utils.py non). Coût : relire quelques petits fichiers ; les résultats en cache (st.cache_data) sont conservés.
for nom, module in list(sys.modules.items()):
    if str(getattr(module, "__file__", "") or "").startswith(str(APPLICATION)):
        del sys.modules[nom]
runpy.run_path(str(APPLICATION / "app.py"), run_name="__main__")

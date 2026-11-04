"""Recherche de communes françaises pour le champ « ville » de l'interface.

Les données viennent de data/communes.csv (API Géo du gouvernement),
généré par scripts/telecharger_communes.py.
"""

import csv
import unicodedata
from pathlib import Path

import streamlit as st

DATA_FILE = Path(__file__).resolve().parent.parent / "data" / "communes.csv"


ABBREVIATIONS = {"st": "saint", "ste": "sainte"}  # « St Malo » → « saint malo »


def _normalize(text: str) -> str:
    """Minuscules, sans accents, tirets et apostrophes remplacés par des espaces, « St » développé."""
    text = unicodedata.normalize("NFD", text.lower())
    text = "".join(c for c in text if unicodedata.category(c) != "Mn")
    words = text.replace("-", " ").replace("'", " ").replace(".", " ").split()
    return " ".join(ABBREVIATIONS.get(word, word) for word in words)


@st.cache_data
def load_communes() -> list[dict]:
    """Charge les communes une seule fois (déjà triées par population décroissante)."""
    with DATA_FILE.open(encoding="utf-8") as file:
        return [
            {
                "city": row["nom"],
                "department": row["departement"],
                "lat": float(row["lat"]),
                "lon": float(row["lon"]),
                "search": _normalize(row["nom"]),
            }
            for row in csv.DictReader(file)
        ]


def search_communes(query: str, limit: int = 20) -> list[dict]:
    """Renvoie les communes dont le nom commence par la saisie, puis celles qui la contiennent."""
    needle = _normalize(query)
    if not needle:
        return []

    communes = load_communes()
    starts = [c for c in communes if c["search"].startswith(needle)]
    if len(starts) >= limit:
        return starts[:limit]
    contains = [c for c in communes if needle in c["search"] and not c["search"].startswith(needle)]
    return (starts + contains)[:limit]


def format_commune(commune: dict) -> str:
    return f"{commune['city']} ({commune['department']})"

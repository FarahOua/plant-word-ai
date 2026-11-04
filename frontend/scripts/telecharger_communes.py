"""Télécharge la liste des communes françaises dans data/communes.csv.

Source : API Géo du gouvernement (https://geo.api.gouv.fr), données publiques.
À relancer seulement pour mettre la liste à jour :

    python scripts/telecharger_communes.py
"""

import csv
from pathlib import Path

import requests

URL = "https://geo.api.gouv.fr/communes?fields=nom,codeDepartement,population,centre&format=json"
OUTPUT = Path(__file__).resolve().parent.parent / "data" / "communes.csv"


def main() -> None:
    communes = requests.get(URL, timeout=60).json()

    rows = []
    for commune in communes:
        if not commune.get("centre"):
            continue
        lon, lat = commune["centre"]["coordinates"]
        rows.append({
            "nom": commune["nom"],
            "departement": commune["codeDepartement"],
            "population": commune.get("population") or 0,
            "lat": lat,
            "lon": lon,
        })

    # Les communes les plus peuplées en premier : elles sortent en tête des recherches
    rows.sort(key=lambda row: row["population"], reverse=True)

    OUTPUT.parent.mkdir(exist_ok=True)
    with OUTPUT.open("w", newline="", encoding="utf-8") as file:
        writer = csv.DictWriter(file, fieldnames=["nom", "departement", "population", "lat", "lon"])
        writer.writeheader()
        writer.writerows(rows)

    print(f"{len(rows)} communes enregistrées dans {OUTPUT}")


if __name__ == "__main__":
    main()

"""
Genere les PDF de documentation technique a partir des sources Markdown.

Reutilise le convertisseur de 00_documentation/_build_pdf.py plutot que de
dupliquer la logique de rendu : une seule mise en page pour tout le projet.

Le Markdown reste la source unique — les PDF ne sont jamais edites a la main.

Usage :
    python 08_rapport/_build_doc_pdf.py
"""

from __future__ import annotations

import sys
from pathlib import Path

DOSSIER = Path(__file__).resolve().parent
RACINE = DOSSIER.parent

sys.path.insert(0, str(RACINE / "00_documentation"))

from _build_pdf import convertir  # noqa: E402

DOCUMENTS = [
    "Documentation_Technique_ETL_EDA.md",
]


def main() -> None:
    for nom in DOCUMENTS:
        chemin = DOSSIER / nom
        if not chemin.exists():
            print(f"  ! introuvable : {nom}")
            continue
        sortie = convertir(chemin)
        ko = sortie.stat().st_size / 1024
        print(f"  {nom:44s} -> {sortie.name:44s} {ko:7.1f} Ko")
    print("\nTermine.")


if __name__ == "__main__":
    main()

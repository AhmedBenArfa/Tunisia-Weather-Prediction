"""
Orchestrateur ETL : charge le Parquet brut, controle, nettoie, controle a
nouveau, ecrit le Parquet propre.

Idempotent : relançable sans effet de bord.

Usage :
    python 01_etl/run_etl.py
"""

from __future__ import annotations

import sys
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))

import checks
import clean
import config


def afficher(titre: str, lignes: list[str]) -> None:
    print(f"\n--- {titre} ---")
    if not lignes:
        print("  aucune anomalie")
        return
    for ligne in lignes:
        print(f"  ! {ligne}")


def main() -> int:
    if not config.PARQUET_BRUT.exists():
        print(f"Introuvable : {config.PARQUET_BRUT}")
        print("Lancer d'abord 01_etl/build_parquet.py")
        return 1

    print(f"Lecture de {config.PARQUET_BRUT.name}")
    df = pd.read_parquet(config.PARQUET_BRUT)
    print(f"  {len(df):,} lignes x {df.shape[1]} colonnes")

    afficher("Controles avant nettoyage", checks.executer_controles(df))

    df, journal = clean.nettoyer(df)
    afficher("Corrections appliquees", journal)

    restantes = checks.executer_controles(df)
    afficher("Controles apres nettoyage", restantes)

    if restantes:
        print("\nDes anomalies subsistent : le Parquet propre n'est pas ecrit.")
        return 1

    df.to_parquet(config.PARQUET_PROPRE, compression="zstd", index=False)
    taille = config.PARQUET_PROPRE.stat().st_size / 1e6
    print(f"\n--- Termine ---")
    print(f"Ecrit : {config.PARQUET_PROPRE.name}  ({taille:.1f} Mo)")
    print(f"  lignes   : {len(df):,}")
    print(f"  periode  : {df['time'].min()} -> {df['time'].max()}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

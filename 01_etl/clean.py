"""
Corrections des anomalies connues du jeu horaire.

Chaque fonction retourne une copie corrigee et le journal des corrections,
pour que l'orchestrateur puisse tracer ce qui a ete modifie.
"""

from __future__ import annotations

import pandas as pd

COUCHES_HUMIDITE = [
    "soil_moisture_0_to_7cm",
    "soil_moisture_7_to_28cm",
    "soil_moisture_28_to_100cm",
]


def corriger_humidite_sol(df: pd.DataFrame) -> tuple[pd.DataFrame, list[str]]:
    """Ramene a zero les humidites de sol negatives.

    Une teneur en eau volumique ne peut pas etre negative. Les valeurs sous
    zero sont un artefact numerique de la reanalyse sur sols tres secs, ou la
    grandeur oscille autour de zero. Elles se concentrent sur les gouvernorats
    arides du sud.
    """
    corrige = df.copy()
    journal = []

    for colonne in COUCHES_HUMIDITE:
        if colonne not in corrige.columns:
            continue
        negatives = corrige[colonne] < 0
        nb = int(negatives.sum())
        if nb:
            mini = corrige.loc[negatives, colonne].min()
            corrige.loc[negatives, colonne] = 0.0
            journal.append(
                f"{colonne} : {nb:,} valeurs negatives ramenees a 0 "
                f"(minimum observe {mini:.4f})"
            )

    return corrige, journal


def nettoyer(df: pd.DataFrame) -> tuple[pd.DataFrame, list[str]]:
    """Enchaine toutes les corrections."""
    corrige, journal = corriger_humidite_sol(df)
    return corrige, journal

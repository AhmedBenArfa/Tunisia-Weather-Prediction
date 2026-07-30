"""
Controles de qualite du jeu horaire.

Chaque fonction retourne la liste des anomalies detectees, vide si le jeu est
conforme. Aucune n'affiche ni ne leve : l'orchestrateur decide quoi en faire.
"""

from __future__ import annotations

import pandas as pd

import config


def verifier_completude(df: pd.DataFrame) -> list[str]:
    """Aucune valeur manquante attendue."""
    anomalies = []
    manquants = df.isna().sum()
    for colonne, nb in manquants[manquants > 0].items():
        anomalies.append(f"{colonne} : {nb:,} valeurs manquantes")
    return anomalies


def verifier_doublons(df: pd.DataFrame) -> list[str]:
    """Le couple (gouvernorat, heure) doit etre unique."""
    nb = df.duplicated(["gouvernorat", "time"]).sum()
    if nb:
        return [f"{nb:,} doublons sur (gouvernorat, time)"]
    return []


def verifier_continuite_horaire(df: pd.DataFrame) -> list[str]:
    """Chaque serie doit avancer d'exactement une heure a chaque pas."""
    anomalies = []
    for nom, groupe in df.sort_values("time").groupby("gouvernorat", observed=True):
        ecarts = groupe["time"].diff().dropna()
        irreguliers = ecarts[ecarts != pd.Timedelta(hours=1)]
        if len(irreguliers):
            anomalies.append(
                f"{nom} : {len(irreguliers)} intervalle(s) different(s) d'une heure"
            )
    return anomalies


def verifier_plages_physiques(df: pd.DataFrame) -> list[str]:
    """Les valeurs doivent rester dans des bornes physiquement admissibles."""
    anomalies = []
    for colonne, (mini, maxi) in config.PLAGES.items():
        if colonne not in df.columns:
            continue
        hors = ((df[colonne] < mini) | (df[colonne] > maxi)).sum()
        if hors:
            anomalies.append(
                f"{colonne} : {hors:,} valeurs hors de [{mini}, {maxi}] "
                f"(observe {df[colonne].min():.3f} a {df[colonne].max():.3f})"
            )
    return anomalies


def verifier_decalage_groupe(df: pd.DataFrame, colonne: str,
                             horizon: int) -> list[str]:
    """Verifie qu'un decalage a bien ete calcule par gouvernorat.

    Un decalage groupe laisse exactement `horizon` valeurs manquantes au debut
    de chaque serie. Un decalage global n'en laisse qu'au tout premier
    gouvernorat : les suivants recuperent silencieusement les dernieres heures
    du precedent. C'est une erreur sans exception, invisible sans ce controle.
    """
    anomalies = []
    for nom, groupe in df.sort_values("time").groupby("gouvernorat", observed=True):
        nb_manquants = groupe[colonne].head(horizon).isna().sum()
        if nb_manquants != horizon:
            anomalies.append(
                f"{nom} : {nb_manquants}/{horizon} valeurs manquantes en tete de "
                f"'{colonne}' — le decalage n'a pas ete groupe par gouvernorat"
            )
    return anomalies


def executer_controles(df: pd.DataFrame) -> list[str]:
    """Enchaine tous les controles structurels."""
    anomalies = []
    anomalies += verifier_completude(df)
    anomalies += verifier_doublons(df)
    anomalies += verifier_continuite_horaire(df)
    anomalies += verifier_plages_physiques(df)

    nb_gouv = df["gouvernorat"].nunique()
    if nb_gouv != config.NB_GOUVERNORATS:
        anomalies.append(
            f"{nb_gouv} gouvernorats au lieu de {config.NB_GOUVERNORATS}"
        )
    return anomalies

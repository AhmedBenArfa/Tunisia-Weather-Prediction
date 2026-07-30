"""Tests des controles de qualite, sur donnees synthetiques."""

import sys
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "01_etl"))

import checks  # noqa: E402


def jeu_valide(nb_heures=48, gouvernorats=("Tunis", "Sfax")):
    """Deux series horaires continues, sans anomalie."""
    lignes = []
    for nom in gouvernorats:
        temps = pd.date_range("2020-01-01", periods=nb_heures, freq="h")
        lignes.append(pd.DataFrame({
            "gouvernorat": nom,
            "time": temps,
            "temperature_2m": 20.0,
            "relative_humidity_2m": 50.0,
            "soil_moisture_0_to_7cm": 0.2,
        }))
    return pd.concat(lignes, ignore_index=True)


def test_jeu_valide_ne_remonte_aucune_anomalie():
    assert checks.verifier_completude(jeu_valide()) == []
    assert checks.verifier_doublons(jeu_valide()) == []
    assert checks.verifier_continuite_horaire(jeu_valide()) == []
    assert checks.verifier_plages_physiques(jeu_valide()) == []


def test_valeur_manquante_detectee():
    df = jeu_valide()
    df.loc[5, "temperature_2m"] = None
    anomalies = checks.verifier_completude(df)
    assert len(anomalies) == 1
    assert "temperature_2m" in anomalies[0]


def test_doublon_detecte():
    df = jeu_valide()
    df = pd.concat([df, df.iloc[[0]]], ignore_index=True)
    assert len(checks.verifier_doublons(df)) == 1


def test_trou_horaire_detecte():
    df = jeu_valide()
    df = df.drop(index=10).reset_index(drop=True)
    anomalies = checks.verifier_continuite_horaire(df)
    assert len(anomalies) == 1
    assert "Tunis" in anomalies[0]


def test_valeur_hors_plage_detectee():
    df = jeu_valide()
    df.loc[3, "soil_moisture_0_to_7cm"] = -0.01
    anomalies = checks.verifier_plages_physiques(df)
    assert len(anomalies) == 1
    assert "soil_moisture_0_to_7cm" in anomalies[0]


def test_decalage_groupe_correct_accepte():
    """Un decalage calcule par gouvernorat laisse H valeurs manquantes par serie."""
    df = jeu_valide()
    df["lag"] = df.groupby("gouvernorat", observed=True)["temperature_2m"].shift(24)
    assert checks.verifier_decalage_groupe(df, "lag", 24) == []


def test_decalage_global_detecte_comme_faux():
    """Un decalage global contamine la frontiere entre gouvernorats."""
    df = jeu_valide().sort_values(["gouvernorat", "time"]).reset_index(drop=True)
    df["lag"] = df["temperature_2m"].shift(24)
    anomalies = checks.verifier_decalage_groupe(df, "lag", 24)
    assert len(anomalies) == 1
    assert "Tunis" in anomalies[0] or "Sfax" in anomalies[0]

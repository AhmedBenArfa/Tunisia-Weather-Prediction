"""Tests du nettoyage, sur donnees synthetiques."""

import sys
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "01_etl"))

import clean  # noqa: E402


def jeu_avec_humidite_negative():
    return pd.DataFrame({
        "gouvernorat": ["Tozeur"] * 4,
        "time": pd.date_range("2020-01-01", periods=4, freq="h"),
        "soil_moisture_0_to_7cm": [0.20, -0.013, 0.18, -0.001],
        "soil_moisture_7_to_28cm": [0.22, 0.21, -0.012, 0.20],
        "soil_moisture_28_to_100cm": [0.19, 0.19, 0.19, 0.19],
    })


def test_humidite_negative_ramenee_a_zero():
    df, journal = clean.corriger_humidite_sol(jeu_avec_humidite_negative())
    for colonne in [c for c in df.columns if c.startswith("soil_moisture")]:
        assert (df[colonne] >= 0).all()
    assert len(journal) == 2          # deux couches concernees


def test_valeurs_positives_inchangees():
    origine = jeu_avec_humidite_negative()
    df, _ = clean.corriger_humidite_sol(origine)
    assert df.loc[0, "soil_moisture_0_to_7cm"] == 0.20
    assert df.loc[2, "soil_moisture_0_to_7cm"] == 0.18


def test_tableau_origine_non_modifie():
    origine = jeu_avec_humidite_negative()
    clean.corriger_humidite_sol(origine)
    assert origine.loc[1, "soil_moisture_0_to_7cm"] == -0.013


def test_journal_mentionne_le_nombre_corrige():
    _, journal = clean.corriger_humidite_sol(jeu_avec_humidite_negative())
    assert any("soil_moisture_0_to_7cm" in ligne and "2" in ligne
               for ligne in journal)


def test_jeu_sans_anomalie_produit_journal_vide():
    df = jeu_avec_humidite_negative()
    df[[c for c in df.columns if c.startswith("soil_moisture")]] = 0.2
    _, journal = clean.corriger_humidite_sol(df)
    assert journal == []

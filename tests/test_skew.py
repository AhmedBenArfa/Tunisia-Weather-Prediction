"""Tests du calcul de metriques de decalage, sans reseau."""

import sys
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "01_etl"))

import skew_analysis  # noqa: E402


def paire_synthetique():
    """Le forecast est decale de +2 par rapport a l'archive."""
    temps = pd.date_range("2026-05-01", periods=100, freq="h")
    archive = pd.DataFrame({
        "time": temps,
        "temperature_2m": [20.0 + i % 10 for i in range(100)],
    })
    forecast = archive.copy()
    forecast["temperature_2m"] = forecast["temperature_2m"] + 2.0
    return archive, forecast


def test_biais_constant_detecte():
    archive, forecast = paire_synthetique()
    res = skew_analysis.calculer_metriques(archive, forecast, ["temperature_2m"])
    ligne = res.iloc[0]
    assert ligne["variable"] == "temperature_2m"
    assert abs(ligne["biais"] - 2.0) < 1e-9
    assert abs(ligne["mae"] - 2.0) < 1e-9
    assert ligne["n"] == 100


def test_sources_identiques_donnent_zero():
    archive, _ = paire_synthetique()
    res = skew_analysis.calculer_metriques(archive, archive, ["temperature_2m"])
    assert abs(res.iloc[0]["biais"]) < 1e-9
    assert abs(res.iloc[0]["mae"]) < 1e-9
    assert abs(res.iloc[0]["mae_sur_sigma"]) < 1e-9


def test_seules_les_heures_communes_comptent():
    archive, forecast = paire_synthetique()
    forecast = forecast.iloc[:40]
    res = skew_analysis.calculer_metriques(archive, forecast, ["temperature_2m"])
    assert res.iloc[0]["n"] == 40


def test_resultat_trie_par_mae_sur_sigma():
    temps = pd.date_range("2026-05-01", periods=50, freq="h")
    archive = pd.DataFrame({
        "time": temps,
        "a": [float(i % 7) for i in range(50)],
        "b": [float(i % 7) for i in range(50)],
    })
    forecast = archive.copy()
    forecast["a"] = forecast["a"] + 0.1
    forecast["b"] = forecast["b"] + 3.0
    res = skew_analysis.calculer_metriques(archive, forecast, ["a", "b"])
    assert list(res["variable"]) == ["a", "b"]

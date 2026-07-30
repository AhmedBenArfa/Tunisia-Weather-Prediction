"""
Mesure du decalage entre la source d'entrainement et la source de production.

Le modele s'entrainera sur la reanalyse ERA5 mais predira a partir de l'API
forecast. Ces deux sources ne coincident pas exactement. Une variable dont les
deux sources divergent est un risque : le biais se propagerait dans toutes ses
variables de decalage.

La metrique de decision est MAE / ecart-type : elle rapporte le desaccord a la
variabilite propre de la variable, seule facon de comparer des grandeurs
d'unites differentes.

Usage :
    python 01_etl/skew_analysis.py
"""

from __future__ import annotations

import time as horloge

import pandas as pd
import requests

import config

API_FORECAST = "https://api.open-meteo.com/v1/forecast"
TIMEZONE = "Africa/Tunis"
JOURS_PASSES = 92                     # profondeur maximale de l'API forecast


def recuperer_forecast(lat: float, lon: float, variables: list[str],
                       jours: int = JOURS_PASSES,
                       max_essais: int = 5) -> pd.DataFrame:
    """Recupere les heures passees publiees par l'API forecast.

    Deux modes de repli distincts, comme dans extract_openmeteo.py :
    un 429 signale un quota epuise et impose d'attendre la reouverture de la
    fenetre ; un 5xx est une panne transitoire du serveur, ou un repli court
    suffit.
    """
    params = {
        "latitude": lat, "longitude": lon,
        "hourly": ",".join(variables),
        "timezone": TIMEZONE,
        "past_days": jours, "forecast_days": 1,
    }

    for essai in range(max_essais):
        try:
            reponse = requests.get(API_FORECAST, params=params, timeout=120)

            if reponse.status_code == 429:
                motif = reponse.json().get("reason", "")
                attente = 70.0 if "minutely" in motif.lower() else 300.0
                print(f"\n   ! quota atteint ({motif}) - attente {attente:.0f}s",
                      flush=True)
                horloge.sleep(attente)
                continue

            reponse.raise_for_status()
            df = pd.DataFrame(reponse.json()["hourly"])
            df["time"] = pd.to_datetime(df["time"])
            return df

        except Exception as exc:
            if essai == max_essais - 1:
                raise
            attente = 15.0 * (essai + 1)
            print(f"\n   ! {type(exc).__name__} - nouvel essai dans "
                  f"{attente:.0f}s", flush=True)
            horloge.sleep(attente)

    raise RuntimeError("Echec definitif de la recuperation forecast")


def calculer_metriques(archive: pd.DataFrame, forecast: pd.DataFrame,
                       variables: list[str]) -> pd.DataFrame:
    """Compare les deux sources sur leurs heures communes.

    Retourne une ligne par variable, triee par desaccord croissant.
    """
    fusion = archive.merge(forecast, on="time", suffixes=("_arc", "_fc"))

    lignes = []
    for variable in variables:
        col_arc, col_fc = f"{variable}_arc", f"{variable}_fc"
        if col_arc not in fusion.columns or col_fc not in fusion.columns:
            continue
        a, f = fusion[col_arc], fusion[col_fc]
        sigma = float(a.std())
        mae = float((f - a).abs().mean())
        lignes.append({
            "variable": variable,
            "n": int(len(fusion)),
            "biais": float((f - a).mean()),
            "mae": mae,
            "sigma": sigma,
            "mae_sur_sigma": mae / sigma if sigma > 0 else float("nan"),
        })

    return (pd.DataFrame(lignes)
            .sort_values("mae_sur_sigma")
            .reset_index(drop=True))


def main() -> int:
    df = pd.read_parquet(config.PARQUET_PROPRE)
    variables = [c for c in df.columns
                 if c not in ("gouvernorat", "time", "latitude",
                              "longitude", "elevation")]

    geo = (df.groupby("gouvernorat", observed=True)[["latitude", "longitude"]]
             .first())

    resultats = []
    for i, (nom, ligne) in enumerate(geo.iterrows(), start=1):
        print(f"[{i:2d}/{len(geo)}] {nom} ...", end=" ", flush=True)
        forecast = recuperer_forecast(ligne["latitude"], ligne["longitude"],
                                      variables)
        archive = df[df["gouvernorat"] == nom][["time"] + variables]
        metriques = calculer_metriques(archive, forecast, variables)
        metriques.insert(0, "gouvernorat", nom)
        resultats.append(metriques)
        print(f"{metriques['n'].iloc[0]:,} heures communes")
        horloge.sleep(2)

    complet = pd.concat(resultats, ignore_index=True)
    complet.to_csv(config.SKEW_CSV, index=False)

    synthese = (complet.groupby("variable", as_index=False)
                .agg(biais=("biais", "mean"), mae=("mae", "mean"),
                     mae_sur_sigma=("mae_sur_sigma", "mean"))
                .sort_values("mae_sur_sigma"))

    print(f"\n--- Synthese sur {len(geo)} gouvernorats ---")
    print(synthese.to_string(index=False,
                             float_format=lambda v: f"{v:8.3f}"))
    print(f"\nDetail par gouvernorat ecrit dans {config.SKEW_CSV.name}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

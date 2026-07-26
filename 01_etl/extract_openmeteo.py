"""
Extraction meteo horaire - 24 gouvernorats tunisiens -> fichiers CSV
Source : Open-Meteo Historical Weather API (ERA5) - gratuit, sans cle API

Installation :
    pip install requests pandas

Usage :
    python extract_tunisia_weather_csv.py
"""

import time
from datetime import datetime, timedelta
import pandas as pd
import requests
from pathlib import Path


class QuotaJournalierEpuise(Exception):
    """Plafond de 10 000 appels/jour atteint : il faut reprendre le lendemain."""

# ---------------------------------------------------------------------------
# CONFIGURATION
# ---------------------------------------------------------------------------

START_DATE = "2019-01-01"
END_DATE = "2026-07-15"          # ERA5 accuse ~5 jours de retard
OUTPUT_DIR = Path("data")
OUTPUT_DIR.mkdir(exist_ok=True)

API_URL = "https://archive-api.open-meteo.com/v1/archive"
TIMEZONE = "Africa/Tunis"

# Les 24 gouvernorats (chef-lieu)
GOUVERNORATS = {
    "Tunis":        (36.8065, 10.1815),
    "Ariana":       (36.8625, 10.1956),
    "Ben Arous":    (36.7545, 10.2278),
    "Manouba":      (36.8081, 10.0972),
    "Nabeul":       (36.4513, 10.7357),
    "Zaghouan":     (36.4029, 10.1429),
    "Bizerte":      (37.2744, 9.8739),
    "Beja":         (36.7256, 9.1817),
    "Jendouba":     (36.5011, 8.7803),
    "Kef":          (36.1742, 8.7049),
    "Siliana":      (36.0819, 9.3708),
    "Kairouan":     (35.6781, 10.0963),
    "Kasserine":    (35.1676, 8.8365),
    "Sidi Bouzid":  (35.0382, 9.4849),
    "Sousse":       (35.8256, 10.6360),
    "Monastir":     (35.7643, 10.8113),
    "Mahdia":       (35.5047, 11.0622),
    "Sfax":         (34.7406, 10.7603),
    "Gafsa":        (34.4250, 8.7842),
    "Tozeur":       (33.9197, 8.1335),
    "Kebili":       (33.7044, 8.9690),
    "Gabes":        (33.8815, 10.0982),
    "Medenine":     (33.3549, 10.5055),
    "Tataouine":    (32.9297, 10.4518),
}

HOURLY_VARS = [
    "temperature_2m",
    "relative_humidity_2m",
    "dew_point_2m",
    "apparent_temperature",
    "precipitation",
    "rain",
    "snowfall",
    "pressure_msl",
    "surface_pressure",
    "cloud_cover",
    "cloud_cover_low",
    "cloud_cover_mid",
    "cloud_cover_high",
    "et0_fao_evapotranspiration",
    "vapour_pressure_deficit",
    "wind_speed_10m",
    "wind_speed_100m",
    "wind_direction_10m",
    "wind_direction_100m",
    "wind_gusts_10m",
    "soil_temperature_0_to_7cm",
    "soil_temperature_7_to_28cm",
    "soil_temperature_28_to_100cm",
    "soil_moisture_0_to_7cm",
    "soil_moisture_7_to_28cm",
    "soil_moisture_28_to_100cm",
    "shortwave_radiation",
    "direct_radiation",
    "diffuse_radiation",
    "direct_normal_irradiance",
    "terrestrial_radiation",
]

# ---------------------------------------------------------------------------
# EXTRACTION
# ---------------------------------------------------------------------------


def attente_apres_429(reason: str) -> float:
    """Duree d'attente deduite du motif exact renvoye par Open-Meteo.

    Le quota est pondere : (nb_variables / 10) x (nb_jours / 14). Ici une seule
    requete (31 variables x ~7,5 ans) pese ~610 appels, d'ou les 429 frequents.
    Inutile de retenter avant la reouverture de la fenetre concernee.
    """
    r = reason.lower()
    maintenant = datetime.now()

    if "daily" in r:
        raise QuotaJournalierEpuise(reason)

    if "hourly" in r:
        prochaine = (maintenant.replace(minute=0, second=0, microsecond=0)
                     + timedelta(hours=1))
        return (prochaine - maintenant).total_seconds() + 30

    # Limite par minute (600/min) : la fenetre se reouvre tres vite.
    return 65.0


def fetch_gouvernorat(nom: str, lat: float, lon: float,
                      max_retries: int = 8) -> pd.DataFrame:
    """Telecharge la serie horaire complete pour un gouvernorat."""
    params = {
        "latitude": lat,
        "longitude": lon,
        "start_date": START_DATE,
        "end_date": END_DATE,
        "hourly": ",".join(HOURLY_VARS),
        "timezone": TIMEZONE,
    }

    for attempt in range(max_retries):
        try:
            r = requests.get(API_URL, params=params, timeout=180)
            if r.status_code == 429:
                reason = r.json().get("reason", "")
                wait = attente_apres_429(reason)
                reprise = datetime.now() + timedelta(seconds=wait)
                print(f"\n   ! {nom} : quota atteint ({reason}) "
                      f"- reprise a {reprise:%H:%M:%S}", flush=True)
                time.sleep(wait)
                continue
            r.raise_for_status()
            payload = r.json()
            break
        except QuotaJournalierEpuise:
            raise
        except Exception as exc:
            wait = 10 * (attempt + 1)
            print(f"\n   ! {nom} tentative {attempt + 1} echouee "
                  f"({type(exc).__name__}) - nouvel essai dans {wait:.0f}s",
                  flush=True)
            time.sleep(wait)
    else:
        raise RuntimeError(f"Echec definitif pour {nom}")

    df = pd.DataFrame(payload["hourly"])
    df["time"] = pd.to_datetime(df["time"])

    # Metadonnees geographiques (utiles comme features)
    df.insert(0, "gouvernorat", nom)
    df["latitude"] = payload["latitude"]
    df["longitude"] = payload["longitude"]
    df["elevation"] = payload["elevation"]

    return df


def main():
    frames = []
    total = len(GOUVERNORATS)

    for i, (nom, (lat, lon)) in enumerate(GOUVERNORATS.items(), start=1):
        nom_fichier = nom.replace(" ", "_")
        chemin = OUTPUT_DIR / f"raw_{nom_fichier}.csv"

        # Reprise : on ne retelecharge pas ce qui est deja sur le disque
        if chemin.exists():
            df = pd.read_csv(chemin, parse_dates=["time"])
            frames.append(df)
            print(f"[{i:2d}/{total}] {nom} ... deja present "
                  f"({len(df):,} lignes)", flush=True)
            continue

        print(f"[{i:2d}/{total}] {nom} ...", end=" ", flush=True)
        try:
            df = fetch_gouvernorat(nom, lat, lon)
        except QuotaJournalierEpuise:
            manquants = [n for n in GOUVERNORATS
                         if not (OUTPUT_DIR / f"raw_{n.replace(' ', '_')}.csv").exists()]
            print(f"\n\n--- Quota journalier epuise ---")
            print(f"Telecharges : {total - len(manquants)}/{total}")
            print(f"Restants    : {', '.join(manquants)}")
            print("Relancer le meme script demain : il reprendra "
                  "automatiquement ou il s'est arrete.")
            return
        df.to_csv(chemin, index=False)

        frames.append(df)
        print(f"{len(df):,} lignes", flush=True)
        time.sleep(20)           # respect du quota pondere (fenetre 1 min)

    # Fichier combine (les 24 empiles)
    full = pd.concat(frames, ignore_index=True)
    full = full.sort_values(["gouvernorat", "time"]).reset_index(drop=True)
    out = OUTPUT_DIR / "tunisia_weather_hourly.csv"
    full.to_csv(out, index=False)

    print(f"\n--- Termine ---")
    print(f"24 fichiers CSV par gouvernorat : {OUTPUT_DIR}/raw_*.csv")
    print(f"Fichier combine                 : {out}")
    print(f"  lignes   : {len(full):,}")
    print(f"  colonnes : {full.shape[1]}")
    print(f"  periode  : {full['time'].min()} -> {full['time'].max()}")
    print(f"  taille   : {out.stat().st_size / 1e6:.1f} Mo")


if __name__ == "__main__":
    main()

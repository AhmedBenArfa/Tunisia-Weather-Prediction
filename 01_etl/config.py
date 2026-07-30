"""Chemins et constantes partages par les modules ETL."""

from pathlib import Path

RACINE = Path(__file__).resolve().parent.parent
DATA = RACINE / "data"

PARQUET_BRUT = DATA / "tunisia_weather_hourly.parquet"
PARQUET_PROPRE = DATA / "tunisia_weather_clean.parquet"
SKEW_CSV = DATA / "skew_era5_forecast.csv"

NB_GOUVERNORATS = 24
NB_HEURES_ATTENDUES = 66_072          # 2019-01-01 -> 2026-07-15, pas horaire

# Plages physiquement admissibles, volontairement larges : on cherche
# l'aberration franche, pas la valeur rare.
PLAGES = {
    "temperature_2m": (-20.0, 60.0),
    "apparent_temperature": (-30.0, 65.0),
    "dew_point_2m": (-40.0, 40.0),
    "relative_humidity_2m": (0.0, 100.0),
    "precipitation": (0.0, 200.0),
    "rain": (0.0, 200.0),
    "snowfall": (0.0, 100.0),
    "pressure_msl": (900.0, 1100.0),
    "surface_pressure": (850.0, 1100.0),
    "cloud_cover": (0.0, 100.0),
    "cloud_cover_low": (0.0, 100.0),
    "cloud_cover_mid": (0.0, 100.0),
    "cloud_cover_high": (0.0, 100.0),
    "wind_speed_10m": (0.0, 250.0),
    "wind_speed_100m": (0.0, 300.0),
    "wind_direction_10m": (0.0, 360.0),
    "wind_direction_100m": (0.0, 360.0),
    "wind_gusts_10m": (0.0, 350.0),
    "soil_moisture_0_to_7cm": (0.0, 1.0),
    "soil_moisture_7_to_28cm": (0.0, 1.0),
    "soil_moisture_28_to_100cm": (0.0, 1.0),
    "shortwave_radiation": (0.0, 1400.0),
    "direct_radiation": (0.0, 1400.0),
    "diffuse_radiation": (0.0, 1400.0),
}

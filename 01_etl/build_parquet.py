"""
Conversion des CSV bruts en un Parquet unique, compresse et versionnable.

Les 24 CSV produits par extract_openmeteo.py pesent ~587 Mo au total, ce qui
depasse la limite GitHub de 100 Mo par fichier. Le meme contenu tient en ~42 Mo
en Parquet zstd, format lu nativement par DuckDB sans import prealable.

Usage :
    python 01_etl/build_parquet.py
"""

from pathlib import Path
import pandas as pd

DATA_DIR = Path(__file__).resolve().parent.parent / "data"
SORTIE = DATA_DIR / "tunisia_weather_hourly.parquet"


def main():
    fichiers = sorted(DATA_DIR.glob("raw_*.csv"))
    if not fichiers:
        raise SystemExit(
            f"Aucun fichier raw_*.csv dans {DATA_DIR}. "
            "Lancer d'abord 01_etl/extract_openmeteo.py."
        )

    print(f"{len(fichiers)} fichiers a convertir")
    frames = []
    for f in fichiers:
        df = pd.read_csv(f, parse_dates=["time"])
        frames.append(df)
        print(f"  {f.name:32s} {len(df):>8,} lignes")

    full = pd.concat(frames, ignore_index=True)
    full = full.sort_values(["gouvernorat", "time"]).reset_index(drop=True)

    # Le gouvernorat est une categorie : 24 valeurs repetees 66 072 fois.
    full["gouvernorat"] = full["gouvernorat"].astype("category")

    full.to_parquet(SORTIE, compression="zstd", index=False)

    csv_mo = sum(f.stat().st_size for f in fichiers) / 1e6
    pq_mo = SORTIE.stat().st_size / 1e6

    print(f"\n--- Termine ---")
    print(f"Fichier   : {SORTIE}")
    print(f"  lignes  : {len(full):,}")
    print(f"  colonnes: {full.shape[1]}")
    print(f"  periode : {full['time'].min()} -> {full['time'].max()}")
    print(f"  CSV     : {csv_mo:.1f} Mo")
    print(f"  Parquet : {pq_mo:.1f} Mo  (ratio {csv_mo / pq_mo:.1f}x)")


if __name__ == "__main__":
    main()

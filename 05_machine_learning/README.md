# 05 — Machine learning

Prévision de température à t+1 h, t+24 h et t+72 h. Régression sur série
temporelle.

**État : à venir.**

## Fichiers prévus

| Fichier | Rôle |
|---|---|
| `features.py` | `build_features(df, horizon)` — **partagée avec l'application** |
| `baselines.py` | Persistance et climatologie |
| `train.py` | Entraînement des trois modèles d'horizon |
| `evaluate.py` | Métriques par horizon et par gouvernorat |
| `models/` | Modèles sérialisés (non versionnés côté entraînement) |

## La règle qui gouverne tout : pas de fuite temporelle

La cible est `temperature_2m` décalée de H heures. Une variable n'est
admissible que si elle est **connue à l'instant t**.

Prédire la température à t à partir de la température ressentie à t donne un R²
proche de 0,99 — les deux décrivent le même instant. Prédire la température à
t+24 h à partir de la ressentie à t est légitime : à t, cette valeur est
observée. **La fuite tient à l'horizon, pas à la variable.**

Conséquence pratique sur les fenêtres glissantes : le décalage précède
toujours le calcul (`shift(1)` puis `rolling`), faute de quoi la fenêtre
inclurait l'instant courant.

## Variables retenues

Filtrées par cohérence entre la source d'entraînement (ERA5) et la source de
production (API forecast) — voir `01_etl/README.md` et le document de
conception. Ne sont gardées que celles dont les deux sources s'accordent :

- `temperature_2m`, `apparent_temperature`
- `pressure_msl`, `surface_pressure`
- `shortwave_radiation`, `direct_radiation`, `diffuse_radiation`
- `et0_fao_evapotranspiration`
- `precipitation`, `rain`
- `soil_temperature_*`, `soil_moisture_*`

Variables construites : décalages (t−1 à t−168), fenêtres glissantes décalées
(24 h, 72 h, 168 h), encodage cyclique de l'heure et du jour de l'année,
latitude, longitude, altitude, `cluster_climatique`.

## Découpage chronologique

| Jeu | Période | Volume |
|---|---|---|
| Entraînement | 2019-01-01 → 2023-12-31 | 1 051 776 |
| Validation | 2024-01-01 → 2025-06-30 | 315 072 |
| Test | 2025-07-01 → 2026-07-15 | 218 880 |

Aucun mélange aléatoire : sur une série temporelle, un `train_test_split`
aléatoire place des observations futures dans l'entraînement et fabrique des
scores qui ne veulent rien dire.

## Baselines

1. **Persistance** — `T(t+H) = T(t)`. Solide à t+1 h, s'effondre à t+72 h.
2. **Climatologie** — moyenne historique pour ce gouvernorat, cette heure, ce
   jour de l'année. Insensible à l'horizon, donc de plus en plus compétitive
   quand H grandit.

Un modèle n'a d'intérêt que s'il bat nettement la meilleure des deux, à chaque
horizon.

## Modèles et métriques

Ridge, Random Forest, XGBoost — chacun dans un `Pipeline` scikit-learn
entièrement sérialisé, pour que l'application applique un prétraitement
rigoureusement identique.

Trois modèles directs indépendants, un par horizon, plutôt qu'un schéma
récursif qui accumulerait l'erreur sur 72 pas.

Métriques : MAE (critère de sélection), RMSE, R², gain relatif sur chaque
baseline. Le MAPE est écarté — la température passe par zéro en hiver, ce qui
fait exploser un rapport en pourcentage.

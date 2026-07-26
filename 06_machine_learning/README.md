# 05 — Machine learning

Prévision de température à t+1 h, t+24 h et t+72 h. Régression sur série
temporelle.

**État : à venir.**

## Fichiers prévus

| Fichier | Rôle |
|---|---|
| `features.py` | `build_features(df, horizon)` — **partagée avec l'application** |
| `baselines.py` | Persistance et climatologie |
| `train.py` | Entraînement et comparaison des modèles, par horizon |
| `evaluate.py` | Métriques par horizon et par gouvernorat |
| `models/` | Modèles sérialisés (non versionnés côté entraînement) |
| `notebooks/01_ml.ipynb` | Comparaison, sélection, interprétation |

## Un modèle global sur 24 séries parallèles

Les 24 gouvernorats forment **24 séries parallèles**. Un modèle global par
horizon est entraîné sur les 24 empilées — 1,58 M de lignes — plutôt que 24
modèles locaux de 66 000 lignes chacun.

| | Global (retenu) | 24 locaux |
|---|---|---|
| Lignes d'entraînement | 1 585 728 | 66 072 |
| Modèles produits | 3 | 72 |
| Spécificités locales | lat/lon/altitude/cluster | Apprises directement |

Le volume d'entraînement est vingt-quatre fois supérieur et la physique apprise
est commune. Les spécificités locales restent portées explicitement par la
latitude, la longitude, l'altitude et `cluster_climatique`. Et 3 modèles se
déploient là où 72 satureraient le dépôt.

L'évaluation est **ventilée par gouvernorat** : si le modèle commun sert mal un
gouvernorat en particulier, il faut le voir et le documenter.

**Conséquence impérative** — tout décalage se calcule par gouvernorat :

```python
# CORRECT
df.groupby("gouvernorat")["temperature_2m"].shift(24)

# FAUX : contamine chaque serie avec la fin de la precedente
df["temperature_2m"].shift(24)
```

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

## Baselines naïves

1. **Persistance** — `T(t+H) = T(t)`. Solide à t+1 h, s'effondre à t+72 h.
2. **Climatologie** — moyenne historique pour ce gouvernorat, cette heure, ce
   jour de l'année. Insensible à l'horizon, donc de plus en plus compétitive
   quand H grandit.

## Modèles comparés

Comme dans les projets précédents, plusieurs familles sont mises en concurrence
puis départagées sur une métrique unique — ici la **MAE**, là où le churn se
tranchait au ROC-AUC.

| Famille | Modèles |
|---|---|
| Linéaire | Régression linéaire, Ridge |
| Voisinage | k-NN *(sous-échantillon — ne passe pas à 1,58 M lignes)* |
| Arbres | Arbre de décision, Forêt aléatoire |
| Boosting | XGBoost |

Chacun dans un `Pipeline` scikit-learn intégralement sérialisé, pour que
l'application applique un prétraitement rigoureusement identique.

Trois modèles directs indépendants, un par horizon, plutôt qu'un schéma
récursif qui accumulerait l'erreur sur 72 pas.

## Le tableau qui conclut le projet

Les baselines naïves, les modèles statistiques de la phase 05 et les modèles ML
sont réunis dans une même comparaison :

| Modèle | MAE t+1 h | MAE t+24 h | MAE t+72 h |
|---|---|---|---|
| Persistance | | | |
| Climatologie | | | |
| ARIMA | | | |
| SARIMA | | | |
| Fourier + ARIMA | | | |
| Ridge | | | |
| Forêt aléatoire | | | |
| XGBoost | | | |

C'est ce qui donne son sens à la phase 05 : elle ne se contente pas de préparer
le feature engineering, elle **entre en concurrence**. Battre une moyenne naïve
ne prouve pas grand-chose ; battre une régression harmonique avec erreurs ARIMA
est un résultat.

## Métriques

MAE (critère de sélection), RMSE, R², et gain relatif sur chaque baseline.
Résultats ventilés par horizon et par gouvernorat.

Le MAPE est écarté — la température passe par zéro en hiver, ce qui fait
exploser un rapport en pourcentage.

## Interprétation

Importance des variables et SHAP sur le modèle retenu, comme dans les projets
précédents. Point d'attention particulier : vérifier que les décalages de
température dominent, et qu'aucune variable ne pèse anormalement — un poids
excessif sur une variable contemporaine signalerait une fuite passée inaperçue.

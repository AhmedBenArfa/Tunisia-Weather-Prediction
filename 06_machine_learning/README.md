# 06 — Machine learning

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

La liste découle de la mesure de cohérence entre la source d'entraînement
(ERA5) et la source de production (API forecast), conduite sur les 24
gouvernorats. Seuil retenu : **MAE/σ ≤ 0,20**, placé dans la rupture nette du
classement.

**17 variables retenues**

| Famille | Variables |
|---|---|
| Température | `temperature_2m`, `apparent_temperature` |
| Pression | `pressure_msl` |
| Rayonnement | `shortwave_radiation`, `direct_radiation`, `diffuse_radiation`, `direct_normal_irradiance`, `terrestrial_radiation` |
| Sol | `soil_temperature_*` (3 couches), `soil_moisture_*` (3 couches) |
| Eau | `precipitation`, `rain`, `et0_fao_evapotranspiration` |

**14 écartées** : `surface_pressure`, les quatre nébulosités, les cinq
variables de vent, `relative_humidity_2m`, `dew_point_2m`,
`vapour_pressure_deficit`. Plus `snowfall`, non évaluable.

Deux résultats méritent d'être signalés. **`surface_pressure` est écartée
(MAE/σ = 0,669) alors que `pressure_msl` est retenue (0,088)** : la pression de
surface dépend de l'altitude du relief telle que chaque modèle la représente,
et les deux modèles ne partagent pas le même relief ; la pression ramenée au
niveau de la mer est normalisée, d'où son accord. Sans cette mesure, la
variable serait entrée dans le modèle.

**`terrestrial_radiation` et les variables de sol sont identiques au millième**
entre les deux sources — pour le rayonnement terrestre c'est attendu, il est
purement astronomique.

> Source : `01_etl/skew_analysis.py`. Détail par gouvernorat dans
> `data/skew_era5_forecast.csv`, analyse et justification du seuil dans
> `01_etl/notebooks/01_eda.ipynb` §5.

Variables construites à partir de cette liste :

- **Décalages** de la température : t−1 à t−168, profondeurs retenues d'après
  la PACF de la phase 05
- **Décalages** des autres variables sélectionnées : t−1, t−24
- **Fenêtres glissantes décalées** (`shift(1)` puis `rolling`) sur 24 h, 72 h
  et 168 h : moyenne, minimum, maximum
- **Encodage cyclique** de l'heure et du jour de l'année
- **Statiques** : latitude, longitude, altitude, `cluster_climatique`


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

Sept modèles, départagés sur une métrique unique — la **MAE**, là où le churn se
tranchait au ROC-AUC. Chacun répond à une question distincte : l'objectif n'est
pas d'empiler des algorithmes, mais que la liste raconte une progression.

| Modèle | La question à laquelle il répond |
|---|---|
| Régression linéaire | La relation est-elle simplement linéaire ? |
| Ridge | La régularisation aide-t-elle face à des décalages corrélés ? |
| Lasso | Quelles variables comptent vraiment ? |
| k-NN | Une approche purement locale suffit-elle ? |
| Arbre de décision | Un arbre seul capture-t-il la non-linéarité ? |
| Forêt aléatoire | Le bagging corrige-t-il le sur-apprentissage de l'arbre ? |
| XGBoost | Le boosting fait-il mieux que le bagging ? |

**Le Lasso a un rôle particulier.** Avec une soixantaine de variables de
décalage et de fenêtres glissantes, il en annulera une partie. Or la PACF de la
phase 05 aura déjà répondu indépendamment à la même question. Comparer les
deux — le Lasso retient-il les décalages que la PACF désignait ? — fait
dialoguer les deux phases au lieu de les juxtaposer.

Chacun dans un `Pipeline` scikit-learn intégralement sérialisé, pour que
l'application applique un prétraitement rigoureusement identique. Trois modèles
directs indépendants par famille, un par horizon, plutôt qu'un schéma récursif
qui accumulerait l'erreur sur 72 pas.

## Le problème d'échelle, et le témoin qui le résout

**k-NN ne passe pas à 1,58 M de lignes.** Il doit calculer la distance à chaque
point d'entraînement pour chaque prédiction ; le coût est prohibitif. Il est
donc entraîné sur un sous-échantillon d'environ 50 000 lignes.

Cela crée un biais de comparaison : XGBoost sur 1,58 M contre k-NN sur 50 000
n'est pas une comparaison équitable. Si k-NN perd, impossible de savoir si c'est
l'algorithme ou le manque de données.

D'où un **XGBoost témoin**, entraîné sur le même sous-échantillon. Il n'entre
pas dans la sélection du modèle final et n'est jamais déployé — il répond à une
seule question, isolément.

| Comparaison | Volume | Modèles | Usage |
|---|---|---|---|
| Principale | 1 585 728 | Linéaire, Ridge, Lasso, arbre, forêt, XGBoost | Sélection et déploiement |
| Secondaire | ~50 000 | k-NN, XGBoost témoin | Départager algorithme et volume |

Le sous-échantillon est tiré **en respectant la chronologie** : il conserve la
même partition entraînement/validation/test, sans mélange aléatoire.

## Le tableau qui conclut le projet

Les baselines naïves, les modèles statistiques de la phase 05 et les modèles ML
sont réunis dans une même comparaison :

| Modèle | Origine | MAE t+1 h | MAE t+24 h | MAE t+72 h |
|---|---|---|---|---|
| Persistance | baseline | | | |
| Climatologie | baseline | | | |
| ARIMA | phase 05 | | | |
| SARIMA | phase 05 | | | |
| Fourier + ARIMA | phase 05 | | | |
| Régression linéaire | phase 06 | | | |
| Ridge | phase 06 | | | |
| Lasso | phase 06 | | | |
| Arbre de décision | phase 06 | | | |
| Forêt aléatoire | phase 06 | | | |
| XGBoost | phase 06 | | | |

Les baselines sont calculées **avant** tout entraînement : sans elles, aucun
score de modèle n'est interprétable. La barre à battre à chaque horizon est la
meilleure des deux, et elle ne sera pas la même partout — la persistance domine
aux horizons courts, la climatologie finit par la dépasser.

C'est aussi ce qui donne son sens à la phase 05 : elle ne se contente pas de
préparer le feature engineering, elle **entre en concurrence**. Battre une
moyenne naïve ne prouve pas grand-chose ; battre une régression harmonique avec
erreurs ARIMA est un résultat.

> Toutes les valeurs de ce tableau sont produites par les scripts de la phase
> concernée et documentées dans les notebooks correspondants. Aucune n'est
> inscrite ici tant qu'elle n'est pas reproductible depuis le dépôt.

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

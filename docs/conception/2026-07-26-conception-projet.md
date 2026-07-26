# Conception — Prévision de température en Tunisie

> **Auteur** : Ahmed Ben Arfa. Date : 2026-07-26.
> Démarche CRISP-DM, alignée sur les projets ProjetIntegre (churn) et
> BRFSS-Heart-Analytics.
> **Statut : validé, non implémenté.**

## 1. Objectif

Prévoir la température à trois horizons (t+1 h, t+24 h, t+72 h) pour chacun des
24 gouvernorats tunisiens, à partir de l'état météorologique observé jusqu'à
l'instant t.

Le livrable final est une application web : l'utilisateur choisit un
gouvernorat et un horizon, l'application récupère les observations récentes,
applique le modèle et affiche la prévision.

C'est un problème de **régression sur série temporelle**, ce qui le distingue
des deux projets précédents (classification binaire). Les conséquences
méthodologiques — découpage chronologique, baselines de référence, prévention
de la fuite temporelle — structurent toute la conception.

## 2. Cartographie CRISP-DM

| Phase CRISP-DM | Dossier | Contenu |
|---|---|---|
| Business Understanding | `00_documentation/` | Cadrage, objectifs, critères de succès |
| Data Understanding | `01_etl/` | Extraction, contrôles qualité, EDA |
| Data Preparation | `02_data_warehouse/` | Nettoyage, schéma en étoile, agrégats |
| — (restitution descriptive) | `03_power_bi/` | Rapport Power BI, mesures DAX |
| Data Understanding (spatial) | `04_data_mining/` | ACP, clustering climatique |
| Data Understanding (temporel) | `05_series_temporelles/` | STL, stationnarité, ACF/PACF, ARIMA/SARIMA/Fourier |
| Modeling | `06_machine_learning/` | Features, entraînement, comparaison |
| Evaluation | `06_machine_learning/` | Métriques par horizon, écart aux baselines |
| Deployment | `07_web_app/` | Application Streamlit + journalisation |

Les deux phases d'analyse précèdent volontairement la modélisation, parce que
chacune produit quelque chose qu'elle consomme : le clustering fournit
`cluster_climatique`, l'analyse temporelle justifie le choix des décalages par
la PACF au lieu de les poser par intuition.

## 3. Données

### 3.1 Source et volume

Open-Meteo, deux points d'entrée distincts :

| Usage | API | Rôle |
|---|---|---|
| Entraînement | `archive-api.open-meteo.com` (réanalyse ERA5) | Historique 2019-01-01 → 2026-07-15 |
| Production | `api.open-meteo.com/v1/forecast` | Observations des 168 dernières heures |

Jeu extrait : 24 gouvernorats × 66 072 heures = **1 585 728 lignes**, 36
colonnes (31 variables météo + gouvernorat, horodatage, latitude, longitude,
altitude). Aucune valeur manquante, aucun doublon.

### 3.2 Format de stockage et versionnement

Les données Open-Meteo sont publiques : contrairement aux projets précédents,
aucune contrainte de confidentialité n'interdit de les versionner. Elles sont
donc livrées avec le dépôt, sous une forme qui respecte les limites de GitHub.

| Forme | Taille | Versionné |
|---|---|---|
| 24 CSV bruts (`raw_*.csv`) | ~308 Mo | Non — redondants, regénérables |
| CSV combiné | 308 Mo | Non — dépasse la limite de 100 Mo par fichier |
| **Parquet zstd combiné** | **42,1 Mo** | **Oui** |

Le Parquet divise le volume par 7,3 et se lit nativement par DuckDB, sans
import préalable. `01_etl/build_parquet.py` assure la conversion.

### 3.3 Contrainte de quota

Le quota Open-Meteo est pondéré par le volume :
`(nb_variables / 10) × (nb_jours / 14)`. Une extraction complète pèse
~14 600 appels pour un plafond de 10 000 par jour, et s'étale donc sur deux
jours. Le quota journalier se réinitialise à minuit UTC. Le script
`01_etl/extract_openmeteo.py` gère ces limites : reprise sur les fichiers déjà
présents, attente déduite du motif exact du code 429, arrêt propre au plafond
journalier.

## 4. Répartition des outils

| Étape | Outil | Où |
|---|---|---|
| ETL, nettoyage, schéma en étoile, EDA, agrégation | DuckDB | Local |
| Entraînement | Python + Parquet | Local |
| Application déployée + journal des prédictions | Supabase (Postgres) | En ligne |

DuckDB assume toute la charge lourde en local et lit le Parquet nativement.
Seul le produit fini et léger part vers Supabase, dont le palier gratuit est
limité à 500 Mo : `dim_gouvernorat`, le fait journalier agrégé et la table de
journalisation. **Le fait horaire ne quitte jamais le poste local.**

Le modèle est entraîné en local et déployé avec l'application sous forme de
fichier `.joblib`. La base ne sert pas à prédire : le modèle prédit,
Open-Meteo fournit les entrées fraîches, Supabase enregistre le résultat.

## 5. Structure du dépôt

```
00_documentation/   Cadrage, description des données, planning, guide technique
01_etl/             Extraction Open-Meteo, contrôles qualité, EDA
02_data_warehouse/  Schéma en étoile DuckDB, exports Parquet, pont Supabase
03_power_bi/        Rapport .pbix, mesures DAX, captures
04_data_mining/     ACP, clustering climatique des gouvernorats
05_series_temporelles/ STL, stationnarité, ACF/PACF, ARIMA/SARIMA/Fourier
06_machine_learning/ features.py, entraînement multi-horizon, modèles
07_web_app/         Application Streamlit, journalisation Supabase
08_rapport/         Documentation technique et rapport final (PDF)
09_presentation/    Slides HTML
data/               Parquet versionné ; CSV bruts ignorés
docs/conception/    Documents de conception
```

## 6. Schéma en étoile

| Table | Grain | Lignes |
|---|---|---|
| `dim_gouvernorat` | Un gouvernorat | 24 |
| `dim_temps` | Une heure | 66 072 |
| `fait_meteo_horaire` | Gouvernorat × heure | 1 585 728 |
| `fait_meteo_journalier` | Gouvernorat × jour | 66 072 |

`dim_gouvernorat` porte le nom, la latitude, la longitude, l'altitude, la
région administrative et le groupe climatique issu du clustering (phase 04).
`dim_temps` porte date, heure, jour, mois, année, saison, indicateur de
week-end, ainsi que les encodages cycliques réutilisés par le modèle.

`fait_meteo_journalier` agrège les 31 mesures en minimum, moyenne et maximum
par jour. C'est cette table, et elle seule, qui alimente Supabase et le
rapport Power BI en ligne.

## 7. Structure des données et portée du modèle

### 7.1 Vingt-quatre séries parallèles, un modèle global

Les 24 gouvernorats constituent **24 séries temporelles parallèles**, partageant
le même calendrier mais dotées chacune de sa dynamique. C'est une structure de
panel, et deux stratégies s'offraient.

| | Modèle global (retenu) | 24 modèles locaux |
|---|---|---|
| Lignes d'entraînement | 1 585 728 | 66 072 chacun |
| Modèles à produire | 3 | 72 |
| Spécificités locales | Via lat/lon/altitude/cluster | Apprises directement |
| Poids au déploiement | 3 fichiers | 72 fichiers versionnés |

Le **modèle global** est retenu, pour trois raisons.

Le volume d'entraînement est vingt-quatre fois supérieur, et la relation
physique apprise est commune : l'influence de la pression, du rayonnement et de
l'inertie thermique du sol sur la température ne dépend pas du gouvernorat.

Les spécificités locales ne sont pas perdues pour autant : latitude, longitude,
altitude et `cluster_climatique` les portent explicitement. Kef à 637 m et
Tozeur à 50 m sont distingués par ces variables.

Enfin le déploiement : une forêt aléatoire entraînée sur ces volumes pèse
plusieurs dizaines de mégaoctets ; multipliée par 72, elle saturerait le dépôt.

L'évaluation est **ventilée par gouvernorat** afin de vérifier qu'aucun n'est
systématiquement mal servi par le modèle commun. Un écart marqué sur un
gouvernorat particulier serait un résultat à documenter, pas à masquer.

### 7.2 Conséquence technique impérative

Toute opération temporelle doit être effectuée **par gouvernorat** :

```python
# CORRECT
df.groupby("gouvernorat")["temperature_2m"].shift(24)

# FAUX
df["temperature_2m"].shift(24)
```

Un décalage global ferait récupérer aux premières heures de chaque gouvernorat
les dernières heures du gouvernorat précédent dans l'ordre de tri. L'erreur est
**silencieuse** — aucune exception, seulement des valeurs contaminées aux
frontières. Sur 24 séries et 168 heures de profondeur maximale, cela représente
environ 4 000 lignes fausses. Un contrôle dédié figure dans `01_etl/checks.py`.

### 7.3 Indépendance des observations

Les 1 585 728 lignes ne constituent pas 1 585 728 observations indépendantes. À
une heure donnée, les 24 gouvernorats sont fortement corrélés, et les quatre du
Grand Tunis sont quasiment le même point de grille. La taille d'échantillon
effective est très inférieure au nombre de lignes.

Cela n'invalide pas l'approche mais impose de la prudence dans l'interprétation
de petits écarts de performance entre modèles.

## 8. Feature engineering

### 8.1 Principe

Une seule fonction `build_features(df, horizon)` dans
`06_machine_learning/features.py`, importée à la fois par le script
d'entraînement et par l'application. Cette logique n'est jamais dupliquée :
mêmes colonnes, mêmes noms, même ordre des deux côtés.

### 8.2 Règle anti-fuite

La cible est `temperature_2m.shift(-H)`. Une variable n'est admissible comme
feature que si sa valeur est réellement connue à l'instant t.

Cela autorise l'état météorologique complet à t et avant — à l'instant t, ces
valeurs sont observées et l'API forecast les fournit en production. Cela
interdit toute variable postérieure à t.

La confusion à éviter : prédire `temperature_2m(t)` à partir de
`apparent_temperature(t)` produit un R² artificiel proche de 0,99, parce que
les deux décrivent le même instant. Prédire `temperature_2m(t+24)` à partir de
`apparent_temperature(t)` est légitime. La fuite tient à l'horizon, pas à la
variable.

### 8.3 Filtrage par cohérence inter-sources

L'entraînement se fait sur ERA5, la production sur l'API forecast. Ces deux
sources ne coïncident pas exactement. Mesure effectuée sur Tunis, 1 968 heures
communes (25 avril → 15 juillet 2026) :

| Variable | Biais | MAE | MAE/σ |
|---|---|---|---|
| `soil_temperature_0_to_7cm` | 0,000 | 0,000 | 0,00 |
| `soil_moisture_0_to_7cm` | 0,000 | 0,000 | 0,00 |
| `shortwave_radiation` | +3,23 | 14,30 | 0,04 |
| `pressure_msl` | −0,20 | 0,28 | 0,07 |
| `et0_fao_evapotranspiration` | −0,003 | 0,018 | 0,07 |
| `precipitation` | −0,013 | 0,021 | 0,11 |
| `apparent_temperature` | −0,38 | 0,86 | 0,13 |
| `temperature_2m` | −0,77 | 0,96 | 0,16 |
| `vapour_pressure_deficit` | −0,32 | 0,37 | 0,29 |
| `wind_gusts_10m` | −1,85 | 4,02 | 0,34 |
| `relative_humidity_2m` | +6,25 | 7,39 | 0,35 |
| `dew_point_2m` | +1,21 | 1,57 | 0,41 |
| `cloud_cover` | +8,38 | 15,85 | 0,44 |
| `wind_speed_10m` | +0,84 | 2,22 | 0,49 |

Un biais d'entrée de 0,8 °C sur la température n'est pas négligeable face à une
MAE cible de l'ordre de 1,5 à 2 °C. Les variables retenues comme features sont
donc celles dont les deux sources s'accordent (MAE/σ ≤ 0,16) :

- `temperature_2m`, `apparent_temperature`
- `pressure_msl`, `surface_pressure`
- `shortwave_radiation`, `direct_radiation`, `diffuse_radiation`
- `et0_fao_evapotranspiration`
- `precipitation`, `rain`
- `soil_temperature_*`, `soil_moisture_*`

Les variables écartées — humidité relative, point de rosée, nébulosité, vents,
déficit de pression de vapeur — restent pleinement exploitées en EDA, dans le
rapport Power BI et dans le data mining, où aucune contrainte de production ne
s'applique.

Cette mesure sera étendue aux 24 gouvernorats en phase ETL, et le tableau
obtenu constituera une section du rapport.

### 8.4 Variables construites

- **Décalages** de `temperature_2m` : t−1, t−2, t−3, t−6, t−12, t−24, t−48, t−168
- **Décalages** des autres variables retenues : t−1, t−24
- **Fenêtres glissantes décalées** (`shift(1)` puis `rolling`) sur 24 h, 72 h et
  168 h : moyenne, minimum, maximum. Le décalage précède systématiquement le
  calcul, faute de quoi la fenêtre inclurait l'instant courant.
- **Encodage cyclique** : sinus et cosinus de l'heure et du jour de l'année
- **Statiques** : latitude, longitude, altitude, `cluster_climatique`

## 9. Découpage chronologique

| Jeu | Période | Volume approximatif |
|---|---|---|
| Entraînement | 2019-01-01 → 2023-12-31 | ~1 050 000 |
| Validation | 2024-01-01 → 2025-06-30 | ~315 000 |
| Test | 2025-07-01 → 2026-07-15 | ~220 000 |

Découpage par date, appliqué identiquement aux 24 gouvernorats. Aucun mélange
aléatoire : sur une série temporelle, un `train_test_split` aléatoire place des
observations futures dans l'entraînement et produit des scores faux.

Les premières 168 heures de chaque gouvernorat sont écartées, faute de
profondeur suffisante pour calculer les décalages.

## 10. Baselines et modèles

### 10.1 Baselines naïves

Deux références obligatoires, calculées sur le jeu de test :

1. **Persistance** — `T(t+H) = T(t)`. Solide à t+1 h, s'effondre à t+72 h.
2. **Climatologie** — moyenne historique pour ce gouvernorat, cette heure et ce
   jour de l'année. Insensible à l'horizon, donc de plus en plus compétitive
   quand H augmente.

Ces deux références sont naïves par construction : les battre est nécessaire,
pas suffisant.

Elles sont **déjà mesurées** sur la période de test (217 152 lignes,
juillet 2025 → juillet 2026) :

| Horizon | Persistance | Climatologie | Barre à battre |
|---|---|---|---|
| t+1 h | **0,88 °C** | 2,25 °C | 0,88 °C |
| t+24 h | **1,74 °C** | 2,25 °C | 1,74 °C |
| t+72 h | 2,54 °C | **2,25 °C** | 2,25 °C |

Deux enseignements. La persistance se dégrade régulièrement avec l'horizon,
tandis que la climatologie reste rigoureusement constante — prévoir à trois
jours ne lui coûte pas plus cher qu'à une heure, puisqu'elle ne consulte que le
calendrier.

Et surtout, **elles se croisent entre t+24 h et t+72 h**. C'est ce croisement
qui justifie d'en avoir retenu deux : avec la seule persistance, la barre à
t+72 h aurait été estimée à 2,54 °C alors qu'elle est en réalité à 2,25 °C.

La barre de t+1 h est sévère : battre 0,88 °C suppose de faire mieux que
« la température ne change pas en une heure », ce qui est déjà une très bonne
approximation.

### 10.2 Modèles comparés

Sept modèles, départagés sur une métrique unique — la MAE — selon la même
démarche que les projets de classification précédents, où le ROC-AUC jouait ce
rôle. Chacun répond à une question distincte : la liste doit raconter une
progression, pas empiler des algorithmes.

| Modèle | Question |
|---|---|
| Régression linéaire | La relation est-elle simplement linéaire ? |
| Ridge | La régularisation aide-t-elle face à des décalages corrélés ? |
| Lasso | Quelles variables comptent vraiment ? |
| k-NN | Une approche purement locale suffit-elle ? |
| Arbre de décision | Un arbre seul capture-t-il la non-linéarité ? |
| Forêt aléatoire | Le bagging corrige-t-il le sur-apprentissage de l'arbre ? |
| XGBoost | Le boosting fait-il mieux que le bagging ? |

Le Lasso occupe une place particulière : il annulera une partie des variables
de décalage, et la comparaison entre celles qu'il retient et celles que la PACF
de la phase 05 désignait fait dialoguer les deux phases.

Chacun dans un `Pipeline` scikit-learn, la totalité du pipeline étant
sérialisée pour que l'application réutilise un prétraitement rigoureusement
identique.

### 10.3 Contrainte d'échelle et comparaison témoin

k-NN ne passe pas à 1,58 M de lignes : le calcul de distance à chaque point
d'entraînement rend la prédiction prohibitive. Il est entraîné sur un
sous-échantillon d'environ 50 000 lignes, tiré **en respectant la partition
chronologique**.

Comparer alors k-NN à un XGBoost entraîné sur trente fois plus de données
serait malhonnête. Un **XGBoost témoin** est donc entraîné sur le même
sous-échantillon. Il n'entre pas dans la sélection du modèle final et n'est
jamais déployé.

| Comparaison | Volume | Modèles | Usage |
|---|---|---|---|
| Principale | 1 585 728 | Linéaire, Ridge, Lasso, arbre, forêt, XGBoost | Sélection, déploiement |
| Secondaire | ~50 000 | k-NN, XGBoost témoin | Départager algorithme et volume |

### 10.4 Le tableau comparatif final

Baselines naïves, modèles statistiques de la phase 05 et modèles ML sont réunis
dans une seule comparaison, par horizon :

| Modèle | Origine | MAE t+1 h | MAE t+24 h | MAE t+72 h |
|---|---|---|---|---|
| Persistance | baseline | 0,88 | 1,74 | 2,54 |
| Climatologie | baseline | 2,25 | 2,25 | 2,25 |
| ARIMA | phase 05 | | | |
| SARIMA | phase 05 | | | |
| Fourier + ARIMA | phase 05 | | | |
| Régression linéaire | phase 06 | | | |
| Ridge | phase 06 | | | |
| Lasso | phase 06 | | | |
| Arbre de décision | phase 06 | | | |
| Forêt aléatoire | phase 06 | | | |
| XGBoost | phase 06 | | | |

C'est ce tableau qui donne sa portée à la phase 05 : les modèles statistiques
n'y préparent pas seulement le feature engineering, ils concourent. Battre une
moyenne naïve ne démontre rien ; battre une régression harmonique à erreurs
ARIMA est un résultat défendable.

### 10.5 Interprétation

Importance des variables et SHAP sur le modèle retenu. Contrôle spécifique :
les décalages de température doivent dominer. Un poids anormal sur une variable
contemporaine signalerait une fuite temporelle passée inaperçue.

### 10.6 Stratégie multi-horizon

Trois modèles directs indépendants, un par horizon, partageant le même
pipeline de features. Approche préférée au schéma récursif, qui accumulerait
l'erreur sur 72 pas successifs.

### 10.7 Métriques

MAE (critère de sélection), RMSE, R², et gain relatif sur chacune des deux
baselines. Résultats ventilés par horizon et par gouvernorat.

Le MAPE est écarté : la température tunisienne passe par zéro en hiver, ce qui
fait exploser un rapport en pourcentage.

## 11. Les deux phases d'analyse

### 11.1 Data mining — dimension spatiale

ACP sur les profils climatiques agrégés des 24 gouvernorats, puis K-means pour
faire émerger les groupes climatiques. Validation de cohérence : les groupes
obtenus doivent correspondre à la géographie réelle — littoral nord, intérieur,
sud saharien. Le nombre de groupes est choisi par méthode du coude et score de
silhouette.

Point de vigilance : Tunis, Ariana, Ben Arous et Manouba occupent des points de
grille quasi confondus. Leur regroupement traduirait la proximité géographique
autant que la similarité climatique, et ne doit pas être présenté comme une
découverte.

Sortie exploitée en aval : la colonne `cluster_climatique` de
`dim_gouvernorat`, utilisée comme variable statique par les modèles.

### 11.2 Séries temporelles — dimension temporelle

Décomposition STL (cycles diurne et annuel), tests de stationnarité ADF et
KPSS, puis ACF et PACF.

**La PACF justifie le choix des décalages.** Poser des lags à t−1, t−24 et
t−168 par intuition est une supposition ; l'autocorrélation partielle montre
lesquels portent une information propre, une fois retiré l'effet des décalages
intermédiaires. La phase 08 s'appuie sur ce résultat.

Trois modèles statistiques, en progression délibérée :

| Modèle | Capture | Ne capture pas |
|---|---|---|
| `ARIMA(p,d,q)` | Structure autorégressive courte | Toute saisonnalité |
| `SARIMA(p,d,q)(P,D,Q)₂₄` | Cycle diurne | Cycle annuel |
| Fourier + ARIMA | Cycles diurne et annuel | — |

ARIMA est inclus alors qu'il va échouer : son échec démontre que la
saisonnalité porte l'essentiel du signal.

**Pourquoi Fourier plutôt qu'un SARIMA annuel.** La température horaire a deux
périodes saisonnières, 24 h et 8 766 h. SARIMA n'en gère qu'une, et une période
de 8 766 est numériquement infaisable — la dimension de l'espace d'états
l'interdit. La régression harmonique contourne l'obstacle : des termes de
Fourier entrent comme régresseurs exogènes, et ARIMA ne modélise plus que la
structure résiduelle.

Ces trois modèles sont ajustés sur un sous-ensemble de gouvernorats
représentatifs — l'objectif est un point de comparaison, pas un modèle de
production — et figurent au tableau comparatif de la section 10.3.

## 12. Application web

Enchaînement à chaque prédiction :

1. L'utilisateur choisit un gouvernorat et un horizon.
2. L'application interroge l'API forecast pour les 168 dernières heures.
3. `build_features()` — la même fonction qu'à l'entraînement — construit le
   vecteur d'entrée.
4. Le modèle correspondant à l'horizon produit la prévision.
5. Affichage, puis journalisation dans Supabase.

L'interface affiche également l'écart entre la prévision du modèle et celle
publiée par Open-Meteo pour le même instant. C'est un repère honnête : il
situe le modèle face à un système opérationnel professionnel, sans prétendre
le dépasser.

La chaîne de connexion Supabase est lue depuis un fichier `.env`, jamais
inscrite en dur. `.env` figure dans `.gitignore` ; un `.env.example` documente
les variables attendues.

## 13. Limites assumées

- **Couverture saisonnière du test de cohérence inter-sources.** L'API forecast
  ne remonte qu'à 92 jours. La comparaison ERA5/forecast ne couvrira jamais
  l'hiver, et les biais mesurés au printemps-été pourraient différer en saison
  froide.
- **Chef-lieu et non gouvernorat.** Chaque gouvernorat est représenté par les
  coordonnées de son chef-lieu. Les gouvernorats étendus, notamment au sud,
  présentent une variabilité interne que ce point unique ne capture pas.
- **ERA5 est une réanalyse, pas une mesure de station.** Les valeurs sont
  issues d'un modèle assimilant des observations, non de relevés directs.
- **Le modèle ne concurrence pas la prévision numérique du temps.** Open-Meteo
  s'appuie sur des modèles physiques à assimilation de données. L'objectif est
  de démontrer une démarche complète, pas de rivaliser avec l'état de l'art.

## 14. Livrables

1. Dépôt GitHub public, documenté et reproductible.
2. Rapport PDF dans `08_rapport/`.
3. Slides dans `09_presentation/`.
4. URL publique de l'application déployée, mentionnée dans le `README.md`.

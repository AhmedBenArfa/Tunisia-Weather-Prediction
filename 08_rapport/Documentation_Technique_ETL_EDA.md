# Documentation technique — Phase ETL et analyse exploratoire

> **Auteur** : Ahmed Ben Arfa
> **Projet** : Tunisia Weather Prediction
> **Phase** : 01 — Extraction, contrôles, nettoyage, exploration
> **Date** : juillet 2026

## 1. Objectif de la phase

Constituer un jeu de données horaire fiable pour les 24 gouvernorats tunisiens,
en établir la qualité par des contrôles automatisés, corriger les anomalies
identifiées, et déterminer **quelles variables sont utilisables en production**.

Ce dernier point est la contribution principale de la phase. Le modèle
s'entraînera sur la réanalyse ERA5 mais prédira à partir de l'API forecast :
une variable dont ces deux sources divergent propagerait son biais dans toutes
ses variables dérivées, et le modèle se dégraderait en production sans que rien
ne l'annonce en validation.

## 2. Architecture des modules

```
01_etl/
    config.py            Chemins, plages physiques admissibles
    extract_openmeteo.py Extraction ERA5, gestion du quota
    build_parquet.py     Conversion CSV -> Parquet compresse
    checks.py            Controles de qualite, sans effet de bord
    clean.py             Corrections des anomalies connues
    run_etl.py           Orchestrateur
    skew_analysis.py     Comparaison archive / forecast
    notebooks/
        _build_eda.py    Generateur du notebook
        01_eda.ipynb     Analyse exploratoire, genere
tests/
    test_checks.py       7 tests
    test_clean.py        5 tests
    test_skew.py         4 tests
```

Le principe directeur est la séparation entre **fonctions pures** et **effets
de bord**. `checks.py` et `clean.py` ne lisent aucun fichier, n'affichent rien
et ne lèvent aucune exception : ils reçoivent un tableau et retournent un
résultat. C'est l'orchestrateur qui décide quoi en faire. Cette séparation rend
les modules testables sur des données synthétiques, sans réseau ni fichier.

Le notebook est **généré** par un script versionné. Il ne s'édite jamais à la
main : toute correction passe par `_build_eda.py`, puis régénération. Les
différences Git restent lisibles et le résultat est reproductible.

## 3. Extraction des données

### 3.1 Source

Open-Meteo, API d'archive `archive-api.open-meteo.com`, qui restitue la
réanalyse ERA5 du ECMWF produite dans le cadre du programme Copernicus.

Une réanalyse n'est pas un relevé de station : c'est la sortie d'un modèle
atmosphérique assimilant les observations disponibles pour reconstituer un état
cohérent de l'atmosphère sur une grille régulière.

### 3.2 La contrainte de quota

Le quota Open-Meteo n'est pas un compte de requêtes mais un **volume pondéré** :

```
poids = (nb_variables / 10) x (nb_jours / 14)
```

Une requête de ce projet — 31 variables sur 7,5 ans — pèse à elle seule
**environ 610 appels**. Les 24 gouvernorats totalisent ~14 600 appels pour un
plafond gratuit de 10 000 par jour : **l'extraction complète ne tient pas dans
une journée.**

Trois plafonds se superposent : 600 appels par minute, 5 000 par heure, 10 000
par jour. Un backoff exponentiel classique échoue : il retente avant la
réouverture de la fenêtre et épuise ses essais dans le vide.

Le script lit donc le motif exact renvoyé dans le corps de la réponse 429 :

| Motif renvoyé | Réaction |
|---|---|
| `Minutely ... limit exceeded` | attente de 65 s |
| `Hourly ... limit exceeded` | attente jusqu'à l'heure pleine suivante |
| `Daily ... limit exceeded` | arrêt propre, liste des gouvernorats restants |

Il **reprend là où il s'est arrêté** : tout gouvernorat dont le fichier existe
déjà est relu depuis le disque au lieu d'être retéléchargé.

Le **quota journalier se réinitialise à minuit UTC**, ce que la documentation
Open-Meteo ne précise pas. Le comportement a été établi empiriquement : blocage
à 19:22 UTC, requêtes acceptées à nouveau à 03:58 UTC le lendemain.

L'extraction s'est déroulée sur deux jours — 21 gouvernorats le premier,
les 3 derniers le lendemain matin.

### 3.3 Format de stockage

| Forme | Taille | Versionnée |
|---|---|---|
| 24 CSV bruts | ~308 Mo | Non — redondants |
| CSV combiné | 308 Mo | Non — dépasse la limite GitHub de 100 Mo |
| **Parquet zstd** | **42,1 Mo** | **Oui** |

Le Parquet divise le volume par 7,3 et se lit nativement par DuckDB, sans
import préalable. Les données Open-Meteo étant publiques (licence CC BY 4.0),
rien n'imposait de les exclure du dépôt.

### 3.4 Jeu obtenu

| Caractéristique | Valeur |
|---|---|
| Lignes | 1 585 728 |
| Colonnes | 36 |
| Gouvernorats | 24 |
| Heures par gouvernorat | 66 072 |
| Période | 2019-01-01 00:00 → 2026-07-15 23:00 |
| Fuseau | `Africa/Tunis` |

## 4. Contrôles de qualité

### 4.1 Les cinq contrôles

| Contrôle | Ce qu'il vérifie |
|---|---|
| `verifier_completude` | Aucune valeur manquante |
| `verifier_doublons` | Unicité du couple (gouvernorat, heure) |
| `verifier_continuite_horaire` | Chaque série avance d'exactement une heure |
| `verifier_plages_physiques` | 24 variables dans des bornes admissibles |
| `verifier_decalage_groupe` | Un décalage a bien été calculé par gouvernorat |

Les plages physiques sont volontairement larges : l'objectif est l'aberration
franche, pas la valeur rare. Une température de 55 °C serait signalée, une de
48 °C ne le serait pas — et c'est voulu, puisque le maximum réel du jeu atteint
50,2 °C.

### 4.2 Le contrôle qui compte pour la suite

`verifier_decalage_groupe` mérite une explication. Le jeu empile **24 séries
parallèles** dans un même tableau. Un décalage global contamine les premières
heures de chaque série avec les dernières de la précédente :

```python
# CORRECT
df.groupby("gouvernorat")["temperature_2m"].shift(24)

# FAUX : les premieres heures de Ben Arous recuperent
# les dernieres heures d'Ariana
df["temperature_2m"].shift(24)
```

L'erreur est **silencieuse** : aucune exception n'est levée, seules les valeurs
aux frontières entre gouvernorats sont fausses. Sur 24 séries et 168 heures de
profondeur maximale, cela représente environ 4 000 lignes erronées noyées dans
1,58 million.

Le contrôle vérifie qu'un décalage groupé laisse exactement `horizon` valeurs
manquantes en tête de chaque série. Il resservira en phase 06 pour valider la
fonction de construction des variables.

### 4.3 Résultats sur le jeu réel

| Contrôle | Résultat |
|---|---|
| Complétude | **0 valeur manquante** sur 1 585 728 × 36 |
| Doublons | **0** |
| Continuité horaire | **Tous les intervalles valent exactement 1 h** |
| Nombre de gouvernorats | 24, avec 66 072 heures chacun |
| Plages physiques | Une seule famille d'anomalies |

La continuité parfaite mérite d'être soulignée : sur les 66 071 intervalles de
chaque série, aucun ne diffère d'une heure. Aucun trou, aucune heure dupliquée.
La Tunisie n'appliquant pas l'heure d'été, il n'y a pas non plus d'artefact de
changement d'heure — un problème classique sur des séries horaires.

## 5. Anomalies identifiées et traitement

### 5.1 Humidités de sol négatives

`soil_moisture_*` descendait à **−0,013 m³/m³**, ce qui est physiquement
impossible : une teneur en eau volumique ne peut pas être négative.

| Couche | Lignes concernées | Part |
|---|---|---|
| `soil_moisture_0_to_7cm` | 493 | 0,031 % |
| `soil_moisture_7_to_28cm` | 460 | 0,029 % |
| `soil_moisture_28_to_100cm` | 428 | 0,027 % |

Les cas se concentrent sur les gouvernorats arides du sud — Tozeur, Kebili,
Gabès, Médenine, Tataouine, Gafsa, Sidi Bouzid, Sfax. Il s'agit d'un artefact
numérique de la réanalyse sur sols très secs, où la grandeur oscille autour de
zéro.

**Traitement** : troncature à zéro par `clean.py`. L'ampleur (0,03 %) et la
nature de l'artefact rendent toute autre correction inutilement sophistiquée.

### 5.2 Redondance entre `rain` et `precipitation`

Les deux colonnes ne diffèrent que sur **144 lignes** — exactement celles où il
neige. Leur corrélation atteint **1,000** après arrondi.

**Traitement** : aucun au niveau des données. C'est une décision de
modélisation, prise en phase 06 : une seule des deux entrera dans le modèle.

### 5.3 Points de grille partagés

Trois paires de gouvernorats partagent la même latitude de grille :
Tunis/Manouba, Beja/Ben Arous, Zaghouan/Nabeul. Leurs longitudes diffèrent,
donc les points restent distincts, mais la résolution ERA5 ne sépare pas
finement des chefs-lieux voisins.

Les quatre gouvernorats du Grand Tunis occupent des points quasi confondus.
**Conséquence à retenir pour la phase 04** : un regroupement de ces quatre-là au
clustering traduirait la proximité géographique autant que la similarité
climatique, et ne devra pas être présenté comme une découverte.

## 6. Cohérence entre source d'entraînement et source de production

### 6.1 Le problème

Le modèle s'entraînera sur ERA5 mais prédira à partir de l'API forecast, qui
provient d'un modèle de prévision opérationnel. Un biais systématique sur une
variable se propagerait dans tous ses décalages et fenêtres glissantes.

### 6.2 Protocole

Pour chaque variable, sur les heures communes aux deux sources et sur les 24
gouvernorats — 1 872 heures par gouvernorat :

- **biais moyen** : l'écart systématique entre les deux sources ;
- **MAE** : l'ampleur moyenne du désaccord ;
- **MAE / σ** : ce désaccord rapporté à la variabilité propre de la variable,
  seule grandeur comparable entre des unités différentes.

### 6.3 Résultats

| Variable | Biais | MAE | MAE/σ |
|---|---|---|---|
| `soil_moisture_*` (3 couches) | 0,000 | 0,000 | 0,000 |
| `terrestrial_radiation` | +0,002 | 0,129 | 0,000 |
| `soil_temperature_*` (3 couches) | −0,023 | 0,077 | 0,012 – 0,021 |
| `shortwave_radiation` | +2,800 | 16,342 | 0,047 |
| `rain` | −0,013 | 0,014 | 0,070 |
| `precipitation` | −0,007 | 0,016 | 0,083 |
| `pressure_msl` | −0,224 | 0,350 | 0,088 |
| `et0_fao_evapotranspiration` | −0,003 | 0,027 | 0,103 |
| `direct_radiation` | +6,846 | 29,361 | 0,108 |
| `direct_normal_irradiance` | +11,665 | 44,349 | 0,141 |
| `temperature_2m` | −0,146 | 0,878 | 0,152 |
| `diffuse_radiation` | −4,046 | 14,743 | 0,158 |
| `apparent_temperature` | +0,126 | 1,038 | 0,164 |
| **— seuil 0,20 —** | | | |
| `vapour_pressure_deficit` | −0,082 | 0,286 | 0,235 |
| `cloud_cover_high` | +0,331 | 9,496 | 0,266 |
| `relative_humidity_2m` | +2,155 | 5,754 | 0,295 |
| `dew_point_2m` | +0,539 | 1,538 | 0,392 |
| `cloud_cover` | +8,690 | 15,994 | 0,437 |
| `wind_gusts_10m` | −2,920 | 5,383 | 0,457 |
| `wind_speed_10m` | −0,229 | 2,608 | 0,458 |
| `cloud_cover_mid` | +7,937 | 10,353 | 0,541 |
| `surface_pressure` | −0,503 | 2,609 | 0,669 |
| `cloud_cover_low` | +3,952 | 4,244 | 0,671 |

### 6.4 Choix du seuil

Le classement présente une rupture nette entre **0,164 et 0,235** — le saut le
plus large de la zone. Le seuil est placé à **0,20** dans cet intervalle : il
découle de la distribution observée, il n'est pas un chiffre rond posé
d'avance. **17 variables sur 31 sont retenues.**

### 6.5 Deux résultats notables

**`surface_pressure` est écartée quand `pressure_msl` est retenue.** Un rapport
de 0,669 contre 0,088. L'explication est physique : la pression de surface
dépend de l'altitude du relief telle que chaque modèle la représente, et les
deux modèles ne partagent pas le même relief. La pression ramenée au niveau de
la mer, elle, est normalisée — d'où son excellent accord. Sans cette mesure,
`surface_pressure` serait entrée dans le modèle.

**Le biais de température est bien plus faible qu'estimé initialement.**
−0,146 °C sur les 24 gouvernorats, contre −0,77 °C lors d'une mesure
préliminaire sur Tunis seul. Tunis n'était pas représentatif, et l'alarme
initiale était exagérée.

Les variables de sol et le rayonnement terrestre sont **identiques au
millième** entre les deux sources. Pour le rayonnement terrestre c'est
attendu : il est purement astronomique, calculé à partir de la géométrie
Soleil-Terre, pas simulé.

### 6.6 Limites de la mesure

**Couverture saisonnière partielle.** L'API forecast ne remonte qu'à 92 jours :
la comparaison ne couvrira jamais l'hiver, et les biais mesurés en saison
chaude pourraient différer en saison froide.

**Variables sans variance.** `snowfall` ressort indéterminée — il n'a pas neigé
sur la fenêtre, son écart-type est nul et le rapport indéfini.

**Variables circulaires.** Les MAE sur `wind_direction_10m` et
`wind_direction_100m` ne sont pas interprétables : 359° et 1° sont voisins mais
donnent un écart de 358. Ces deux variables sont écartées par ailleurs, mais
leur valeur ne constitue pas une mesure valide.

## 7. Analyse exploratoire

### 7.1 Contrastes régionaux

La Tunisie s'étend sur près de 900 km, du littoral méditerranéen aux portes du
Sahara. Le gradient nord-sud est le fait structurant du jeu.

**Précipitations annuelles moyennes (2019-2025)** : de **525 mm à Bizerte** à
**83 mm à Tozeur**, soit un rapport de **1 à 6**.

**Température moyenne** : de 17,0 °C au Kef à 22,8 °C à Tozeur.

Le classement thermique n'est pas purement latitudinal. Les gouvernorats les
plus frais — Kef et Kasserine — sont aussi les plus élevés, à 637 m et 674 m.
Bizerte présente le minimum le plus doux malgré sa position la plus au nord,
effet modérateur de la mer, tandis que Sidi Bouzid et Kasserine descendent sous
−3 °C.

**Conséquence pour la modélisation** : latitude, longitude et altitude portent
tous trois de l'information. Ce sont ces variables statiques qui permettront à
un modèle global unique de distinguer les gouvernorats.

### 7.2 Structure temporelle

**Deux saisonnalités coexistent** : un cycle diurne de 24 heures et un cycle
annuel de 8 766 heures.

C'est la contrainte centrale de la phase 05. SARIMA ne gère qu'une seule
période saisonnière, et une période de 8 766 est numériquement infaisable —
l'espace d'états atteindrait des dimensions hors de portée. D'où le recours
prévu aux termes de Fourier en régresseurs exogènes.

L'amplitude diurne varie fortement entre littoral et intérieur continental, ce
qui recoupe le contraste climatique attendu.

### 7.3 Distributions

| Variable | Asymétrie | Aplatissement |
|---|---|---|
| `snowfall` | **234,73** | **69 693,87** |
| `rain` | 18,39 | 528,71 |
| `precipitation` | 18,37 | 527,02 |
| `cloud_cover_low` | 3,10 | 9,04 |
| `surface_pressure` | −1,33 | 1,02 |

`snowfall` n'est pas une variable exploitable : 144 heures de neige sur
1,58 million donnent une asymétrie de 234 et un aplatissement de près de
70 000. Elle était déjà écartée faute de variance dans la fenêtre de
comparaison ; ces chiffres le confirment indépendamment.

Les précipitations suivent avec une asymétrie de 18,4 — attendu, puisqu'il ne
pleut pas la plupart des heures et que l'intensité peut être forte quand il
pleut. Une telle asymétrie écarte toute hypothèse de normalité.

La température est **bimodale**, les deux modes correspondant aux saisons et
non à deux populations distinctes. La pression est la seule variable proche
d'une gaussienne.

La dispersion des températures de sol **décroît nettement avec la
profondeur** : le sol profond filtre les variations rapides et porte l'inertie
thermique saisonnière — un signal potentiellement précieux pour la prévision.

### 7.4 Corrélations entre variables retenues

**14 paires dépassent 0,90**, regroupées en trois familles.

| Paire | Corrélation |
|---|---|
| `precipitation` ↔ `rain` | **1,000** |
| `direct_radiation` ↔ `shortwave_radiation` | 0,982 |
| `apparent_temperature` ↔ `temperature_2m` | 0,975 |
| `shortwave_radiation` ↔ `terrestrial_radiation` | 0,971 |
| `soil_temperature_0_to_7cm` ↔ `temperature_2m` | 0,964 |
| `apparent_temperature` ↔ `soil_temperature_0_to_7cm` | 0,951 |
| `et0_fao_evapotranspiration` ↔ `shortwave_radiation` | 0,946 |
| `diffuse_radiation` ↔ `terrestrial_radiation` | 0,943 |
| `soil_temperature_28_to_100cm` ↔ `soil_temperature_7_to_28cm` | 0,935 |
| `direct_radiation` ↔ `et0_fao_evapotranspiration` | 0,933 |
| `direct_normal_irradiance` ↔ `direct_radiation` | 0,932 |
| `direct_normal_irradiance` ↔ `shortwave_radiation` | 0,928 |
| `direct_radiation` ↔ `terrestrial_radiation` | 0,916 |
| `et0_fao_evapotranspiration` ↔ `terrestrial_radiation` | 0,914 |

**Conséquences directes pour la phase 06.**

Le groupe rayonnement est le plus lourd : cinq variables retenues se recoupant
à plus de 0,91. Leur construire à chacune huit décalages et trois fenêtres
glissantes produirait **environ 55 colonnes portant l'information d'une
dizaine**. Un ou deux représentants suffiront.

La colinéarité rend par ailleurs les coefficients d'une régression ordinaire
instables — de petites variations des données produisent de grands changements
de coefficients. C'est exactement le problème que traitent Ridge et Lasso :
leur comparaison avec la régression simple devient un résultat, et non un
passage obligé.

`soil_temperature_0_to_7cm` corrèle à 0,964 avec la température de l'air, ce
qui est logique en surface. Les couches profondes décrochent, et c'est
précisément leur intérêt : elles portent une inertie que l'air ne porte pas.

## 8. Tests

16 tests automatisés, exécutés par `pytest tests/ -v`.

| Fichier | Tests | Portée |
|---|---|---|
| `test_checks.py` | 7 | Chaque contrôle sur jeu valide et jeu dégradé |
| `test_clean.py` | 5 | Correction, non-modification de l'origine, journal |
| `test_skew.py` | 4 | Calcul des métriques, hors réseau |

Tous s'appuient sur des données **synthétiques** construites dans le test : ni
fichier, ni réseau, exécution en moins d'une seconde.

Le test le plus important est `test_decalage_global_detecte_comme_faux` : il
construit deux séries, applique un décalage global, et vérifie que le contrôle
le refuse. C'est le garde-fou contre le bug silencieux décrit en 4.2.

**Non couvert** : la fonction `recuperer_forecast` de `skew_analysis.py`, qui
touche au réseau. Sa logique de reprise sur erreur — distinguant un 429 de
quota d'un 5xx transitoire — a été ajoutée après un échec réel en cours
d'exécution, mais n'a pas été éprouvée par un test.

## 9. Livrables de la phase

| Livrable | Contenu |
|---|---|
| `data/tunisia_weather_clean.parquet` | 1 585 728 lignes, nettoyées, 42,1 Mo |
| `data/skew_era5_forecast.csv` | Décalage par gouvernorat et par variable |
| `01_etl/notebooks/01_eda.ipynb` | 45 cellules, 8 figures, exécuté |
| `tests/` | 16 tests |

## 10. Conséquences pour la suite

**Phase 02 — entrepôt.** Le schéma en étoile part de
`tunisia_weather_clean.parquet`, pas du fichier brut.

**Phase 04 — data mining.** Le clustering doit tenir compte de l'artefact du
Grand Tunis, dont les quatre gouvernorats partagent des points de grille quasi
confondus.

**Phase 05 — séries temporelles.** Les deux saisonnalités identifiées imposent
le recours aux termes de Fourier, SARIMA seul étant structurellement
insuffisant.

**Phase 06 — modélisation.** Les 17 variables retenues constituent le point de
départ. Les groupes colinéaires identifiés en 7.4 réduiront encore ce nombre.
Le garde-fou `verifier_decalage_groupe` validera la construction des variables.

## 11. Limites assumées

- **La comparaison inter-sources ne couvre pas l'hiver** — l'API forecast ne
  remonte qu'à 92 jours.
- **Un point par gouvernorat.** Les gouvernorats étendus du sud ont une
  variabilité interne que leur chef-lieu ne capture pas.
- **ERA5 est une réanalyse, pas une mesure de station.** Les extrêmes peuvent
  être lissés.
- **Les contrôles de plage détectent l'aberration franche, pas la valeur
  plausible mais fausse.** Aucun contrôle automatisé ne peut faire mieux sans
  source de vérité indépendante.
- **7,5 ans d'historique** — suffisant pour la variabilité saisonnière et
  interannuelle courante, insuffisant pour des événements rares ou une tendance
  climatique.

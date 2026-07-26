# 1 — Description du projet

> **Auteur** : Ahmed Ben Arfa
> **Projet** : Tunisia Weather Prediction
> **Date** : juillet 2026

## 1. Contexte

La Tunisie s'étend sur près de 900 km du nord au sud, du littoral
méditerranéen aux portes du Sahara. Cette étendue produit des régimes
climatiques très différents d'un gouvernorat à l'autre : sur la période
étudiée, le cumul de précipitations annuel moyen va de **525 mm à Bizerte** à
**83 mm à Tozeur**, soit un rapport de 1 à 6. La température moyenne varie de
17,0 °C au Kef à 22,8 °C à Tozeur.

Prévoir la température à court terme a une valeur pratique directe :
planification agricole et irrigation, dimensionnement de la production solaire,
anticipation des vagues de chaleur, gestion de la demande énergétique.

Ce projet construit une chaîne analytique complète sur ce sujet, de
l'extraction des données jusqu'à une application web déployée.

## 2. Objectif

Prévoir la **température à t+1 h, t+24 h et t+72 h** pour chacun des 24
gouvernorats, à partir de l'état météorologique observé jusqu'à l'instant
courant.

Trois horizons plutôt qu'un seul, parce que la comparaison entre eux est
elle-même un résultat : elle montre comment la prévisibilité se dégrade avec le
temps, et à partir de quand un modèle statistique cesse d'apporter quelque
chose face à une simple moyenne climatique.

## 3. Ce qui distingue ce projet des précédents

Les deux projets antérieurs traitaient des problèmes de **classification sur
données transversales** — churn client, risque cardiaque. Ici il s'agit d'une
**régression sur série temporelle**, ce qui change la méthode sur trois points
non négociables :

| Point | Classification transversale | Série temporelle |
|---|---|---|
| Découpage | Aléatoire stratifié | Chronologique strict |
| Fuite de données | Variables encodant la cible | Variables postérieures à l'instant de prédiction |
| Référence | Classe majoritaire, tirage au hasard | Persistance, climatologie, ARIMA |
| Structure | Observations indépendantes | 24 séries parallèles, fortement corrélées |

Un découpage aléatoire placerait des observations futures dans l'entraînement
et produirait des scores flatteurs mais faux. Un modèle qui utiliserait la
température ressentie au même instant que la cible afficherait un R² proche de
0,99 sans rien prédire du tout.

Ces pièges sont faciles à commettre et difficiles à repérer après coup. Les
éviter — et montrer comment — constitue une part importante de la valeur du
projet.

## 4. Périmètre fonctionnel

### 4.1 Extraction et préparation

Extraire l'historique horaire des 24 gouvernorats depuis Open-Meteo, contrôler
sa qualité, le convertir dans un format exploitable et versionnable.

Particularité : **les données ont été extraites par l'équipe projet**, elles
n'ont pas été fournies. Cela ajoute au périmètre la conception de la stratégie
d'extraction, la gestion des quotas de l'API et la vérification de l'intégrité
du jeu obtenu.

### 4.2 Entrepôt et modèle dimensionnel

Construire un schéma en étoile dans DuckDB — fait horaire, fait journalier
agrégé, dimensions gouvernorat et temps — et alimenter Supabase avec la seule
partie utile à l'application déployée.

### 4.3 Restitution descriptive

Produire un rapport Power BI sur la climatologie tunisienne : profils
mensuels, contrastes régionaux, extrêmes, précipitations.

### 4.4 Data mining — dimension spatiale

Regrouper les gouvernorats par profil climatique via ACP et K-means. Le
regroupement obtenu alimente ensuite les modèles prédictifs.

### 4.5 Séries temporelles — dimension temporelle

Décomposer les séries (tendance, saisonnalités, résidu), tester la
stationnarité, et analyser l'autocorrélation. L'autocorrélation partielle sert
directement à **justifier le choix des décalages** utilisés en modélisation, au
lieu de les poser par intuition.

Trois modèles statistiques en progression — ARIMA, puis SARIMA à période
diurne, puis régression harmonique de Fourier avec erreurs ARIMA — qui
deviennent des concurrents à part entière des modèles de machine learning.

### 4.6 Machine learning

Construire les variables explicatives sans fuite temporelle, comparer plusieurs
familles de modèles à trois horizons, les évaluer face aux baselines naïves et
aux modèles statistiques, puis retenir le meilleur.

Un **modèle global** par horizon est entraîné sur les 24 gouvernorats empilés,
plutôt que 24 modèles locaux : le volume d'entraînement est vingt-quatre fois
supérieur, la physique atmosphérique apprise est commune, et les spécificités
locales restent portées par la latitude, l'altitude et le groupe climatique.

### 4.7 Application web

Déployer une application où l'utilisateur choisit un gouvernorat et un horizon,
reçoit une prévision calculée à partir de données fraîches, et peut la comparer
à la prévision publiée par Open-Meteo.

## 5. Critères de succès

| Critère | Seuil |
|---|---|
| Le modèle bat la meilleure baseline à t+1 h | Gain en MAE mesurable |
| Le modèle bat la meilleure baseline à t+24 h | Gain net et documenté |
| Le modèle bat la meilleure baseline à t+72 h | Gain net, ou constat argumenté de son absence |
| Absence de fuite temporelle | Vérifiée par construction et par l'écart validation/test |
| Cohérence entraînement / production | Écart mesuré et variables filtrées en conséquence |
| Reproductibilité | Pipeline ré-exécutable depuis le dépôt seul |

Le troisième critère mérite une précision : **si le modèle ne bat pas la
climatologie à 72 h, ce n'est pas un échec du projet.** C'est un résultat, et
il devra être présenté comme tel plutôt que masqué. La prévision à trois jours
relève de la modélisation physique de l'atmosphère, pas de la régression sur
historique.

## 6. Livrables

| Livrable | Format | Contenu |
|---|---|---|
| Code source | Dépôt GitHub public | Scripts, notebooks, application, données Parquet, documentation |
| Application déployée | URL publique | Interface de prévision fonctionnelle |
| Rapport | PDF | Démarche, architecture, choix techniques, résultats, limites |
| Présentation | Slides | Synthèse et démonstration |

## 7. Hors périmètre

- **Concurrencer la prévision numérique du temps.** Open-Meteo s'appuie sur des
  modèles physiques à assimilation de données, alimentés par des observations
  mondiales. L'objectif ici est de démontrer une démarche complète et rigoureuse,
  pas de rivaliser avec l'état de l'art opérationnel.
- **Prévoir d'autres variables que la température.** Précipitations et vent
  restent exploités en analyse descriptive, sans modèle prédictif dédié.
- **Descendre sous la maille du gouvernorat.** Chaque gouvernorat est représenté
  par un point unique.

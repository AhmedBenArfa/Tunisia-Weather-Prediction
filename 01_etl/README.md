# 01 — ETL

Extraction des données horaires Open-Meteo pour les 24 gouvernorats, conversion
en Parquet compressé, contrôles qualité et analyse exploratoire.

## Flux de données

```mermaid
flowchart LR
    API[Open-Meteo Archive<br/>ERA5] --> EX[extract_openmeteo.py]
    EX --> CSV[data/raw_*.csv<br/>24 fichiers, ~308 Mo]
    CSV --> BP[build_parquet.py]
    BP --> PQ[(data/tunisia_weather_hourly.parquet<br/>1 585 728 lignes, 42 Mo)]
```

## Fichiers

| Fichier | Rôle |
|---|---|
| `config.py` | Chemins, plages physiques admissibles |
| `extract_openmeteo.py` | Extraction ERA5, gestion du quota, reprise sur incident |
| `build_parquet.py` | Concaténation des 24 CSV en un Parquet zstd |
| `checks.py` | Contrôles qualité, sans effet de bord |
| `clean.py` | Correction des anomalies connues |
| `run_etl.py` | Orchestrateur : charge → contrôle → nettoie → écrit |
| `skew_analysis.py` | Comparaison ERA5 / API forecast sur les 24 gouvernorats |
| `notebooks/_build_eda.py` | Générateur du notebook, versionné |
| `notebooks/01_eda.ipynb` | Analyse exploratoire, généré |

## Exécution

```bash
python 01_etl/run_etl.py                  # controles + nettoyage -> Parquet propre
python 01_etl/skew_analysis.py            # decalage inter-sources (reseau, ~2 min)
python 01_etl/notebooks/_build_eda.py     # (re)genere le notebook
python -m nbconvert --to notebook --execute --inplace 01_etl/notebooks/01_eda.ipynb
python -m pytest tests/ -v                # 16 tests
```

Le notebook ne s'édite **jamais** à la main : on modifie `_build_eda.py` puis on
régénère.

## Ce que les contrôles ont trouvé

Sur les 1 585 728 lignes : aucune valeur manquante, aucun doublon, continuité
horaire parfaite (tous les intervalles valent exactement une heure), 24
gouvernorats.

Une seule famille d'anomalies — les humidités de sol négatives, physiquement
impossibles : 493, 460 et 428 valeurs selon la couche, soit 0,03 %, concentrées
sur les gouvernorats arides du sud. Artefact numérique de la réanalyse sur sols
très secs. `clean.py` les ramène à zéro, et le second passage des contrôles ne
remonte plus rien.

## Le contrôle qui compte pour la suite

`verifier_decalage_groupe(df, colonne, horizon)` vérifie qu'un décalage a bien
été calculé **par gouvernorat**. Un `shift()` global contamine les premières
heures de chaque série avec les dernières de la précédente — sans exception, et
donc invisible. Ce garde-fou resservira en phase 06 pour valider
`build_features()`.

## Cohérence entre source d'entraînement et source de production

Le modèle s'entraînera sur la réanalyse ERA5 mais prédira à partir de l'API
forecast. Ces deux sources ne coïncident pas exactement : la première
reconstitue le passé, la seconde provient d'un modèle opérationnel.

Un biais systématique sur la température se propagerait dans toutes les
variables de décalage et pèserait lourd face à une MAE cible de l'ordre du
degré. `skew_analysis.py` mesure donc, pour chaque variable et sur les 24
gouvernorats, le biais moyen, la MAE et la MAE rapportée à l'écart-type.

**C'est ce calcul qui décide** des variables admises comme features : celles
dont les deux sources divergent sont écartées du modèle, tout en restant
exploitées en EDA, en Power BI et en data mining.

Limite connue : l'API forecast ne remonte qu'à 92 jours, la comparaison ne
couvrira donc jamais l'hiver.

## Exécution

```bash
# Extraction complete depuis Open-Meteo (plusieurs heures, voir plus bas)
python 01_etl/extract_openmeteo.py

# Reconstruction du Parquet a partir des CSV
python 01_etl/build_parquet.py
```

Les données livrées avec le dépôt rendent ces deux étapes facultatives.

## La contrainte de quota, et comment le script la gère

Le quota Open-Meteo n'est pas un compte de requêtes mais un **volume pondéré** :

```
poids = (nb_variables / 10) x (nb_jours / 14)
```

Une requête ici — 31 variables sur 7,5 ans — pèse donc à elle seule ~610
appels. Les 24 gouvernorats totalisent ~14 600 appels pour un plafond gratuit
de 10 000 par jour : **l'extraction complète ne tient pas dans une journée.**

Trois plafonds se superposent : 600 appels par minute, 5 000 par heure, 10 000
par jour. Le script lit le motif exact renvoyé dans la réponse 429 et réagit en
conséquence :

| Motif renvoyé | Réaction |
|---|---|
| `Minutely ... limit exceeded` | attente de 65 s |
| `Hourly ... limit exceeded` | attente jusqu'à l'heure pleine suivante |
| `Daily ... limit exceeded` | arrêt propre, liste des gouvernorats restants |

Un backoff exponentiel classique ne suffit pas : il retente avant la
réouverture de la fenêtre et épuise ses essais dans le vide.

Le script **reprend là où il s'est arrêté** — tout gouvernorat dont le CSV
existe déjà est relu depuis le disque au lieu d'être retéléchargé. Relancer la
même commande le lendemain suffit à terminer.

Le **quota journalier se réinitialise à minuit UTC**, ce que la documentation
Open-Meteo ne précise pas ; le comportement a été vérifié empiriquement.

## Décisions de conception

- **Chef-lieu comme point de mesure.** Chaque gouvernorat est représenté par
  les coordonnées de son chef-lieu. Les gouvernorats étendus du sud ont une
  variabilité interne que ce point unique ne capture pas.
- **Fuseau `Africa/Tunis`** demandé à l'API, pour que les heures soient
  directement interprétables sans conversion.
- **Fin de série au 2026-07-15.** ERA5 accuse environ cinq jours de retard sur
  le temps réel.
- **Parquet plutôt que CSV** pour le versionnement : 42 Mo contre 308 Mo, et
  DuckDB le lit sans import préalable.

## Sortie

`data/tunisia_weather_hourly.parquet` — 1 585 728 lignes × 36 colonnes,
2019-01-01 → 2026-07-15, sans valeur manquante ni doublon.

# 03 — Power BI

Rapport descriptif alimenté par le schéma en étoile DuckDB, exporté vers
Power BI via les fichiers Parquet ou CSV du dossier `exports/`.

**État : à venir.**

## Pages prévues

| Page | Contenu |
|---|---|
| Vue d'ensemble | Carte des 24 gouvernorats, températures moyennes, période couverte |
| Climatologie | Profils mensuels et horaires, amplitudes thermiques, comparaison nord/sud |
| Extrêmes | Records de chaleur et de froid, vagues de chaleur, jours de gel |
| Précipitations | Cumuls, saisonnalité, contraste littoral / intérieur / sud |
| Groupes climatiques | Restitution du clustering de la phase `04_data_mining` |

## Mesures DAX

Documentées dans `mesures_dax.md` au fur et à mesure de leur création.

## Note sur les variables utilisées

Le rapport Power BI exploite **les 31 variables**, y compris celles écartées du
modèle prédictif (humidité relative, nébulosité, vents). Ce filtrage ne
concerne que la production : il vient du décalage entre la source
d'entraînement et la source de prédiction, contrainte qui n'existe pas pour une
analyse descriptive sur l'historique.

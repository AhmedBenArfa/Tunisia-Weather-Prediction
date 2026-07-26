# 07 — Rapport

Documentation technique par phase et rapport final.

**État : à venir.**

| Document | Portée |
|---|---|
| `Documentation_Technique_ETL_EDA.pdf` | Extraction, gestion du quota, qualité, exploration |
| `Documentation_Technique_StarSchema_PowerBI.pdf` | Modèle dimensionnel et restitution |
| `Documentation_Technique_DataMining.pdf` | ACP et groupes climatiques |
| `Documentation_Technique_MachineLearning.pdf` | Features, modèles, évaluation |
| `Documentation_Technique_Application_Web.pdf` | Architecture et déploiement |
| `Rapport_Final.pdf` | Synthèse complète |

## Sections qui méritent un traitement approfondi

- **Le décalage entre source d'entraînement et source de production.** Mesuré,
  chiffré, et à l'origine du filtrage des variables. C'est le résultat
  méthodologique le plus solide du projet.
- **Le choix des baselines.** Montrer comment la persistance se dégrade avec
  l'horizon pendant que la climatologie reste stable justifie l'intérêt du
  modèle bien mieux qu'un R² isolé.
- **Les limites assumées** — couverture saisonnière partielle du test de
  cohérence, représentation d'un gouvernorat par son seul chef-lieu, ERA5 qui
  est une réanalyse et non une mesure de station.

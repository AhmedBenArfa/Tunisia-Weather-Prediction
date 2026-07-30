# 08 — Rapport

Documentation technique par phase et rapport final.

| Document | Portée | État |
|---|---|---|
| `Documentation_Technique_ETL_EDA` | Extraction, quota, contrôles, nettoyage, cohérence inter-sources, exploration | **Livré — 9 pages** |
| `Documentation_Technique_StarSchema_PowerBI` | Modèle dimensionnel et restitution | À venir |
| `Documentation_Technique_DataMining` | ACP et groupes climatiques | À venir |
| `Documentation_Technique_SeriesTemporelles` | STL, stationnarité, ARIMA/SARIMA/Fourier | À venir |
| `Documentation_Technique_MachineLearning` | Features, modèles, évaluation | À venir |
| `Documentation_Technique_Application_Web` | Architecture et déploiement | À venir |
| `Rapport_Final` | Synthèse complète | À venir |

## Génération

```bash
python 08_rapport/_build_doc_pdf.py
```

**Le Markdown est la source unique.** Les PDF en sont dérivés et ne s'éditent
jamais à la main : toute correction se fait dans le `.md`, puis on régénère.

Le script réutilise le convertisseur de `00_documentation/_build_pdf.py` plutôt
que de dupliquer la logique de rendu — une seule mise en page pour tout le
projet, et une seule correction quand elle doit évoluer.

## Sections qui méritent un traitement approfondi

- **Le décalage entre source d'entraînement et source de production.** Mesuré,
  chiffré, et à l'origine du filtrage des variables. C'est le résultat
  méthodologique le plus solide du projet. Le cas de la pression de surface —
  écartée à 0,669 quand la pression au niveau de la mer tient à 0,088, pour une
  raison physique identifiable — en est la meilleure illustration.
- **Le choix des baselines.** Montrer comment la persistance se dégrade avec
  l'horizon pendant que la climatologie reste stable justifie l'intérêt du
  modèle bien mieux qu'un R² isolé.
- **Les limites assumées** — couverture saisonnière partielle du test de
  cohérence, représentation d'un gouvernorat par son seul chef-lieu, ERA5 qui
  est une réanalyse et non une mesure de station.

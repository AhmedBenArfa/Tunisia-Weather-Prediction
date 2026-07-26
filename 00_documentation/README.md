# 00 — Documentation

Cadrage du projet : ce qu'on cherche à prédire, avec quelles données, selon
quel planning et quelles conventions techniques.

| Document | Contenu | Pages |
|---|---|---|
| `1_description_projet` | Contexte, objectifs, périmètre, livrables, critères de succès | 3 |
| `2_description_donnees` | Dictionnaire des 36 colonnes, volumétrie, qualité, limites | 7 |
| `3_timeline` | Découpage en phases et jalons | 3 |
| `4_guide_technique` | Conventions de code, outils, environnement, workflow Git | 3 |

Chaque document existe en `.md` et en `.pdf`.

## Génération des PDF

**Le Markdown est la source unique.** Les PDF en sont dérivés et ne doivent
jamais être édités à la main : toute correction se fait dans le `.md`, puis on
régénère.

```bash
python 00_documentation/_build_pdf.py
```

Le rendu s'appuie sur `fpdf2` et les polices DejaVu livrées avec matplotlib —
aucune installation LaTeX n'est nécessaire. Le script localise les polices via
le chemin de données de matplotlib, donc il fonctionne sur toute machine où les
dépendances du projet sont installées.

Sont rendus : titres, gras, code inline, liens, citations, listes, tableaux et
blocs de code. Les diagrammes Mermaid apparaissent sous forme de source dans le
PDF — ils ne se rendent graphiquement que dans la version Markdown, sur GitHub.

La conception détaillée — architecture, features, modèles, évaluation — vit
dans `docs/conception/`.

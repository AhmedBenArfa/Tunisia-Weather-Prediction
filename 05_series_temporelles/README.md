# 05 — Séries temporelles

Analyse de la structure temporelle des 24 séries : décomposition, stationnarité,
autocorrélation, et une baseline statistique classique.

**État : à venir.**

## Pourquoi cette phase existe

Deux raisons, et la première est la plus importante.

**Elle justifie le choix des décalages.** Poser des lags à t−1, t−24 et t−168
parce que « ça paraît raisonnable » est une intuition. L'autocorrélation
partielle (PACF) le démontre : elle montre quels décalages portent une
information propre, une fois retiré l'effet des décalages intermédiaires. Le
feature engineering de la phase 06 s'appuie sur ce résultat au lieu de le
supposer.

**Elle fournit de vraies baselines concurrentes.** Persistance et climatologie
sont des références naïves. ARIMA et ses variantes sont de véritables méthodes
de prévision : les battre a nettement plus de valeur, et elles entrent au même
titre que les modèles ML dans le tableau comparatif final de la phase 06.

## Démarche

### 1. Décomposition STL

Séparation tendance / saisonnalité / résidu, par gouvernorat. Deux
saisonnalités coexistent ici — le cycle diurne (24 h) et le cycle annuel
(8 766 h) — ce qui demande une décomposition en deux passes ou une variante
multi-saisonnière.

### 2. Stationnarité

Tests ADF et KPSS. Les deux sont complémentaires : ADF teste l'hypothèse nulle
de non-stationnarité, KPSS l'hypothèse inverse. Les faire converger évite les
conclusions hâtives.

Une série de température n'est pas stationnaire au sens strict — elle porte une
saisonnalité annuelle forte. La question utile est de savoir ce qui reste après
désaisonnalisation.

### 3. Autocorrélation

ACF et PACF sur la série brute et sur les résidus de la décomposition. C'est ce
qui alimente directement le choix des décalages en phase 06.

### 4. Trois modèles, en progression

L'intérêt n'est pas d'obtenir le meilleur modèle statistique possible, mais de
montrer **pourquoi** chaque niveau de complexité est nécessaire.

| Modèle | Ce qu'il capture | Ce qu'il rate |
|---|---|---|
| `ARIMA(p,d,q)` | Structure autorégressive courte | Toute saisonnalité |
| `SARIMA(p,d,q)(P,D,Q)₂₄` | Cycle diurne | Cycle annuel |
| Fourier + ARIMA | Cycle diurne **et** annuel | — |

ARIMA est volontairement inclus alors qu'il va échouer : son échec démontre que
la saisonnalité porte l'essentiel du signal. C'est la même logique que la
progression sans rééquilibrage → `class_weight` → SMOTE des projets de
classification précédents.

**Pourquoi Fourier et non SARIMA à période annuelle.** La température horaire a
deux saisonnalités : 24 h et 8 766 h. SARIMA n'en gère qu'une. Une période
saisonnière de 8 766 est numériquement infaisable — l'espace d'états atteindrait
des dimensions que statsmodels ne peut pas traiter. La solution standard est la
régression harmonique : des termes de Fourier (sinus/cosinus des harmoniques
annuelles) entrent comme régresseurs exogènes, et ARIMA ne modélise plus que la
structure résiduelle.

Les trois sont ajustés sur un sous-ensemble de gouvernorats représentatifs :
l'ajustement sur 66 000 points horaires est coûteux, et l'objectif est un point
de comparaison, pas un modèle de production.

## Ce que cette phase produit

| Sortie | Consommée par |
|---|---|
| Décalages justifiés par la PACF | `06_machine_learning/features.py` |
| MAE des trois modèles aux trois horizons | Tableau comparatif de la phase 06 |
| Graphiques de décomposition | Rapport et présentation |

## Note sur la structure des données

Les 24 gouvernorats forment **24 séries parallèles**, pas une seule série. Elles
partagent le même calendrier mais ont chacune leur dynamique.

Toute opération temporelle — décalage, fenêtre glissante, différenciation —
doit donc être effectuée **par gouvernorat** :

```python
# CORRECT
df.groupby("gouvernorat")["temperature_2m"].shift(24)

# FAUX : les premieres lignes d'un gouvernorat recuperent
# les dernieres heures du precedent
df["temperature_2m"].shift(24)
```

L'erreur est silencieuse — aucune exception, seulement des valeurs contaminées
aux frontières entre gouvernorats. Sur 24 séries et 168 heures de profondeur,
cela représente environ 4 000 lignes fausses qui passent inaperçues.

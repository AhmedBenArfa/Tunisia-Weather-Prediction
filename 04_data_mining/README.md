# 04 — Data mining

Analyse non supervisée : réduction de dimension et regroupement des 24
gouvernorats par profil climatique.

**État : à venir.**

## Pourquoi cette phase précède le machine learning

Le regroupement produit une variable — `cluster_climatique` — qui alimente
`dim_gouvernorat` puis les modèles de la phase 05. Placer le data mining après
le ML en aurait fait une analyse décorative, sans effet sur le reste de la
chaîne.

## Démarche

1. **Agrégation** — un profil par gouvernorat : moyennes mensuelles de
   température, amplitude thermique, cumul de précipitations, humidité,
   ensoleillement, vent.
2. **ACP** — réduction de dimension et visualisation en deux composantes.
3. **K-means** — nombre de groupes choisi par méthode du coude et score de
   silhouette.
4. **Validation géographique** — les groupes obtenus doivent correspondre à des
   réalités connues : littoral nord, intérieur, sud saharien. Un regroupement
   qui contredirait la géographie signalerait une erreur de préparation.

## Sortie

Colonne `cluster_climatique` ajoutée à `dim_gouvernorat`, réutilisée comme
variable statique par les modèles de prévision.

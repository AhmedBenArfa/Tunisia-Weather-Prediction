# 09 — Présentation

Slides de soutenance, au format HTML comme dans les projets précédents.

**État : à venir.**

## Trame envisagée

| Bloc | Contenu |
|---|---|
| Problème | Pourquoi une régression sur série temporelle ne se traite pas comme une classification |
| Données | Open-Meteo, 24 gouvernorats, 1,58 M lignes, et la contrainte de quota |
| Architecture | Le partage local / en ligne, et pourquoi le fait horaire reste local |
| Le piège évité | La fuite temporelle, et le R² à 0,99 qui aurait dû alerter |
| Le décalage train/prod | Mesuré et chiffré, à l'origine du filtrage des variables |
| Résultats | Gain sur les deux baselines, par horizon |
| Démonstration | L'application en direct |
| Limites | Ce que le modèle ne fait pas, et pourquoi |

Le fil conducteur est méthodologique : sur ce sujet, les erreurs qui gonflent
artificiellement les scores sont faciles à commettre et difficiles à repérer.
Montrer comment elles ont été évitées vaut mieux qu'annoncer une métrique
flatteuse.

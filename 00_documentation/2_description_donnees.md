# 2 — Description des données

> **Auteur** : Ahmed Ben Arfa
> **Projet** : Tunisia Weather Prediction
> **Date** : juillet 2026

Toutes les statistiques de ce document sont calculées sur le jeu réel
(`data/tunisia_weather_hourly.parquet`), pas reprises d'une documentation
externe.

## 1. Provenance

Les données n'ont pas été fournies : elles ont été **extraites par l'équipe
projet** depuis [Open-Meteo](https://open-meteo.com), via l'API d'archive
`archive-api.open-meteo.com/v1/archive`.

Cette API restitue la **réanalyse ERA5** du ECMWF, produite dans le cadre du
programme européen Copernicus. Une réanalyse n'est pas un relevé de station :
c'est la sortie d'un modèle atmosphérique qui assimile les observations
disponibles pour reconstituer un état cohérent de l'atmosphère sur une grille
régulière. Les valeurs sont donc physiquement cohérentes entre elles, mais ne
correspondent pas exactement à ce qu'aurait mesuré un thermomètre à un endroit
précis.

Licence : [CC BY 4.0](https://open-meteo.com/en/license) — usage libre avec
attribution.

## 2. Volumétrie

| Caractéristique | Valeur |
|---|---|
| Lignes | 1 585 728 |
| Colonnes | 36 |
| Gouvernorats | 24 |
| Pas de temps | Horaire |
| Période | 2019-01-01 00:00 → 2026-07-15 23:00 |
| Heures par gouvernorat | 66 072 (2 753 jours) |
| Fuseau | `Africa/Tunis` |
| Valeurs manquantes | 0 |
| Doublons (gouvernorat, heure) | 0 |

La série est **parfaitement continue** : sur les 66 071 intervalles d'un
gouvernorat, tous valent exactement une heure. Aucun trou, aucune heure
dupliquée. La Tunisie n'appliquant pas l'heure d'été, il n'y a pas non plus
d'artefact de changement d'heure.

## 3. Couverture géographique

Chaque gouvernorat est représenté par les coordonnées de son chef-lieu. Les
latitudes et longitudes du jeu final sont celles du **point de grille ERA5 le
plus proche**, pas celles demandées.

| Gouvernorat | Latitude | Longitude | Altitude (m) |
|---|---|---|---|
| Bizerte | 37,293 | 9,788 | 5 |
| Ariana | 36,872 | 10,184 | 9 |
| Tunis | 36,801 | 10,171 | 11 |
| Manouba | 36,801 | 10,053 | 28 |
| Beja | 36,731 | 9,213 | 247 |
| Ben Arous | 36,731 | 10,276 | 8 |
| Jendouba | 36,520 | 8,824 | 145 |
| Zaghouan | 36,450 | 10,104 | 172 |
| Nabeul | 36,450 | 10,692 | 11 |
| Kef | 36,169 | 8,766 | 637 |
| Siliana | 36,098 | 9,339 | 431 |
| Sousse | 35,817 | 10,568 | 32 |
| Monastir | 35,747 | 10,786 | 29 |
| Kairouan | 35,677 | 10,077 | 64 |
| Mahdia | 35,536 | 10,976 | 6 |
| Kasserine | 35,185 | 8,839 | 674 |
| Sidi Bouzid | 35,044 | 9,504 | 333 |
| Sfax | 34,763 | 10,709 | 11 |
| Gafsa | 34,411 | 8,830 | 299 |
| Tozeur | 33,919 | 8,080 | 50 |
| Gabes | 33,849 | 10,087 | 10 |
| Kebili | 33,708 | 8,944 | 43 |
| Medenine | 33,357 | 10,556 | 92 |
| Tataouine | 32,935 | 10,478 | 238 |

L'altitude va de 5 m (Bizerte) à 674 m (Kasserine), amplitude suffisante pour
peser sur les températures.

## 4. Dictionnaire des variables

36 colonnes : 31 mesures météorologiques, plus `gouvernorat`, `time`,
`latitude`, `longitude`, `elevation`.

Statistiques calculées sur l'ensemble des 1 585 728 lignes.

### Température et humidité de l'air

| Variable | Unité | Min | Moy | Max |
|---|---|---|---|---|
| `temperature_2m` | °C | −3,60 | 19,88 | 50,20 |
| `apparent_temperature` | °C | −7,80 | 18,77 | 47,60 |
| `dew_point_2m` | °C | −17,90 | 10,59 | 27,10 |
| `relative_humidity_2m` | % | 4,00 | 60,89 | 100,00 |
| `vapour_pressure_deficit` | kPa | 0,00 | 1,22 | 11,89 |

`temperature_2m` est la **cible** du projet.

### Précipitations

| Variable | Unité | Min | Moy | Max |
|---|---|---|---|---|
| `precipitation` | mm | 0,00 | 0,04 | 21,00 |
| `rain` | mm | 0,00 | 0,04 | 21,00 |
| `snowfall` | cm | 0,00 | 0,0002 | 1,96 |

### Pression

| Variable | Unité | Min | Moy | Max |
|---|---|---|---|---|
| `pressure_msl` | hPa | 983,30 | 1016,86 | 1038,80 |
| `surface_pressure` | hPa | 914,70 | 999,55 | 1036,90 |

### Nébulosité

| Variable | Unité | Min | Moy | Max |
|---|---|---|---|---|
| `cloud_cover` | % | 0 | 33,88 | 100 |
| `cloud_cover_low` | % | 0 | 8,61 | 100 |
| `cloud_cover_mid` | % | 0 | 12,77 | 100 |
| `cloud_cover_high` | % | 0 | 23,03 | 100 |

### Vent

| Variable | Unité | Min | Moy | Max |
|---|---|---|---|---|
| `wind_speed_10m` | km/h | 0,00 | 12,21 | 74,00 |
| `wind_speed_100m` | km/h | 0,00 | 19,43 | 108,30 |
| `wind_gusts_10m` | km/h | 0,70 | 25,74 | 130,70 |
| `wind_direction_10m` | ° | 0 | 191,57 | 360 |
| `wind_direction_100m` | ° | 0 | 192,22 | 360 |

Les directions sont **circulaires** : 0° et 360° désignent le même nord. Une
moyenne arithmétique n'a donc aucun sens sur ces colonnes, et un modèle qui les
traiterait comme des nombres ordinaires apprendrait une discontinuité fictive
entre 359° et 1°. Un encodage sinus/cosinus est nécessaire si elles sont
utilisées.

### Sol

| Variable | Unité | Min | Moy | Max |
|---|---|---|---|---|
| `soil_temperature_0_to_7cm` | °C | −2,30 | 21,39 | 57,50 |
| `soil_temperature_7_to_28cm` | °C | 4,30 | 21,28 | 40,50 |
| `soil_temperature_28_to_100cm` | °C | 8,80 | 21,16 | 33,90 |
| `soil_moisture_0_to_7cm` | m³/m³ | −0,013 | 0,16 | 0,54 |
| `soil_moisture_7_to_28cm` | m³/m³ | −0,012 | 0,17 | 0,52 |
| `soil_moisture_28_to_100cm` | m³/m³ | −0,011 | 0,15 | 0,51 |

L'amplitude des températures de sol décroît nettement avec la profondeur
(59,8 °C en surface contre 25,1 °C entre 28 et 100 cm) : le sol profond filtre
les variations rapides et porte l'inertie thermique saisonnière. C'est un
signal potentiellement utile pour la prévision.

### Rayonnement

| Variable | Unité | Min | Moy | Max |
|---|---|---|---|---|
| `shortwave_radiation` | W/m² | 0 | 212,32 | 1012,00 |
| `direct_radiation` | W/m² | 0 | 145,01 | 829,00 |
| `diffuse_radiation` | W/m² | 0 | 67,31 | 502,00 |
| `direct_normal_irradiance` | W/m² | 0 | 237,55 | 936,40 |
| `terrestrial_radiation` | W/m² | 0 | 349,43 | 1302,90 |
| `et0_fao_evapotranspiration` | mm | 0,00 | 0,18 | 1,31 |

### Identification et géographie

| Variable | Type | Description |
|---|---|---|
| `gouvernorat` | catégorie | Nom du gouvernorat (24 modalités) |
| `time` | datetime | Horodatage horaire, fuseau `Africa/Tunis` |
| `latitude` | float | Latitude du point de grille |
| `longitude` | float | Longitude du point de grille |
| `elevation` | float | Altitude du point de grille (m) |

## 5. Contrastes climatiques observés

### Température moyenne par gouvernorat

Du plus frais au plus chaud, avec les extrêmes atteints :

| Gouvernorat | Min | Moy | Max |
|---|---|---|---|
| Kef | −3,4 | 17,0 | 44,0 |
| Kasserine | −3,6 | 17,7 | 44,4 |
| Beja | −1,6 | 18,3 | 46,8 |
| Siliana | −1,6 | 18,5 | 45,2 |
| Zaghouan | 0,4 | 19,0 | 47,1 |
| Nabeul | 3,1 | 19,2 | 42,7 |
| Ariana | 1,2 | 19,3 | 48,3 |
| Bizerte | 4,9 | 19,4 | 46,9 |
| Tunis | 0,7 | 19,4 | 48,5 |
| Manouba | 0,3 | 19,5 | 48,7 |
| Ben Arous | 1,2 | 19,5 | 48,0 |
| Jendouba | −0,5 | 19,6 | 48,2 |
| Sidi Bouzid | −3,0 | 19,7 | 47,5 |
| Mahdia | 2,7 | 20,0 | 48,3 |
| Sousse | 0,9 | 20,1 | 48,6 |
| Monastir | 2,4 | 20,2 | 49,8 |
| Sfax | 2,2 | 20,4 | 46,2 |
| Gafsa | −1,8 | 20,6 | 46,3 |
| Kairouan | −1,0 | 20,9 | 50,2 |
| Tataouine | 2,3 | 21,0 | 47,1 |
| Gabes | 1,8 | 21,2 | 47,5 |
| Medenine | 1,5 | 21,6 | 48,4 |
| Kebili | −0,8 | 22,2 | 48,9 |
| Tozeur | −0,3 | 22,8 | 49,1 |

Le classement n'est pas purement latitudinal : Kef et Kasserine, les plus
frais, sont aussi les plus élevés (637 m et 674 m). L'altitude compte autant
que la position nord-sud.

Bizerte présente le minimum le plus doux (4,9 °C) malgré sa position la plus au
nord — effet modérateur de la mer. À l'inverse, Sidi Bouzid et Kasserine
descendent sous −3 °C : continentalité et altitude produisent des nuits
froides que le littoral ne connaît pas.

### Précipitations annuelles moyennes (2019-2025)

| Gouvernorat | mm/an | | Gouvernorat | mm/an |
|---|---|---|---|---|
| Bizerte | 525 | | Kairouan | 268 |
| Ben Arous | 434 | | Sidi Bouzid | 217 |
| Beja | 432 | | Sfax | 212 |
| Jendouba | 415 | | Gabes | 158 |
| Kef | 410 | | Medenine | 136 |
| Tunis | 402 | | Gafsa | 135 |
| Siliana | 402 | | Tataouine | 124 |
| Ariana | 399 | | Kebili | 89 |
| Zaghouan | 390 | | Tozeur | 83 |
| Manouba | 385 | | | |
| Nabeul, Mahdia, Monastir, Sousse, Kasserine | 272-350 | | | |

Le gradient nord-sud est le fait structurant du jeu : **un rapport de 1 à 6**
entre Bizerte et Tozeur. C'est ce contraste que le clustering de la phase
`04_data_mining` doit faire ressortir.

## 6. Qualité des données

Le jeu ne présente **aucune valeur manquante ni doublon**, et sa continuité
horaire est parfaite. Trois points méritent néanmoins d'être signalés.

### 6.1 Humidité du sol négative

`soil_moisture_*` descend à **−0,013 m³/m³**, ce qui est physiquement
impossible : une teneur en eau volumique ne peut pas être négative.

| Couche | Lignes concernées | Part |
|---|---|---|
| `soil_moisture_0_to_7cm` | 493 | 0,031 % |
| `soil_moisture_7_to_28cm` | 460 | 0,029 % |
| `soil_moisture_28_to_100cm` | 428 | 0,027 % |

Les cas se concentrent sur les gouvernorats arides — Tozeur, Kebili, Gabes,
Medenine, Tataouine, Gafsa, Sidi Bouzid, Sfax. Il s'agit d'un artefact
numérique de la réanalyse sur sols très secs, où la valeur oscille autour de
zéro. L'ampleur est négligeable (0,03 %) et la correction évidente : tronquer à
zéro lors du nettoyage.

### 6.2 `rain` quasi redondante avec `precipitation`

Les deux colonnes ne diffèrent que sur **144 lignes** — exactement celles où
`snowfall > 0`. Leur corrélation atteint 0,99976.

Conserver les deux dans un modèle introduirait une colinéarité quasi parfaite
sans apport d'information. `precipitation` suffit ; `rain` et `snowfall` ne
gardent un intérêt que pour distinguer les épisodes neigeux, rarissimes et
cantonnés aux gouvernorats élevés du nord-ouest.

### 6.3 Points de grille partagés

Trois paires de gouvernorats partagent la même latitude de grille :
Tunis/Manouba, Beja/Ben Arous, Zaghouan/Nabeul. Leurs longitudes diffèrent, les
points restent donc distincts — mais cela rappelle que la résolution ERA5
(~9 km après post-traitement) ne sépare pas finement des chefs-lieux voisins.

Pour le Grand Tunis en particulier — Tunis, Ariana, Ben Arous, Manouba — les
quatre points sont si proches que leurs séries sont fortement corrélées. C'est
à garder en tête lors de l'interprétation du clustering : un regroupement de
ces quatre gouvernorats refléterait la géographie autant que le climat.

## 7. Format de stockage

| Forme | Taille | Versionné |
|---|---|---|
| 24 CSV bruts (`raw_*.csv`) | ~308 Mo | Non |
| CSV combiné | 308 Mo | Non — au-delà de la limite GitHub de 100 Mo |
| **Parquet zstd** | **42,1 Mo** | **Oui** |

Le Parquet divise le volume par 7,3 et se lit nativement par DuckDB, sans
import préalable. Les données étant publiques, rien n'impose de les exclure du
dépôt — contrairement aux projets précédents où la confidentialité l'interdisait.

## 8. Source de production

L'application déployée ne peut pas utiliser l'archive ERA5, qui accuse environ
cinq jours de retard. Elle interroge l'API forecast
`api.open-meteo.com/v1/forecast`, qui fournit les 168 dernières heures
observées.

Les 31 variables y sont disponibles avec les mêmes unités. Mais les deux
sources **ne coïncident pas exactement** — l'écart mesuré et ses conséquences
sur le choix des variables sont documentés dans
`docs/conception/2026-07-26-conception-projet.md`, section 7.3.

## 9. Limites du jeu de données

- **Un point par gouvernorat.** Les gouvernorats étendus du sud ont une
  variabilité interne que ce point unique ne capture pas.
- **Réanalyse, pas mesure.** Les valeurs proviennent d'un modèle, non de
  stations. Les extrêmes en particulier peuvent être lissés.
- **7,5 ans d'historique.** Suffisant pour la variabilité saisonnière et
  interannuelle courante, insuffisant pour caractériser des événements rares ou
  une tendance climatique.
- **Chef-lieu comme proxy du gouvernorat.** Choix pratique qui ignore la
  diversité intra-gouvernorat, notamment entre littoral et intérieur.

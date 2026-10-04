# Mireille Tuto

Application Python (fenêtres Qt) pour explorer des concepts d'algèbre et d'apprentissage
automatique à partir d'exemples visuels. Le premier module est une carte du monde interactive.

## Installation (Windows)

L'environnement est géré par [uv](https://docs.astral.sh/uv/), qui installe aussi Python.

```powershell
powershell -ExecutionPolicy ByPass -c "irm https://astral.sh/uv/install.ps1 | iex"
uv sync
```

## Lancer l'application

```powershell
uv run mireille-tuto            # frontières détaillées (1:50m)
uv run mireille-tuto --simple   # frontières simplifiées (1:110m)
uv run mireille-tuto --pays FRA # pays centré au démarrage et cible de l'échantillon (défaut : JPN)
```

## Utilisation de la carte

| Action | Effet |
| --- | --- |
| Clic (mode « Sélectionner ») | Met en évidence les frontières du pays et affiche ses infos |
| Double-clic | Centre la vue sur le pays sélectionné |
| Clic (mode « Ajouter des points ») | Ajoute un point avec le nom du pays et ses coordonnées |
| Molette | Zoom autour du curseur |
| « Échantillonner la vue » (`E`) | Tire N points au hasard dans la vue et les marque d'un ✕ coloré : eau, pays cible, autre pays |
| `S` / `P` | Passer en mode sélection / ajout de points |
| `Échap` / `Origine` | Désélectionner / revenir à la vue du monde |

La barre matplotlib au-dessus de la carte permet aussi de se déplacer (main), de zoomer sur
un rectangle, de revenir en arrière et d'enregistrer une image.

## Tests

```powershell
uv run pytest
```

## Structure

```
src/mireille_tuto/
  app.py              point d'entrée (QApplication)
  data/               frontières des pays (Natural Earth, domaine public)
  geo/                chargement des pays, recherche spatiale, coordonnées
  ui/                 fenêtre principale et widget de carte
scripts/
  update_maps.py      mise à jour des données cartographiques
tests/
```

## Données cartographiques

### Source

Les frontières viennent de [Natural Earth](https://www.naturalearthdata.com/), jeu
« Admin 0 – Countries », dans le domaine public. Les fichiers GeoJSON proviennent du dépôt
officiel [nvkelso/natural-earth-vector](https://github.com/nvkelso/natural-earth-vector)
(dossier `geojson/`) et sont copiés dans `src/mireille_tuto/data/` :

| Fichier | Échelle | Utilisé par |
| --- | --- | --- |
| `ne_50m_admin_0_countries.geojson` | 1:50 millions (~3 Mo) | `uv run mireille-tuto` |
| `ne_110m_admin_0_countries.geojson` | 1:110 millions (~0,8 Mo) | `uv run mireille-tuto --simple`, tests |

La version exacte installée (référence, commit, version Natural Earth, date) est notée dans
`src/mireille_tuto/data/SOURCE.json`. L'application ne télécharge rien à l'exécution.

### Mise à jour

```powershell
uv run python scripts/update_maps.py               # dernière version (branche master)
uv run python scripts/update_maps.py --ref v5.1.2  # version figée (tag du dépôt)
uv run pytest
```

Le script télécharge les deux fichiers, les valide (propriétés requises présentes, nombre de
pays plausible, Montréal au Canada, Paris en France, Tokyo au Japon), puis seulement remplace
les fichiers du projet et met à jour `SOURCE.json`. En cas d'échec, les données existantes ne
sont pas touchées.

### Propriétés utilisées

Le code (`geo/countries.py`) dépend de ces propriétés de chaque pays :

| Propriété | Usage |
| --- | --- |
| `ADM0_A3` | code unique du pays (plus fiable que `ISO_A3`, qui vaut `-99` pour la France ou la Norvège) |
| `NAME_FR`, `NAME` | nom affiché en français, nom anglais en repli |
| `CONTINENT` | continent |
| `POP_EST` | population estimée |
| `MAPCOLOR7` | indice 1–7 garantissant que deux pays voisins ont des couleurs différentes |

### Frontières contestées

Natural Earth représente les frontières de fait (*de facto*) : par exemple le Sahara
occidental y est un territoire distinct. Le dépôt propose aussi, à l'échelle 1:10m seulement,
des variantes selon le point de vue d'un pays (`ne_10m_admin_0_countries_fra.geojson` pour la
France, `_usa`, `_chn`, etc.).

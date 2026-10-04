# Mireille Tuto

Application interactive (PySide6 / Qt + Matplotlib) pour explorer et enseigner l'algèbre
et l'apprentissage automatique (Machine Learning) à partir d'exemples visuels et ludiques.
Le premier module est une carte du monde interactive centrée sur le Japon.

---

## Téléchargement direct (Pour tous : Zéro installation)

Pour les utilisateurs qui ne sont pas développeurs (élèves, parents, enseignants),
l'application est disponible en téléchargement direct sans avoir besoin d'installer Python :

👉 Rendez-vous sur la page des **[Releases GitHub](../../releases)** et téléchargez la version correspondant à votre système :
- **Windows** : `Mireille-Tuto-Windows-Installateur.exe`, puis suivez l'assistant (aucun droit
  administrateur requis). Windows SmartScreen peut afficher « Windows a protégé votre ordinateur » :
  cliquez sur « Informations complémentaires » puis « Exécuter quand même ».
  Sans installation : `Mireille-Tuto-Windows-Portable.zip`, à extraire, puis `Mireille-Tuto.exe`.
- **macOS** (Mac Apple Silicon, M1 et plus récents) : `Mireille-Tuto-macOS.dmg`, puis glissez
  l'application dans *Applications*. L'application n'étant pas signée par Apple, le premier
  lancement est bloqué : ouvrez *Réglages Système > Confidentialité et sécurité* et cliquez sur
  « Ouvrir quand même ».
- **ChromeOS** : activez l'environnement Linux (*Paramètres > À propos de ChromeOS > Développeurs*),
  téléchargez `Mireille-Tuto-Linux.deb`, puis double-cliquez dessus dans l'application *Fichiers*
  et choisissez « Installer ». Mireille Tuto apparaît ensuite dans le lanceur (dossier *Applications Linux*).
  Chromebooks à processeur Intel ou AMD seulement.
- **Linux** : `sudo apt install ./Mireille-Tuto-Linux.deb` (Debian, Ubuntu), ou
  `Mireille-Tuto-Linux.tar.gz` à extraire, puis `Mireille-Tuto/Mireille-Tuto`.

### Publier une nouvelle version

Créez une release sur GitHub (*Releases > Draft a new release*) avec un **nouveau** tag, par
exemple `v1.0.1`, puis publiez-la. Le workflow `.github/workflows/release.yml` compile alors
l'application sur Windows, macOS et Linux et joint les fichiers ci-dessus à la release
(environ 15 minutes, suivi dans l'onglet *Actions*). « Run workflow » dans l'onglet *Actions*
fait une compilation de test sans release.

Pour compiler localement : `uv run --with pyinstaller --with pillow pyinstaller --clean --noconfirm mireille_tuto.spec`
(résultat dans `dist/`).

---

## Utilisation développeur (avec `uv`)

Le support pour exécuter directement le code source avec `uv` reste parfaitement fonctionnel :

### Installation

L'environnement est géré par [uv](https://docs.astral.sh/uv/), qui installe et gère automatiquement Python.

```powershell
powershell -ExecutionPolicy ByPass -c "irm https://astral.sh/uv/install.ps1 | iex"
uv sync
```

### Lancer l'application

```powershell
uv run mireille-tuto            # frontières détaillées (1:50m)
uv run mireille-tuto --simple   # frontières simplifiées (1:110m)
uv run mireille-tuto --pays FRA # présélectionne un pays au démarrage
```

## Utilisation

L'application démarre sur la carte du monde et se déroule en deux étapes :

1. **Choisir un pays** : clique sur un pays pour le mettre en évidence, puis sur « Passer au mode Algèbre ».
2. **Mode Algèbre** : la vue se centre sur le pays, qui devient la cible de l'échantillon, des
   inéquations et de l'apprentissage ML. Un clic sur la carte y ajoute un point manuel.
   « Changer de pays » ramène à l'étape 1 : l'échantillon et le modèle sont effacés,
   les points manuels sont conservés.

| Action | Effet |
| --- | --- |
| Clic (étape 1) | Met en évidence les frontières du pays et affiche ses infos |
| Clic (mode Algèbre) | Ajoute un point avec le nom du pays et ses coordonnées |
| Double-clic | Centre la vue sur le pays sélectionné |
| Molette | Zoom autour du curseur |
| « Échantillonner » (`E`, mode Algèbre) | Tire N points additionnels au hasard dans la vue (s'accumulent à l'échantillon existant) et les marque d'un ✕ coloré : eau, pays cible, autre pays |
| `Échap` / `Origine` | Désélectionner (étape 1) / revenir à la vue du monde |

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
  geo/                chargement des pays, recherche spatiale, coordonnées, échantillonnage
  ml/                 inéquations, formules, registre de transformations, entraîneur moindres carrés
  ui/                 fenêtre principale, widget de carte et atelier Algèbre & ML
scripts/
  update_maps.py      mise à jour des données cartographiques
tests/
```

## Atelier Algèbre & Apprentissage Machine

L'application comprend un atelier latéral en trois onglets :

### 1. Carte & Points
- Affiche les détails du pays sélectionné (population, centre, nombre de sommets).
- Liste des points manuels ajoutés et résumé de l'échantillon visible.

### 2. Inéquations (Mode manuel)
Mireille peut taper une inéquation ou équation directement dans la zone de texte pour tracer
une frontière de décision sur la carte. Trois repères de coordonnées sont proposés :
- **Fenêtre `[-1, 1]`** : repère relatif à l'écran visible ($[-1, 1]$ en x et y).
- **Latitude & Longitude** : degrés réels sur la Terre (`lat` et `lon`, avec alias `x=lon, y=lat`).
- **Centré sur le pays** : degrés relatifs au centre du pays ($x = \text{lon} - \text{lon}_0, \; y = \text{lat} - \text{lat}_0$).

La syntaxe est naturelle et simplifiée pour Mireille (aucun besoin de manipuler numpy !) :
- **Variables** : `x, y` ou `lat, lon`
- **Opérateurs arithmétiques** : `+`, `-`, `*`, `/`, `**` (ou `^`)
- **Inéquations & Comparaisons** : `<`, `>`, `<=`, `>=`, `==`, `and`, `or`, `not`
- **Fonctions prêtes à l'emploi** :
  - `relu(u)` : le neurone du Deep Learning ($\max(0, u)$)
  - `between(u, min, max)` / `bucket(...)` : tranche / bucket ($1.0$ si dans l'intervalle, $0.0$ sinon)
  - `dist(x, y, x0, y0)` : distance euclidienne directe $\sqrt{(x-x_0)^2 + (y-y_0)^2}$
  - `sqrt(u)` : racine carrée sécurisée contre les négatifs
  - `abs(u)`, `step(u)`, `clamp(u, min, max)`, `sigmoid(u)`

La zone solution est surlignée en vert translucide et les métriques sont calculées en direct
sur l'ensemble des points visibles (points manuels et échantillon aléatoire).

### 3. Apprentissage Machine Learning (Moindres carrés)
L'ordinateur apprend lui-même les coefficients de la frontière avec une fonction de perte
des moindres carrés (MSE) et une descente de gradient animée à chaque epoch :
- **Données d'entraînement : Union des points manuels et des échantillons aléatoires** :
  Mireille peut placer des points à la main (clic sur la carte), tirer un échantillon
  aléatoire (`E`), ou combiner les deux ! Le modèle apprend sur l'union de tous ces points.
- Menu déroulant des **transformations nommées** (`transforms.py`) :
  1. Droite simple `[1, x, y]`
  2. Droite + Diagonale `[1, x, y, x*y]`
  3. Ellipse droite `[1, x, y, x², y²]`
  4. Polynôme degré 2 complet `[1, x, y, x*y, x², y²]`
  5. Inéquations & Demi-plans `[1, x>0, y>0, y>x, y<x+4, x²+y²<30]`
  6. Distance à Tokyo `[1, d, d²]`
  7. Réseau de neurones ReLU `[relu(x), relu(-x), relu(y)...]`
  8. Buckets & Tranches `[between(x, a, b)]`
  9. Mon laboratoire (Mireille) : espace où Mireille écrit ses propres caractéristiques avec `"1": 1`, inéquations, `relu()`, `between()`, `dist()`.
- **Sélecteur du nombre de neurones cachés (0 à 32)** :
  - **`0` (Modèle direct)** : régression linéaire classique directe sur les caractéristiques choisies (strictement identique au fonctionnement d'origine).
  - **`1+` neurones** : réseau de neurones avec couche cachée ReLU ! Chaque neurone $N_k$ apprend automatiquement une combinaison pondérée des caractéristiques transformées ($\text{relu}(\sum w_j \phi_j + b)$).
  - Compatible à la fois avec la **rétropropagation par descente de gradient** (mise à jour animée des neurones à chaque epoch) et avec la **solution algébrique directe** (Random Features / ELM).
- **Contrôles d'apprentissage flexibles (Pause, Reprise, Réglages à la volée)** :
  - **Démarrer / Pause / Reprendre** : cliquer sur Pause suspend l'entraînement sans jamais perdre les poids ni l'équation apprise. Cliquer sur Reprendre repart exactement du point d'arrêt.
  - **Taux d'apprentissage ($\eta$) à la volée** : modifiable en direct ou en pause sans réinitialiser le modèle.
  - **Époques / mise à jour** : permet de choisir combien d'époques de gradient sont calculées à chaque rafraîchissement visuel (ex. 1 pour observer chaque pas fin, ou 10/25/50 pour avancer rapidement).
  - **Époques max (Arrêt)** : seuil d'arrêt automatique (ex. 50 ou 100 époques) pour observer les résultats à un palier donné (0 = illimité).
  - **Cadence (images/s)** : règle la fréquence des rafraîchissements visuels de la carte.
  - **Étape +1 / Étape +10 / Étape +50** : pour avancer manuellement d'un nombre précis d'époques.
  - **Solution directe $\to$ Gradient** : calculer la solution algébrique directe puis continuer l'ajustement par descente de gradient avec le bouton « Continuer (Gradient) ».
- Affichage en temps réel de l'équation apprise (avec le détail de chaque neurone $N_1, N_2, \dots$ lorsqu'ils sont activés) et du nombre de points utilisés (manuels + échantillonnés).

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

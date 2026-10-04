"""Registre des transformations de caractéristiques pour l'apprentissage ML.

Chaque transformation prend (x, y) et retourne un dictionnaire associant
le nom de chaque terme mathématique à sa valeur.

Pour Mireille : Syntaxe simplifiée (pas besoin de manipuler numpy !)
--------------------------------------------------------------------
1. Biais constant : écris simplement `"1": 1` (plus besoin de np.ones_like !)
2. Inéquations : écris directement `"x > 0": x > 0` (converti automatiquement en 0.0 et 1.0)
3. ReLU (neurone) : `relu(x)` ou `relu(y - 2)` (la base du Deep Learning : max(0, u))
4. Buckets / tranches : `between(x, -2, 2)` (vaut 1.0 dans l'intervalle, 0.0 sinon)
5. Fonctions directes : `sqrt(u)`, `dist(x, y, x0, y0)`, `step(u)`, `clamp(u, a, b)`
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable

import numpy as np


# ============================================================================
# Fonctions mathématiques simplifiées pour Mireille
# ============================================================================


def relu(u: np.ndarray | float) -> np.ndarray | float:
    """Neurone ReLU (Rectified Linear Unit) : max(0, u).

    C'est la brique fondamentale des réseaux de neurones profonds !
    Il vaut 0 quand u <= 0, puis monte en ligne droite quand u > 0.
    """
    return np.maximum(0.0, u)


def step(u: np.ndarray | float | bool) -> np.ndarray | float:
    """Fonction seuil / marche (Heaviside) : 1.0 si u >= 0 ou vrai, sinon 0.0."""
    arr = np.asarray(u)
    if np.issubdtype(arr.dtype, np.bool_):
        return arr.astype(float)
    return np.where(arr >= 0.0, 1.0, 0.0)


def between(u: np.ndarray | float, a: float, b: float) -> np.ndarray | float:
    """Bucket / tranche : 1.0 si a <= u <= b, sinon 0.0."""
    arr = np.asarray(u)
    return np.where((arr >= a) & (arr <= b), 1.0, 0.0)


def bucket(u: np.ndarray | float, a: float, b: float) -> np.ndarray | float:
    """Alias de between(u, a, b) pour créer des tranches ou paniers de valeurs."""
    return between(u, a, b)


def sqrt(u: np.ndarray | float) -> np.ndarray | float:
    """Racine carrée sécurisée : sqrt(max(0, u)). Évite les erreurs sur les négatifs."""
    return np.sqrt(np.maximum(0.0, u))


def dist(
    x: np.ndarray | float,
    y: np.ndarray | float,
    x0: float = 0.0,
    y0: float = 0.0,
) -> np.ndarray | float:
    """Distance euclidienne jusqu'au point (x0, y0) : sqrt((x - x0)² + (y - y0)²)."""
    return np.sqrt((x - x0) ** 2 + (y - y0) ** 2)


def clamp(u: np.ndarray | float, low: float, high: float) -> np.ndarray | float:
    """Borne u entre low et high."""
    return np.clip(u, low, high)


def sigmoid(u: np.ndarray | float) -> np.ndarray | float:
    """Fonction sigmoïde logistique : 1 / (1 + exp(-u))."""
    u_safe = np.clip(u, -50.0, 50.0)
    return 1.0 / (1.0 + np.exp(-u_safe))


# ============================================================================
# Classe de transformation de caractéristiques
# ============================================================================


@dataclass(frozen=True)
class FeatureTransform:
    name: str
    description: str
    func: Callable[[np.ndarray, np.ndarray], dict[str, Any]]

    def apply(self, x: np.ndarray, y: np.ndarray) -> tuple[np.ndarray, list[str]]:
        """Applique la transformation et retourne la matrice (N, D) et la liste des noms."""
        features_dict = self.func(x, y)
        names = list(features_dict.keys())
        columns: list[np.ndarray] = []

        for name in names:
            val = features_dict[name]
            arr = np.asarray(val, dtype=float)

            # Si c'est un scalaire (ex: "1": 1), on le diffuse à la taille de x
            if arr.ndim == 0:
                arr = np.full_like(x, arr, dtype=float)
            elif arr.shape != x.shape:
                try:
                    arr = np.broadcast_to(arr, x.shape).astype(float)
                except ValueError as err:
                    raise ValueError(
                        f"Le terme '{name}' a une dimension incompatible avec x : "
                        f"{arr.shape} vs {x.shape}"
                    ) from err
            columns.append(arr)

        if not columns:
            return np.empty((x.size, 0), dtype=float), []

        # Si les entrées sont 2D (meshgrid pour l'affichage de la grille), on aplatit
        if columns[0].ndim > 1:
            flat_cols = [c.ravel() for c in columns]
            mat = np.column_stack(flat_cols)
        else:
            mat = np.column_stack(columns)

        return mat, names


TRANSFORMS: dict[str, FeatureTransform] = {}


def register_transform(name: str, description: str = "") -> Callable:
    def decorator(fn: Callable[[np.ndarray, np.ndarray], dict[str, Any]]) -> Callable:
        TRANSFORMS[name] = FeatureTransform(name=name, description=description, func=fn)
        return fn

    return decorator


# ============================================================================
# Transformations pédagogiques prédéfinies
# ============================================================================


@register_transform(
    "1. Droite simple [1, x, y]",
    "Une ligne droite. Est-il possible d'isoler une île avec une seule droite ?",
)
def transform_droite(x: np.ndarray, y: np.ndarray) -> dict[str, Any]:
    return {
        "1": 1,
        "x": x,
        "y": y,
    }


@register_transform(
    "2. Droite + Diagonale [1, x, y, x*y]",
    "Ajoute le produit x*y : permet de créer une inclinaison Sud-Ouest / Nord-Est.",
)
def transform_diagonale(x: np.ndarray, y: np.ndarray) -> dict[str, Any]:
    return {
        "1": 1,
        "x": x,
        "y": y,
        "x*y": x * y,
    }


@register_transform(
    "3. Ellipse droite [1, x, y, x², y²]",
    "Courbures horizontale et verticale (polynôme de degré 2 sans terme croisé).",
)
def transform_ellipse(x: np.ndarray, y: np.ndarray) -> dict[str, Any]:
    return {
        "1": 1,
        "x": x,
        "y": y,
        "x²": x**2,
        "y²": y**2,
    }


@register_transform(
    "4. Polynôme degré 2 complet [1, x, y, x*y, x², y²]",
    "La combinaison idéale pour le Japon : une ellipse courbée et pivotée à 45° !",
)
def transform_poly2(x: np.ndarray, y: np.ndarray) -> dict[str, Any]:
    return {
        "1": 1,
        "x": x,
        "y": y,
        "x*y": x * y,
        "x²": x**2,
        "y²": y**2,
    }


@register_transform(
    "5. Inéquations & Demi-plans [1, x>0, y>0, y>x, y<x+4, x²+y²<30]",
    "Combinaison de plusieurs seuils et demi-plans (comme des règles logiques ou un neurone).",
)
def transform_inequations(x: np.ndarray, y: np.ndarray) -> dict[str, Any]:
    return {
        "1": 1,
        "x > 0": x > 0.0,
        "y > 0": y > 0.0,
        "y > x (diagonale)": y > x,
        "y < x + 4": y < x + 4.0,
        "x² + y² < 30": (x**2 + y**2) < 30.0,
    }


@register_transform(
    "6. Distance à Tokyo [1, d, d²]",
    "Plus on s'éloigne de Tokyo, plus on est dans l'eau (introduction aux noyaux RBF).",
)
def transform_distance_tokyo(x: np.ndarray, y: np.ndarray) -> dict[str, Any]:
    d = dist(x, y, 1.69, -0.31)
    return {
        "1": 1,
        "dist_tokyo": d,
        "dist_tokyo²": d**2,
    }


@register_transform(
    "7. Réseau de neurones ReLU [relu(x), relu(-x), relu(y)...]",
    "La brique du Deep Learning ! Des charnières linéaires combinées pour entourer le pays.",
)
def transform_relu_network(x: np.ndarray, y: np.ndarray) -> dict[str, Any]:
    return {
        "1": 1,
        "relu(x)": relu(x),
        "relu(-x)": relu(-x),
        "relu(y)": relu(y),
        "relu(-y)": relu(-y),
        "relu(y - 0.7*x)": relu(y - 0.7 * x),
        "relu(0.7*x - y)": relu(0.7 * x - y),
        "relu(y + 0.7*x)": relu(y + 0.7 * x),
    }


@register_transform(
    "8. Buckets & Tranches [between(x, a, b)]",
    "Découpe le monde en bandes et tranches (comme une grille ou un histogramme).",
)
def transform_buckets(x: np.ndarray, y: np.ndarray) -> dict[str, Any]:
    return {
        "1": 1,
        "ouest (x < -2)": x < -2,
        "centre_x (-2..2)": between(x, -2, 2),
        "est (x > 2)": x > 2,
        "sud (y < -2)": y < -2,
        "centre_y (-2..2)": between(y, -2, 2),
        "nord (y > 2)": y > 2,
        "boîte centrale": between(x, -2, 2) * between(y, -2, 2),
    }


@register_transform(
    "9. Mon laboratoire (Mireille)",
    "Espace pour inventer tes propres formules (ReLU, inéquations, buckets, distance...) !",
)
def transform_laboratoire(x: np.ndarray, y: np.ndarray) -> dict[str, Any]:
    """Laboratoire de Mireille.

    Tu peux ajouter, modifier ou commenter des lignes ci-dessous :
    - Écris simplement 1 pour le biais constant (plus besoin de np.ones_like !)
    - Écris directement des inéquations : x > 0, y < x + 2, dist(x, y) < 4
    - Utilise relu(u) pour ajouter des neurones charnières : relu(x), relu(-y)
    - Utilise between(u, a, b) pour créer des buckets / tranches
    - Utilise dist(x, y, x0, y0) pour calculer une distance
    - Utilise sqrt(u) sans te soucier des nombres négatifs
    """
    return {
        "1": 1,
        "x": x,
        "y": y,
        "x*y": x * y,
        "x²": x**2,
        "y²": y**2,
        "relu(x)": relu(x),
        "relu(-x)": relu(-x),
        "tranche_y": between(y, -3, 3),
        "banane": y - 0.08 * x**2,
        "proche_centre": dist(x, y) < 4,
    }

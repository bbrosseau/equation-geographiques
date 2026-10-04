"""Évaluateur sécurisé de formules mathématiques et inéquations avec syntaxe naturelle.

Permet à Mireille d'écrire des équations et inéquations en :
    - Coordonnées de la fenêtre : x, y dans [-1, 1]
    - Coordonnées géographiques : lat [-90, 90], lon [-180, 180] (et x=lon, y=lat)
    - Coordonnées centrées en degrés : x = lon - lon₀, y = lat - lat₀
"""

from __future__ import annotations

import ast
from dataclasses import dataclass
from enum import Enum

import numpy as np

from mireille_tuto.geo.sampling import TARGET, LabeledSample
from mireille_tuto.ml.transforms import (
    between,
    bucket,
    clamp,
    dist,
    relu,
    sigmoid,
    sqrt,
    step,
)


class CoordMode(str, Enum):
    WINDOW = "window"       # x, y dans [-1, 1] (coordonnées de la fenêtre visible)
    GEO = "geo"             # Latitude / Longitude réelles sur la Terre (x=lon, y=lat)
    CENTERED = "centered"   # x, y centrés en degrés sur le pays (ex: Japon)


PRESETS_BY_MODE: dict[CoordMode, list[tuple[str, str, str]]] = {
    CoordMode.WINDOW: [
        (
            "1. Demi-plan (droite fenêtre)",
            "y > 0.5*x",
            "Droite passant par le centre de l'écran (0, 0) : sépare le haut du bas.",
        ),
        (
            "2. Cercle centré fenêtre",
            "x**2 + y**2 < 0.25",
            "Cercle de rayon 0.5 centré exactement au milieu de la fenêtre visible.",
        ),
        (
            "3. Boîte centrale (encadrement)",
            "-0.5 < x < 0.5 and -0.4 < y < 0.4",
            "Rectangle délimité par des doubles inégalités dans l'écran.",
        ),
        (
            "4. Bande diagonale (Japon)",
            "y > 0.6*x - 0.2 and y < 0.6*x + 0.3 and -0.5 < x < 0.6",
            "Deux droites parallèles inclinées encadrant l'archipel dans la vue.",
        ),
        (
            "5. Ellipse inclinée (Honshu à 45°)",
            "0.15 - (x**2 + 2*y**2) + 1.8*x*y > 0",
            "Le terme x*y pivote l'ellipse à 45° dans les axes de la fenêtre.",
        ),
        (
            "6. Distance au centre de l'écran (sqrt)",
            "sqrt(x**2 + y**2) < 0.5",
            "Fonction racine carrée calculant la distance au centre (0, 0).",
        ),
        (
            "7. Neurone ReLU (charnière)",
            "relu(x + y) > 0.3",
            "Le neurone ReLU s'active en ligne droite après un coude.",
        ),
        (
            "8. Boîte bucket (between)",
            "between(x, -0.4, 0.4) and between(y, -0.4, 0.4)",
            "Tranche ou boîte 2D définie facilement avec between().",
        ),
        (
            "9. Distance au centre (dist)",
            "dist(x, y) < 0.5",
            "Distance directe au centre avec la fonction dist(x, y).",
        ),
    ],
    CoordMode.GEO: [
        (
            "1. Boîte géographique (lat / lon)",
            "30 < lat < 46 and 128 < lon < 146",
            "Encadrement en degrés réels : latitude entre 30° et 46° N, longitude entre 128° et 146° E.",
        ),
        (
            "2. Démarcation diagonale",
            "lat > 0.5 * lon - 35",
            "Une droite tracée directement dans le repère latitude / longitude.",
        ),
        (
            "3. Avec x (lon) et y (lat)",
            "30 < y < 46 and 128 < x < 146",
            "Ici x représente la longitude et y la latitude !",
        ),
        (
            "4. Bande diagonale géographique",
            "lat > 0.4*lon - 22 and lat < 0.4*lon - 16 and 130 < lon < 145",
            "Bande inclinée suivant les méridiens et parallèles de la Terre.",
        ),
        (
            "5. Rayon autour de Tokyo (sqrt)",
            "sqrt((lon - 139.7)**2 + (lat - 35.7)**2) < 5",
            "Cercle de rayon 5° autour de Tokyo (139.7° E, 35.7° N).",
        ),
        (
            "6. Tranches géographiques (between)",
            "between(lon, 130, 145) and between(lat, 31, 45)",
            "Encadrement simplifié sans syntaxe lourde grâce à between().",
        ),
        (
            "7. Distance directe à Tokyo (dist)",
            "dist(lon, lat, 139.7, 35.7) < 5",
            "Distance directe en degrés par rapport aux coordonnées de Tokyo.",
        ),
    ],
    CoordMode.CENTERED: [
        (
            "1. Demi-plan (droite)",
            "y > 0.5*x - 1",
            "Une droite inclinée dans le repère centré sur le pays.",
        ),
        (
            "2. Cercle centré",
            "x**2 + y**2 < 25",
            "Rayon de 5 degrés autour du centre (x² + y² < r²).",
        ),
        (
            "3. Boîte rectangulaire (encadrement)",
            "-4 < x < 4 and -3 < y < 3",
            "Double inégalité chaînée avec 'and' : délimite un rectangle en degrés.",
        ),
        (
            "4. Bande diagonale (2 droites)",
            "y > 0.4*x - 2 and y < 0.4*x + 2 and -5 < x < 5",
            "Deux droites parallèles et deux bornes : encadre la forme étirée de l'archipel !",
        ),
        (
            "5. Ellipse inclinée (Honshu à 45°)",
            "20 - (x**2 + 2*y**2) + 1.8*x*y > 0",
            "Le terme croisé x*y fait pivoter l'ellipse le long de l'île de Honshu.",
        ),
        (
            "6. Parabole courbée (banane)",
            "y > 0.08*x**2 - 1 and y < 0.08*x**2 + 3 and -5 < x < 5",
            "Une courbe en forme de banane pour suivre la courbure naturelle du Japon.",
        ),
        (
            "7. Distance euclidienne (sqrt)",
            "sqrt(x**2 + y**2) < 4.5",
            "Fonction racine carrée sqrt() pour calculer la distance directe au centre.",
        ),
        (
            "8. Neurones ReLU combinés",
            "relu(x + 2) - relu(x - 2) + y > 0",
            "Somme de deux neurones ReLU pour créer un palier.",
        ),
        (
            "9. Boîte bucket (between)",
            "between(x, -3.5, 3.5) and between(y, -3, 3)",
            "Bucket rectangulaire défini simplement avec between().",
        ),
        (
            "10. Distance directe (dist)",
            "dist(x, y) < 4.5",
            "Distance directe au centre avec la fonction dist(x, y).",
        ),
    ],
}

# Compatibilité descendante
PRESET_FORMULAS = PRESETS_BY_MODE[CoordMode.CENTERED]


def compute_coord_vars(
    lons: np.ndarray,
    lats: np.ndarray,
    bounds: tuple[float, float, float, float],
    center: tuple[float, float],
    mode: CoordMode | str = CoordMode.WINDOW,
) -> dict[str, np.ndarray]:
    """Calcule l'ensemble des variables de coordonnées pour les formules et le ML.

    Retourne un dictionnaire contenant :
        - 'x', 'y' : selon le mode choisi (fenêtre, géo ou centré)
        - 'lat', 'latitude' : latitude réelle [-90, 90]
        - 'lon', 'longitude' : longitude réelle [-180, 180]
        - 'x_win', 'y_win' : coordonnées dans la fenêtre [-1, 1]
        - 'x_deg', 'y_deg' : coordonnées en degrés relatives au centre
    """
    min_lon, min_lat, max_lon, max_lat = bounds
    span_x = max(max_lon - min_lon, 1e-6)
    span_y = max(max_lat - min_lat, 1e-6)

    lons = np.asarray(lons, dtype=float)
    lats = np.asarray(lats, dtype=float)

    x_win = 2.0 * (lons - min_lon) / span_x - 1.0
    y_win = 2.0 * (lats - min_lat) / span_y - 1.0

    cx, cy = center
    x_deg = lons - cx
    y_deg = lats - cy

    mode_str = mode.value if isinstance(mode, CoordMode) else str(mode)

    if mode_str == CoordMode.WINDOW.value:
        x, y = x_win, y_win
    elif mode_str == CoordMode.GEO.value:
        x, y = lons, lats
    else:  # CENTERED
        x, y = x_deg, y_deg

    return {
        "x": x,
        "y": y,
        "lat": lats,
        "latitude": lats,
        "lon": lons,
        "longitude": lons,
        "x_win": x_win,
        "y_win": y_win,
        "x_deg": x_deg,
        "y_deg": y_deg,
    }


@dataclass(frozen=True)
class EvaluationResult:
    values: np.ndarray
    is_boolean: bool

    @property
    def binary_prediction(self) -> np.ndarray:
        """Retourne +1 pour la prédiction cible (Japon), -1 pour eau/autre."""
        if self.is_boolean:
            return np.where(self.values, 1.0, -1.0)
        return np.where(self.values >= 0.0, 1.0, -1.0)


@dataclass(frozen=True)
class FormulaMetrics:
    accuracy: float
    target_recall: float
    water_specificity: float
    target_caught: int
    target_total: int
    water_errors: int
    water_total: int


class _ASTEvaluator(ast.NodeVisitor):
    def __init__(self, context: dict[str, any]):
        self.context = context

    def eval(self, expr_str: str) -> any:
        cleaned = expr_str.strip().replace("^", "**")
        tree = ast.parse(cleaned, mode="eval")
        return self.visit(tree.body)

    def visit_Constant(self, node: ast.Constant) -> any:
        return node.value

    def visit_Num(self, node: ast.Num) -> any:
        return node.n

    def visit_Name(self, node: ast.Name) -> any:
        if node.id in self.context:
            return self.context[node.id]
        raise NameError(f"Variable inconnue : '{node.id}' (utilisez 'x', 'y', 'lat', 'lon')")

    def visit_UnaryOp(self, node: ast.UnaryOp) -> any:
        val = self.visit(node.operand)
        if isinstance(node.op, ast.USub):
            return -val
        if isinstance(node.op, ast.UAdd):
            return +val
        if isinstance(node.op, ast.Not):
            return np.logical_not(val)
        raise NotImplementedError(f"Opérateur unaire non supporté : {type(node.op).__name__}")

    def visit_BinOp(self, node: ast.BinOp) -> any:
        left = self.visit(node.left)
        right = self.visit(node.right)
        if isinstance(node.op, ast.Add):
            return left + right
        if isinstance(node.op, ast.Sub):
            return left - right
        if isinstance(node.op, ast.Mult):
            return left * right
        if isinstance(node.op, ast.Div):
            return left / right
        if isinstance(node.op, ast.Pow):
            return left**right
        raise NotImplementedError(f"Opérateur binaire non supporté : {type(node.op).__name__}")

    def visit_BoolOp(self, node: ast.BoolOp) -> any:
        vals = [self.visit(v) for v in node.values]
        if isinstance(node.op, ast.And):
            res = vals[0]
            for v in vals[1:]:
                res = np.logical_and(res, v)
            return res
        if isinstance(node.op, ast.Or):
            res = vals[0]
            for v in vals[1:]:
                res = np.logical_or(res, v)
            return res
        raise NotImplementedError(f"Opérateur logique non supporté : {type(node.op).__name__}")

    def visit_Compare(self, node: ast.Compare) -> any:
        curr_left = self.visit(node.left)
        res = None
        for op, comparator in zip(node.ops, node.comparators):
            curr_right = self.visit(comparator)
            if isinstance(op, ast.Lt):
                c = curr_left < curr_right
            elif isinstance(op, ast.LtE):
                c = curr_left <= curr_right
            elif isinstance(op, ast.Gt):
                c = curr_left > curr_right
            elif isinstance(op, ast.GtE):
                c = curr_left >= curr_right
            elif isinstance(op, ast.Eq):
                c = curr_left == curr_right
            elif isinstance(op, ast.NotEq):
                c = curr_left != curr_right
            else:
                raise NotImplementedError(f"Comparateur non supporté : {type(op).__name__}")
            res = c if res is None else np.logical_and(res, c)
            curr_left = curr_right
        return res

    def visit_Call(self, node: ast.Call) -> any:
        func_name = node.func.id if isinstance(node.func, ast.Name) else None
        if func_name in self.context and callable(self.context[func_name]):
            args = [self.visit(a) for a in node.args]
            return self.context[func_name](*args)
        raise NameError(f"Fonction inconnue : '{func_name}'")


def evaluate_formula(
    expr: str,
    x: np.ndarray,
    y: np.ndarray,
    extra_vars: dict[str, any] | None = None,
) -> EvaluationResult:
    """Évalue une formule ou inéquation sur x, y et les variables supplémentaires."""
    context = {
        "x": x,
        "y": y,
        "np": np,
        "sqrt": sqrt,
        "abs": np.abs,
        "sin": np.sin,
        "cos": np.cos,
        "exp": np.exp,
        "min": np.minimum,
        "max": np.maximum,
        "relu": relu,
        "step": step,
        "between": between,
        "bucket": bucket,
        "dist": dist,
        "clamp": clamp,
        "sigmoid": sigmoid,
    }
    if extra_vars:
        context.update(extra_vars)

    evaluator = _ASTEvaluator(context)
    raw = evaluator.eval(expr)

    # Si le résultat est un scalaire (ex: "5"), on le diffuse à la forme de x
    if np.isscalar(raw):
        raw = np.full_like(x, raw)
    elif isinstance(raw, (bool, np.bool_)):
        raw = np.full(x.shape, bool(raw))
    else:
        raw = np.asarray(raw)

    is_bool = raw.dtype == bool or np.issubdtype(raw.dtype, np.bool_)
    return EvaluationResult(values=raw, is_boolean=is_bool)


def compute_metrics(
    eval_result: EvaluationResult,
    sample: LabeledSample,
) -> FormulaMetrics:
    """Calcule la précision, le rappel (Japon capturé) et la spécificité (eau évitée)."""
    preds = eval_result.binary_prediction
    truth = np.where(sample.labels == TARGET, 1.0, -1.0)

    is_target = truth == 1.0
    is_water = truth == -1.0

    target_total = int(np.sum(is_target))
    water_total = int(np.sum(is_water))

    target_caught = int(np.sum(preds[is_target] == 1.0)) if target_total > 0 else 0
    water_errors = int(np.sum(preds[is_water] == 1.0)) if water_total > 0 else 0

    acc = float(np.mean(preds == truth))
    target_recall = (target_caught / target_total) if target_total > 0 else 0.0
    water_spec = (1.0 - (water_errors / water_total)) if water_total > 0 else 1.0

    return FormulaMetrics(
        accuracy=acc,
        target_recall=target_recall,
        water_specificity=water_spec,
        target_caught=target_caught,
        target_total=target_total,
        water_errors=water_errors,
        water_total=water_total,
    )

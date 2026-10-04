"""Entraîneur par moindres carrés (Least Squares / MSE) avec descente de gradient et solution directe."""

from __future__ import annotations

from dataclasses import dataclass, field

import numpy as np

from mireille_tuto.geo.sampling import TARGET, LabeledSample
from mireille_tuto.ml.formula import compute_coord_vars
from mireille_tuto.ml.transforms import FeatureTransform


@dataclass
class TrainingMetrics:
    epoch: int
    loss: float
    accuracy: float
    target_recall: float
    water_specificity: float
    target_caught: int
    target_total: int
    water_errors: int
    water_total: int
    equation: str


@dataclass
class LeastSquaresTrainer:
    transform: FeatureTransform
    center: tuple[float, float]
    balance_classes: bool = False
    coord_mode: str = "centered"
    bounds: tuple[float, float, float, float] = (-180.0, -90.0, 180.0, 90.0)
    n_neurons: int = 0
    seed: int = 42

    # État des données
    Phi: np.ndarray = field(default_factory=lambda: np.empty((0, 0)))
    scales: np.ndarray = field(default_factory=lambda: np.empty(0))
    Phi_norm: np.ndarray = field(default_factory=lambda: np.empty((0, 0)))
    y_target: np.ndarray = field(default_factory=lambda: np.empty(0))
    weights: np.ndarray = field(default_factory=lambda: np.empty(0))
    feature_names: list[str] = field(default_factory=list)

    # État du modèle linéaire (n_neurons == 0)
    w_norm: np.ndarray = field(default_factory=lambda: np.empty(0))

    # État du modèle réseau de neurones (n_neurons > 0)
    W1: np.ndarray = field(default_factory=lambda: np.empty((0, 0)))
    b1: np.ndarray = field(default_factory=lambda: np.empty(0))
    w2: np.ndarray = field(default_factory=lambda: np.empty(0))
    b2: float = 0.0

    epoch: int = 0
    loss_history: list[float] = field(default_factory=list)
    acc_history: list[float] = field(default_factory=list)

    @classmethod
    def from_sample(
        cls,
        sample: LabeledSample,
        center: tuple[float, float],
        transform: FeatureTransform,
        balance_classes: bool = False,
        coord_mode: str = "centered",
        bounds: tuple[float, float, float, float] | None = None,
        n_neurons: int = 0,
        seed: int = 42,
    ) -> LeastSquaresTrainer:
        if bounds is None:
            if len(sample) > 0:
                bounds = (
                    float(sample.lons.min()),
                    float(sample.lats.min()),
                    float(sample.lons.max()),
                    float(sample.lats.max()),
                )
            else:
                bounds = (-180.0, -90.0, 180.0, 90.0)
        trainer = cls(
            transform=transform,
            center=center,
            balance_classes=balance_classes,
            coord_mode=coord_mode,
            bounds=bounds,
            n_neurons=n_neurons,
            seed=seed,
        )
        trainer.set_data(sample, bounds)
        return trainer

    def set_data(
        self,
        sample: LabeledSample,
        bounds: tuple[float, float, float, float] | None = None,
        keep_weights: bool = True,
    ) -> None:
        if bounds is not None:
            self.bounds = bounds

        coords = compute_coord_vars(sample.lons, sample.lats, self.bounds, self.center, self.coord_mode)
        x = coords["x"]
        y = coords["y"]

        old_w_raw = self.w_raw if (self.n_neurons == 0 and self.w_norm.size > 0) else None
        old_W1 = self.W1.copy() if (self.n_neurons > 0 and self.W1.size > 0) else None
        old_b1 = self.b1.copy() if (self.n_neurons > 0 and self.b1.size > 0) else None
        old_w2 = self.w2.copy() if (self.n_neurons > 0 and self.w2.size > 0) else None
        old_b2 = self.b2
        old_epoch = self.epoch

        self.Phi, self.feature_names = self.transform.apply(x, y)
        d = self.Phi.shape[1]

        # Normalisation des colonnes pour assurer la stabilité du pas d'apprentissage (learning rate)
        scales = np.std(self.Phi, axis=0)
        # Ne pas mettre à l'échelle le terme constant / biais s'il a un std nul
        scales[scales < 1e-6] = 1.0
        self.scales = scales
        self.Phi_norm = self.Phi / scales

        # Cible : +1 pour le pays cible (Japon), -1 pour l'eau et autres
        self.y_target = np.where(sample.labels == TARGET, 1.0, -1.0)
        n = len(self.y_target)
        n_pos = int(np.sum(self.y_target == 1.0))
        n_neg = int(np.sum(self.y_target == -1.0))

        if self.balance_classes and n_pos > 0 and n_neg > 0:
            # Pondération pour que la somme des poids du Japon égale celle de l'eau
            self.weights = np.where(self.y_target == 1.0, 1.0 / n_pos, 1.0 / n_neg) * (n / 2.0)
        else:
            self.weights = np.ones(n, dtype=float)

        if keep_weights and old_epoch > 0:
            if self.n_neurons == 0 and old_w_raw is not None and len(old_w_raw) == d:
                self.w_norm = old_w_raw * self.scales
                self.epoch = old_epoch
            elif self.n_neurons > 0 and old_W1 is not None and old_W1.shape == (d, self.n_neurons):
                self.W1 = old_W1
                self.b1 = old_b1
                self.w2 = old_w2
                self.b2 = old_b2
                self.epoch = old_epoch
            else:
                self.reset()
        else:
            self.reset()

    def reset(self) -> None:
        d = self.Phi.shape[1] if self.Phi.size > 0 else 0
        self.epoch = 0
        self.loss_history.clear()
        self.acc_history.clear()

        if self.n_neurons == 0:
            self.w_norm = np.zeros(d, dtype=float)
            self.W1 = np.empty((0, 0))
            self.b1 = np.empty(0)
            self.w2 = np.empty(0)
            self.b2 = 0.0
        else:
            self.w_norm = np.empty(0)
            if d > 0 and self.n_neurons > 0:
                rng = np.random.default_rng(self.seed)
                scale1 = float(np.sqrt(2.0 / max(1, d)))
                self.W1 = rng.standard_normal((d, self.n_neurons)) * scale1
                self.b1 = rng.uniform(-0.5, 0.5, size=self.n_neurons)
                scale2 = float(np.sqrt(2.0 / max(1, self.n_neurons)))
                self.w2 = rng.standard_normal(self.n_neurons) * scale2
                self.b2 = 0.0
            else:
                self.W1 = np.empty((0, 0))
                self.b1 = np.empty(0)
                self.w2 = np.empty(0)
                self.b2 = 0.0

    @property
    def w_raw(self) -> np.ndarray:
        """Poids dénormalisés correspondant directement à la formule mathématique (modèle linéaire)."""
        if self.w_norm.size == 0 or self.scales.size == 0:
            return np.empty(0)
        return self.w_norm / self.scales

    def step(self, lr: float = 0.05, n_steps: int = 1) -> TrainingMetrics:
        """Exécute un ou plusieurs pas de descente de gradient."""
        if self.Phi_norm.size == 0:
            raise ValueError("Aucune donnée chargée dans l'entraîneur.")

        n = len(self.y_target)
        for _ in range(n_steps):
            if self.n_neurons == 0:
                pred = self.Phi_norm @ self.w_norm
                err = self.weights * (pred - self.y_target)
                grad = (2.0 / n) * (self.Phi_norm.T @ err)
                self.w_norm -= lr * grad
            else:
                Z = self.Phi_norm @ self.W1 + self.b1
                H = np.maximum(0.0, Z)
                pred = H @ self.w2 + self.b2
                err = self.weights * (pred - self.y_target)
                dy = (2.0 / n) * err

                dw2 = H.T @ dy
                db2 = float(np.sum(dy))

                dH = np.outer(dy, self.w2)
                dZ = dH * (Z > 0)
                dW1 = self.Phi_norm.T @ dZ
                db1 = np.sum(dZ, axis=0)

                self.W1 -= lr * dW1
                self.b1 -= lr * db1
                self.w2 -= lr * dw2
                self.b2 -= lr * db2

            self.epoch += 1

        return self.compute_metrics()

    def solve_analytical(self, reg: float = 1e-3) -> TrainingMetrics:
        """Calcule instantanément la solution algébrique exacte (moindres carrés régularisés)."""
        if self.Phi.size == 0:
            raise ValueError("Aucune donnée chargée dans l'entraîneur.")

        if self.n_neurons == 0:
            d = self.Phi.shape[1]
            w_mat = self.weights[:, None] * self.Phi
            lhs = self.Phi.T @ w_mat + reg * np.eye(d)
            rhs = self.Phi.T @ (self.weights * self.y_target)
            w_direct = np.linalg.solve(lhs, rhs)

            self.w_norm = w_direct * self.scales
        else:
            # Random Features / ELM : résout exactement la couche de sortie par moindres carrés
            Z = self.Phi_norm @ self.W1 + self.b1
            H = np.maximum(0.0, Z)
            N = len(self.y_target)
            H_ext = np.column_stack([np.ones(N), H])
            K_ext = H_ext.shape[1]

            lhs = H_ext.T @ (self.weights[:, None] * H_ext) + reg * np.eye(K_ext)
            rhs = H_ext.T @ (self.weights * self.y_target)
            w_ext = np.linalg.solve(lhs, rhs)

            self.b2 = float(w_ext[0])
            self.w2 = w_ext[1:]

        self.epoch += 1
        return self.compute_metrics()

    def compute_metrics(self) -> TrainingMetrics:
        if self.n_neurons == 0:
            pred = self.Phi_norm @ self.w_norm
        else:
            Z = self.Phi_norm @ self.W1 + self.b1
            H = np.maximum(0.0, Z)
            pred = H @ self.w2 + self.b2

        n = len(self.y_target)
        loss = float((1.0 / n) * np.sum(self.weights * (pred - self.y_target) ** 2))
        self.loss_history.append(loss)

        pred_binary = np.where(pred >= 0.0, 1.0, -1.0)
        acc = float(np.mean(pred_binary == self.y_target))
        self.acc_history.append(acc)

        is_target = self.y_target == 1.0
        is_water = self.y_target == -1.0

        n_target = int(np.sum(is_target))
        n_water = int(np.sum(is_water))

        caught = int(np.sum(pred_binary[is_target] == 1.0)) if n_target > 0 else 0
        water_err = int(np.sum(pred_binary[is_water] == 1.0)) if n_water > 0 else 0

        recall = caught / n_target if n_target > 0 else 0.0
        spec = 1.0 - (water_err / n_water) if n_water > 0 else 1.0

        return TrainingMetrics(
            epoch=self.epoch,
            loss=loss,
            accuracy=acc,
            target_recall=recall,
            water_specificity=spec,
            target_caught=caught,
            target_total=n_target,
            water_errors=water_err,
            water_total=n_water,
            equation=self.format_equation(),
        )

    def predict_grid(self, x_grid: np.ndarray, y_grid: np.ndarray) -> np.ndarray:
        """Évalue le modèle sur une grille 2D pour tracer la frontière sur la carte."""
        if self.n_neurons == 0:
            if self.w_norm.size == 0:
                return np.zeros_like(x_grid)
            phi_grid, _ = self.transform.apply(x_grid, y_grid)
            scores = phi_grid @ self.w_raw
            return scores.reshape(x_grid.shape)
        else:
            if self.W1.size == 0 or self.w2.size == 0:
                return np.zeros_like(x_grid)
            phi_grid, _ = self.transform.apply(x_grid, y_grid)
            phi_grid_norm = phi_grid / self.scales
            Z = phi_grid_norm @ self.W1 + self.b1
            H = np.maximum(0.0, Z)
            scores = H @ self.w2 + self.b2
            return scores.reshape(x_grid.shape)

    def format_equation(self, decimals: int = 3) -> str:
        """Formate l'équation mathématique apprise pour affichage."""
        mode_str = self.coord_mode if isinstance(self.coord_mode, str) else getattr(self.coord_mode, "value", str(self.coord_mode))
        is_geo = mode_str == "geo"
        var_x = "lon" if is_geo else "x"
        var_y = "lat" if is_geo else "y"

        if self.n_neurons == 0:
            if self.w_raw.size == 0:
                return f"f({var_x}, {var_y}) = 0"

            terms: list[str] = []
            for weight, raw_name in zip(self.w_raw, self.feature_names):
                if abs(weight) < 1e-5:
                    continue
                name = raw_name
                if is_geo:
                    name = name.replace("x", "lon").replace("y", "lat")
                sign = "+" if weight >= 0 else "-"
                val = abs(weight)
                if name == "1":
                    terms.append(f"{sign} {val:.{decimals}f}")
                else:
                    terms.append(f"{sign} {val:.{decimals}f}·({name})")

            if not terms:
                return f"f({var_x}, {var_y}) = 0"

            expr = " ".join(terms)
            if expr.startswith("+ "):
                expr = expr[2:]
            return f"f({var_x}, {var_y}) = {expr}"
        else:
            if self.w2.size == 0:
                return f"f({var_x}, {var_y}) = 0 ({self.n_neurons} neurones)"

            # 1. Combinaison des neurones en sortie
            out_terms: list[str] = []
            for k in range(self.n_neurons):
                w = self.w2[k]
                sign = "+" if w >= 0 else "-"
                out_terms.append(f"{sign} {abs(w):.{decimals}f}·N{k+1}")
            if abs(self.b2) >= 1e-5:
                b_sign = "+" if self.b2 >= 0 else "-"
                out_terms.append(f"{b_sign} {abs(self.b2):.{decimals}f}")

            out_expr = " ".join(out_terms)
            if out_expr.startswith("+ "):
                out_expr = out_expr[2:]

            lines = [f"f({var_x}, {var_y}) = {out_expr}"]

            # 2. Formule de chaque neurone (combinaisons des features transformées)
            # Z_k = sum_j (W1[j, k] / scales[j]) * phi_j + b1[k]
            W1_raw = self.W1 / self.scales[:, None]
            max_shown = 4
            for k in range(min(self.n_neurons, max_shown)):
                n_terms: list[str] = []
                for j, name in enumerate(self.feature_names):
                    if is_geo:
                        name = name.replace("x", "lon").replace("y", "lat")
                    w = W1_raw[j, k]
                    if abs(w) < 1e-3:
                        continue
                    sign = "+" if w >= 0 else "-"
                    val = abs(w)
                    if name == "1":
                        n_terms.append(f"{sign} {val:.{decimals}f}")
                    else:
                        n_terms.append(f"{sign} {val:.{decimals}f}·({name})")
                b_val = self.b1[k]
                if abs(b_val) >= 1e-3:
                    b_s = "+" if b_val >= 0 else "-"
                    n_terms.append(f"{b_s} {abs(b_val):.{decimals}f}")

                n_expr = " ".join(n_terms)
                if n_expr.startswith("+ "):
                    n_expr = n_expr[2:]
                if not n_expr:
                    n_expr = "0"
                lines.append(f"  • N{k+1} = relu({n_expr})")

            if self.n_neurons > max_shown:
                lines.append(f"  • ... (+ {self.n_neurons - max_shown} autres neurones)")

            return "\n".join(lines)

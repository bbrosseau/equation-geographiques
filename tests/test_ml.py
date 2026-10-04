import numpy as np
import pytest

from equation_geographique.geo.countries import DATASET_110M, CountryAtlas
from equation_geographique.geo.sampling import sample_view
from equation_geographique.ml import (
    PRESET_FORMULAS,
    PRESETS_BY_MODE,
    TRANSFORMS,
    CoordMode,
    LeastSquaresTrainer,
    compute_coord_vars,
    compute_metrics,
    evaluate_formula,
)


@pytest.fixture(scope="module")
def atlas() -> CountryAtlas:
    return CountryAtlas.load(DATASET_110M)


@pytest.fixture(scope="module")
def sample_japan(atlas):
    japan = atlas.by_code("JPN")
    return sample_view(atlas, japan.geometry.bounds, 1000, japan, np.random.default_rng(42))


def test_evaluate_inequality_simple():
    x = np.array([-2.0, 0.0, 3.0])
    y = np.array([1.0, 1.0, 1.0])
    res = evaluate_formula("y > 0.5*x", x, y)
    assert res.is_boolean
    assert res.values.tolist() == [True, True, False]
    assert res.binary_prediction.tolist() == [1.0, 1.0, -1.0]


def test_evaluate_chained_inequalities():
    x = np.array([-6.0, 0.0, 6.0])
    y = np.array([0.0, 0.0, 0.0])
    res = evaluate_formula("-5 < x < 5 and y >= 0", x, y)
    assert res.is_boolean
    assert res.values.tolist() == [False, True, False]


def test_evaluate_numeric_formula():
    x = np.array([0.0, 3.0, 5.0])
    y = np.array([0.0, 4.0, 5.0])
    res = evaluate_formula("25 - (x**2 + y**2)", x, y)
    assert not res.is_boolean
    assert res.values.tolist() == [25.0, 0.0, -25.0]
    assert res.binary_prediction.tolist() == [1.0, 1.0, -1.0]


def test_preset_formulas_evaluate_without_error():
    x = np.linspace(-5, 5, 20)
    y = np.linspace(-5, 5, 20)
    for name, expr, _ in PRESET_FORMULAS:
        res = evaluate_formula(expr, x, y)
        assert len(res.values) == 20


def test_transforms_registered():
    assert len(TRANSFORMS) >= 6
    assert "1. Droite simple [1, x, y]" in TRANSFORMS
    assert "4. Polynôme degré 2 complet [1, x, y, x*y, x², y²]" in TRANSFORMS
    assert "5. Inéquations & Demi-plans [1, x>0, y>0, y>x, y<x+4, x²+y²<30]" in TRANSFORMS


def test_trainer_gradient_descent(atlas, sample_japan):
    japan = atlas.by_code("JPN")
    transform = TRANSFORMS["4. Polynôme degré 2 complet [1, x, y, x*y, x², y²]"]
    trainer = LeastSquaresTrainer.from_sample(sample_japan, japan.center, transform, balance_classes=True)

    initial_loss = trainer.compute_metrics().loss
    metrics = trainer.step(lr=0.05, n_steps=20)
    assert metrics.epoch == 20
    assert metrics.loss < initial_loss
    assert metrics.accuracy > 0.5
    assert len(metrics.equation) > 0


def test_trainer_solve_analytical(atlas, sample_japan):
    japan = atlas.by_code("JPN")
    transform = TRANSFORMS["4. Polynôme degré 2 complet [1, x, y, x*y, x², y²]"]
    trainer = LeastSquaresTrainer.from_sample(sample_japan, japan.center, transform, balance_classes=True)

    metrics = trainer.solve_analytical()
    assert metrics.epoch == 1
    assert metrics.target_recall > 0.85
    assert "x*y" in metrics.equation


def test_compute_coord_vars():
    lons = np.array([120.0, 140.0, 160.0])
    lats = np.array([20.0, 35.0, 50.0])
    bounds = (120.0, 20.0, 160.0, 50.0)
    center = (138.0, 36.0)

    # Window mode: x and y in [-1, 1]
    vars_win = compute_coord_vars(lons, lats, bounds, center, CoordMode.WINDOW)
    assert np.allclose(vars_win["x"], [-1.0, 0.0, 1.0])
    assert np.allclose(vars_win["y"], [-1.0, 0.0, 1.0])
    assert np.allclose(vars_win["lat"], lats)
    assert np.allclose(vars_win["lon"], lons)

    # Geo mode: x=lon, y=lat
    vars_geo = compute_coord_vars(lons, lats, bounds, center, CoordMode.GEO)
    assert np.allclose(vars_geo["x"], lons)
    assert np.allclose(vars_geo["y"], lats)

    # Centered mode: x = lon - cx, y = lat - cy
    vars_cen = compute_coord_vars(lons, lats, bounds, center, CoordMode.CENTERED)
    assert np.allclose(vars_cen["x"], lons - 138.0)
    assert np.allclose(vars_cen["y"], lats - 36.0)


def test_formula_with_lat_and_lon():
    lons = np.array([139.7, 10.0, 145.0])
    lats = np.array([35.7, 50.0, 20.0])
    bounds = (0.0, 0.0, 180.0, 90.0)
    center = (138.0, 36.0)

    vars_win = compute_coord_vars(lons, lats, bounds, center, CoordMode.WINDOW)
    # Using 'lat' and 'lon' directly in formula
    res = evaluate_formula("30 < lat < 40 and 130 < lon < 150", vars_win["x"], vars_win["y"], extra_vars=vars_win)
    assert res.values.tolist() == [True, False, False]

    # Using 'x' and 'y' in geo mode
    vars_geo = compute_coord_vars(lons, lats, bounds, center, CoordMode.GEO)
    res_geo = evaluate_formula("30 < y < 40 and 130 < x < 150", vars_geo["x"], vars_geo["y"], extra_vars=vars_geo)
    assert res_geo.values.tolist() == [True, False, False]


def test_presets_by_mode():
    assert len(PRESETS_BY_MODE[CoordMode.WINDOW]) >= 5
    assert len(PRESETS_BY_MODE[CoordMode.GEO]) >= 5
    assert len(PRESETS_BY_MODE[CoordMode.CENTERED]) >= 5


def test_math_helpers_and_simplified_syntax():
    from equation_geographique.ml.transforms import (
        between,
        bucket,
        dist,
        relu,
        sigmoid,
        sqrt,
        step,
    )

    x = np.array([-2.0, 0.0, 1.5, 4.0])
    y = np.array([1.0, 2.0, -1.0, 0.0])

    # ReLU : max(0, u)
    assert np.allclose(relu(x), [0.0, 0.0, 1.5, 4.0])
    assert relu(-3.0) == 0.0
    assert relu(5.0) == 5.0

    # Step : 1.0 if >= 0 or bool True
    assert np.allclose(step(x), [0.0, 1.0, 1.0, 1.0])
    assert np.allclose(step(x > 1.0), [0.0, 0.0, 1.0, 1.0])

    # Between / Bucket : 1.0 if a <= u <= b
    assert np.allclose(between(x, -1.0, 2.0), [0.0, 1.0, 1.0, 0.0])
    assert np.allclose(bucket(x, -1.0, 2.0), [0.0, 1.0, 1.0, 0.0])

    # Dist : sqrt((x-x0)^2 + (y-y0)^2)
    assert np.allclose(dist(np.array([3.0]), np.array([4.0])), [5.0])
    assert np.allclose(dist(x, y, 0.0, 0.0), np.sqrt(x**2 + y**2))

    # Sqrt : safe from negative numbers
    assert np.allclose(sqrt(np.array([-4.0, 0.0, 9.0])), [0.0, 0.0, 3.0])

    # Sigmoid
    assert np.allclose(sigmoid(np.array([0.0])), [0.5])


def test_transform_laboratoire_and_scalar_broadcasting():
    x = np.array([-2.0, 0.0, 2.0])
    y = np.array([1.0, 3.0, 5.0])

    tf_lab = TRANSFORMS["9. Mon laboratoire (Mireille)"]
    mat, names = tf_lab.apply(x, y)
    assert mat.shape == (3, len(names))
    # Vérifie que "1" a été correctement diffusé en un vecteur de 1.0 sans np.ones_like
    idx_1 = names.index("1")
    assert np.allclose(mat[:, idx_1], [1.0, 1.0, 1.0])

    # Vérifie relu(x) dans le laboratoire
    idx_relu = names.index("relu(x)")
    assert np.allclose(mat[:, idx_relu], [0.0, 0.0, 2.0])


def test_transform_relu_and_buckets_networks():
    x = np.array([-3.0, 0.0, 3.0])
    y = np.array([-3.0, 0.0, 3.0])

    tf_relu = TRANSFORMS["7. Réseau de neurones ReLU [relu(x), relu(-x), relu(y)...]"]
    mat_r, names_r = tf_relu.apply(x, y)
    assert mat_r.shape == (3, len(names_r))

    tf_buck = TRANSFORMS["8. Buckets & Tranches [between(x, a, b)]"]
    mat_b, names_b = tf_buck.apply(x, y)
    assert mat_b.shape == (3, len(names_b))


def test_formula_with_relu_and_between():
    x = np.array([-2.0, 0.0, 2.0])
    y = np.array([1.0, 2.0, 3.0])

    # Test formula evaluating relu and between
    res_relu = evaluate_formula("relu(x) > 1", x, y)
    assert res_relu.values.tolist() == [False, False, True]

    res_between = evaluate_formula("between(x, -1, 1)", x, y)
    assert res_between.values.tolist() == [0.0, 1.0, 0.0]

    res_dist = evaluate_formula("dist(x, y) < 3", x, y)
    assert res_dist.values.tolist() == [True, True, False]


def test_trainer_with_hidden_neurons(atlas, sample_japan):
    japan = atlas.by_code("JPN")
    transform = TRANSFORMS["1. Droite simple [1, x, y]"]

    # 1. 0 neurones = modèle linéaire standard
    trainer_0 = LeastSquaresTrainer.from_sample(
        sample_japan, japan.center, transform, balance_classes=True, n_neurons=0
    )
    assert trainer_0.n_neurons == 0
    assert trainer_0.w_norm.size > 0
    assert trainer_0.W1.size == 0
    m0 = trainer_0.solve_analytical()
    assert "f(x, y) =" in m0.equation
    assert "• N1" not in m0.equation

    # 2. 4 neurones cachés apprenant des combinaisons de features transformées
    trainer_k = LeastSquaresTrainer.from_sample(
        sample_japan, japan.center, transform, balance_classes=True, n_neurons=4
    )
    assert trainer_k.n_neurons == 4
    assert trainer_k.W1.shape == (trainer_k.Phi.shape[1], 4)
    assert trainer_k.b1.shape == (4,)
    assert trainer_k.w2.shape == (4,)
    assert trainer_k.w_norm.size == 0

    # Résolution analytique (Random features / ELM)
    mk_direct = trainer_k.solve_analytical()
    assert mk_direct.epoch == 1
    assert "N1" in mk_direct.equation
    assert "relu(" in mk_direct.equation
    assert mk_direct.target_recall > 0.6

    # Descente de gradient / rétropropagation
    initial_loss = mk_direct.loss
    initial_W1 = trainer_k.W1.copy()
    initial_w2 = trainer_k.w2.copy()

    trainer_k.step(lr=0.05, n_steps=10)
    # Vérifie que les poids W1 et w2 ont tous les deux été mis à jour par rétropropagation
    assert not np.allclose(trainer_k.W1, initial_W1)
    assert not np.allclose(trainer_k.w2, initial_w2)

    # Grille 2D
    x_g, y_g = np.meshgrid(np.linspace(-5, 5, 10), np.linspace(-5, 5, 10))
    grid_scores = trainer_k.predict_grid(x_g, y_g)
    assert grid_scores.shape == (10, 10)




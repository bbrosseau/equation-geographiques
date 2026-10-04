import os

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import numpy as np
import pytest
from PySide6.QtWidgets import QApplication

from equation_geographique.geo.countries import DATASET_110M, CountryAtlas
from equation_geographique.ui import MainWindow


@pytest.fixture(scope="module")
def window():
    app = QApplication.instance() or QApplication([])
    win = MainWindow(CountryAtlas.load(DATASET_110M), focus_code="JPN")
    win.show()
    yield win
    win.close()
    app.processEvents()


def enter_algebra(window):
    """Choisit le pays de départ (Japon) et passe au mode Algèbre."""
    if window.in_algebra_mode and window.map.selected is window.focus_country:
        return
    if window.in_algebra_mode:
        window.leave_algebra_mode()
    window.map.select_country(window.focus_country)
    window.enter_algebra_button.click()
    assert window.in_algebra_mode


def test_starts_with_whole_world(window):
    min_lon, min_lat, max_lon, max_lat = window.map.visible_bounds()
    assert min_lon <= -179 and max_lon >= 179
    assert min_lat <= -89 and max_lat >= 89
    assert window.sample_size.value() == 1000
    assert not window.in_algebra_mode
    assert window.map.selected is window.focus_country
    assert window.enter_algebra_button.isEnabled()


def test_sample_view_updates_panel(window):
    enter_algebra(window)
    sample = window.map.sample_view(300, window.focus_country)
    assert len(sample) == 300
    assert "japon" in window.sample_info.text()
    # Vérification de la transparence (50%) et taille réduite (~20)
    scatters = [a for a in window.map._sample_artists if hasattr(a, "get_alpha")]
    assert len(scatters) > 0
    assert scatters[0].get_alpha() == 0.5
    assert np.all(scatters[0].get_sizes() == 20)
    window.map.clear_sample()
    assert window.map.sample is None


def test_select_country_updates_panel(window):
    if window.in_algebra_mode:
        window.leave_algebra_mode()
    canada = window.map.atlas.country_at(-100, 60)
    window.map.select_country(canada)
    assert "Canada" in window.country_info.text()
    assert window.zoom_button.isEnabled()
    assert window.enter_algebra_button.isEnabled()

    window.map.select_country(None)
    assert not window.enter_algebra_button.isEnabled()
    window.enter_algebra_mode()
    assert not window.in_algebra_mode


def test_algebra_mode_flow_keeps_manual_points(window):
    from equation_geographique.ui.map_canvas import MapMode

    window.map.clear_points()
    enter_algebra(window)
    assert window.map.mode is MapMode.ADD_POINT
    assert window.focus_country.name in window.algebra_title.text()
    bounds = window.map.visible_bounds()
    min_lon, min_lat, max_lon, max_lat = bounds
    assert max_lon - min_lon < 90

    # La vue est verrouillée en mode Algèbre
    assert window.map.view_locked
    assert not window.map.toolbar.isEnabled()
    window.map.reset_view()
    window.map.zoom_to(window.map.atlas.by_code("CAN"))
    assert window.map.visible_bounds() == pytest.approx(bounds)

    # Les graduations suivent le repère choisi (fenêtre [-1, 1] par défaut)
    assert window.map.coord_frame == "window"
    x0, y0, x1, y1 = window.map.visible_bounds()
    fmt_x = window.map.ax.xaxis.get_major_formatter()
    assert fmt_x(x0, 0) == "-1" and fmt_x((x0 + x1) / 2, 0) == "0" and fmt_x(x1, 0) == "1"
    window.algebra_panel.coord_combo.setCurrentIndex(2)  # centré sur le pays
    assert window.map.coord_frame == "centered"
    assert window.map.ax.xaxis.get_major_formatter()(window.focus_country.center[0], 0) == "0°"
    window.algebra_panel.coord_combo.setCurrentIndex(0)

    window.map.add_point(139.69, 35.69)
    window.sample_action.trigger()
    assert window.map.sample is not None

    window.leave_algebra_mode()
    assert not window.in_algebra_mode
    assert window.map.mode is MapMode.SELECT
    assert not window.map.view_locked
    assert window.map.toolbar.isEnabled()
    assert window.map.coord_frame is None
    assert window.map.sample is None
    assert len(window.map.points) == 1
    assert window.algebra_panel.trainer is None or window.algebra_panel.trainer.epoch == 0

    window.sample_action.trigger()
    assert window.map.sample is None
    window.map.clear_points()


def test_add_and_remove_points(window):
    window.map.add_point(2.35, 48.86, "#2a9d8f")
    window.map.add_point(-30.0, 30.0)
    assert window.points_list.count() == 2
    assert window.map.points[0].country == "France"
    assert window.map.points[1].country is None

    window.map.remove_point(0)
    assert window.points_list.count() == 1
    window.map.clear_points()
    assert window.points_list.count() == 0


def test_algebra_panel_formula(window):
    enter_algebra(window)
    panel = window.algebra_panel
    panel.formula_input.setText("y > 0.5*x - 1")
    panel._apply_formula()
    assert "✓ Inéquation active" in panel.formula_status.text()
    assert window.map._boundary_evaluator is not None

    panel._clear_formula()
    assert window.map._boundary_evaluator is None


def test_algebra_panel_ml_solve(window):
    enter_algebra(window)
    window.map.sample_view(400, window.focus_country)
    panel = window.algebra_panel

    panel._solve_analytical()
    assert panel.trainer is not None
    assert panel.trainer.epoch >= 1
    assert "Solution algébrique directe" in panel.ml_stats.text()
    assert "f(x, y) =" in panel.ml_equation.text()
    assert window.map._boundary_evaluator is not None


def test_algebra_panel_coordinate_modes(window):
    enter_algebra(window)
    panel = window.algebra_panel

    # 1. Switch to GEO mode
    panel.coord_combo.setCurrentIndex(1)  # GEO
    assert "lat [-90, 90]" in panel.coord_hint.text()
    assert panel.formula_presets.count() >= 5

    # Test geo formula with 'lat' and 'lon'
    panel.formula_input.setText("30 < lat < 46 and 128 < lon < 146")
    panel._apply_formula()
    assert "✓ Inéquation active" in panel.formula_status.text()
    assert window.map._boundary_evaluator is not None

    # 2. Switch to WINDOW mode
    panel.coord_combo.setCurrentIndex(0)  # WINDOW
    assert "x, y dans [-1, 1]" in panel.coord_hint.text()
    panel.formula_input.setText("x**2 + y**2 < 0.25")
    panel._apply_formula()
    assert "✓ Inéquation active" in panel.formula_status.text()


def test_algebra_panel_ml_union_manual_and_sample(window):
    enter_algebra(window)
    panel = window.algebra_panel
    window.map.clear_sample()
    window.map.clear_points()

    # 1. Ajouter des points manuels
    window.map.add_point(139.69, 35.69)  # Tokyo (Japon)
    window.map.add_point(150.0, 30.0)    # Océan

    manual_sample = window.map.get_manual_sample(window.focus_country)
    assert manual_sample is not None
    assert len(manual_sample) == 2

    training_sample = window.map.get_training_sample(window.focus_country)
    assert training_sample is not None
    assert len(training_sample) == 2

    # L'entraînement ML fonctionne avec les points manuels seuls
    panel._solve_analytical()
    assert panel.trainer is not None
    assert len(panel.trainer.y_target) == 2
    assert "2 points manuels" in panel.ml_stats.text()

    # 2. Tirer des points aléatoires : l'entraînement utilise l'union
    window.map.sample_view(50, window.focus_country)
    union_sample = window.map.get_training_sample(window.focus_country)
    assert union_sample is not None
    assert len(union_sample) == 52

    panel._solve_analytical()
    assert len(panel.trainer.y_target) == 52
    assert "52 points" in panel.ml_stats.text()
    assert "manuels" in panel.ml_stats.text()
    assert "échantillonnés" in panel.ml_stats.text()


def test_algebra_panel_neurons_selector(window):
    enter_algebra(window)
    panel = window.algebra_panel
    window.map.sample_view(100, window.focus_country)

    # 1. Par défaut : 0 neurones (modèle direct)
    assert panel.neurons_spin.value() == 0
    panel._solve_analytical()
    assert panel.trainer.n_neurons == 0
    assert "• N1" not in panel.ml_equation.text()

    # 2. On choisit 3 neurones cachés
    panel.neurons_spin.setValue(3)
    assert panel.neurons_spin.value() == 3
    panel._solve_analytical()
    assert panel.trainer.n_neurons == 3
    assert "N1" in panel.ml_equation.text()
    assert "relu(" in panel.ml_equation.text()

    # Un pas de rétropropagation
    panel._single_step()
    assert panel.trainer.epoch >= 2

    # 3. On revient à 0 neurones : le modèle direct est restauré
    panel.neurons_spin.setValue(0)
    panel._solve_analytical()
    assert panel.trainer.n_neurons == 0
    assert "• N1" not in panel.ml_equation.text()
    assert "f(x, y) =" in panel.ml_equation.text()


def test_window_icon(window):
    from equation_geographique.ui import get_app_icon

    icon = window.windowIcon()
    assert not icon.isNull()
    pix = icon.pixmap(64, 64)
    assert not pix.isNull()
    assert pix.width() == 64 and pix.height() == 64


def test_sample_view_accumulates_additional_points(window):
    enter_algebra(window)
    window.map.clear_sample()
    assert window.map.sample is None

    # Premier tirage de 100 points
    s1 = window.map.sample_view(100, window.focus_country)
    assert len(s1) == 100
    assert len(window.map.sample) == 100

    # Deuxième tirage : ajoute 150 points additionnels (total 250)
    s2 = window.map.sample_view(150, window.focus_country)
    assert len(s2) == 250
    assert len(window.map.sample) == 250

    window.map.clear_sample()
    assert window.map.sample is None


def test_pause_resume_change_lr_and_max_epochs(window):
    enter_algebra(window)
    panel = window.algebra_panel
    panel._reset_trainer()
    window.map.clear_sample()
    window.map.sample_view(120, window.focus_country)

    # 1. Résolution ou premier pas
    panel.lr_spin.setValue(0.05)
    panel.max_epochs_spin.setValue(10)
    panel._single_step()
    assert panel.trainer is not None
    assert panel.trainer.epoch == 1
    w_initial = panel.trainer.w_norm.copy()

    # 2. Étape +10
    panel._step_n(10)
    assert panel.trainer.epoch == 11
    assert not np.allclose(panel.trainer.w_norm, w_initial)
    w_after_11 = panel.trainer.w_norm.copy()

    # 3. Changer le taux d'apprentissage sans réinitialiser
    panel.lr_spin.setValue(0.01)
    # Vérifier que w_norm et epoch n'ont pas été réinitialisés
    assert panel.trainer.epoch == 11
    assert np.allclose(panel.trainer.w_norm, w_after_11)

    # 4. Simulation de pause et reprise : le modèle conserve son état
    panel._toggle_training()  # Démarre
    assert panel._training_timer.isActive()
    panel._toggle_training()  # Pause
    assert not panel._training_timer.isActive()
    assert panel.btn_train.text() == "▶ Reprendre"
    assert panel.trainer.epoch == 11
    assert np.allclose(panel.trainer.w_norm, w_after_11)

    # 5. Ajout de points additionnels par échantillonnage : la solution apprise est conservée
    window.map.sample_view(50, window.focus_country)
    assert len(window.map.sample) == 170
    assert panel.trainer.epoch == 11
    assert len(panel.trainer.w_raw) > 0


def test_epochs_per_tick_and_target_stop(window):
    enter_algebra(window)
    panel = window.algebra_panel
    panel._reset_trainer()
    window.map.clear_sample()
    window.map.sample_view(100, window.focus_country)

    panel._ensure_trainer()
    assert panel.trainer.epoch == 0

    # 1. Vérification que le sélecteur d'époques par mise à jour applique bien N pas
    panel.epochs_per_tick_spin.setValue(25)
    panel._on_train_tick()
    assert panel.trainer.epoch == 25

    # 2. Deuxième mise à jour : passe à 50
    panel._on_train_tick()
    assert panel.trainer.epoch == 50

    # 3. Arrêt sur cible (max_epochs)
    panel.max_epochs_spin.setValue(60)
    # Même si le batch est de 25, il ne doit faire que 10 pas pour s'arrêter pile à 60
    panel._on_train_tick()
    assert panel.trainer.epoch == 60






"""Panneau pédagogique pour explorer l'algèbre, les inéquations et l'apprentissage ML."""

from __future__ import annotations

from typing import Callable

import numpy as np
from PySide6.QtCore import Qt, QTimer
from PySide6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QDoubleSpinBox,
    QFrame,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QScrollArea,
    QSpinBox,
    QTabWidget,
    QVBoxLayout,
    QWidget,
)

from mireille_tuto.geo.countries import Country
from mireille_tuto.geo.sampling import TARGET, LabeledSample
from mireille_tuto.ml import (
    PRESET_FORMULAS,
    PRESETS_BY_MODE,
    TRANSFORMS,
    CoordMode,
    EvaluationResult,
    LeastSquaresTrainer,
    TrainingMetrics,
    compute_coord_vars,
    compute_metrics,
    evaluate_formula,
)


class AlgebraPanel(QWidget):
    def __init__(
        self,
        map_canvas,
        get_center: Callable[[], tuple[float, float]],
        get_target: Callable[[], Country | None] | None = None,
        parent=None,
    ):
        super().__init__(parent)
        self.map_canvas = map_canvas
        self.get_center = get_center
        self.get_target = get_target or (
            lambda: getattr(self.map_canvas, "selected", None)
            or (self.map_canvas.atlas.by_code("JPN") if hasattr(self.map_canvas, "atlas") else None)
        )
        self.trainer: LeastSquaresTrainer | None = None

        self._training_timer = QTimer(self)
        self._training_timer.timeout.connect(self._on_train_tick)

        self._build_ui()
        self.map_canvas.sampleChanged.connect(self._on_data_changed)
        if hasattr(self.map_canvas, "pointsChanged"):
            self.map_canvas.pointsChanged.connect(self._on_data_changed)
        if hasattr(self.map_canvas, "countrySelected"):
            self.map_canvas.countrySelected.connect(self._on_country_changed)

    def get_training_sample(self) -> LabeledSample | None:
        """Retourne l'échantillon d'entraînement combinant points manuels et échantillon aléatoire."""
        target = self.get_target()
        if target is None:
            return getattr(self.map_canvas, "sample", None)
        return self.map_canvas.get_training_sample(target)

    def _on_country_changed(self, country: Any) -> None:
        self._reset_trainer()
        self._on_data_changed()

    def current_coord_mode(self) -> CoordMode:
        data = self.coord_combo.currentData()
        if isinstance(data, CoordMode):
            return data
        try:
            return CoordMode(data)
        except (ValueError, TypeError):
            return CoordMode.WINDOW

    def _build_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)

        # 1. Sélecteur de repère de coordonnées
        coord_bar = QWidget(self)
        coord_bar_layout = QVBoxLayout(coord_bar)
        coord_bar_layout.setContentsMargins(8, 8, 8, 4)

        row = QHBoxLayout()
        row.addWidget(QLabel("<b>🌐 Repère :</b>"))
        self.coord_combo = QComboBox(coord_bar)
        self.coord_combo.addItem("🪟 Fenêtre [-1, 1]", CoordMode.WINDOW)
        self.coord_combo.addItem("🌍 Latitude & Longitude", CoordMode.GEO)
        self.coord_combo.addItem("📍 Centré sur le pays (degrés)", CoordMode.CENTERED)
        self.coord_combo.currentIndexChanged.connect(self._on_coord_mode_changed)
        row.addWidget(self.coord_combo, stretch=1)
        coord_bar_layout.addLayout(row)

        self.coord_hint = QLabel("", coord_bar)
        self.coord_hint.setWordWrap(True)
        self.coord_hint.setStyleSheet("color: #4b5563; font-size: 11px;")
        coord_bar_layout.addWidget(self.coord_hint)

        layout.addWidget(coord_bar)

        # 2. Onglets Inéquations & ML
        self.formula_widget = self._build_formula_tab()
        self.ml_widget = self._build_ml_tab()

        self.tabs = QTabWidget(self)
        self.tabs.addTab(self.formula_widget, "Inéquations")
        self.tabs.addTab(self.ml_widget, "Apprentissage Machine")
        layout.addWidget(self.tabs)

        self._update_coord_hint()
        self._refresh_example_cards()

    def _update_coord_hint(self) -> None:
        mode = self.current_coord_mode()
        if mode == CoordMode.WINDOW:
            self.coord_hint.setText(
                "<b>x, y dans [-1, 1]</b> dans la fenêtre (centre = (0, 0)).<br>"
                "💡 <i>lat et lon restent utilisables en tout temps !</i>"
            )
        elif mode == CoordMode.GEO:
            self.coord_hint.setText(
                "<b>lat [-90, 90]°, lon [-180, 180]°</b> sur la Terre.<br>"
                "💡 <i>x = lon et y = lat sont aussi définis !</i>"
            )
        else:  # CENTERED
            self.coord_hint.setText(
                "<b>x = lon - lon₀, y = lat - lat₀</b> (degrés par rapport au centre).<br>"
                "💡 <i>lat et lon restent utilisables en tout temps !</i>"
            )

    def _on_coord_mode_changed(self, index: int) -> None:
        self._update_coord_hint()
        self._refresh_example_cards()
        self._reset_trainer()
        if self.formula_input.text().strip():
            self._apply_formula()

    # ========================================================================
    # Onglet 1 : Formules et Inéquations
    # ========================================================================

    def _build_formula_tab(self) -> QWidget:
        container = QWidget(self)
        container_layout = QVBoxLayout(container)
        container_layout.setContentsMargins(0, 0, 0, 0)

        scroll = QScrollArea(container)
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)

        widget = QWidget(scroll)
        layout = QVBoxLayout(widget)
        layout.setContentsMargins(8, 8, 8, 8)

        # Zone de saisie principale
        layout.addWidget(QLabel("<b>Ta formule ou inéquation :</b>", widget))

        self.formula_input = QLineEdit(widget)
        self.formula_input.setPlaceholderText("Ex: y > 0.5*x ou 30 < lat < 46 and 128 < lon < 146")
        self.formula_input.setStyleSheet("font-family: monospace; font-size: 12px; padding: 5px;")
        self.formula_input.returnPressed.connect(self._apply_formula)
        layout.addWidget(self.formula_input)

        btn_row = QHBoxLayout()
        btn_apply = QPushButton("🎯 Tracer la frontière", widget)
        btn_apply.setStyleSheet("background-color: #10b981; color: white; font-weight: bold; padding: 5px;")
        btn_apply.clicked.connect(self._apply_formula)
        btn_row.addWidget(btn_apply)

        btn_clear = QPushButton("Effacer", widget)
        btn_clear.clicked.connect(self._clear_formula)
        btn_row.addWidget(btn_clear)
        layout.addLayout(btn_row)

        # Statut de validation
        self.formula_status = QLabel("", widget)
        self.formula_status.setWordWrap(True)
        layout.addWidget(self.formula_status)

        # Résultats sur l'échantillon
        self.formula_stats = QLabel("<i>Tire un échantillon sur la carte (touche E) pour évaluer la précision.</i>", widget)
        self.formula_stats.setWordWrap(True)
        self.formula_stats.setTextFormat(Qt.TextFormat.RichText)
        self.formula_stats.setStyleSheet(
            "background-color: #f9fafb; border: 1px solid #e5e7eb; border-radius: 4px; padding: 6px;"
        )
        layout.addWidget(self.formula_stats)

        layout.addSpacing(12)

        # Guide de syntaxe et Exemples cliquables
        examples_box = QGroupBox("💡 Exemples & Guide de syntaxe", widget)
        examples_layout = QVBoxLayout(examples_box)

        syntax_guide = QLabel(
            "<div style='font-size: 11px; line-height: 1.4; color: #1f2937;'>"
            "<b>Variables :</b> <code>x, y</code> (selon repère) &nbsp;|&nbsp; <code>lat, lon</code> (Terre)<br>"
            "<b>Opérateurs :</b> <code>+ - * /</code> &nbsp;|&nbsp; <b>Puissances :</b> <code>**</code> ou <code>^</code><br>"
            "<b>Inéquations :</b> <code>&lt; &gt; &lt;= &gt;=</code> &nbsp;|&nbsp; <b>Logique :</b> <code>and</code>, <code>or</code><br>"
            "<b>Fonctions :</b> <code>relu(x)</code>, <code>between(x, a, b)</code>, <code>dist(x, y)</code>, <code>sqrt(x)</code>"
            "</div>",
            examples_box,
        )
        syntax_guide.setTextFormat(Qt.TextFormat.RichText)
        examples_layout.addWidget(syntax_guide)

        examples_layout.addSpacing(8)
        examples_layout.addWidget(QLabel("<b>Clique sur un exemple pour le charger :</b>", examples_box))

        self.formula_presets = QComboBox(examples_box)
        self.formula_presets.currentIndexChanged.connect(self._on_preset_selected)
        examples_layout.addWidget(self.formula_presets)

        self.preset_desc = QLabel("", examples_box)
        self.preset_desc.setWordWrap(True)
        self.preset_desc.setStyleSheet("color: #4b5563; font-size: 11px;")
        examples_layout.addWidget(self.preset_desc)

        # Conteneur des cartes d'exemples
        self.cards_widget = QWidget(examples_box)
        self.cards_layout = QVBoxLayout(self.cards_widget)
        self.cards_layout.setContentsMargins(0, 0, 0, 0)
        examples_layout.addWidget(self.cards_widget)

        layout.addWidget(examples_box)
        layout.addStretch(1)

        scroll.setWidget(widget)
        container_layout.addWidget(scroll)
        return container

    def _refresh_example_cards(self) -> None:
        mode = self.current_coord_mode()
        presets = PRESETS_BY_MODE.get(mode, PRESET_FORMULAS)

        # Nettoyer les anciennes cartes
        while self.cards_layout.count() > 0:
            child = self.cards_layout.takeAt(0)
            if child.widget():
                child.widget().deleteLater()

        # Mettre à jour la combobox d'exemples
        self.formula_presets.blockSignals(True)
        self.formula_presets.clear()
        self.formula_presets.addItem("Choisir un exemple dans la liste…", "")
        for name, expr, desc in presets:
            self.formula_presets.addItem(f"{name} : {expr}", (expr, desc))
        self.formula_presets.blockSignals(False)
        self.preset_desc.setText("")

        # Générer les boutons de cartes
        for name, expr, desc in presets:
            card = QWidget(self.cards_widget)
            card_layout = QVBoxLayout(card)
            card_layout.setContentsMargins(4, 4, 4, 4)

            btn = QPushButton(expr, card)
            btn.setStyleSheet(
                "text-align: left; font-family: monospace; font-size: 11px; "
                "background-color: #ffffff; border: 1px solid #cbd5e1; border-radius: 4px; padding: 4px 6px;"
            )
            btn.setToolTip(f"{name} : {desc}")
            btn.clicked.connect(lambda _=False, e=expr, d=desc: self._load_example(e, d))
            card_layout.addWidget(btn)

            sub_desc = QLabel(f"<small style='color: #64748b;'>{name} — {desc}</small>", card)
            sub_desc.setWordWrap(True)
            sub_desc.setTextFormat(Qt.TextFormat.RichText)
            card_layout.addWidget(sub_desc)

            self.cards_layout.addWidget(card)

    def _load_example(self, expr: str, desc: str) -> None:
        self.formula_input.setText(expr)
        self.preset_desc.setText(desc)
        self._apply_formula()

    def _on_preset_selected(self, index: int) -> None:
        data = self.formula_presets.currentData()
        if not data:
            self.preset_desc.setText("")
            return
        expr, desc = data
        self._load_example(expr, desc)

    def _apply_formula(self) -> None:
        expr = self.formula_input.text().strip()
        if not expr:
            self._clear_formula()
            return

        cx, cy = self.get_center()
        bounds = self.map_canvas.visible_bounds()
        mode = self.current_coord_mode()

        # Test de validation préalable
        try:
            dummy_coords = compute_coord_vars(
                np.array([cx, cx + 1.0]),
                np.array([cy, cy + 1.0]),
                bounds,
                (cx, cy),
                mode,
            )
            test_res = evaluate_formula(
                expr,
                dummy_coords["x"],
                dummy_coords["y"],
                extra_vars=dummy_coords,
            )
        except Exception as e:
            self.formula_status.setText(f"<span style='color:#dc2626;'><b>Erreur de syntaxe :</b> {e}</span>")
            return

        is_boolean = test_res.is_boolean
        kind = "Inéquation" if is_boolean else "Équation f(x, y) = 0"
        self.formula_status.setText(f"<span style='color:#059669;'>✓ {kind} active</span>")

        # Fonction d'évaluation passée au canvas pour le tracé 2D
        def evaluator(lons_2d: np.ndarray, lats_2d: np.ndarray) -> tuple[np.ndarray, bool]:
            cur_bounds = self.map_canvas.visible_bounds()
            coords = compute_coord_vars(lons_2d, lats_2d, cur_bounds, (cx, cy), mode)
            res = evaluate_formula(expr, coords["x"], coords["y"], extra_vars=coords)
            return res.values, res.is_boolean

        self.map_canvas.set_decision_boundary(evaluator)
        self._evaluate_formula_on_sample(expr)

    def _clear_formula(self) -> None:
        self.map_canvas.clear_decision_boundary()
        self.formula_status.setText("")
        self.formula_stats.setText("Frontière effacée.")

    def _evaluate_formula_on_sample(self, expr: str) -> None:
        sample = self.get_training_sample()
        if sample is None or len(sample) == 0:
            self.formula_stats.setText("<i>Place des points manuels (clic) ou tire un échantillon (touche E) pour voir le score !</i>")
            return

        cx, cy = self.get_center()
        bounds = self.map_canvas.visible_bounds()
        mode = self.current_coord_mode()
        coords = compute_coord_vars(sample.lons, sample.lats, bounds, (cx, cy), mode)
        res = evaluate_formula(expr, coords["x"], coords["y"], extra_vars=coords)
        m = compute_metrics(res, sample)

        n_manual = len(self.map_canvas.points) if hasattr(self.map_canvas, "points") else 0
        n_rand = len(self.map_canvas.sample) if getattr(self.map_canvas, "sample", None) else 0
        if n_manual > 0 and n_rand > 0:
            pts_tag = f"l'union ({len(sample)} points : {n_manual} manuels + {n_rand} échantillonnés)"
        elif n_manual > 0:
            pts_tag = f"{n_manual} point{'s' if n_manual > 1 else ''} manuel{'s' if n_manual > 1 else ''}"
        else:
            pts_tag = f"l'échantillon ({n_rand} points)"

        comment = ""
        if m.target_recall >= 0.85 and (1.0 - m.water_specificity) <= 0.15:
            comment = "<br><span style='color:#059669;'>⭐ <b>Excellent !</b> Tu as capturé le pays en évitant l'eau !</span>"
        elif m.target_recall < 0.5:
            comment = "<br><span style='color:#ea580c;'>💡 La zone est trop petite ou décalée : agrandis-la !</span>"
        elif (1.0 - m.water_specificity) > 0.4:
            comment = "<br><span style='color:#ea580c;'>💡 La zone est trop grande : elle attrape beaucoup d'eau.</span>"

        self.formula_stats.setText(
            f"<b>Résultats sur {pts_tag} :</b><br>"
            f"• Précision globale : <b>{m.accuracy:.1%}</b><br>"
            f"• Cible capturée : <b>{m.target_caught} / {m.target_total}</b> ({m.target_recall:.1%})<br>"
            f"• Erreurs sur l'eau : <b>{m.water_errors} / {m.water_total}</b> ({(1.0 - m.water_specificity):.1%})"
            f"{comment}"
        )

    # ========================================================================
    # Onglet 2 : Apprentissage Machine Learning (Moindres carrés)
    # ========================================================================

    def _build_ml_tab(self) -> QWidget:
        container = QWidget(self)
        container_layout = QVBoxLayout(container)
        container_layout.setContentsMargins(0, 0, 0, 0)

        scroll = QScrollArea(container)
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)

        widget = QWidget(scroll)
        layout = QVBoxLayout(widget)
        layout.setContentsMargins(8, 8, 8, 8)

        # Choix de la transformation
        layout.addWidget(QLabel("<b>1. Transformation (features) :</b>", widget))
        self.transform_combo = QComboBox(widget)
        for name, tf in TRANSFORMS.items():
            self.transform_combo.addItem(name, tf)
        self.transform_combo.currentIndexChanged.connect(self._on_transform_changed)
        layout.addWidget(self.transform_combo)

        self.transform_desc = QLabel("", widget)
        self.transform_desc.setWordWrap(True)
        self.transform_desc.setStyleSheet("color: #4b5563; font-size: 11px;")
        layout.addWidget(self.transform_desc)

        # Paramètres
        params_box = QGroupBox("Paramètres", widget)
        params_layout = QVBoxLayout(params_box)

        # Sélecteur de neurones
        neurons_row = QHBoxLayout()
        neurons_row.addWidget(QLabel("🧠 Neurones cachés :"))
        self.neurons_spin = QSpinBox(params_box)
        self.neurons_spin.setRange(0, 32)
        self.neurons_spin.setValue(0)
        self.neurons_spin.setSpecialValueText("0 (Modèle direct)")
        self.neurons_spin.setSuffix(" neurone(s)")
        self.neurons_spin.valueChanged.connect(self._on_neurons_changed)
        neurons_row.addWidget(self.neurons_spin)
        params_layout.addLayout(neurons_row)

        neurons_hint = QLabel(
            "<small style='color:#64748b;'>• <b>0</b> = régression directe sur tes caractéristiques.<br>"
            "• <b>1+</b> = neurones ReLU apprenant des combinaisons de tes caractéristiques !</small>",
            params_box,
        )
        neurons_hint.setTextFormat(Qt.TextFormat.RichText)
        neurons_hint.setWordWrap(True)
        params_layout.addWidget(neurons_hint)

        lr_row = QHBoxLayout()
        lr_row.addWidget(QLabel("Taux d'apprentissage (η) :"))
        self.lr_spin = QDoubleSpinBox(params_box)
        self.lr_spin.setRange(0.001, 1.0)
        self.lr_spin.setSingleStep(0.01)
        self.lr_spin.setValue(0.05)
        self.lr_spin.setDecimals(3)
        lr_row.addWidget(self.lr_spin)
        params_layout.addLayout(lr_row)

        batch_row = QHBoxLayout()
        batch_row.addWidget(QLabel("⚡ Époques / mise à jour :"))
        self.epochs_per_tick_spin = QSpinBox(params_box)
        self.epochs_per_tick_spin.setRange(1, 1000)
        self.epochs_per_tick_spin.setSingleStep(5)
        self.epochs_per_tick_spin.setValue(10)
        self.epochs_per_tick_spin.setSuffix(" ep / màj")
        self.epochs_per_tick_spin.setToolTip(
            "Nombre d'époques de descente de gradient exécutées à chaque rafraîchissement visuel de la carte."
        )
        batch_row.addWidget(self.epochs_per_tick_spin)
        params_layout.addLayout(batch_row)

        epochs_row = QHBoxLayout()
        epochs_row.addWidget(QLabel("🎯 Époques max (Arrêt) :"))
        self.max_epochs_spin = QSpinBox(params_box)
        self.max_epochs_spin.setRange(0, 10000)
        self.max_epochs_spin.setSingleStep(50)
        self.max_epochs_spin.setValue(0)
        self.max_epochs_spin.setSpecialValueText("0 (Illimité)")
        self.max_epochs_spin.setSuffix(" époques")
        self.max_epochs_spin.setToolTip("Objectif d'époques pour l'arrêt automatique lors de l'entraînement (0 = illimité).")
        epochs_row.addWidget(self.max_epochs_spin)
        params_layout.addLayout(epochs_row)

        speed_row = QHBoxLayout()
        speed_row.addWidget(QLabel("Cadence (images/s) :"))
        self.speed_spin = QSpinBox(params_box)
        self.speed_spin.setRange(1, 30)
        self.speed_spin.setSingleStep(2)
        self.speed_spin.setValue(10)
        self.speed_spin.setSuffix(" img/s")
        self.speed_spin.setToolTip("Fréquence de rafraîchissement visuel de la carte par seconde.")
        self.speed_spin.valueChanged.connect(self._update_timer_speed)
        speed_row.addWidget(self.speed_spin)
        params_layout.addLayout(speed_row)

        self.balance_check = QCheckBox("Pondérer les classes (Eau vs Pays)", params_box)
        self.balance_check.setChecked(False)
        self.balance_check.toggled.connect(self._reset_trainer)
        params_layout.addWidget(self.balance_check)

        layout.addWidget(params_box)

        # Boutons d'entraînement
        btn_row1 = QHBoxLayout()
        self.btn_train = QPushButton("▶ Démarrer", widget)
        self.btn_train.setStyleSheet("background-color: #2563eb; color: white; font-weight: bold; padding: 5px;")
        self.btn_train.clicked.connect(self._toggle_training)
        btn_row1.addWidget(self.btn_train)

        self.btn_step = QPushButton("Étape +1", widget)
        self.btn_step.clicked.connect(self._single_step)
        btn_row1.addWidget(self.btn_step)

        self.btn_step10 = QPushButton("Étape +10", widget)
        self.btn_step10.clicked.connect(lambda: self._step_n(10))
        btn_row1.addWidget(self.btn_step10)

        self.btn_step50 = QPushButton("Étape +50", widget)
        self.btn_step50.clicked.connect(lambda: self._step_n(50))
        btn_row1.addWidget(self.btn_step50)

        self.btn_reset = QPushButton("⟲ Réinit", widget)
        self.btn_reset.clicked.connect(self._reset_trainer)
        btn_row1.addWidget(self.btn_reset)
        layout.addLayout(btn_row1)

        self.btn_direct = QPushButton("⚡ Solution directe (Algèbre matricielle)", widget)
        self.btn_direct.setStyleSheet("background-color: #7c3aed; color: white; font-weight: bold; padding: 4px;")
        self.btn_direct.clicked.connect(self._solve_analytical)
        layout.addWidget(self.btn_direct)

        # Indicateurs en direct
        layout.addWidget(QLabel("<b>Statistiques en direct :</b>", widget))
        self.ml_stats = QLabel("Prêt. Cliquez sur « Démarrer ».", widget)
        self.ml_stats.setWordWrap(True)
        self.ml_stats.setTextFormat(Qt.TextFormat.RichText)
        layout.addWidget(self.ml_stats)

        # Équation apprise
        layout.addWidget(QLabel("<b>Équation apprise :</b>", widget))
        self.ml_equation = QLabel("f(x, y) = 0", widget)
        self.ml_equation.setWordWrap(True)
        self.ml_equation.setStyleSheet(
            "background-color: #f3f4f6; border: 1px solid #d1d5db; border-radius: 4px; padding: 6px; font-family: monospace; font-size: 11px;"
        )
        layout.addWidget(self.ml_equation)

        layout.addStretch(1)
        self._on_transform_changed(0)

        scroll.setWidget(widget)
        container_layout.addWidget(scroll)
        return container

    def _on_neurons_changed(self, value: int) -> None:
        self._reset_trainer()

    def _on_transform_changed(self, index: int) -> None:
        tf = self.transform_combo.currentData()
        if tf:
            self.transform_desc.setText(tf.description)
        self._reset_trainer()

    def _ensure_trainer(self) -> bool:
        sample = self.get_training_sample()
        if sample is None or len(sample) == 0:
            self.ml_stats.setText(
                "<span style='color:#ea580c;'>Veuillez placer des points manuels (clic) ou échantillonner la vue (touche E).</span>"
            )
            return False

        tf = self.transform_combo.currentData()
        center = self.get_center()
        bounds = self.map_canvas.visible_bounds()
        mode = self.current_coord_mode()
        n_neurons = self.neurons_spin.value()

        if (
            self.trainer is None
            or self.trainer.transform != tf
            or self.trainer.coord_mode != mode.value
            or self.trainer.n_neurons != n_neurons
        ):
            self.trainer = LeastSquaresTrainer.from_sample(
                sample=sample,
                center=center,
                transform=tf,
                balance_classes=self.balance_check.isChecked(),
                coord_mode=mode.value,
                bounds=bounds,
                n_neurons=n_neurons,
            )
        return True

    def _reset_trainer(self) -> None:
        if self._training_timer.isActive():
            self._toggle_training()
        if self.trainer:
            self.trainer.reset()
        self.ml_stats.setText("Modèle réinitialisé.")
        n_neurons = self.neurons_spin.value() if hasattr(self, "neurons_spin") else 0
        if n_neurons == 0:
            self.ml_equation.setText("f(x, y) = 0")
        else:
            self.ml_equation.setText(f"f(x, y) = 0 ({n_neurons} neurones en attente)")
        self.map_canvas.clear_decision_boundary()

    def _update_timer_speed(self) -> None:
        if self._training_timer.isActive():
            fps = max(1, self.speed_spin.value())
            self._training_timer.setInterval(int(1000 / fps))

    def _toggle_training(self) -> None:
        if self._training_timer.isActive():
            self._training_timer.stop()
            self.btn_train.setText("▶ Reprendre")
            self.btn_train.setStyleSheet("background-color: #2563eb; color: white; font-weight: bold; padding: 5px;")
        else:
            if not self._ensure_trainer():
                return
            max_ep = self.max_epochs_spin.value()
            if max_ep > 0 and self.trainer and self.trainer.epoch >= max_ep:
                # Si l'objectif actuel est déjà atteint, on l'augmente automatiquement de 50 époques
                self.max_epochs_spin.setValue(self.trainer.epoch + 50)
            fps = max(1, self.speed_spin.value())
            self._training_timer.start(int(1000 / fps))
            self.btn_train.setText("⏸ Pause")
            self.btn_train.setStyleSheet("background-color: #ea580c; color: white; font-weight: bold; padding: 5px;")

    def _on_train_tick(self) -> None:
        if not self.trainer:
            return
        max_ep = self.max_epochs_spin.value()
        if max_ep > 0 and self.trainer.epoch >= max_ep:
            self._training_timer.stop()
            self.btn_train.setText("▶ Reprendre")
            self.btn_train.setStyleSheet("background-color: #2563eb; color: white; font-weight: bold; padding: 5px;")
            self.ml_stats.setText(
                self.ml_stats.text() + f"<br><span style='color:#059669;'>🎯 <b>Objectif de {max_ep} époques atteint !</b> (Tu peux augmenter l'objectif ou continuer)</span>"
            )
            return

        batch = max(1, self.epochs_per_tick_spin.value())
        if max_ep > 0:
            remaining = max_ep - self.trainer.epoch
            steps = min(batch, remaining)
        else:
            steps = batch

        if steps <= 0:
            return

        lr = self.lr_spin.value()
        metrics = self.trainer.step(lr=lr, n_steps=steps)
        self._update_ml_display(metrics)

        if max_ep > 0 and self.trainer.epoch >= max_ep:
            self._training_timer.stop()
            self.btn_train.setText("▶ Reprendre")
            self.btn_train.setStyleSheet("background-color: #2563eb; color: white; font-weight: bold; padding: 5px;")
            self.ml_stats.setText(
                self.ml_stats.text() + f"<br><span style='color:#059669;'>🎯 <b>Objectif de {max_ep} époques atteint !</b> (Tu peux augmenter l'objectif ou continuer)</span>"
            )

    def _step_n(self, n: int = 1) -> None:
        if not self._ensure_trainer():
            return
        lr = self.lr_spin.value()
        metrics = self.trainer.step(lr=lr, n_steps=n)
        self._update_ml_display(metrics)

    def _single_step(self) -> None:
        self._step_n(1)

    def _solve_analytical(self) -> None:
        if not self._ensure_trainer():
            return
        metrics = self.trainer.solve_analytical()
        self._update_ml_display(metrics)
        self.ml_stats.setText(self.ml_stats.text() + "<br><span style='color:#7c3aed;'>⚡ <b>Solution algébrique directe calculée !</b></span>")
        if not self._training_timer.isActive():
            self.btn_train.setText("▶ Continuer (Gradient)")

    def _update_ml_display(self, m: TrainingMetrics) -> None:
        sample = self.get_training_sample()
        n_manual = len(self.map_canvas.points) if hasattr(self.map_canvas, "points") else 0
        n_rand = len(self.map_canvas.sample) if getattr(self.map_canvas, "sample", None) else 0
        total = len(sample) if sample else (n_manual + n_rand)

        if n_manual > 0 and n_rand > 0:
            pts_desc = f"{total} points (<b>{n_manual}</b> manuels + <b>{n_rand}</b> échantillonnés)"
        elif n_manual > 0:
            pts_desc = f"{total} points manuels"
        else:
            pts_desc = f"{total} points échantillonnés"

        self.ml_stats.setText(
            f"<b>Données :</b> {pts_desc}<br>"
            f"<b>Epoch :</b> {m.epoch} &nbsp;|&nbsp; <b>Perte (Loss MSE) :</b> {m.loss:.4f}<br>"
            f"• Précision globale : <b>{m.accuracy:.1%}</b><br>"
            f"• Pays capturé : <b>{m.target_caught} / {m.target_total}</b> ({m.target_recall:.1%})<br>"
            f"• Erreurs eau : <b>{m.water_errors} / {m.water_total}</b> ({(1.0 - m.water_specificity):.1%})"
        )
        self.ml_equation.setText(m.equation)

        # Mettre à jour la frontière tracée sur la carte
        trainer = self.trainer
        cx, cy = self.get_center()
        mode = self.current_coord_mode()

        def ml_evaluator(lons_2d: np.ndarray, lats_2d: np.ndarray) -> tuple[np.ndarray, bool]:
            cur_bounds = self.map_canvas.visible_bounds()
            coords = compute_coord_vars(lons_2d, lats_2d, cur_bounds, (cx, cy), mode)
            scores = trainer.predict_grid(coords["x"], coords["y"])
            return scores, False

        self.map_canvas.set_decision_boundary(ml_evaluator)

    def _on_data_changed(self, *args) -> None:
        sample = self.get_training_sample()
        if self.trainer is not None:
            if sample is not None and len(sample) > 0:
                was_trained = self.trainer.epoch > 0
                self.trainer.set_data(sample, self.map_canvas.visible_bounds(), keep_weights=True)
                if was_trained:
                    metrics = self.trainer.compute_metrics()
                    self._update_ml_display(metrics)
            else:
                self._reset_trainer()
        expr = self.formula_input.text().strip()
        if expr:
            self._evaluate_formula_on_sample(expr)

    def _on_sample_changed(self, sample: LabeledSample | None) -> None:
        self._on_data_changed(sample)

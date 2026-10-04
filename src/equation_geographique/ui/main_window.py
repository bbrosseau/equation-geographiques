"""Fenêtre principale de l'application."""

from __future__ import annotations

from matplotlib.backends.backend_qtagg import NavigationToolbar2QT
from PySide6.QtCore import Qt
from PySide6.QtGui import QAction, QColor, QIcon, QKeySequence, QPixmap
from PySide6.QtWidgets import (
    QCheckBox,
    QColorDialog,
    QDockWidget,
    QHBoxLayout,
    QLabel,
    QListWidget,
    QListWidgetItem,
    QMainWindow,
    QPushButton,
    QSpinBox,
    QStackedWidget,
    QToolButton,
    QVBoxLayout,
    QWidget,
)

from equation_geographique.geo import Country, CountryAtlas, LabeledSample, format_coords
from equation_geographique.ui.algebra_panel import AlgebraPanel
from equation_geographique.ui.icon import get_app_icon
from equation_geographique.ui.map_canvas import SAMPLE_COLORS, MapMode, WorldMapCanvas

QUICK_COLORS = ["#e63946", "#f4a261", "#2a9d8f", "#264653", "#8338ec", "#ff006e"]

COUNTRY_PAGE = 0
ALGEBRA_PAGE = 1

PRIMARY_BUTTON_STYLE = "background-color: #2563eb; color: white; font-weight: bold; padding: 8px;"


def color_icon(color: str, size: int = 16) -> QIcon:
    pixmap = QPixmap(size, size)
    pixmap.fill(QColor(color))
    return QIcon(pixmap)


class MainWindow(QMainWindow):
    def __init__(self, atlas: CountryAtlas, focus_code: str | None = None):
        super().__init__()
        self.focus_country = atlas.by_code(focus_code) if focus_code else None
        self.setWindowTitle("Équation géographique - Carte du monde")
        self.setWindowIcon(get_app_icon())
        self.resize(1400, 800)

        self.map = WorldMapCanvas(atlas, self)
        central = QWidget(self)
        layout = QVBoxLayout(central)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(NavigationToolbar2QT(self.map, central, coordinates=False))
        layout.addWidget(self.map)
        self.setCentralWidget(central)

        self._build_actions()
        self._build_side_panel()
        self.statusBar().showMessage(f"{len(atlas)} pays chargés")

        self.map.countrySelected.connect(self._show_country)
        self.map.pointsChanged.connect(self._refresh_points)
        self.map.sampleChanged.connect(self._show_sample)
        self.map.cursorMoved.connect(self._show_cursor)

        if self.focus_country is not None:
            self.map.select_country(self.focus_country)

    @property
    def in_algebra_mode(self) -> bool:
        return self.stack.currentIndex() == ALGEBRA_PAGE

    # ----- Construction de l'interface --------------------------------------

    def _build_actions(self) -> None:
        world = QAction("Vue du monde", self)
        world.setShortcut(QKeySequence("Home"))
        world.triggered.connect(self.map.reset_view)
        self.addAction(world)

        self.deselect_action = QAction("Désélectionner", self)
        self.deselect_action.setShortcut(QKeySequence("Esc"))
        self.deselect_action.triggered.connect(lambda: self.map.select_country(None))
        self.addAction(self.deselect_action)

        self.sample_action = QAction("Échantillonner la vue", self)
        self.sample_action.setShortcut(QKeySequence("E"))
        self.sample_action.setEnabled(False)
        self.sample_action.triggered.connect(self._sample_view)
        self.addAction(self.sample_action)

    def _build_side_panel(self) -> None:
        self.stack = QStackedWidget(self)
        self.stack.addWidget(self._build_country_page())
        self.stack.addWidget(self._build_algebra_page())

        dock = QDockWidget("Atelier Algèbre & ML", self)
        dock.setWidget(self.stack)
        dock.setFeatures(QDockWidget.DockWidgetFeature.DockWidgetMovable)
        dock.setMinimumWidth(320)
        dock.setMaximumWidth(430)
        self.addDockWidget(Qt.DockWidgetArea.RightDockWidgetArea, dock)

    def _build_country_page(self) -> QWidget:
        page = QWidget(self)
        layout = QVBoxLayout(page)

        layout.addWidget(QLabel("<h3>1. Choisis un pays</h3>", page))
        hint = QLabel("Clique sur un pays de la carte. Utilise la molette pour zoomer.", page)
        hint.setWordWrap(True)
        layout.addWidget(hint)

        layout.addSpacing(8)
        self.country_info = QLabel("Aucun pays sélectionné.", page)
        self.country_info.setWordWrap(True)
        self.country_info.setTextFormat(Qt.TextFormat.RichText)
        layout.addWidget(self.country_info)

        row = QHBoxLayout()
        self.zoom_button = QPushButton("Centrer sur ce pays", page)
        self.zoom_button.setEnabled(False)
        self.zoom_button.clicked.connect(lambda: self.map.zoom_to(self.map.selected))
        row.addWidget(self.zoom_button)
        world_button = QPushButton("Vue du monde", page)
        world_button.clicked.connect(self.map.reset_view)
        row.addWidget(world_button)
        layout.addLayout(row)

        layout.addSpacing(16)
        self.enter_algebra_button = QPushButton("Passer au mode Algèbre ▶", page)
        self.enter_algebra_button.setStyleSheet(PRIMARY_BUTTON_STYLE)
        self.enter_algebra_button.setEnabled(False)
        self.enter_algebra_button.clicked.connect(self.enter_algebra_mode)
        layout.addWidget(self.enter_algebra_button)

        layout.addStretch(1)
        return page

    def _build_algebra_page(self) -> QWidget:
        page = QWidget(self)
        layout = QVBoxLayout(page)
        layout.setContentsMargins(4, 4, 4, 4)

        header = QHBoxLayout()
        self.algebra_title = QLabel("", page)
        self.algebra_title.setTextFormat(Qt.TextFormat.RichText)
        header.addWidget(self.algebra_title, stretch=1)
        back = QPushButton("◀ Changer de pays", page)
        back.setToolTip("Retourne au choix du pays. L'échantillon est effacé, les points manuels sont conservés.")
        back.clicked.connect(self.leave_algebra_mode)
        header.addWidget(back)
        layout.addLayout(header)

        # Échantillon aléatoire
        row = QHBoxLayout()
        self.sample_size = QSpinBox(page)
        self.sample_size.setRange(10, 20000)
        self.sample_size.setSingleStep(100)
        self.sample_size.setValue(1000)
        self.sample_size.setSuffix(" points")
        row.addWidget(self.sample_size)
        sample_button = QPushButton("Échantillonner (E)", page)
        sample_button.clicked.connect(self._sample_view)
        row.addWidget(sample_button)
        clear_sample = QPushButton("Effacer", page)
        clear_sample.clicked.connect(self.map.clear_sample)
        row.addWidget(clear_sample)
        layout.addLayout(row)

        self.sample_info = QLabel("", page)
        self.sample_info.setWordWrap(True)
        self.sample_info.setTextFormat(Qt.TextFormat.RichText)
        layout.addWidget(self.sample_info)
        self._show_sample(None)

        # Points manuels
        layout.addWidget(QLabel("<b>Points manuels</b> — clique sur la carte pour en ajouter", page))
        colors = QHBoxLayout()
        for color in QUICK_COLORS:
            button = QToolButton(page)
            button.setIcon(color_icon(color))
            button.setToolTip(color)
            button.clicked.connect(lambda _=False, c=color: self._set_color(c))
            colors.addWidget(button)
        self.color_button = QToolButton(page)
        self.color_button.setIcon(color_icon(self.map.point_color, 22))
        self.color_button.setToolTip("Autre couleur…")
        self.color_button.clicked.connect(self._pick_color)
        colors.addWidget(self.color_button)
        colors.addStretch(1)
        layout.addLayout(colors)

        self.points_list = QListWidget(page)
        self.points_list.setMaximumHeight(90)
        layout.addWidget(self.points_list)
        row = QHBoxLayout()
        labels = QCheckBox("Étiquettes", page)
        labels.setChecked(True)
        labels.toggled.connect(self.map.set_labels_visible)
        row.addWidget(labels)
        remove = QPushButton("Supprimer", page)
        remove.clicked.connect(self._remove_selected_point)
        row.addWidget(remove)
        clear = QPushButton("Tout effacer", page)
        clear.clicked.connect(self.map.clear_points)
        row.addWidget(clear)
        layout.addLayout(row)

        self.algebra_panel = AlgebraPanel(
            map_canvas=self.map,
            get_center=lambda: self.map.selected.center if self.map.selected else (0.0, 0.0),
            get_target=lambda: self.map.selected,
            parent=page,
        )
        self.algebra_panel.coord_combo.currentIndexChanged.connect(lambda _: self._apply_coord_frame())
        layout.addWidget(self.algebra_panel, stretch=1)
        return page

    # ----- Modes ------------------------------------------------------------

    def enter_algebra_mode(self) -> None:
        country = self.map.selected
        if country is None:
            return
        self.algebra_title.setText(f"<h3>2. Algèbre — {country.name}</h3>")
        self.stack.setCurrentIndex(ALGEBRA_PAGE)
        self.map.zoom_to(country)
        self.map.set_view_locked(True)
        self._apply_coord_frame()
        self._set_map_mode(MapMode.ADD_POINT)
        self.sample_action.setEnabled(True)
        self.deselect_action.setEnabled(False)

    def leave_algebra_mode(self) -> None:
        self.algebra_panel._reset_trainer()
        self.algebra_panel._clear_formula()
        self.map.clear_sample()
        self.stack.setCurrentIndex(COUNTRY_PAGE)
        self.map.set_view_locked(False)
        self.map.set_coord_frame(None)
        self._set_map_mode(MapMode.SELECT)
        self.sample_action.setEnabled(False)
        self.deselect_action.setEnabled(True)

    def _apply_coord_frame(self) -> None:
        if self.in_algebra_mode and self.map.selected is not None:
            mode = self.algebra_panel.current_coord_mode()
            self.map.set_coord_frame(mode.value, self.map.selected.center)

    # ----- Réactions --------------------------------------------------------

    def _set_map_mode(self, mode: MapMode) -> None:
        self.map.mode = mode
        cursor = Qt.CursorShape.CrossCursor if mode is MapMode.ADD_POINT else Qt.CursorShape.ArrowCursor
        self.map.setCursor(cursor)

    def _sample_view(self) -> None:
        if self.in_algebra_mode and self.map.selected is not None:
            self.map.sample_view(self.sample_size.value(), self.map.selected)

    def _set_color(self, color: str) -> None:
        self.map.point_color = color
        self.color_button.setIcon(color_icon(color, 22))

    def _pick_color(self) -> None:
        color = QColorDialog.getColor(QColor(self.map.point_color), self, "Couleur des points")
        if color.isValid():
            self._set_color(color.name())

    def _show_country(self, country: Country | None) -> None:
        self.zoom_button.setEnabled(country is not None)
        self.enter_algebra_button.setEnabled(country is not None)
        if country is None:
            self.country_info.setText("Aucun pays sélectionné.")
            return
        lon, lat = country.center
        population = f"{country.population:,}".replace(",", " ")
        self.country_info.setText(
            f"<h2>{country.name}</h2>"
            f"<p>{country.name_en} ({country.code})</p>"
            f"<p><b>Continent :</b> {country.continent}<br>"
            f"<b>Population :</b> {population}<br>"
            f"<b>Centre :</b> {format_coords(lon, lat)}<br>"
            f"<b>Parties :</b> {len(country.polygons)}<br>"
            f"<b>Sommets de la frontière :</b> {country.vertex_count}</p>"
        )

    def _refresh_points(self) -> None:
        self.points_list.clear()
        for point in self.map.points:
            item = QListWidgetItem(color_icon(point.color), point.label.replace("\n", " — "))
            self.points_list.addItem(item)

    def _show_sample(self, sample: LabeledSample | None) -> None:
        if sample is None:
            self.sample_info.setText("Aucun échantillon. Clique sur « Échantillonner » (touche E).")
            return
        rows = "".join(
            f"<tr><td><span style='color:{color}'>✕</span> {name}</td>"
            f"<td align='right'>&nbsp;{count}</td>"
            f"<td align='right'>&nbsp;{count / len(sample):.0%}</td></tr>"
            for (name, count), color in zip(sample.counts().items(), SAMPLE_COLORS)
        )
        self.sample_info.setText(f"<p>{len(sample)} points tirés dans la vue</p><table>{rows}</table>")

    def _remove_selected_point(self) -> None:
        row = self.points_list.currentRow()
        if row >= 0:
            self.map.remove_point(row)

    def _show_cursor(self, info) -> None:
        if info is None:
            self.statusBar().clearMessage()
            return
        lon, lat, country = info
        place = country.name if country else "Océan"
        coords = format_coords(lon, lat)
        frame = self.map.frame_coords(lon, lat)
        if frame is not None:
            coords = f"x = {frame[0]:+.2f}, y = {frame[1]:+.2f}   ({coords})"
        self.statusBar().showMessage(f"{coords}   |   {place}")

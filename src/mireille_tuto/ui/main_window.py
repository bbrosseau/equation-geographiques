"""Fenêtre principale de l'application."""

from __future__ import annotations

from matplotlib.backends.backend_qtagg import NavigationToolbar2QT
from PySide6.QtCore import Qt
from PySide6.QtGui import QAction, QActionGroup, QColor, QIcon, QKeySequence, QPixmap
from PySide6.QtWidgets import (
    QCheckBox,
    QColorDialog,
    QDockWidget,
    QLabel,
    QListWidget,
    QListWidgetItem,
    QMainWindow,
    QPushButton,
    QToolBar,
    QVBoxLayout,
    QWidget,
)

from mireille_tuto.geo import Country, CountryAtlas, format_coords
from mireille_tuto.ui.map_canvas import MapMode, WorldMapCanvas

QUICK_COLORS = ["#e63946", "#f4a261", "#2a9d8f", "#264653", "#8338ec", "#ff006e"]


def color_icon(color: str, size: int = 16) -> QIcon:
    pixmap = QPixmap(size, size)
    pixmap.fill(QColor(color))
    return QIcon(pixmap)


class MainWindow(QMainWindow):
    def __init__(self, atlas: CountryAtlas):
        super().__init__()
        self.setWindowTitle("Mireille Tuto — Carte du monde")
        self.resize(1400, 800)

        self.map = WorldMapCanvas(atlas, self)
        central = QWidget(self)
        layout = QVBoxLayout(central)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(NavigationToolbar2QT(self.map, central, coordinates=False))
        layout.addWidget(self.map)
        self.setCentralWidget(central)

        self._build_toolbar()
        self._build_side_panel()
        self.statusBar().showMessage(f"{len(atlas)} pays chargés")

        self.map.countrySelected.connect(self._show_country)
        self.map.pointsChanged.connect(self._refresh_points)
        self.map.cursorMoved.connect(self._show_cursor)

    # ----- Construction de l'interface --------------------------------------

    def _build_toolbar(self) -> None:
        bar = QToolBar("Outils", self)
        bar.setMovable(False)
        self.addToolBar(bar)

        modes = QActionGroup(self)
        select = QAction("Sélectionner un pays", self, checkable=True, checked=True)
        select.setShortcut(QKeySequence("S"))
        select.triggered.connect(lambda: self._set_mode(MapMode.SELECT))
        add = QAction("Ajouter des points", self, checkable=True)
        add.setShortcut(QKeySequence("P"))
        add.triggered.connect(lambda: self._set_mode(MapMode.ADD_POINT))
        for action in (select, add):
            modes.addAction(action)
            bar.addAction(action)

        bar.addSeparator()
        bar.addWidget(QLabel(" Couleur : "))
        for color in QUICK_COLORS:
            action = QAction(color_icon(color), color, self)
            action.triggered.connect(lambda _=False, c=color: self._set_color(c))
            bar.addAction(action)
        self.color_action = QAction(color_icon(self.map.point_color, 22), "Autre couleur…", self)
        self.color_action.triggered.connect(self._pick_color)
        bar.addAction(self.color_action)

        bar.addSeparator()
        world = QAction("Vue du monde", self)
        world.setShortcut(QKeySequence("Home"))
        world.triggered.connect(self.map.reset_view)
        bar.addAction(world)
        clear = QAction("Effacer les points", self)
        clear.triggered.connect(self.map.clear_points)
        bar.addAction(clear)

        deselect = QAction("Désélectionner", self)
        deselect.setShortcut(QKeySequence("Esc"))
        deselect.triggered.connect(lambda: self.map.select_country(None))
        self.addAction(deselect)

    def _build_side_panel(self) -> None:
        panel = QWidget(self)
        layout = QVBoxLayout(panel)

        layout.addWidget(QLabel("<b>Pays sélectionné</b>"))
        self.country_info = QLabel("Clique sur un pays.", panel)
        self.country_info.setWordWrap(True)
        self.country_info.setTextFormat(Qt.TextFormat.RichText)
        layout.addWidget(self.country_info)
        self.zoom_button = QPushButton("Centrer sur ce pays", panel)
        self.zoom_button.setEnabled(False)
        self.zoom_button.clicked.connect(lambda: self.map.zoom_to(self.map.selected))
        layout.addWidget(self.zoom_button)

        layout.addSpacing(16)
        layout.addWidget(QLabel("<b>Points</b>"))
        self.points_list = QListWidget(panel)
        layout.addWidget(self.points_list, stretch=1)
        labels = QCheckBox("Afficher les étiquettes", panel)
        labels.setChecked(True)
        labels.toggled.connect(self.map.set_labels_visible)
        layout.addWidget(labels)
        remove = QPushButton("Supprimer le point", panel)
        remove.clicked.connect(self._remove_selected_point)
        layout.addWidget(remove)

        dock = QDockWidget("Informations", self)
        dock.setWidget(panel)
        dock.setFeatures(QDockWidget.DockWidgetFeature.DockWidgetMovable)
        dock.setMinimumWidth(280)
        self.addDockWidget(Qt.DockWidgetArea.RightDockWidgetArea, dock)

    # ----- Réactions --------------------------------------------------------

    def _set_mode(self, mode: MapMode) -> None:
        self.map.mode = mode
        cursor = Qt.CursorShape.CrossCursor if mode is MapMode.ADD_POINT else Qt.CursorShape.ArrowCursor
        self.map.setCursor(cursor)

    def _set_color(self, color: str) -> None:
        self.map.point_color = color
        self.color_action.setIcon(color_icon(color, 22))

    def _pick_color(self) -> None:
        color = QColorDialog.getColor(QColor(self.map.point_color), self, "Couleur des points")
        if color.isValid():
            self._set_color(color.name())

    def _show_country(self, country: Country | None) -> None:
        self.zoom_button.setEnabled(country is not None)
        if country is None:
            self.country_info.setText("Clique sur un pays.")
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
        self.statusBar().showMessage(f"{format_coords(lon, lat)}   |   {place}")

"""Widget de carte du monde : affichage des pays, sélection et points."""

from __future__ import annotations

import logging
from enum import Enum

import numpy as np
from matplotlib.backend_bases import MouseButton, MouseEvent
from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg
from matplotlib.collections import PatchCollection
from matplotlib.figure import Figure
from matplotlib.patches import PathPatch
from matplotlib.path import Path
from matplotlib.ticker import FuncFormatter
from PySide6.QtCore import Signal

from mireille_tuto.geo import (
    Country,
    CountryAtlas,
    LabeledSample,
    MapPoint,
    format_coords,
    format_lat,
    format_lon,
    label_points,
    sample_view,
)

OCEAN_COLOR = "#a9d6f5"
SAMPLE_COLORS = ("#1d4ed8", "#d62828", "#6b6b6b")  # eau, pays cible, autre pays
BORDER_COLOR = "#5a5a5a"
SELECTED_FILL = "#ffd166"
SELECTED_EDGE = "#d62828"
COUNTRY_PALETTE = ["#cfe8b0", "#f6e3a1", "#f3c5a8", "#d9c7ec", "#bfe3dc", "#f2bfcf", "#e6dcc3"]

WORLD_XLIM = (-180.0, 180.0)
WORLD_YLIM = (-90.0, 90.0)
ZOOM_STEP = 1.25

# L'aspect « equal » + adjustable="datalim" élargit volontairement les limites fixées pour
# remplir le widget ; matplotlib le signale à chaque redessin.
logging.getLogger("matplotlib.axes._base").setLevel(logging.ERROR)


class MapMode(Enum):
    SELECT = "select"
    ADD_POINT = "add_point"


def country_path(country: Country) -> Path:
    return Path.make_compound_path(*(Path(ring, closed=True) for ring in country.rings()))


class WorldMapCanvas(FigureCanvasQTAgg):
    countrySelected = Signal(object)  # Country | None
    pointsChanged = Signal()
    sampleChanged = Signal(object)  # LabeledSample | None
    cursorMoved = Signal(object)  # (lon, lat, Country | None) | None

    def __init__(self, atlas: CountryAtlas, parent=None):
        self.figure = Figure(figsize=(10, 5), layout="constrained")
        super().__init__(self.figure)
        self.setParent(parent)

        self.atlas = atlas
        self.mode = MapMode.SELECT
        self.point_color = "#e63946"
        self.show_labels = True
        self.points: list[MapPoint] = []
        self.selected: Country | None = None
        self.sample: LabeledSample | None = None

        self._paths = {c.code: country_path(c) for c in atlas.countries}
        self._point_artists: list[tuple] = []
        self._sample_artists: list = []
        self._boundary_artists: list = []
        self._boundary_evaluator = None  # Callable[[np.ndarray, np.ndarray], tuple[np.ndarray, bool]]
        self._selected_patch: PathPatch | None = None

        self.ax = self.figure.add_subplot()
        self._setup_axes()
        self._draw_countries()

        self.mpl_connect("button_press_event", self._on_click)
        self.mpl_connect("scroll_event", self._on_scroll)
        self.mpl_connect("motion_notify_event", self._on_motion)

    # ----- Dessin -----------------------------------------------------------

    def _setup_axes(self) -> None:
        ax = self.ax
        ax.set_facecolor(OCEAN_COLOR)
        ax.set_aspect("equal", adjustable="datalim")
        ax.set_xlim(*WORLD_XLIM)
        ax.set_ylim(*WORLD_YLIM)
        ax.set_xticks(range(-180, 181, 30))
        ax.set_yticks(range(-90, 91, 30))
        ax.xaxis.set_major_formatter(FuncFormatter(lambda x, _: format_lon(x, 0)))
        ax.yaxis.set_major_formatter(FuncFormatter(lambda y, _: format_lat(y, 0)))
        ax.tick_params(labelsize=8)
        ax.grid(True, color="white", linewidth=0.6, alpha=0.7)
        ax.set_axisbelow(False)
        ax.format_coord = lambda x, y: format_coords(x, y)

    def _draw_countries(self) -> None:
        patches = [PathPatch(self._paths[c.code]) for c in self.atlas.countries]
        colors = [COUNTRY_PALETTE[(c.map_color - 1) % len(COUNTRY_PALETTE)] for c in self.atlas.countries]
        collection = PatchCollection(
            patches, facecolors=colors, edgecolors=BORDER_COLOR, linewidths=0.4, zorder=2
        )
        self.ax.add_collection(collection)

    def _draw_point(self, point: MapPoint) -> tuple:
        (marker,) = self.ax.plot(
            point.lon, point.lat, "o", color=point.color,
            markersize=8, markeredgecolor="black", markeredgewidth=0.8, zorder=5,
        )
        label = self.ax.annotate(
            point.label, (point.lon, point.lat),
            xytext=(7, 7), textcoords="offset points", fontsize=8, zorder=6,
            bbox=dict(boxstyle="round,pad=0.3", fc="white", ec=point.color, alpha=0.85),
            visible=self.show_labels,
        )
        return marker, label

    # ----- Sélection --------------------------------------------------------

    def select_country(self, country: Country | None) -> None:
        if self._selected_patch is not None:
            self._selected_patch.remove()
            self._selected_patch = None
        self.selected = country
        if country is not None:
            self._selected_patch = PathPatch(
                self._paths[country.code],
                facecolor=SELECTED_FILL, edgecolor=SELECTED_EDGE, linewidth=2.0, zorder=3,
            )
            self.ax.add_patch(self._selected_patch)
        self.draw_idle()
        self.countrySelected.emit(country)

    def zoom_to(self, country: Country, margin: float = 0.30) -> None:
        minx, miny, maxx, maxy = country.geometry.bounds
        dx = max(maxx - minx, 2.0) * margin
        dy = max(maxy - miny, 2.0) * margin
        self._set_view((minx - dx, maxx + dx), (miny - dy, maxy + dy))

    def reset_view(self) -> None:
        self._set_view(WORLD_XLIM, WORLD_YLIM)

    # ----- Points -----------------------------------------------------------

    def add_point(self, lon: float, lat: float, color: str | None = None) -> MapPoint:
        country = self.atlas.country_at(lon, lat)
        point = MapPoint(lon, lat, color or self.point_color, country.name if country else None)
        self.points.append(point)
        self._point_artists.append(self._draw_point(point))
        self.draw_idle()
        self.pointsChanged.emit()
        return point

    def remove_point(self, index: int) -> None:
        self.points.pop(index)
        for artist in self._point_artists.pop(index):
            artist.remove()
        self.draw_idle()
        self.pointsChanged.emit()

    def clear_points(self) -> None:
        for artists in self._point_artists:
            for artist in artists:
                artist.remove()
        self.points.clear()
        self._point_artists.clear()
        self.draw_idle()
        self.pointsChanged.emit()

    # ----- Échantillonnage --------------------------------------------------

    def visible_bounds(self) -> tuple[float, float, float, float]:
        self.ax.apply_aspect()
        (x0, x1), (y0, y1) = self.ax.get_xlim(), self.ax.get_ylim()
        return x0, y0, x1, y1

    def sample_view(self, n: int, target: Country) -> LabeledSample:
        """Tire n points additionnels dans la vue visible et les affiche en ✕ colorés selon leur classe."""
        new_batch = sample_view(self.atlas, self.visible_bounds(), n, target)
        if self.sample is not None and len(self.sample) > 0:
            self.sample = LabeledSample.concat(self.sample, new_batch)
        else:
            self.sample = new_batch

        self._remove_sample_artists()
        for k, (name, color) in enumerate(zip(self.sample.class_names, SAMPLE_COLORS)):
            mask = self.sample.labels == k
            self._sample_artists.append(self.ax.scatter(
                self.sample.lons[mask], self.sample.lats[mask],
                marker="x", s=20, linewidths=1.2, color=color, alpha=0.5, zorder=4,
                label=f"{name} ({int(mask.sum())})",
            ))
        self._sample_artists.append(self.ax.legend(loc="upper right", fontsize=9, framealpha=0.9))
        self.draw_idle()
        self.sampleChanged.emit(self.sample)
        return self.sample

    def clear_sample(self) -> None:
        self._remove_sample_artists()
        self.sample = None
        self.draw_idle()
        self.sampleChanged.emit(None)

    def get_manual_sample(self, target: Country) -> LabeledSample | None:
        """Retourne les points manuels sous forme de LabeledSample étiqueté par rapport à target."""
        if not self.points:
            return None
        lons = np.array([p.lon for p in self.points], dtype=float)
        lats = np.array([p.lat for p in self.points], dtype=float)
        return label_points(self.atlas, lons, lats, target)

    def get_training_sample(self, target: Country) -> LabeledSample | None:
        """Retourne l'union des points manuels et des points échantillonnés dans la vue."""
        manual = self.get_manual_sample(target)
        return LabeledSample.concat(manual, self.sample)

    def _remove_sample_artists(self) -> None:
        for artist in self._sample_artists:
            artist.remove()
        self._sample_artists.clear()

    # ----- Frontière algébrique / ML ----------------------------------------

    def set_decision_boundary(self, evaluator) -> None:
        """Définit la fonction d'évaluation (lon_2d, lat_2d) -> (values, is_boolean) et trace la frontière."""
        self._boundary_evaluator = evaluator
        self.redraw_decision_boundary()

    def clear_decision_boundary(self) -> None:
        self._boundary_evaluator = None
        self._remove_boundary_artists()
        self.draw_idle()

    def redraw_decision_boundary(self) -> None:
        self._remove_boundary_artists()
        if self._boundary_evaluator is None:
            self.draw_idle()
            return

        min_lon, min_lat, max_lon, max_lat = self.visible_bounds()
        grid_n = 90
        lons = np.linspace(min_lon, max_lon, grid_n)
        lats = np.linspace(min_lat, max_lat, grid_n)
        lon_grid, lat_grid = np.meshgrid(lons, lats)

        try:
            values, is_boolean = self._boundary_evaluator(lon_grid, lat_grid)
        except Exception:
            self.draw_idle()
            return

        z = np.where(values, 1.0, -1.0) if is_boolean else np.asarray(values, dtype=float)

        # Zone solution remplie en vert translucide
        try:
            cf = self.ax.contourf(
                lon_grid, lat_grid, z,
                levels=[0.0, np.inf],
                colors=["#10b981"],
                alpha=0.18,
                zorder=3,
            )
            self._boundary_artists.append(cf)
        except Exception:
            pass

        # Ligne de démarcation de la frontière f(x, y) = 0
        try:
            cs = self.ax.contour(
                lon_grid, lat_grid, z,
                levels=[0.0],
                colors=["#047857"],
                linewidths=2.4,
                zorder=4,
            )
            self._boundary_artists.append(cs)
        except Exception:
            pass

        self.draw_idle()

    def _remove_boundary_artists(self) -> None:
        for artist in self._boundary_artists:
            try:
                artist.remove()
            except Exception:
                pass
        self._boundary_artists.clear()

    def set_labels_visible(self, visible: bool) -> None:
        self.show_labels = visible
        for _, label in self._point_artists:
            label.set_visible(visible)
        self.draw_idle()

    # ----- Événements souris ------------------------------------------------

    def _toolbar_busy(self) -> bool:
        """Vrai si l'outil pan/zoom de la barre matplotlib est actif."""
        return self.toolbar is not None and self.toolbar.mode.name != "NONE"

    def _on_click(self, event: MouseEvent) -> None:
        if event.inaxes is not self.ax or event.button != MouseButton.LEFT or self._toolbar_busy():
            return
        if event.dblclick:
            if self.selected is not None:
                self.zoom_to(self.selected)
            return
        if self.mode is MapMode.ADD_POINT:
            self.add_point(event.xdata, event.ydata)
        else:
            self.select_country(self.atlas.country_at(event.xdata, event.ydata))

    def _on_scroll(self, event: MouseEvent) -> None:
        if event.inaxes is not self.ax:
            return
        factor = 1 / ZOOM_STEP if event.button == "up" else ZOOM_STEP
        x, y = event.xdata, event.ydata
        x0, x1 = self.ax.get_xlim()
        y0, y1 = self.ax.get_ylim()
        self._set_view(
            (x - (x - x0) * factor, x + (x1 - x) * factor),
            (y - (y - y0) * factor, y + (y1 - y) * factor),
        )

    def _on_motion(self, event: MouseEvent) -> None:
        if event.inaxes is not self.ax:
            self.cursorMoved.emit(None)
            return
        country = self.atlas.country_at(event.xdata, event.ydata)
        self.cursorMoved.emit((event.xdata, event.ydata, country))

    def _set_view(self, xlim: tuple[float, float], ylim: tuple[float, float]) -> None:
        """Change la vue en l'enregistrant dans l'historique de la barre d'outils (Précédent/Suivant)."""
        if self.toolbar is not None and self.toolbar._nav_stack() is None:
            self.toolbar.push_current()
        self.ax.set_xlim(*xlim)
        self.ax.set_ylim(*ylim)
        if self.toolbar is not None:
            self.toolbar.push_current()
        if self._boundary_evaluator is not None:
            self.redraw_decision_boundary()
        else:
            self.draw_idle()

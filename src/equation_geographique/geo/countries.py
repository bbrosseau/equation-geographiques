"""Chargement des frontières des pays (Natural Earth) et recherche géographique."""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path

import numpy as np
import shapely
from shapely import STRtree
from shapely.geometry import MultiPolygon, Point, Polygon, shape
from shapely.geometry.base import BaseGeometry
from shapely.geometry.polygon import orient

import sys

from equation_geographique.geo.coords import wrap_lon

DATA_DIR = (
    Path(sys._MEIPASS) / "data"
    if hasattr(sys, "_MEIPASS")
    else Path(__file__).resolve().parent.parent / "data"
)
DATASET_50M = DATA_DIR / "ne_50m_admin_0_countries.geojson"
DATASET_110M = DATA_DIR / "ne_110m_admin_0_countries.geojson"


@dataclass(frozen=True)
class Country:
    code: str
    name: str
    name_en: str
    continent: str
    population: int
    map_color: int
    geometry: BaseGeometry

    @property
    def polygons(self) -> list[Polygon]:
        """Polygones du pays, extérieur anti-horaire et trous horaires."""
        geom = self.geometry
        parts = list(geom.geoms) if isinstance(geom, MultiPolygon) else [geom]
        return [orient(p, sign=1.0) for p in parts]

    def rings(self) -> list[np.ndarray]:
        """Tous les anneaux (extérieurs et trous) en tableaux (N, 2) de (lon, lat)."""
        rings: list[np.ndarray] = []
        for poly in self.polygons:
            rings.append(np.asarray(poly.exterior.coords))
            rings.extend(np.asarray(hole.coords) for hole in poly.interiors)
        return rings

    @property
    def vertex_count(self) -> int:
        return sum(len(r) - 1 for r in self.rings())

    @property
    def lon_extent(self) -> tuple[float, float]:
        """Plus petit intervalle (ouest, est) de longitudes couvrant le pays.

        Pour un pays à cheval sur ±180° (Nouvelle-Zélande, Fidji, Russie…), l'intervalle sort
        de [-180, 180] ; il est placé de façon à contenir `center`, qui reste dans [-180, 180].
        """
        intervals = sorted((p.bounds[0], p.bounds[2]) for p in self.polygons)
        merged: list[list[float]] = []
        for west, east in intervals:
            if merged and west <= merged[-1][1]:
                merged[-1][1] = max(merged[-1][1], east)
            else:
                merged.append([west, east])
        # Le pays occupe tout sauf le plus grand vide entre ses parties, en faisant le tour du globe.
        west, east = merged[0][0], merged[-1][1]
        largest_gap = merged[0][0] + 360.0 - merged[-1][1]
        for left, right in zip(merged, merged[1:]):
            gap = right[0] - left[1]
            if gap > largest_gap:
                largest_gap = gap
                west, east = right[0], left[1] + 360.0
        if self.center[0] < west:
            west, east = west - 360.0, east - 360.0
        return west, east

    @property
    def view_bounds(self) -> tuple[float, float, float, float]:
        """(min_lon, min_lat, max_lon, max_lat) avec les longitudes de `lon_extent`."""
        west, east = self.lon_extent
        _, min_lat, _, max_lat = self.geometry.bounds
        return west, min_lat, east, max_lat

    @property
    def center(self) -> tuple[float, float]:
        """Point garanti à l'intérieur du pays, en (lon, lat)."""
        p = self.geometry.representative_point()
        return p.x, p.y


class CountryAtlas:
    """Collection de pays avec un index spatial pour trouver le pays sous un point."""

    def __init__(self, countries: list[Country]):
        self.countries = countries
        self._tree = STRtree([c.geometry for c in countries])

    @classmethod
    def load(cls, path: Path = DATASET_50M) -> CountryAtlas:
        with open(path, encoding="utf-8") as f:
            data = json.load(f)
        countries = [_country_from_feature(feat) for feat in data["features"]]
        countries.sort(key=lambda c: c.name)
        return cls(countries)

    def country_at(self, lon: float, lat: float) -> Country | None:
        hits = self._tree.query(Point(float(wrap_lon(lon)), lat), predicate="intersects")
        return self.countries[int(hits[0])] if len(hits) else None

    def country_indices_at(self, lons: np.ndarray, lats: np.ndarray) -> np.ndarray:
        """Indice dans `countries` du pays sous chaque point, -1 pour l'océan."""
        points = shapely.points(wrap_lon(lons), lats)
        point_idx, country_idx = self._tree.query(points, predicate="intersects")
        result = np.full(len(points), -1, dtype=int)
        result[point_idx] = country_idx
        return result

    def by_code(self, code: str) -> Country:
        for country in self.countries:
            if country.code == code:
                return country
        raise KeyError(f"Pays inconnu : {code}")

    def __len__(self) -> int:
        return len(self.countries)


def _country_from_feature(feature: dict) -> Country:
    props = feature["properties"]
    return Country(
        code=props["ADM0_A3"],
        name=props.get("NAME_FR") or props["NAME"],
        name_en=props["NAME"],
        continent=props.get("CONTINENT", ""),
        population=int(props.get("POP_EST") or 0),
        map_color=int(props.get("MAPCOLOR7") or 1),
        geometry=shape(feature["geometry"]),
    )

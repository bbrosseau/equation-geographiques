"""Points placés par l'utilisateur sur la carte."""

from __future__ import annotations

from dataclasses import dataclass

from mireille_tuto.geo.coords import format_coords


@dataclass
class MapPoint:
    lon: float
    lat: float
    color: str
    country: str | None

    @property
    def country_label(self) -> str:
        return self.country or "Océan"

    @property
    def label(self) -> str:
        return f"{self.country_label}\n{format_coords(self.lon, self.lat)}"

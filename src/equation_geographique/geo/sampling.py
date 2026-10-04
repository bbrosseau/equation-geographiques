"""Échantillonnage de points aléatoires sur la carte et étiquetage par classe."""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np

from equation_geographique.geo.countries import Country, CountryAtlas

WATER, TARGET, OTHER_LAND = 0, 1, 2


@dataclass(frozen=True)
class LabeledSample:
    """Points (lon, lat) avec une classe : 0 = eau, 1 = pays cible, 2 = autre pays."""

    lons: np.ndarray
    lats: np.ndarray
    labels: np.ndarray
    class_names: tuple[str, str, str]

    @property
    def X(self) -> np.ndarray:
        """Caractéristiques (N, 2) : longitude, latitude."""
        return np.column_stack([self.lons, self.lats])

    @property
    def y(self) -> np.ndarray:
        return self.labels

    def counts(self) -> dict[str, int]:
        return {name: int(np.sum(self.labels == k)) for k, name in enumerate(self.class_names)}

    def __len__(self) -> int:
        return len(self.labels)

    @classmethod
    def concat(cls, *samples: LabeledSample | None) -> LabeledSample | None:
        """Combine plusieurs LabeledSample en un seul."""
        valid = [s for s in samples if s is not None and len(s) > 0]
        if not valid:
            return None
        if len(valid) == 1:
            return valid[0]
        lons = np.concatenate([s.lons for s in valid])
        lats = np.concatenate([s.lats for s in valid])
        labels = np.concatenate([s.labels for s in valid])
        return cls(lons=lons, lats=lats, labels=labels, class_names=valid[0].class_names)


def sample_uniform(
    bounds: tuple[float, float, float, float], n: int, rng: np.random.Generator | None = None
) -> tuple[np.ndarray, np.ndarray]:
    """Tire n points uniformément dans (min_lon, min_lat, max_lon, max_lat).

    Les longitudes ne sont pas bornées (la carte se répète au-delà de ±180°) ; les latitudes
    restent limitées aux pôles.
    """
    rng = rng or np.random.default_rng()
    min_lon, min_lat, max_lon, max_lat = bounds
    min_lat, max_lat = max(min_lat, -90.0), min(max_lat, 90.0)
    return rng.uniform(min_lon, max_lon, n), rng.uniform(min_lat, max_lat, n)


def label_points(atlas: CountryAtlas, lons: np.ndarray, lats: np.ndarray, target: Country) -> LabeledSample:
    indices = atlas.country_indices_at(lons, lats)
    target_index = atlas.countries.index(target)
    labels = np.full(len(indices), OTHER_LAND, dtype=int)
    labels[indices == -1] = WATER
    labels[indices == target_index] = TARGET
    return LabeledSample(lons, lats, labels, ("eau", target.name.lower(), "autre pays"))


def sample_view(
    atlas: CountryAtlas,
    bounds: tuple[float, float, float, float],
    n: int,
    target: Country,
    rng: np.random.Generator | None = None,
) -> LabeledSample:
    lons, lats = sample_uniform(bounds, n, rng)
    return label_points(atlas, lons, lats, target)

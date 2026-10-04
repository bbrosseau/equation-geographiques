"""Mise en forme des coordonnées géographiques."""

import numpy as np


def wrap_lon(lon):
    """Ramène une longitude (ou un tableau) dans [-180, 180[ : la carte se répète tous les 360°."""
    return (np.asarray(lon, dtype=float) + 180.0) % 360.0 - 180.0


def format_lat(lat: float, decimals: int = 2) -> str:
    return f"{abs(lat):.{decimals}f}° {'N' if lat >= 0 else 'S'}"


def format_lon(lon: float, decimals: int = 2) -> str:
    lon = float(wrap_lon(lon))
    return f"{abs(lon):.{decimals}f}° {'E' if lon >= 0 else 'O'}"


def format_coords(lon: float, lat: float, decimals: int = 2) -> str:
    return f"{format_lat(lat, decimals)}, {format_lon(lon, decimals)}"

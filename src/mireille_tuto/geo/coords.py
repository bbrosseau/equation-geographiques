"""Mise en forme des coordonnées géographiques."""


def format_lat(lat: float, decimals: int = 2) -> str:
    return f"{abs(lat):.{decimals}f}° {'N' if lat >= 0 else 'S'}"


def format_lon(lon: float, decimals: int = 2) -> str:
    return f"{abs(lon):.{decimals}f}° {'E' if lon >= 0 else 'O'}"


def format_coords(lon: float, lat: float, decimals: int = 2) -> str:
    return f"{format_lat(lat, decimals)}, {format_lon(lon, decimals)}"

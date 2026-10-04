import pytest

from equation_geographique.geo import CountryAtlas, MapPoint, format_coords
from equation_geographique.geo.countries import DATASET_110M


@pytest.fixture(scope="module")
def atlas() -> CountryAtlas:
    return CountryAtlas.load(DATASET_110M)


@pytest.mark.parametrize(
    ("lon", "lat", "code"),
    [
        (-73.57, 45.50, "CAN"),  # Montréal
        (2.35, 48.86, "FRA"),  # Paris
        (139.69, 35.69, "JPN"),  # Tokyo
        (-47.88, -15.79, "BRA"),  # Brasília
    ],
)
def test_country_at(atlas, lon, lat, code):
    country = atlas.country_at(lon, lat)
    assert country is not None and country.code == code


def test_ocean_has_no_country(atlas):
    assert atlas.country_at(-30.0, 30.0) is None


def test_french_names(atlas):
    assert atlas.country_at(10.45, 51.17).name == "Allemagne"


def test_format_coords():
    assert format_coords(-73.567, 45.5017) == "45.50° N, 73.57° O"
    assert format_coords(151.21, -33.87) == "33.87° S, 151.21° E"


def test_point_label():
    point = MapPoint(lon=-73.57, lat=45.50, color="#ff0000", country="Canada")
    assert point.label == "Canada\n45.50° N, 73.57° O"
    assert MapPoint(0, 0, "#000", None).country_label == "Océan"

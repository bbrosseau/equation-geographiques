import numpy as np
import pytest

from mireille_tuto.geo.countries import DATASET_110M, CountryAtlas
from mireille_tuto.geo.sampling import OTHER_LAND, TARGET, WATER, label_points, sample_uniform, sample_view


@pytest.fixture(scope="module")
def atlas() -> CountryAtlas:
    return CountryAtlas.load(DATASET_110M)


def test_label_points(atlas):
    japan = atlas.by_code("JPN")
    lons = np.array([139.69, 150.0, 116.40])  # Tokyo, Pacifique, Pékin
    lats = np.array([35.69, 30.0, 39.90])
    sample = label_points(atlas, lons, lats, japan)
    assert sample.labels.tolist() == [TARGET, WATER, OTHER_LAND]
    assert sample.class_names == ("eau", "japon", "autre pays")


def test_sample_uniform_crosses_antimeridian_but_not_poles():
    lons, lats = sample_uniform((170.0, -95.0, 200.0, 10.0), 1000, np.random.default_rng(0))
    assert lons.min() >= 170.0 and lons.max() <= 200.0 and lons.max() > 180.0
    assert lats.min() >= -90.0 and lats.max() <= 10.0


def test_points_beyond_antimeridian_are_labeled(atlas):
    fiji = atlas.by_code("FJI")
    lon, lat = fiji.center
    assert atlas.country_at(lon + 360.0, lat) is fiji
    assert atlas.country_at(lon - 360.0, lat) is fiji


@pytest.mark.parametrize("code", ["NZL", "FJI", "RUS", "USA"])
def test_lon_extent_of_countries_crossing_antimeridian(atlas, code):
    country = atlas.by_code(code)
    west, east = country.lon_extent
    assert east - west < 200.0
    assert west <= country.center[0] <= east
    sample = sample_view(atlas, country.view_bounds, 3000, country, np.random.default_rng(1))
    assert np.sum(sample.labels == TARGET) > 0


def test_sample_view_around_japan(atlas):
    japan = atlas.by_code("JPN")
    sample = sample_view(atlas, japan.geometry.bounds, 2000, japan, np.random.default_rng(42))
    counts = sample.counts()
    assert len(sample) == 2000 and sum(counts.values()) == 2000
    assert counts["eau"] > 0 and counts["japon"] > 0
    assert sample.X.shape == (2000, 2)


def test_labeled_sample_concat(atlas):
    from mireille_tuto.geo.sampling import LabeledSample

    japan = atlas.by_code("JPN")
    s1 = label_points(atlas, np.array([139.69]), np.array([35.69]), japan)
    s2 = label_points(atlas, np.array([150.0, 116.40]), np.array([30.0, 39.90]), japan)

    # Concat s1 and s2
    combined = LabeledSample.concat(s1, s2)
    assert combined is not None
    assert len(combined) == 3
    assert combined.labels.tolist() == [TARGET, WATER, OTHER_LAND]
    assert np.allclose(combined.lons, [139.69, 150.0, 116.40])
    assert np.allclose(combined.lats, [35.69, 30.0, 39.90])

    # Concat with None and empty
    assert LabeledSample.concat(None, s1) is s1
    assert LabeledSample.concat(s2, None) is s2
    assert LabeledSample.concat(None, None) is None


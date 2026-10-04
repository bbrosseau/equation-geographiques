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


def test_sample_uniform_stays_in_bounds_and_on_globe():
    lons, lats = sample_uniform((170.0, -95.0, 200.0, 10.0), 1000, np.random.default_rng(0))
    assert lons.min() >= 170.0 and lons.max() <= 180.0
    assert lats.min() >= -90.0 and lats.max() <= 10.0


def test_sample_view_around_japan(atlas):
    japan = atlas.by_code("JPN")
    sample = sample_view(atlas, japan.geometry.bounds, 2000, japan, np.random.default_rng(42))
    counts = sample.counts()
    assert len(sample) == 2000 and sum(counts.values()) == 2000
    assert counts["eau"] > 0 and counts["japon"] > 0
    assert sample.X.shape == (2000, 2)

import os

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import pytest
from PySide6.QtWidgets import QApplication

from mireille_tuto.geo.countries import DATASET_110M, CountryAtlas
from mireille_tuto.ui import MainWindow


@pytest.fixture(scope="module")
def window():
    app = QApplication.instance() or QApplication([])
    win = MainWindow(CountryAtlas.load(DATASET_110M))
    win.show()
    yield win
    win.close()
    app.processEvents()


def test_starts_centered_on_japan(window):
    min_lon, min_lat, max_lon, max_lat = window.map.visible_bounds()
    lon, lat = window.focus_country.center
    assert min_lon < lon < max_lon and min_lat < lat < max_lat
    assert max_lon - min_lon < 90


def test_sample_view_updates_panel(window):
    sample = window.map.sample_view(300, window.focus_country)
    assert len(sample) == 300
    assert "japon" in window.sample_info.text()
    window.map.clear_sample()
    assert window.map.sample is None


def test_select_country_updates_panel(window):
    canada = window.map.atlas.country_at(-100, 60)
    window.map.select_country(canada)
    assert "Canada" in window.country_info.text()
    assert window.zoom_button.isEnabled()


def test_add_and_remove_points(window):
    window.map.add_point(2.35, 48.86, "#2a9d8f")
    window.map.add_point(-30.0, 30.0)
    assert window.points_list.count() == 2
    assert window.map.points[0].country == "France"
    assert window.map.points[1].country is None

    window.map.remove_point(0)
    assert window.points_list.count() == 1
    window.map.clear_points()
    assert window.points_list.count() == 0

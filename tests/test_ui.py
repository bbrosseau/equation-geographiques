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

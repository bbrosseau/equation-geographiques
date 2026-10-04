"""Point d'entrée de l'application graphique."""

from __future__ import annotations

import argparse
import sys

from PySide6.QtWidgets import QApplication

from mireille_tuto.geo.countries import DATASET_50M, DATASET_110M, CountryAtlas
from mireille_tuto.ui import MainWindow


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="mireille-tuto")
    parser.add_argument(
        "--simple", action="store_true",
        help="frontières moins détaillées (1:110m), plus rapides à afficher",
    )
    args, qt_args = parser.parse_known_args(argv if argv is not None else sys.argv[1:])

    app = QApplication([sys.argv[0], *qt_args])
    app.setApplicationName("Mireille Tuto")

    atlas = CountryAtlas.load(DATASET_110M if args.simple else DATASET_50M)
    window = MainWindow(atlas)
    window.show()
    return app.exec()

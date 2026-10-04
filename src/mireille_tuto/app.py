"""Point d'entrée de l'application graphique."""

from __future__ import annotations

import argparse
import sys

from PySide6.QtWidgets import QApplication

from mireille_tuto.geo.countries import DATASET_50M, DATASET_110M, CountryAtlas
from mireille_tuto.ui import MainWindow, get_app_icon


def main(argv: list[str] | None = None) -> int:
    if sys.platform == "win32":
        try:
            import ctypes
            ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID("mireille_tuto.app")
        except Exception:
            pass

    parser = argparse.ArgumentParser(prog="mireille-tuto")
    parser.add_argument(
        "--simple", action="store_true",
        help="frontières moins détaillées (1:110m), plus rapides à afficher",
    )
    parser.add_argument(
        "--pays", default="JPN", metavar="CODE",
        help="code ADM0_A3 du pays centré au démarrage et utilisé pour l'échantillon (défaut : JPN)",
    )
    args, qt_args = parser.parse_known_args(argv if argv is not None else sys.argv[1:])

    app = QApplication([sys.argv[0], *qt_args])
    app.setApplicationName("Mireille Tuto")
    app.setWindowIcon(get_app_icon())

    atlas = CountryAtlas.load(DATASET_110M if args.simple else DATASET_50M)
    window = MainWindow(atlas, focus_code=args.pays.upper())
    window.show()
    return app.exec()

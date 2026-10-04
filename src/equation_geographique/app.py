"""Point d'entrée de l'application graphique."""

from __future__ import annotations

import argparse
import signal
import sys

from PySide6.QtCore import QTimer
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
        "--pays", default=None, metavar="CODE",
        help="code ADM0_A3 d'un pays à présélectionner au démarrage (ex. : CAN)",
    )
    args, qt_args = parser.parse_known_args(argv if argv is not None else sys.argv[1:])

    app = QApplication([sys.argv[0], *qt_args])
    app.setApplicationName("Mireille Tuto")
    app.setWindowIcon(get_app_icon())

    # Ctrl+C dans la console ferme l'application. La boucle Qt ne rend jamais la main à
    # Python d'elle-même : un minuteur la réveille régulièrement pour traiter le signal.
    signal.signal(signal.SIGINT, lambda *_: app.quit())
    sigint_timer = QTimer()
    sigint_timer.timeout.connect(lambda: None)
    sigint_timer.start(200)

    atlas = CountryAtlas.load(DATASET_110M if args.simple else DATASET_50M)
    window = MainWindow(atlas, focus_code=args.pays.upper() if args.pays else None)
    # Certains gestionnaires de fenêtres (Linux/Wayland, ChromeOS) ignorent la demande de
    # maximisation : on remplit d'abord l'espace disponible de l'écran pour que la fenêtre
    # reste grande et entièrement visible, même sur un petit écran.
    screen = window.screen() or app.primaryScreen()
    if screen is not None:
        window.setGeometry(screen.availableGeometry())
    window.showMaximized()
    return app.exec()

"""
IAD France Property Estimator — launch script.

Run this file to start the desktop application:

    python run_app.py

Or to run as a web app (accessible in a browser):

    python run_app.py --web

Author: [Twoje Imię i Nazwisko]
License: MIT
"""

import sys
from pathlib import Path
import flet as ft

ROOT = Path(__file__).parent
sys.path.insert(0, str(ROOT / "src"))

from app.main import main

if __name__ == "__main__":
    web_mode = "--web" in sys.argv
    ft.app(
        target=main,
        view=ft.AppView.WEB_BROWSER if web_mode else ft.AppView.FLET_APP,
    )

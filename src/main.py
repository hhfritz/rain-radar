import asyncio
import logging
from datetime import datetime, timezone

import flet as ft
import flet_geolocator as fgeo

from rainviewer_api import available_radar_frames

# flet_webview nur importieren, wenn wir NICHT im Browser laufen
# (Verhindert das lautlose Abstürzen des Pyodide Workers)
try:
    import flet_webview as fweb

    HAS_WEBVIEW = True
except ImportError:
    HAS_WEBVIEW = False

LOG_LEVEL = logging.INFO
logging.basicConfig(format="%(levelname)s %(name)s: %(message)s")
log = logging.getLogger("app.main")


async def main(page: ft.Page):
    page.title = "Rain Radar"
    page.theme_mode = ft.ThemeMode.SYSTEM

    geolocator = fgeo.Geolocator()
    page.services.append(geolocator)  # In Flet 1.0 notwendig

    status = ft.Text("Checking location access…")
    coordinates = ft.Text("")
    frame_label = ft.Text("")
    refresh_button = ft.Button(content=ft.Text("Check location and refresh"))
    play_button = ft.Button(content=ft.Text("Play"), disabled=True)

    frame_slider = ft.Slider(
        value=0,
        min=0,
        max=1,
        divisions=1,
        disabled=True,
        visible=False,
    )

    is_web = page.web

    if is_web or not HAS_WEBVIEW:
        map_area = ft.Container(
            content=ft.Text("Kartenansicht im Web wird geladen..."),
            expand=True,
        )
        webview = None
    else:
        webview = fweb.WebView(expand=True)
        map_area = webview

    frames: list[dict] = []
    observed_count = 0
    current_frame = 0
    playback_active = False

    async def refresh_location(e=None):
        status.value = "Anwendung bereit."
        page.update()

    refresh_button.on_click = refresh_location

    page.add(
        ft.SafeArea(
            expand=True,
            content=ft.Column(
                [
                    ft.Text("Rain Radar", size=24, weight="bold"),
                    status,
                    coordinates,
                    refresh_button,
                    map_area,
                ],
                expand=True,
            ),
        )
    )

    if is_web:
        status.value = "Web App erfolgreich gestartet!"
        page.update()


# Richtiger Starter für Web/Pyodide
ft.app(target=main)
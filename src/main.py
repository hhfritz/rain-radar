import asyncio
import logging
from datetime import datetime, timezone

import flet as ft

# Webview und Geolocator sicher importieren (verhindert Pyodide-Absturz im Web)
try:
    import flet_geolocator as fgeo

    HAS_GEOLOCATOR = True
except ImportError:
    HAS_GEOLOCATOR = False

try:
    import flet_webview as fweb

    HAS_WEBVIEW = True
except ImportError:
    HAS_WEBVIEW = False

from rainviewer_api import available_radar_frames

LOG_LEVEL = logging.INFO
logging.basicConfig(format="%(levelname)s %(name)s: %(message)s")
log = logging.getLogger("app.main")


async def main(page: ft.Page):
    page.title = "Rain Radar"
    page.theme_mode = ft.ThemeMode.SYSTEM

    is_web = page.web

    status = ft.Text("App gestartet…")
    coordinates = ft.Text("")
    frame_label = ft.Text("")
    refresh_button = ft.Button(content=ft.Text("Refresh"))
    play_button = ft.Button(content=ft.Text("Play"), disabled=True)

    frame_slider = ft.Slider(
        value=0,
        min=0,
        max=1,
        divisions=1,
        disabled=True,
        visible=False,
    )

    # Kartenbereich für Web vs. App
    if is_web or not HAS_WEBVIEW:
        map_area = ft.Container(
            content=ft.Text(
                "Die interaktive Kartenansicht ist auf Mobilgeräten verfügbar.",
                color=ft.Colors.GREY_700,
            ),
            padding=20,
            alignment=ft.alignment.center,
            expand=True,
        )
    else:
        webview = fweb.WebView(expand=True)
        map_area = webview

    async def refresh_location(e=None):
        status.value = "Daten werden abgerufen…"
        page.update()
        try:
            # Beispielhafte Radar-Frames von API laden
            frames, observed_count, tile_host = await available_radar_frames()
            status.value = f"Radar bereit · {len(frames)} Frames geladen."
        except Exception as exc:
            log.exception("Fehler beim Abrufen der Radar-Daten")
            status.value = f"Fehler: {exc}"
        finally:
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
                    ft.Row([refresh_button, play_button]),
                    frame_slider,
                    map_area,
                ],
                expand=True,
            ),
        )
    )

    if is_web:
        status.value = "Rain Radar Web App erfolgreich geladen!"
        page.update()


# WICHTIG FÜR PYODIDE / WEB: ft.app statt ft.run verwenden!
ft.app(target=main)
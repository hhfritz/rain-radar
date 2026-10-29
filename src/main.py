import asyncio
import logging
from datetime import datetime, timezone

import flet as ft
import flet_map as fm

from rainviewer_api import available_radar_frames

# Geolocator für Web-Abstürze absichern
try:
    import flet_geolocator as fgeo

    HAS_GEOLOCATOR = True
except ImportError:
    HAS_GEOLOCATOR = False

LOG_LEVEL = logging.INFO
logging.basicConfig(format="%(levelname)s %(name)s: %(message)s")
log = logging.getLogger("app.main")


async def main(page: ft.Page):
    page.title = "Rain Radar"
    page.theme_mode = ft.ThemeMode.SYSTEM

    status = ft.Text("Checking location access…")
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

    # Nativer Flet-Kartenbereich (funktioniert im Web & auf Android!)
    marker_layer = fm.MarkerLayer(markers=[])
    radar_tile_layer = fm.TileLayer(
        url_template="https://tile.openstreetmap.org/{z}/{x}/{y}.png",
        opacity=0.7,
    )

    map_control = fm.Map(
        expand=True,
        configuration=fm.MapConfiguration(
            initial_center=fm.MapLatitudeLongitude(48.7758, 9.1829),  # Stuttgart Default
            initial_zoom=8,
        ),
        layers=[
            fm.TileLayer(
                url_template="https://tile.openstreetmap.org/{z}/{x}/{y}.png",
                subdomains=["a", "b", "c"],
            ),
            radar_tile_layer,
            marker_layer,
        ],
    )

    frames: list[dict] = []
    tile_host_url = ""

    def update_radar_layer(index: int):
        if not frames or not tile_host_url:
            return
        frame = frames[index]
        # RainViewer Kacheln als Flet Map TileLayer setzen
        radar_tile_layer.url_template = (
            f"{tile_host_url}{frame['path']}/256/{{z}}/{{x}}/{{y}}/2/1_1.png"
        )
        frame_label.value = f"{index + 1}/{len(frames)}"
        page.update()

    async def refresh_location(e=None):
        nonlocal frames, tile_host_url
        status.value = "Radar-Daten werden geladen…"
        page.update()

        try:
            frames, observed_count, tile_host = await available_radar_frames()
            tile_host_url = tile_host.rstrip("/")
            if frames:
                update_radar_layer(observed_count - 1)
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
                    ft.Row([refresh_button, play_button, frame_label]),
                    frame_slider,
                    map_control,
                ],
                expand=True,
            ),
        )
    )

    # Initialer Start
    await refresh_location()


# Wichtig für Pyodide / WebAssembly
ft.app(target=main)
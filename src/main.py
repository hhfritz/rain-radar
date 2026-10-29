import asyncio
import logging
from datetime import datetime, timezone

import flet as ft
import flet_map as fm

from rainviewer_api import available_radar_frames

LOG_LEVEL = logging.INFO
logging.basicConfig(format="%(levelname)s %(name)s: %(message)s")
log = logging.getLogger("app.main")


async def main(page: ft.Page):
    page.title = "Rain Radar"
    page.theme_mode = ft.ThemeMode.SYSTEM

    status = ft.Text("Radar wird geladen…")
    frame_label = ft.Text("")
    refresh_button = ft.Button(content=ft.Text("Neu laden"))
    play_button = ft.Button(content=ft.Text("Play"), disabled=True)

    # Nativer Flet-Kartenbereich (funktioniert im Web und in Android)
    radar_tile_layer = fm.TileLayer(
        url_template="https://tile.openstreetmap.org/{z}/{x}/{y}.png",
        opacity=0.65,
    )

    map_control = fm.Map(
        expand=True,
        configuration=fm.MapConfiguration(
            initial_center=fm.MapLatitudeLongitude(48.7758, 9.1829),  # Standard-Koordinate
            initial_zoom=8,
        ),
        layers=[
            fm.TileLayer(
                url_template="https://tile.openstreetmap.org/{z}/{x}/{y}.png",
            ),
            radar_tile_layer,
        ],
    )

    frames: list[dict] = []
    tile_host_url = ""

    def update_radar_layer(index: int):
        if not frames or not tile_host_url:
            return
        frame = frames[index]
        # RainViewer Kacheln dynamisch in der Flet-Karte aktualisieren
        radar_tile_layer.url_template = (
            f"{tile_host_url}{frame['path']}/256/{{z}}/{{x}}/{{y}}/2/1_1.png"
        )
        frame_label.value = f"{index + 1}/{len(frames)}"
        page.update()

    async def refresh_location(e=None):
        nonlocal frames, tile_host_url
        status.value = "Lade RainViewer Radar-Daten…"
        page.update()

        try:
            frames, observed_count, tile_host = await available_radar_frames()
            tile_host_url = tile_host.rstrip("/")
            if frames:
                update_radar_layer(max(0, observed_count - 1))
                status.value = f"Radar bereit · {len(frames)} Frames geladen."
        except Exception as exc:
            log.exception("Fehler beim Abrufen der Radar-Daten")
            status.value = f"Fehler beim Laden: {exc}"
        finally:
            page.update()

    refresh_button.on_click = refresh_location

    page.add(
        ft.SafeArea(
            expand=True,
            content=ft.Column(
                [
                    ft.Text("Rain Radar", size=22, weight="bold"),
                    status,
                    ft.Row([refresh_button, play_button, frame_label]),
                    map_control,  # Rendert direkt auf GitHub Pages!
                ],
                expand=True,
            ),
        )
    )

    # Initialer Datenabruf
    await refresh_location()


# # Am Ende von src/main.py:
#
# if __name__ == "__main__":
#     if hasattr(ft, "app_async"):
#         ft.app_async(target=main)
#     elif hasattr(ft, "app") and callable(getattr(ft, "app")):
#         ft.app(target=main)
#     else:
#         # Flet 0.25+ / 1.0 WebAssembly Modulstruktur
#         try:
#             from flet.app import run_async
#             run_async(target=main)
#         except ImportError:
#             ft.run(main)
ft.run(main)
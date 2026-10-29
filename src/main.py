import asyncio
import logging
import flet as ft
import flet_map as fm

from rainviewer_api import available_radar_frames

# Versuche nativen Geolocator zu laden (für Android/iOS)
try:
    import flet_geolocator as fgeo

    HAS_NATIVE_GEO = True
except ImportError:
    HAS_NATIVE_GEO = False

LOG_LEVEL = logging.INFO
logging.basicConfig(format="%(levelname)s %(name)s: %(message)s")
log = logging.getLogger("app.main")


async def main(page: ft.Page):
    page.title = "Rain Radar"
    page.theme_mode = ft.ThemeMode.SYSTEM

    status = ft.Text("Ermittle Standort…")
    coordinates_text = ft.Text("")
    frame_label = ft.Text("")
    refresh_button = ft.Button(content=ft.Text("Standort aktualisieren"))
    play_button = ft.Button(content=ft.Text("Play"), disabled=True)

    # Standard-Koordinaten als Initial-Fallback (z. B. Stuttgart)
    current_lat = 48.7758
    current_lon = 9.1829

    # Radar-Kachelebene
    radar_tile_layer = fm.TileLayer(
        url_template="https://tile.openstreetmap.org/{z}/{x}/{y}.png",
        opacity=0.65,
    )

    # Marker-Ebene für den eigenen Standort
    location_marker_layer = fm.MarkerLayer(markers=[])

    # Flet Map Steuerung
    map_control = fm.Map(
        expand=True,
        initial_center=fm.MapLatitudeLongitude(current_lat, current_lon),
        initial_zoom=9,
        layers=[
            fm.TileLayer(
                url_template="https://tile.openstreetmap.org/{z}/{x}/{y}.png",
            ),
            radar_tile_layer,
            location_marker_layer,
        ],
    )

    frames: list[dict] = []
    tile_host_url = ""

    def update_location_marker(lat: float, lon: float):
        """Setzt einen roten Marker auf die eigenen Koordinaten."""
        location_marker_layer.markers = [
            fm.Marker(
                content=ft.Icon(ft.Icons.LOCATION_ON, color=ft.Colors.RED_600, size=30),
                coordinates=fm.MapLatitudeLongitude(lat, lon),
            )
        ]
        map_control.initial_center = fm.MapLatitudeLongitude(lat, lon)

    def update_radar_layer(index: int):
        if not frames or not tile_host_url:
            return
        frame = frames[index]
        radar_tile_layer.url_template = (
            f"{tile_host_url}{frame['path']}/256/{{z}}/{{x}}/{{y}}/2/1_1.png"
        )
        frame_label.value = f"{index + 1}/{len(frames)}"
        page.update()

    async def get_web_location() -> tuple[float, float] | None:
        """Fragt den Standort im Webbrowser über JavaScript ab."""
        try:
            # Löst die Geolocation-Anfrage im Browser aus
            js_code = """
            navigator.geolocation.getCurrentPosition(
                (pos) => {
                    window._userLat = pos.coords.latitude;
                    window._userLon = pos.coords.longitude;
                },
                (err) => {
                    window._geoError = err.message;
                }
            );
            """
            await page.exec_js(js_code)

            # Warten, bis der Browser die Koordinaten zurückliefert
            for _ in range(10):
                await asyncio.sleep(0.5)
                lat = await page.exec_js("window._userLat")
                lon = await page.exec_js("window._userLon")
                if lat is not None and lon is not None:
                    return float(lat), float(lon)
        except Exception as e:
            log.warning("Web Geolocation konnte nicht ausgeführt werden: %s", e)
        return None

    async def refresh_location(e=None):
        nonlocal frames, tile_host_url, current_lat, current_lon
        status.value = "Frage GPS-Standort ab…"
        refresh_button.disabled = True
        page.update()

        lat, lon = None, None

        # 1. Native Geolocation versuchen (Android App)
        if HAS_NATIVE_GEO and not page.web:
            try:
                geolocator = fgeo.Geolocator()
                if await geolocator.is_location_service_enabled():
                    pos = await geolocator.get_current_position()
                    lat, lon = float(pos.latitude), float(pos.longitude)
            except Exception as err:
                log.warning("Nativer Geolocator fehlgeschlagen: %s", err)

        # 2. Web Geolocation versuchen (Browser / GitHub Pages)
        if lat is None and page.web:
            status.value = "Bitte Standort-Freigabe im Browser bestätigen…"
            page.update()
            coords = await get_web_location()
            if coords:
                lat, lon = coords

        # Standort aktualisieren falls ermittelt
        if lat is not None and lon is not None:
            current_lat, current_lon = lat, lon
            coordinates_text.value = f"Standort: {current_lat:.4f}, {current_lon:.4f}"
            update_location_marker(current_lat, current_lon)
        else:
            coordinates_text.value = "Standort konnte nicht ermittelt werden (Nutze Standard)."

        # 3. RainViewer Daten laden
        status.value = "Lade Radar-Daten…"
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
            refresh_button.disabled = False
            page.update()

    refresh_button.on_click = refresh_location

    page.add(
        ft.SafeArea(
            expand=True,
            content=ft.Column(
                [
                    ft.Text("Rain Radar", size=22, weight="bold"),
                    status,
                    coordinates_text,
                    ft.Row([refresh_button, play_button, frame_label]),
                    map_control,
                ],
                expand=True,
            ),
        )
    )

    # Initialer Standort- & Radar-Abruf
    await refresh_location()


ft.run(main)
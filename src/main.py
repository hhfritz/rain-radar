import asyncio
import logging
from datetime import datetime, timezone

import flet as ft
import flet_geolocator as fgeo
import flet_webview as fweb

from map_view import leaflet_map_html
from rainviewer_api import available_radar_frames

LOG_LEVEL = logging.INFO
logging.basicConfig(format="%(levelname)s %(name)s: %(message)s")
logging.getLogger("app").setLevel(LOG_LEVEL)
log = logging.getLogger("app.main")


async def main(page: ft.Page):
    page.title = "Rain Radar"
    page.theme_mode = ft.ThemeMode.SYSTEM

    geolocator = fgeo.Geolocator()
    status = ft.Text("Checking location access…")
    coordinates = ft.Text("")
    frame_label = ft.Text("")
    refresh_button = ft.Button(content=ft.Text("Check location and refresh"))
    play_button = ft.Button(content=ft.Text("Play"), disabled=True)
    location_settings_button = ft.TextButton(
        content=ft.Text("Open location settings"), visible=False
    )
    app_settings_button = ft.TextButton(
        content=ft.Text("Open app settings"), visible=False
    )
    frame_slider = ft.Slider(
        value=0,
        min=0,
        max=1,
        divisions=1,
        disabled=True,
        visible=False,
    )

    is_web = page.web
    if is_web:
        map_area = ft.Container(
            content=ft.Text(
                "The interactive map and phone GPS are available in the Android app."
            ),
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

    def frame_description(index: int) -> str:
        frame = frames[index]
        timestamp = datetime.fromtimestamp(frame["time"], timezone.utc).strftime(
            "%Y-%m-%d %H:%M UTC"
        )
        return f"{frame['kind']} · {timestamp} · {index + 1}/{len(frames)}"

    async def show_frame(index: int):
        nonlocal current_frame
        if not frames:
            return
        current_frame = max(0, min(index, len(frames) - 1))
        frame_slider.value = current_frame
        frame_label.value = frame_description(current_frame)
        if webview is not None:
            await webview.run_javascript(value=f"window.setRadarFrame({current_frame});")
        page.update()

    async def change_frame(event):
        if playback_active:
            toggle_playback()
        await show_frame(round(event.control.value))

    frame_slider.on_change = change_frame

    async def playback_loop():
        index = 0
        try:
            while playback_active and frames:
                await show_frame(index)
                await asyncio.sleep(0.85)
                index = (index + 1) % len(frames)
        except Exception:
            log.exception("Radar frame playback failed")
            status.value = "Radar playback stopped because a frame could not be displayed."
        finally:
            if playback_active:
                toggle_playback()

    def toggle_playback():
        nonlocal playback_active
        if playback_active:
            playback_active = False
            play_button.content = ft.Text("Play")
        elif len(frames) > 1:
            playback_active = True
            play_button.content = ft.Text("Pause")
            asyncio.create_task(playback_loop())
        page.update()

    play_button.on_click = toggle_playback

    async def open_location_settings():
        await geolocator.open_location_settings()

    async def open_app_settings():
        await geolocator.open_app_settings()

    location_settings_button.on_click = open_location_settings
    app_settings_button.on_click = open_app_settings

    async def refresh_location():
        nonlocal frames, observed_count, current_frame, playback_active
        playback_active = False
        play_button.content = ft.Text("Play")
        play_button.disabled = True
        frame_slider.disabled = True
        frame_slider.visible = False
        frame_label.value = ""
        frames = []
        location_settings_button.visible = False
        app_settings_button.visible = False
        refresh_button.disabled = True
        coordinates.value = ""
        status.value = "Checking whether location services are enabled…"
        page.update()

        try:
            if is_web:
                status.value = "Open this app on Android to use phone GPS and the map."
                return

            if not await geolocator.is_location_service_enabled():
                status.value = "Location services are off. Turn on GPS, then refresh."
                location_settings_button.visible = True
                return

            permission = await geolocator.get_permission_status()
            if permission in (
                fgeo.GeolocatorPermissionStatus.DENIED,
                fgeo.GeolocatorPermissionStatus.UNABLE_TO_DETERMINE,
            ):
                status.value = "Requesting location permission…"
                page.update()
                permission = await geolocator.request_permission()

            if permission == fgeo.GeolocatorPermissionStatus.DENIED_FOREVER:
                status.value = "Location permission is blocked. Allow it in app settings."
                app_settings_button.visible = True
                return
            if permission not in (
                fgeo.GeolocatorPermissionStatus.WHILE_IN_USE,
                fgeo.GeolocatorPermissionStatus.ALWAYS,
            ):
                status.value = "Location permission was not granted. Allow it to continue."
                return

            status.value = "Getting your current position…"
            page.update()
            position = await geolocator.get_current_position()
            latitude = float(position.latitude)
            longitude = float(position.longitude)
            accuracy = position.accuracy
            coordinates.value = (
                f"{latitude:.5f}, {longitude:.5f}"
                + (f"  ·  accuracy {float(accuracy):.0f} m" if accuracy is not None else "")
            )

            status.value = "Loading available RainViewer radar frames…"
            page.update()
            frames, observed_count, tile_host = await available_radar_frames()
            current_frame = max(0, observed_count - 1)

            if webview is not None:
                html = leaflet_map_html(
                    latitude, longitude, frames, current_frame, tile_host
                )
                await webview.load_html(
                    value=html, base_url="https://www.rainviewer.com/"
                )

            frame_slider.max = max(1, len(frames) - 1)
            frame_slider.divisions = max(1, len(frames) - 1)
            frame_slider.value = current_frame
            frame_slider.disabled = len(frames) < 2
            frame_slider.visible = len(frames) > 1
            play_button.disabled = len(frames) < 2
            frame_label.value = frame_description(current_frame)
            nowcast_count = len(frames) - observed_count
            status.value = (
                f"Radar ready · {observed_count} observed frame(s), "
                f"{nowcast_count} nowcast frame(s)"
            )
            log.info(
                "Loaded location %.5f, %.5f and %d radar frames",
                latitude,
                longitude,
                len(frames),
            )
        except Exception as exc:
            log.exception("Unable to load location and rain radar")
            status.value = f"Could not load the map or radar: {exc}"
        finally:
            refresh_button.disabled = False
            page.update()

    refresh_button.on_click = refresh_location

    page.add(
        ft.SafeArea(
            expand=True,
            content=ft.Column(
                [
                    ft.Text("Rain Radar"),
                    status,
                    coordinates,
                    ft.Row(
                        [refresh_button, location_settings_button, app_settings_button],
                        wrap=True,
                    ),
                    ft.Row([play_button, frame_label], wrap=True, visible=not is_web),
                    frame_slider,
                    map_area,
                ],
                expand=True,
            ),
        )
    )

    if is_web:
        status.value = "Open this app on Android to use phone GPS and the interactive radar map."
        refresh_button.disabled = False
        page.update()
    else:
        await refresh_location()


ft.run(main)

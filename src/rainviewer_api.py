import logging

import httpx2 as httpx

log = logging.getLogger(f"app.{__name__}")
WEATHER_MAPS_URL = "https://api.rainviewer.com/public/weather-maps.json"


async def available_radar_frames() -> tuple[list[dict], int, str]:
    """Fetch available observed radar frames and any RainViewer nowcast frames."""
    async with httpx.AsyncClient(timeout=20) as client:
        response = await client.get(WEATHER_MAPS_URL)
        response.raise_for_status()
        payload = response.json()

    radar = payload.get("radar", {})

    def prepare_frames(items: list[dict], kind: str) -> list[dict]:
        valid = [item for item in items if item.get("path") and item.get("time") is not None]
        valid.sort(key=lambda item: item["time"])
        return [
            {"path": item["path"], "time": int(item["time"]), "kind": kind}
            for item in valid
        ]

    past = prepare_frames(radar.get("past", []), "Observed")
    nowcast = prepare_frames(radar.get("nowcast", []), "Nowcast")
    frames = past + nowcast
    if not frames:
        raise ValueError("RainViewer did not return any radar frames.")

    tile_host = payload.get("host", "https://tilecache.rainviewer.com").rstrip("/")
    log.debug("Loaded %d observed and %d nowcast frames", len(past), len(nowcast))
    return frames, len(past), tile_host

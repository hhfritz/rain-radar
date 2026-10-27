import json


def leaflet_map_html(
    latitude: float,
    longitude: float,
    frames: list[dict],
    initial_frame: int,
    tile_host: str,
) -> str:
    """Create a Leaflet map with location and switchable RainViewer radar frames."""
    lat = json.dumps(latitude)
    lon = json.dumps(longitude)
    frames_json = json.dumps(frames, separators=(",", ":"))
    initial = json.dumps(initial_frame)
    host = json.dumps(tile_host.rstrip("/"))
    return f"""<!doctype html>
<html lang="en">
<head>
  <meta name="viewport" content="width=device-width, initial-scale=1.0, maximum-scale=1.0, user-scalable=no">
  <link rel="stylesheet" href="https://unpkg.com/leaflet@1.9.4/dist/leaflet.css">
  <script src="https://unpkg.com/leaflet@1.9.4/dist/leaflet.js"></script>
  <style>
    html, body, #map {{ height: 100%; width: 100%; margin: 0; padding: 0; }}
  </style>
</head>
<body>
  <div id="map"></div>
  <script>
    const latitude = {lat};
    const longitude = {lon};
    const radarFrames = {frames_json};
    const radarHost = {host};
    const map = L.map('map').setView([latitude, longitude], 8);
    L.tileLayer('https://{{s}}.tile.openstreetmap.org/{{z}}/{{x}}/{{y}}.png', {{
      maxZoom: 19,
      attribution: '&copy; OpenStreetMap contributors'
    }}).addTo(map);
    L.marker([latitude, longitude]).addTo(map)
  

    function radarTileUrl(frame) {{
      return radarHost + frame.path + '/256/{{z}}/{{x}}/{{y}}/2/1_1.png';
    }}
    const radarLayer = L.tileLayer(radarTileUrl(radarFrames[{initial}]), {{
      opacity: 0.72,
      tileSize: 256,
      maxNativeZoom: 7,
      maxZoom: 19,
      attribution: '&copy; RainViewer'
    }}).addTo(map);
    window.setRadarFrame = function(index) {{
      const frame = radarFrames[Math.max(0, Math.min(index, radarFrames.length - 1))];
      radarLayer.setUrl(radarTileUrl(frame));
    }};
  </script>
</body>
</html>"""

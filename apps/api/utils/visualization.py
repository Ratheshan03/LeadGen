import folium
from folium.plugins import MarkerCluster


def visualize_tiles_on_map(tiles, save_path="tiles_map.html", zoom=11, color="purple"):
    """
    Visualizes tile boundaries and centers on a Folium map.

    Args:
        tiles (List[Dict]): List of tile dictionaries containing lat/lon boundaries.
        save_path (str): File path to save the HTML map.
        zoom (int): Initial zoom level of the map.
        color (str): Rectangle border color (e.g., 'blue', 'green', 'purple').
    """
    if not tiles:
        print("⚠️ No tiles to visualize.")
        return

    # 🧭 Use center of first tile
    first_tile = tiles[0]
    center_lat = (first_tile["low"]["latitude"] + first_tile["high"]["latitude"]) / 2
    center_lon = (first_tile["low"]["longitude"] + first_tile["high"]["longitude"]) / 2

    m = folium.Map(location=[center_lat, center_lon], zoom_start=zoom, control_scale=True)

    # 📦 Draw rectangles
    for tile in tiles:
        bounds = [
            [tile["low"]["latitude"], tile["low"]["longitude"]],
            [tile["high"]["latitude"], tile["high"]["longitude"]],
        ]
        tile_name = tile.get("tile_name", "tile")

        folium.Rectangle(
            bounds=bounds,
            color=color,
            fill=True,
            fill_opacity=0.25,
            tooltip=tile_name,
        ).add_to(m)

    # 📍 Add center markers
    marker_cluster = MarkerCluster().add_to(m)
    for tile in tiles:
        lat_c = (tile["low"]["latitude"] + tile["high"]["latitude"]) / 2
        lon_c = (tile["low"]["longitude"] + tile["high"]["longitude"]) / 2
        folium.Marker(location=[lat_c, lon_c], popup=tile["tile_name"]).add_to(marker_cluster)

    m.save(save_path)
    print(f"✅ Tile map saved to: {save_path}")

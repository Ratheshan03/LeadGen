import folium
from folium.plugins import MarkerCluster
from shapely.geometry import mapping


def visualize_tiles_on_map(tiles, save_path="tiles_map.html", zoom=11, color="purple"):
    if not tiles:
        print("⚠️ No tiles to visualize.")
        return

    first_tile = tiles[0]
    center_lat = (first_tile["low"]["latitude"] + first_tile["high"]["latitude"]) / 2
    center_lon = (first_tile["low"]["longitude"] + first_tile["high"]["longitude"]) / 2

    m = folium.Map(location=[center_lat, center_lon], zoom_start=zoom, control_scale=True)

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

    marker_cluster = MarkerCluster().add_to(m)
    for tile in tiles:
        lat_c = (tile["low"]["latitude"] + tile["high"]["latitude"]) / 2
        lon_c = (tile["low"]["longitude"] + tile["high"]["longitude"]) / 2
        folium.Marker(location=[lat_c, lon_c], popup=tile["tile_name"]).add_to(marker_cluster)

    m.save(save_path)
    print(f"✅ Tile map saved to: {save_path}")


def visualize_region_polygon(region_name: str, polygon_geom, save_path="region_polygon_map.html", color="green", zoom=11):
    """
    Generic visualizer for any region polygon (GCCSA, LGA, Region, etc.)

    Args:
        region_name (str): Name of the region.
        polygon_geom (Polygon or MultiPolygon): The Shapely geometry to plot.
        save_path (str): Path to save the HTML file.
        color (str): Outline color.
        zoom (int): Initial zoom level for map.
    """
    if polygon_geom is None:
        print("⚠️ No geometry to visualize.")
        return

    centroid = polygon_geom.centroid
    m = folium.Map(location=[centroid.y, centroid.x], zoom_start=zoom)

    folium.GeoJson(
        mapping(polygon_geom),
        name=region_name,
        style_function=lambda x: {
            "fillColor": color,
            "color": color,
            "weight": 2,
            "fillOpacity": 0.25,
        },
        tooltip=region_name,
    ).add_to(m)

    m.save(save_path)
    print(f"✅ Polygon map saved to: {save_path}")

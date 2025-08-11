import geopandas as gpd
import os

# Input folders
DATA_DIR = "data/geo_boundaries"
OUTPUT_DIR = "data/geojson"

# Ensure output directory exists
os.makedirs(OUTPUT_DIR, exist_ok=True)

# Shapefile paths
files = {
    "states": os.path.join(DATA_DIR, "states", "STE_2021_AUST_GDA2020.shp"),
    "regions": os.path.join(DATA_DIR, "regions", "SA2_2021_AUST_GDA2020.shp"),
    "gccsa": os.path.join(DATA_DIR, "gccsa", "GCCSA_2021_AUST_GDA2020.shp"),
    "lga": os.path.join(DATA_DIR, "lga", "LGA_2024_AUST_GDA2020.shp")
}

def convert_and_export(name, path):
    print(f"📦 Converting: {name} ...")
    gdf = gpd.read_file(path)
    output_path = os.path.join(OUTPUT_DIR, f"{name}.geojson")
    gdf.to_file(output_path, driver="GeoJSON")
    print(f"✅ Saved: {output_path}")

def main():
    for name, path in files.items():
        if os.path.exists(path):
            convert_and_export(name, path)
        else:
            print(f"❌ File not found: {path}")

if __name__ == "__main__":
    main()

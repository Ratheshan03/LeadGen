import json
import os

# Input and output paths
lga_geojson_path = "data/geojson/lga.geojson"
output_path = "data/geojson/state_to_lgas_map.json"

# Load the LGA GeoJSON
with open(lga_geojson_path, 'r', encoding='utf-8') as f:
    data = json.load(f)

# Build state -> LGA map
state_to_lgas = {}

for feature in data['features']:
    properties = feature['properties']
    
    # Try to get state and LGA names (adjust if your keys differ)
    state_name = properties.get('STE_NAME21') or properties.get('STATE_NAME') or 'UNKNOWN_STATE'
    lga_name = properties.get('LGA_NAME24') or properties.get('LGA_NAME') or properties.get('NAME') or 'UNKNOWN_LGA'

    state_name = state_name.strip()
    lga_name = lga_name.strip()

    if state_name not in state_to_lgas:
        state_to_lgas[state_name] = []

    if lga_name not in state_to_lgas[state_name]:
        state_to_lgas[state_name].append(lga_name)

# Save to JSON
with open(output_path, 'w', encoding='utf-8') as f:
    json.dump(state_to_lgas, f, indent=2)

print(f"✅ state_to_lgas_map.json saved to {output_path}")

import argparse
import json
from pathlib import Path

import requests


API_URL = "https://apicarto.ign.fr/api/rpg/v2"


def bbox_to_polygon(bbox):
    min_lon, min_lat, max_lon, max_lat = bbox

    return {
        "type": "Polygon",
        "coordinates": [[
            [min_lon, min_lat],
            [max_lon, min_lat],
            [max_lon, max_lat],
            [min_lon, max_lat],
            [min_lon, min_lat],
        ]]
    }


def fetch_rpg_data(year, geom):
    headers = {
        "annee": str(year),
        "geom": json.dumps(geom),
    }

    print("Querying RPG API...")
    print(f"Year: {year}")
    print("Geometry type:", geom["type"])

    response = requests.get(API_URL, headers=headers, timeout=60)

    print("Status code:", response.status_code)

    if response.status_code != 200:
        print("API error response:")
        print(response.text)
        response.raise_for_status()

    return response.json()


def save_geojson(data, output_path):
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

    features = data.get("features", [])
    print(f"Saved {len(features)} features to {output_path}")

    if features:
        print("\nExample properties from first feature:")
        print(json.dumps(features[0].get("properties", {}), ensure_ascii=False, indent=2))


def main():
    parser = argparse.ArgumentParser(
        description="Fetch RPG parcel data from IGN API Carto using a bounding box."
    )

    parser.add_argument(
        "--year",
        default="2023",
        help="RPG year to query. Default: 2023.",
    )

    parser.add_argument(
        "--bbox",
        nargs=4,
        type=float,
        required=True,
        metavar=("MIN_LON", "MIN_LAT", "MAX_LON", "MAX_LAT"),
        help="Bounding box in WGS84 coordinates.",
    )

    parser.add_argument(
        "--output",
        default="data/input/rpg_api_sample.geojson",
        help="Output GeoJSON path.",
    )

    args = parser.parse_args()

    geom = bbox_to_polygon(args.bbox)
    data = fetch_rpg_data(args.year, geom)
    save_geojson(data, args.output)


if __name__ == "__main__":
    main()

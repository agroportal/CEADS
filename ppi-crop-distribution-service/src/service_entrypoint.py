import argparse
import json
import subprocess
import sys
from pathlib import Path


DEFAULT_TEMP_INPUT = "/tmp/rpg_api_input.geojson"

AGROSPAI_INPUTS_DIR = Path("/data/inputs")
AGROSPAI_OUTPUTS_DIR = Path("/data/outputs")
AGROSPAI_CUSTOM_DATA_FILE = Path("/data/inputs/algoCustomData.json")

APP_DIR = Path("/app")


def run_command(command):
    print("\nRunning:")
    print(" ".join(command), flush=True)

    result = subprocess.run(command)

    if result.returncode != 0:
        sys.exit(result.returncode)


def resolve_script(script_name):
    app_script = APP_DIR / "src" / script_name
    local_script = Path(__file__).resolve().parent / script_name

    if app_script.exists():
        return str(app_script)

    return str(local_script)


def flatten_json(value, prefix=""):
    flattened = {}

    if isinstance(value, dict):
        for key, item in value.items():
            new_prefix = f"{prefix}.{key}" if prefix else str(key)
            flattened[new_prefix] = item
            flattened.update(flatten_json(item, new_prefix))

    elif isinstance(value, list):
        for index, item in enumerate(value):
            new_prefix = f"{prefix}.{index}" if prefix else str(index)
            flattened[new_prefix] = item
            flattened.update(flatten_json(item, new_prefix))

    return flattened


def normalize_key(key):
    return (
        key.lower()
        .replace("-", "_")
        .replace(" ", "_")
        .replace(".", "_")
    )


def get_param(flattened, accepted_names, default=None):
    full_normalized = {
        normalize_key(key): value
        for key, value in flattened.items()
    }

    final_key_normalized = {
        normalize_key(key).split("_")[-1]: value
        for key, value in flattened.items()
    }

    for name in accepted_names:
        normalized_name = normalize_key(name)

        if normalized_name in full_normalized:
            return full_normalized[normalized_name]

        if normalized_name in final_key_normalized:
            return final_key_normalized[normalized_name]

    return default


def parse_bbox_from_value(value):
    if value is None:
        return None

    if isinstance(value, list) and len(value) == 4:
        return [float(item) for item in value]

    if isinstance(value, str):
        cleaned = (
            value.replace("[", "")
            .replace("]", "")
            .replace(";", ",")
            .replace(" ", ",")
        )

        parts = [part for part in cleaned.split(",") if part.strip()]

        if len(parts) == 4:
            return [float(part) for part in parts]

    return None


def load_agrospai_custom_parameters():
    if not AGROSPAI_CUSTOM_DATA_FILE.exists():
        print("No AgrospAI custom parameter file found.", flush=True)
        return {}

    print(f"Loading AgrospAI custom parameters from: {AGROSPAI_CUSTOM_DATA_FILE}", flush=True)

    with open(AGROSPAI_CUSTOM_DATA_FILE, "r", encoding="utf-8") as file:
        data = json.load(file)

    flattened = flatten_json(data)

    print("Detected custom parameter keys:", flush=True)
    for key in sorted(flattened.keys()):
        if not isinstance(flattened[key], (dict, list)):
            print(f"- {key}: {flattened[key]}", flush=True)

    year = get_param(
        flattened,
        ["year", "rpg_year", "annee", "année"],
    )

    bbox = parse_bbox_from_value(
        get_param(
            flattened,
            ["bbox", "bounding_box", "boundingbox"],
        )
    )

    if bbox is None:
        min_lon = get_param(flattened, ["min_lon", "min_longitude", "bbox_min_lon", "west"])
        min_lat = get_param(flattened, ["min_lat", "min_latitude", "bbox_min_lat", "south"])
        max_lon = get_param(flattened, ["max_lon", "max_longitude", "bbox_max_lon", "east"])
        max_lat = get_param(flattened, ["max_lat", "max_latitude", "bbox_max_lat", "north"])

        if all(value is not None for value in [min_lon, min_lat, max_lon, max_lat]):
            bbox = [float(min_lon), float(min_lat), float(max_lon), float(max_lat)]

    crop_column = get_param(
        flattened,
        ["crop_column", "cropcolumn", "crop_col"],
        default="code_group",
    )

    return {
        "year": str(year) if year is not None else None,
        "bbox": bbox,
        "crop_column": crop_column,
    }


def find_first_agrospai_input():
    if not AGROSPAI_INPUTS_DIR.exists():
        raise FileNotFoundError("AgrospAI input directory not found: /data/inputs")

    candidates = [
        path for path in AGROSPAI_INPUTS_DIR.rglob("*")
        if path.is_file()
        and path.name != "algoCustomData.json"
        and "/ddos/" not in str(path)
    ]

    if not candidates:
        raise FileNotFoundError("No input dataset file found under /data/inputs")

    candidates = sorted(candidates, key=lambda p: str(p))
    selected = candidates[0]

    print(f"Auto-detected AgrospAI input file: {selected}", flush=True)
    return str(selected)


def run_file_mode(input_file, crop_column, output):
    run_command([
        sys.executable,
        resolve_script("crop_distribution.py"),
        "--input",
        input_file,
        "--crop-column",
        crop_column,
        "--output",
        output,
    ])


def run_api_mode(year, bbox, crop_column, output, temp_input):
    if not year:
        raise ValueError("API mode requires a year.")

    if not bbox:
        raise ValueError("API mode requires bbox values: MIN_LON MIN_LAT MAX_LON MAX_LAT.")

    Path(temp_input).parent.mkdir(parents=True, exist_ok=True)

    run_command([
        sys.executable,
        resolve_script("fetch_rpg_api.py"),
        "--year",
        str(year),
        "--bbox",
        *[str(value) for value in bbox],
        "--output",
        temp_input,
    ])

    run_file_mode(temp_input, crop_column, output)


def run_agrospai_default_mode():
    print("No command-line arguments provided.", flush=True)
    print("Running in AgrospAI automatic mode.", flush=True)

    AGROSPAI_OUTPUTS_DIR.mkdir(parents=True, exist_ok=True)

    params = load_agrospai_custom_parameters()

    year = params.get("year")
    bbox = params.get("bbox")
    crop_column = params.get("crop_column", "code_group")
    output = str(AGROSPAI_OUTPUTS_DIR)

    if year and bbox:
        print("Detected year and bbox parameters.", flush=True)
        print("Running API mode.", flush=True)

        run_api_mode(
            year=year,
            bbox=bbox,
            crop_column=crop_column,
            output=output,
            temp_input=DEFAULT_TEMP_INPUT,
        )

        print("\nService execution completed successfully.", flush=True)
        print("Mode: agrospai-api", flush=True)
        print(f"Year: {year}", flush=True)
        print(f"BBOX: {bbox}", flush=True)
        print(f"Output folder: {output}", flush=True)
        return

    print("No complete API parameters found.", flush=True)
    print("Falling back to file mode using /data/inputs.", flush=True)

    input_file = find_first_agrospai_input()

    run_file_mode(input_file, crop_column, output)

    print("\nService execution completed successfully.", flush=True)
    print("Mode: agrospai-file", flush=True)
    print(f"Input file: {input_file}", flush=True)
    print(f"Output folder: {output}", flush=True)


def main():
    if len(sys.argv) == 1:
        run_agrospai_default_mode()
        return

    parser = argparse.ArgumentParser(
        description="Service entrypoint for RPG crop distribution analysis."
    )

    parser.add_argument(
        "--mode",
        choices=["file", "api"],
        required=True,
        help="Execution mode: 'file' processes an existing dataset; 'api' fetches RPG data first.",
    )

    parser.add_argument("--input", help="Input geospatial file for file mode.")
    parser.add_argument("--year", help="RPG year for API mode.")

    parser.add_argument(
        "--bbox",
        nargs=4,
        type=float,
        metavar=("MIN_LON", "MIN_LAT", "MAX_LON", "MAX_LAT"),
        help="Bounding box in WGS84 coordinates for API mode.",
    )

    parser.add_argument(
        "--crop-column",
        default="code_group",
        help="Column containing crop group or crop class codes. Default: code_group.",
    )

    parser.add_argument(
        "--output",
        default="output",
        help="Output folder. Default: output.",
    )

    parser.add_argument(
        "--temp-input",
        default=DEFAULT_TEMP_INPUT,
        help="Temporary GeoJSON path used in API mode.",
    )

    args = parser.parse_args()

    if args.mode == "file":
        if not args.input:
            raise ValueError("File mode requires --input.")
        run_file_mode(args.input, args.crop_column, args.output)

    elif args.mode == "api":
        run_api_mode(args.year, args.bbox, args.crop_column, args.output, args.temp_input)

    print("\nService execution completed successfully.", flush=True)
    print(f"Mode: {args.mode}", flush=True)
    print(f"Output folder: {args.output}", flush=True)


if __name__ == "__main__":
    main()

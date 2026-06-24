import argparse
import subprocess
import sys
from pathlib import Path


DEFAULT_TEMP_INPUT = "data/input/rpg_api_input.geojson"
AGROSPAI_INPUTS_DIR = Path("/data/inputs")
AGROSPAI_OUTPUTS_DIR = Path("/data/outputs")
APP_DIR = Path("/app")


def run_command(command):
    print("\nRunning:")
    print(" ".join(command), flush=True)
    result = subprocess.run(command)
    if result.returncode != 0:
        sys.exit(result.returncode)


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


def resolve_script(script_name):
    app_script = APP_DIR / "src" / script_name
    local_script = Path("src") / script_name

    if app_script.exists():
        return str(app_script)

    return str(local_script)


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
        raise ValueError("API mode requires --year.")

    if not bbox:
        raise ValueError("API mode requires --bbox MIN_LON MIN_LAT MAX_LON MAX_LAT.")

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
    print("Running in AgrospAI default file mode.", flush=True)

    input_file = find_first_agrospai_input()
    output = str(AGROSPAI_OUTPUTS_DIR)
    crop_column = "code_group"

    AGROSPAI_OUTPUTS_DIR.mkdir(parents=True, exist_ok=True)

    run_file_mode(input_file, crop_column, output)

    print("\nService execution completed successfully.", flush=True)
    print("Mode: agrospai-default-file", flush=True)
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

import argparse
import subprocess
import sys
from pathlib import Path


DEFAULT_TEMP_INPUT = "data/input/rpg_api_input.geojson"


def run_command(command):
    print("\nRunning:")
    print(" ".join(command))
    result = subprocess.run(command)
    if result.returncode != 0:
        sys.exit(result.returncode)


def run_file_mode(args):
    if not args.input:
        raise ValueError("File mode requires --input.")

    run_command([
        sys.executable,
        "src/crop_distribution.py",
        "--input",
        args.input,
        "--crop-column",
        args.crop_column,
        "--output",
        args.output,
    ])


def run_api_mode(args):
    if not args.year:
        raise ValueError("API mode requires --year.")

    if not args.bbox:
        raise ValueError("API mode requires --bbox MIN_LON MIN_LAT MAX_LON MAX_LAT.")

    temp_input = args.temp_input

    Path(temp_input).parent.mkdir(parents=True, exist_ok=True)

    run_command([
        sys.executable,
        "src/fetch_rpg_api.py",
        "--year",
        str(args.year),
        "--bbox",
        *[str(value) for value in args.bbox],
        "--output",
        temp_input,
    ])

    run_command([
        sys.executable,
        "src/crop_distribution.py",
        "--input",
        temp_input,
        "--crop-column",
        args.crop_column,
        "--output",
        args.output,
    ])


def main():
    parser = argparse.ArgumentParser(
        description="Service entrypoint for RPG crop distribution analysis."
    )

    parser.add_argument(
        "--mode",
        choices=["file", "api"],
        required=True,
        help="Execution mode: 'file' processes an existing dataset; 'api' fetches RPG data first.",
    )

    parser.add_argument(
        "--input",
        help="Input geospatial file for file mode.",
    )

    parser.add_argument(
        "--year",
        help="RPG year for API mode.",
    )

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
        run_file_mode(args)
    elif args.mode == "api":
        run_api_mode(args)

    print("\nService execution completed successfully.")
    print(f"Mode: {args.mode}")
    print(f"Output folder: {args.output}")


if __name__ == "__main__":
    main()

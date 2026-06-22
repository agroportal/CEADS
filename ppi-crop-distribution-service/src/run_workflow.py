import argparse
import subprocess
import sys
from pathlib import Path


def run_command(command):
    print("\nRunning:")
    print(" ".join(command))

    result = subprocess.run(command)

    if result.returncode != 0:
        raise RuntimeError(f"Command failed with exit code {result.returncode}")


def main():
    parser = argparse.ArgumentParser(
        description="Fetch RPG data and run crop distribution analysis in one command."
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
        "--input-output",
        default="data/input/rpg_api_sample.geojson",
        help="Path where the fetched RPG GeoJSON will be saved.",
    )

    parser.add_argument(
        "--analysis-output",
        default="output",
        help="Directory where analysis outputs will be saved.",
    )

    parser.add_argument(
        "--crop-column",
        default="code_group",
        help="Column containing the crop group. Default: code_group.",
    )

    args = parser.parse_args()

    input_output = Path(args.input_output)
    analysis_output = Path(args.analysis_output)

    bbox_values = [str(value) for value in args.bbox]

    run_command([
        sys.executable,
        "src/fetch_rpg_api.py",
        "--year",
        str(args.year),
        "--bbox",
        *bbox_values,
        "--output",
        str(input_output),
    ])

    run_command([
        sys.executable,
        "src/crop_distribution.py",
        "--input",
        str(input_output),
        "--crop-column",
        args.crop_column,
        "--output",
        str(analysis_output),
    ])

    print("\nWorkflow completed successfully.")
    print(f"Input GeoJSON: {input_output}")
    print(f"Analysis output folder: {analysis_output}")


if __name__ == "__main__":
    main()

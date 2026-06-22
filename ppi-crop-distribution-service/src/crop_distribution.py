import argparse
import json
from pathlib import Path

import folium
import geopandas as gpd
import pandas as pd


def load_geodata(input_path: Path) -> gpd.GeoDataFrame:
    if not input_path.exists():
        raise FileNotFoundError(f"Input file not found: {input_path}")

    print(f"Loading data from: {input_path}")
    gdf = gpd.read_file(input_path)

    if gdf.empty:
        raise ValueError("The input geospatial file is empty.")

    if "geometry" not in gdf.columns:
        raise ValueError("No geometry column found in the input file.")

    if gdf.geometry.is_empty.all():
        raise ValueError("All geometries are empty.")

    print(f"Loaded {len(gdf)} features.")
    print(f"Input CRS: {gdf.crs}")

    return gdf


def fix_geometries(gdf: gpd.GeoDataFrame) -> gpd.GeoDataFrame:
    gdf = gdf.copy()

    invalid_count = int((~gdf.geometry.is_valid).sum())

    if invalid_count > 0:
        print(f"Fixing {invalid_count} invalid geometries...")
        gdf["geometry"] = gdf.geometry.buffer(0)

    return gdf


def choose_equal_area_crs(gdf: gpd.GeoDataFrame) -> str:
    return "EPSG:3035"


def calculate_area(gdf: gpd.GeoDataFrame) -> gpd.GeoDataFrame:
    gdf = gdf.copy()

    if gdf.crs is None:
        raise ValueError(
            "Input data has no CRS. Please define the CRS before running area calculations."
        )

    equal_area_crs = choose_equal_area_crs(gdf)
    gdf_area = gdf.to_crs(equal_area_crs)

    gdf["area_m2"] = gdf_area.geometry.area
    gdf["area_ha"] = gdf["area_m2"] / 10_000

    return gdf


def load_crop_group_labels(reference_path: Path) -> pd.DataFrame | None:
    if not reference_path.exists():
        print(f"No crop group label file found at: {reference_path}")
        print("The summary will be generated without labels.")
        return None

    labels = pd.read_csv(reference_path)
    labels["code_group"] = labels["code_group"].astype(str)

    return labels


def add_crop_group_labels(
    summary: pd.DataFrame,
    labels: pd.DataFrame | None,
) -> pd.DataFrame:
    if labels is None:
        summary["label"] = ""
        return summary

    summary = summary.copy()
    summary["crop_group"] = summary["crop_group"].astype(str)

    labeled = summary.merge(
        labels,
        left_on="crop_group",
        right_on="code_group",
        how="left",
    )

    labeled["label"] = labeled["label"].fillna("Unknown")

    labeled = labeled[
        ["crop_group", "label", "parcel_count", "total_area_ha", "percentage_area"]
    ]

    return labeled


def create_summary(
    gdf: gpd.GeoDataFrame,
    crop_column: str,
    labels: pd.DataFrame | None = None,
) -> pd.DataFrame:
    if crop_column not in gdf.columns:
        available = ", ".join(gdf.columns)
        raise ValueError(
            f"Crop column '{crop_column}' not found. Available columns: {available}"
        )

    gdf = gdf.copy()
    gdf[crop_column] = gdf[crop_column].fillna("Unknown").astype(str)

    total_area = gdf["area_ha"].sum()

    summary = (
        gdf.groupby(crop_column, dropna=False)
        .agg(
            parcel_count=(crop_column, "size"),
            total_area_ha=("area_ha", "sum"),
        )
        .reset_index()
        .rename(columns={crop_column: "crop_group"})
    )

    summary["percentage_area"] = (summary["total_area_ha"] / total_area) * 100

    summary = summary.sort_values(
        by="total_area_ha",
        ascending=False,
    )

    summary["total_area_ha"] = summary["total_area_ha"].round(2)
    summary["percentage_area"] = summary["percentage_area"].round(2)

    summary = add_crop_group_labels(summary, labels)

    return summary


def create_interactive_map(
    gdf: gpd.GeoDataFrame,
    crop_column: str,
    output_html: Path,
    labels: pd.DataFrame | None = None,
    max_features: int = 5000,
) -> None:
    map_gdf = gdf.copy()

    if len(map_gdf) > max_features:
        print(
            f"Dataset has {len(map_gdf)} features. "
            f"Sampling {max_features} for the interactive map."
        )
        map_gdf = map_gdf.sample(max_features, random_state=42)

    map_gdf = map_gdf.to_crs("EPSG:4326")
    map_gdf[crop_column] = map_gdf[crop_column].fillna("Unknown").astype(str)

    if labels is not None:
        label_dict = dict(zip(labels["code_group"], labels["label"]))
        map_gdf["crop_label"] = map_gdf[crop_column].map(label_dict).fillna("Unknown")

    centroid = map_gdf.geometry.union_all().centroid

    m = folium.Map(
        location=[centroid.y, centroid.x],
        zoom_start=11,
        tiles="CartoDB positron",
    )

    crop_groups = sorted(map_gdf[crop_column].unique())

    color_palette = [
        "red",
        "blue",
        "green",
        "purple",
        "orange",
        "darkred",
        "lightred",
        "beige",
        "darkblue",
        "darkgreen",
        "cadetblue",
        "darkpurple",
        "white",
        "pink",
        "lightblue",
        "lightgreen",
        "gray",
        "black",
        "lightgray",
    ]

    color_map = {
        group: color_palette[i % len(color_palette)]
        for i, group in enumerate(crop_groups)
    }

    def style_function(feature):
        group = str(feature["properties"].get(crop_column, "Unknown"))
        return {
            "fillColor": color_map.get(group, "gray"),
            "color": "black",
            "weight": 0.3,
            "fillOpacity": 0.6,
        }

    tooltip_fields = [crop_column]

    if "crop_label" in map_gdf.columns:
        tooltip_fields.append("crop_label")

    if "code_cultu" in map_gdf.columns:
        tooltip_fields.append("code_cultu")

    tooltip_fields.append("area_ha")

    if "surf_parc" in map_gdf.columns:
        tooltip_fields.append("surf_parc")

    folium.GeoJson(
        map_gdf,
        name="Parcels",
        style_function=style_function,
        tooltip=folium.GeoJsonTooltip(
            fields=tooltip_fields,
            aliases=[field + ":" for field in tooltip_fields],
            localize=True,
        ),
    ).add_to(m)

    folium.LayerControl().add_to(m)
    m.save(output_html)

    print(f"Map saved to: {output_html}")


def save_outputs(
    gdf: gpd.GeoDataFrame,
    summary: pd.DataFrame,
    output_dir: Path,
    input_path: Path,
    crop_column: str,
    labels: pd.DataFrame | None = None,
) -> None:
    output_dir.mkdir(parents=True, exist_ok=True)

    summary_path = output_dir / "crop_distribution_summary.csv"
    geojson_path = output_dir / "processed_parcels.geojson"
    map_path = output_dir / "crop_distribution_map.html"
    report_path = output_dir / "processing_report.json"

    summary.to_csv(summary_path, index=False)
    print(f"Summary saved to: {summary_path}")

    gdf.to_crs("EPSG:4326").to_file(geojson_path, driver="GeoJSON")
    print(f"Processed GeoJSON saved to: {geojson_path}")

    create_interactive_map(gdf, crop_column, map_path, labels=labels)

    report = {
        "input_file": str(input_path),
        "crop_column": crop_column,
        "labels_file": "data/reference/crop_group_labels.csv",
        "feature_count": int(len(gdf)),
        "crs": str(gdf.crs),
        "total_area_ha": round(float(gdf["area_ha"].sum()), 2),
        "number_of_crop_groups": int(summary["crop_group"].nunique()),
        "outputs": {
            "summary_csv": str(summary_path),
            "processed_geojson": str(geojson_path),
            "interactive_map": str(map_path),
        },
    }

    with open(report_path, "w", encoding="utf-8") as f:
        json.dump(report, f, indent=2, ensure_ascii=False)

    print(f"Report saved to: {report_path}")


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Generate crop distribution statistics and maps from PPI/RPG parcel data."
    )

    parser.add_argument(
        "--input",
        required=True,
        help="Path to input geospatial file.",
    )

    parser.add_argument(
        "--crop-column",
        required=True,
        help="Name of the column containing the dominant crop group.",
    )

    parser.add_argument(
        "--output",
        default="output",
        help="Output directory. Default: output",
    )

    parser.add_argument(
        "--labels",
        default="data/reference/crop_group_labels.csv",
        help="Path to crop group label CSV. Default: data/reference/crop_group_labels.csv",
    )

    args = parser.parse_args()

    input_path = Path(args.input)
    output_dir = Path(args.output)
    labels_path = Path(args.labels)

    labels = load_crop_group_labels(labels_path)

    gdf = load_geodata(input_path)
    gdf = fix_geometries(gdf)
    gdf = calculate_area(gdf)

    summary = create_summary(gdf, args.crop_column, labels=labels)

    print("\nCrop distribution summary:")
    print(summary.head(20))

    save_outputs(
        gdf=gdf,
        summary=summary,
        output_dir=output_dir,
        input_path=input_path,
        crop_column=args.crop_column,
        labels=labels,
    )

    print("\nDone.")


if __name__ == "__main__":
    main()

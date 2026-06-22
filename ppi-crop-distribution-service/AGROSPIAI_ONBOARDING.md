# AgrospAI onboarding notes

## Algorithm title

PPI Crop Distribution Service

## Short description

Dockerized algorithm for computing crop distribution statistics from Parcel Identification System / RPG geospatial data.

## Execution mode for first AgrospAI demo

File mode.

The algorithm expects an existing geospatial dataset, such as a GeoJSON file, to be registered as a dataset asset in AgrospAI. The Docker algorithm processes that dataset and generates crop distribution outputs.

## Main input

A geospatial file containing agricultural parcel geometries and a crop group column.

Expected default crop column:

```text
code_group
```

Recommended input format for the first demo:

```text
GeoJSON
```

## Main outputs

```text
crop_distribution_summary.csv
crop_distribution_map.html
processed_parcels.geojson
processing_report.json
```

## Docker build command

```bash
docker build -t ppi-crop-distribution-service:local .
```

## Docker entrypoint

```text
python src/service_entrypoint.py
```

## File mode command

```bash
--mode file --input data/input/rpg_api_sample.geojson --crop-column code_group --output output
```

## API mode command, for future flexible execution

```bash
--mode api --year 2023 --bbox 3.15 43.30 3.25 43.36 --crop-column code_group --output output
```

## Notes

For the first AgrospAI / Pontus-X Compute-to-Data test, file mode is preferred because it follows the standard pattern of running an algorithm on a registered dataset asset.

API mode is included in the same Docker image for a future implementation where users can specify year and bounding box parameters.

# PPI Crop Distribution Service

This prototype processes Parcel Identification System / RPG geospatial data and generates crop distribution outputs.

## Fetch data from the RPG API

You can fetch a sample area from the IGN API Carto RPG module using a bounding box.

```bash
python src/fetch_rpg_api.py --year 2023 --bbox 3.15 43.30 3.25 43.36 --output data/input/rpg_api_sample.geojson
```

The bounding box values are:

```text
MIN_LON MIN_LAT MAX_LON MAX_LAT
```

## Run the crop distribution analysis

```bash
python src/crop_distribution.py --input data/input/rpg_api_sample.geojson --crop-column code_group --output output
```

## Run the full workflow in one command

You can fetch RPG data and run the crop distribution analysis with a single command:

```bash
python src/run_workflow.py --year 2023 --bbox 3.15 43.30 3.25 43.36 --input-output data/input/rpg_api_sample.geojson --analysis-output output
```

This command will:

1. fetch RPG parcel data from the API;
2. save the input GeoJSON in `data/input/`;
3. run the crop distribution analysis;
4. generate the CSV summary, interactive map, processed GeoJSON, and processing report.

## Main processing

The script:

1. loads parcel geometries;
2. fixes invalid geometries when needed;
3. calculates parcel area in hectares;
4. aggregates parcel count and total area by crop group;
5. adds readable crop group labels;
6. generates an interactive HTML map;
7. exports a processed GeoJSON and a processing report.

## Outputs

```text
output/crop_distribution_summary.csv
output/crop_distribution_map.html
output/processed_parcels.geojson
output/processing_report.json
```

## Reference data

The crop group labels are stored in:

```text
data/reference/crop_group_labels.csv
```

## Notes

The `data/input/` and `output/` folders are ignored by Git because they contain downloaded input data and generated outputs.

## Docker usage

Build the Docker image:

```bash
docker build -t ppi-crop-distribution-service:local .
```

### File mode

Use file mode when running the algorithm on an existing geospatial dataset, such as a GeoJSON file registered as a dataset asset.

```bash
docker run --rm \
  -v "$(pwd)/data/input:/app/data/input:ro" \
  -v "$(pwd)/output:/app/output" \
  ppi-crop-distribution-service:local \
  --mode file \
  --input data/input/rpg_api_sample.geojson \
  --crop-column code_group \
  --output output
```

### API mode

Use API mode when the algorithm should fetch RPG data from the IGN API Carto RPG module before running the crop distribution analysis.

```bash
docker run --rm \
  -v "$(pwd)/output:/app/output" \
  ppi-crop-distribution-service:local \
  --mode api \
  --year 2023 \
  --bbox 3.15 43.30 3.25 43.36 \
  --crop-column code_group \
  --output output
```

## AgrospAI deployment idea

For a first AgrospAI / Pontus-X Compute-to-Data demo, use file mode:

1. prepare or register an RPG GeoJSON extract as a dataset asset;
2. register this Docker image as an algorithm asset;
3. run the algorithm on the dataset;
4. collect the generated outputs from the Compute-to-Data job.

The same Docker image also includes API mode, which can support a future implementation where users specify a year and bounding box.

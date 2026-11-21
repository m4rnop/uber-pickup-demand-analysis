# Uber Pickup Demand Analysis

Analysis of 4,534,327 Uber pickup records from April to September 2014. The project describes when and where pickups were recorded and how counts vary by borough and TLC-affiliated base.

## Review the submission

- [Thai report (PDF)](reports/final_report_th.pdf) · [English report (PDF)](reports/final_report.pdf)
- [Executed analysis notebook](notebooks/uber_complete_analysis.ipynb) · [Validation summary](reports/final_validation_summary.md)
- [Borough counts](outputs/tables/borough_summary.csv) · [Monthly data quality](outputs/tables/monthly_data_quality.csv) · [Results JSON](outputs/tables/results.json)
- [Presentation visuals and PNG inventory](outputs/presentation_visuals/README.md)
- [Interactive map HTML](outputs/interactive_map/index.html). Download the file from GitHub and open it in a current browser. It works offline and includes Heatmap, Hexbin, and Point views, filters, and five summary charts.

## Reproduce the analysis

Use Python 3.11 or newer. The submission was verified with Python 3.15. From the project root, create and activate a virtual environment:

```sh
python -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
```

On Windows PowerShell, activate it with `.venv\Scripts\Activate.ps1`.

1. Download the six monthly pickup CSVs into `data/` following the [data instructions](data/README.md). The repository includes the geographic boundaries and prebuilt results.
2. Run the analysis and regenerate the map, charts, and reports:

   ```sh
   python src/analysis.py
   python src/build_interactive_map.py
   python src/presentation_visuals.py
   python src/build_report.py
   python src/build_thai_report.py
   ```

3. To rerun the notebook, start Jupyter with the project environment active and run all cells in [uber_complete_analysis.ipynb](notebooks/uber_complete_analysis.ipynb). The first code cell runs the analysis pipeline. To recreate the notebook source before executing it, run `python src/create_notebook.py`.

The English report builder generates Markdown, DOCX, and PDF. The Thai builder generates Markdown and DOCX. The Thai PDF is included in the repository. To regenerate it, export `reports/final_report_th.docx` to PDF in Word or LibreOffice with a Thai font installed.

## Data handling

NYC membership comes from the union of the five borough polygons. Points within that union are assigned to boroughs. For points outside the city, the state polygons are used to classify the state. Records with no matching state polygon remain in the totals. The newer borough boundaries and the 2014 state boundaries are documented in [data/README.md](data/README.md).

The analysis retains exact repeated rows because the source has no trip identifier to distinguish repeated records from separate events. The reported counts describe the supplied records. The TLC `Base` code is the company affiliation associated with the pickup. It provides no direct measure of the number of drivers or vehicles.

## Project layout

| Path | Contents |
|---|---|
| `src/` | Analysis, reports, presentation graphics, and offline map builder |
| `data/` | Boundary files and local location for the six raw pickup CSVs |
| `notebooks/` | Analysis notebooks |
| `outputs/processed/` | Classified record-level Parquet used by the report and map builders |
| `outputs/tables/`, `outputs/geographic/` | Summary tables and geographic reconciliation |
| `outputs/figures/`, `outputs/presentation_visuals/` | Analysis figures and presentation PNGs |
| `outputs/interactive_map/` | Standalone HTML map |
| `reports/` | Reports and validation summary |

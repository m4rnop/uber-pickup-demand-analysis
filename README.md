# Uber Pickup Demand Analysis

Reproducible analysis of the six NYC Uber pickup CSV files from April to September 2014. Raw data are kept unchanged.

## Project layout

- `data/`: six original monthly CSV files, 2014 US state boundary shapefile, and NYC borough GeoJSON.
- `src/analysis.py`: validation, temporal features, top-down geographic classification, statistics, charts, and exported tables.
- `src/create_notebook.py`: creates the completed analysis notebook.
- `src/build_report.py`: builds Markdown, DOCX, and PDF reports from executed results.
- `src/build_thai_report.py`: builds the Thai Markdown and DOCX reports from the same analysis outputs.
- `notebooks/uber_complete_analysis.ipynb`: end-to-end notebook with outputs.
- `outputs/processed/pickups_classified.parquet`: classified record-level intermediate.
- `outputs/tables/`: temporal, borough, base, and statistical outputs.
- `outputs/geographic/`: state reconciliation and geographic quality summary.
- `outputs/figures/`: generated maps and charts.
- `reports/`: academic reports in English and Thai, with Markdown, DOCX, and PDF versions.

## Reproduce

Use Python 3.11 or newer. Install dependencies with `python -m pip install -r requirements.txt`, then from the project root run:

```bash
python src/analysis.py
python src/create_notebook.py
python src/build_report.py
python src/build_thai_report.py
```

To create the Thai PDF after building the DOCX, let LibreOffice load and embed a Thai
font in a temporary profile. On macOS with the bundled Sathu font:

```bash
mkdir -p /tmp/lo-thai-profile/user/fonts
cp /System/Library/Fonts/Supplemental/Sathu.ttf /tmp/lo-thai-profile/user/fonts/Sathu.ttf
soffice -env:UserInstallation=file:///tmp/lo-thai-profile \
  --headless --convert-to pdf --outdir reports reports/final_report_th.docx
```

Open `notebooks/uber_complete_analysis.ipynb` in Jupyter and run all cells to reproduce the complete workflow and notebook outputs. The notebook executes the same analysis pipeline.

## Geographic method

The pipeline first checks every coordinate against the union of NYC borough boundaries. Only inside-NYC points receive a borough label. Outside-NYC points are classified against state boundaries separately. A state-polygon audit of inside-NYC points is used only to reconcile boundary mismatches; it does not change borough eligibility. The state reconciliation retains unmatched records instead of dropping or forcing them into a state.

## Data handling and interpretation

Exact duplicate rows are reported by month but retained; April has 7,749 repeats. This preserves the source event rows while acknowledging that the dataset does not identify whether repeats are duplicate ingestion or distinct recorded events. All summaries and tests therefore describe the supplied rows. Statistical significance is interpreted with effect size and limitations around temporal/spatial dependence. Base-code pickup totals are not interpreted as driver counts or fleet capacity.

See `reports/final_report.md` and `reports/final_report_th.md` for findings, methods, citations, limitations, and complete deliverables. `outputs/tables/results.json` stores the machine-readable validation snapshot.

See `reports/final_validation_summary.md` for execution status, reconciliation checks, and deliverable validation.

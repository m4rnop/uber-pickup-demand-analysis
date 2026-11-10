# Final Project Validation Summary

## Execution status

The analysis pipeline completed on all six source files. The completed notebook was executed end to end: 4 of 4 code cells ran with no stored errors. The DOCX and PDF were rendered for visual review; the final DOCX has 12 pages and the PDF has 10 pages. Tables, figures, page breaks, and title rendering were inspected.

## Input and data quality

- Total rows: 4,534,327; all six monthly row counts match the expected totals.
- Source file month and timestamp month mismatches: 0.
- Missing required values: 0; invalid timestamps, coordinate ranges, or base codes: 0.
- Exact duplicates retained: April 7,749; May 10,075; June 10,686; July 14,152; August 15,882; September 24,037.
- The raw CSV files were not modified.

## Geographic validation

- Inside NYC boundary: 4,411,894 (97.30% of all rows); outside NYC: 122,433 (2.70%).
- All 4,411,894 inside-NYC records received one borough classification; no observed points lie exactly on the NYC boundary.
- Borough totals sum to the NYC total: Manhattan 3,443,457; Brooklyn 593,595; Queens 342,224; Bronx 31,584; Staten Island 1,034.
- State reconciliation sums to 4,534,327: New York 4,441,067; New Jersey 92,649; Connecticut 546; Massachusetts 1; unmatched 64; other classified states 0.
- The 64 state-polygon unmatched records are 49 outside NYC and 15 inside NYC. The 15 remain eligible for borough analysis. The Massachusetts pickup is counted once.

## Analytical validation

- Temporal summaries, daily averages, heatmaps, normalized borough hourly profiles, base distributions, and spatial figures were generated from the classified data.
- Base counts by month, hour, weekday, and borough are exported. Three listed base codes have no records.
- Five omnibus tests were executed. All reported p-values are below 0.001; effect sizes are included in the report and machine-readable results. Interpretation notes the dependence and inference limitations of event-level counts.
- Borough percentages distinguish the NYC-pickup denominator from the all-record denominator.

## Deliverables

- `notebooks/uber_complete_analysis.ipynb`
- `src/analysis.py`, `src/create_notebook.py`, `src/build_report.py`
- `outputs/processed/pickups_classified.parquet`
- `outputs/tables/`, `outputs/geographic/`, and 13 files in `outputs/figures/`
- `reports/final_report.md`, `reports/final_report.docx`, `reports/final_report.pdf`
- `README.md` and `requirements.txt`

## Remaining limitations

The report documents exact duplicate retention, the six-month 2014 scope, sparse labels for three bases, and the 15 NYC/state polygon edge mismatches. The local dataset and NYC borough GeoJSON do not include source lineage URLs, so those references are identified as provided project files rather than attributed to an unverified publisher. Pickup totals do not measure driver counts, supply, unserved demand, market share, or causal effects.

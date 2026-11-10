"""Generate academic report formats from executed analysis outputs."""

import json
import re
from pathlib import Path
import pandas as pd
from docx import Document
from docx.shared import Inches, Pt
from reportlab.lib import colors
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from reportlab.platypus import (
    SimpleDocTemplate,
    Paragraph,
    Spacer,
    Image,
    Table,
    TableStyle,
)

PROJECT_ROOT = Path(__file__).resolve().parents[1]
REPORT_DIR = PROJECT_ROOT / "reports"
REPORT_DIR.mkdir(exist_ok=True)
results = json.loads((PROJECT_ROOT / "outputs/tables/results.json").read_text())
pickups = pd.read_parquet(PROJECT_ROOT / "outputs/processed/pickups_classified.parquet")
total_records = results["n"]
nyc_records = results["nyc_n"]
outside_records = results["outside_n"]
months = {int(k): int(v) for k, v in results["monthly_counts"].items()}
hours = {int(k): int(v) for k, v in results["hour_counts"].items()}
monthly_day = pickups.groupby(["month", "date"]).size().groupby("month").mean()
weekday_day = (
    pickups.groupby(["day_of_week", "date"]).size().groupby("day_of_week").mean()
)
weekday_names = [
    "Monday",
    "Tuesday",
    "Wednesday",
    "Thursday",
    "Friday",
    "Saturday",
    "Sunday",
]
base_counts = pickups["Base"].value_counts().to_dict()
base_hour = pd.crosstab(pickups["hour"], pickups["Base"])
base_weekday = pd.crosstab(pickups["day_of_week"], pickups["Base"])


def pct(numerator, denominator):
    return f"{numerator/denominator*100:.2f}%"


def pval(x):
    return "<0.001" if x < 0.001 else f"{x:.4g}"


report_lines = []


def add_line(s=""):
    report_lines.append(s)


add_line("# Uber Pickup Demand Analysis 2014")
add_line("**Study period:** April to September 2014")
add_line("**Course:** Data Science, Year 2 Semester 1  ")
add_line(
    "**Team:** Student 1: ____________________ | Student 2: ____________________  "
)
add_line("**Academic context:** Reproducible course research project")
add_line("## Abstract")
add_line(
    f"This study examines {total_records:,} Uber pickup records from April through September 2014. The pipeline validates six monthly files, retains all observed rows, and applies a top-down geographic procedure: NYC boundary membership is tested first, borough classification is limited to points inside NYC, and state classification is applied separately to points outside NYC. Results identify {nyc_records:,} NYC pickups ({pct(nyc_records,total_records)}) and {outside_records:,} outside NYC ({pct(outside_records,total_records)}). Manhattan accounts for 78.05% of NYC pickups. The busiest hour is 17:00 ({hours[17]:,} records) and the lowest is 02:00 ({hours[2]:,}). September has the greatest total and average daily volume. Omnibus tests find statistically significant categorical associations with small to modest effect sizes. These records describe pickup activity only; they do not measure drivers, unserved requests, fleet size, or causal drivers of demand."
)
add_line("## Chapter 1: Introduction")
add_line("### 1.1 Background")
add_line(
    "Timestamped, geocoded pickup records reveal when and where ride activity was observed. Their interpretation must remain within the limits of the recorded fields."
)
add_line("### 1.2 Problem Statement")
add_line(
    "This project characterizes temporal and geographic variation in the 2014 NYC Uber pickup data while preventing locations outside the city from being assigned to a borough."
)
add_line("### 1.3 Research Objectives")
add_line(
    "Measure monthly, daily, hourly, borough, state, and base distributions; validate source data and geographic joins; test selected categorical associations; and identify cautious operations implications."
)
add_line("### 1.4 Research Questions")
add_line(
    "When do pickups peak? Where are they concentrated? Which borough has the highest count? How do patterns vary by hour, weekday, month, and base? Are the categorical distributions associated?"
)
add_line("### 1.5 Scope of Study")
add_line(
    "The study covers the six provided monthly CSVs, April–September 2014, and the provided NYC borough and 2014 US state polygons. No fare, trip destination, driver, or service-quality fields are available."
)
add_line("### 1.6 Expected Contributions")
add_line(
    "The project provides an executable analysis pipeline, top-down geographic classification, validation tables, figures, and research report."
)
add_line("## Chapter 2: Dataset and Data Understanding")
add_line("### 2.1 Dataset Description")
add_line(
    f"The six files contain {total_records:,} records, with each monthly count matching its expected value. Each record contains a timestamp, latitude, longitude, and Uber base identifier."
)
add_line("### 2.2 Dataset Structure and 2.3 Data Dictionary")
add_line("| Field | Definition |")
add_line("|---|---|")
for x, y in [
    ("Date/Time", "Source pickup timestamp"),
    ("Lat", "Latitude, decimal degrees, EPSG:4326"),
    ("Lon", "Longitude, decimal degrees, EPSG:4326"),
    ("Base", "Uber base identifier"),
    ("month_file", "Source month"),
    ("inside_nyc", "Point in union of NYC borough polygons"),
    ("borough", "Borough label, only for NYC-inside points"),
    ("state_outside_nyc", "State label for outside-NYC points"),
    ("state_geometry_audit_inside_nyc", "Independent state audit for reconciliation"),
    (
        "year/month/day/hour/date/day_of_week",
        "Timestamp-derived calendar features; Monday=0",
    ),
]:
    add_line(f"| {x} | {y} |")
add_line("")
add_line(
    "| Month | Rows | Exact duplicate rows | Missing cells | Invalid rows | File-month mismatches |"
)
add_line("|---|---:|---:|---:|---:|---:|")
for q in results["quality"]:
    add_line(
        f"| {q['month']} | {q['rows']:,} | {q['duplicate_rows']:,} | {q['missing_cells']} | {q['invalid_rows']} | {q['wrong_month_rows']} |"
    )
add_line("")
add_line("### 2.4 Data Quality Assessment")
add_line(
    "All monthly row totals match expected counts, and every timestamp month agrees with its source file month. Required fields have zero missing values and zero invalid rows. April contains 7,749 exact repeated rows; duplicates also occur in later months. All records are retained because duplicates may be repeated pickups or source duplication and the local files provide no provenance to distinguish them. Raw CSVs are untouched. There are no observed points on the NYC boundary; all NYC-inside points map to one borough."
)
add_line("### 2.5 Limitations")
add_line(
    "The data represent recorded pickups, not all requests, unique drivers, available supply, completed rides, or market share. The period is six months in 2014. Duplicate rows and boundary resolution affect totals."
)
add_line("## Chapter 3: Methodology")
add_line("### 3.1 Overall Workflow and 3.2 Preprocessing")
add_line(
    "The pipeline reads each CSV, validates row counts and required fields, derives timestamp fields, applies vectorized point-in-polygon operations, saves classified rows as Parquet, and writes summary tables and figures. No rows are removed."
)
add_line("### 3.3 Temporal Feature Engineering")
add_line(
    "The analysis extracts year, month, day, hour, weekday, and date. Monthly and weekday comparisons use per-calendar-date averages where unequal exposure would bias total counts."
)
add_line("### 3.4 Geographic Classification")
add_line(
    "Coordinates are treated as EPSG:4326. The NYC boundary is the union of the five supplied borough polygons. State polygons are from the provided 2014 Census cartographic shapefile. `contains` is used for interiors and `intersects` handles exact boundaries; zero observed points lie on the NYC boundary."
)
add_line("### 3.5 Top-Down Geographic Analysis")
add_line(
    "Every pickup is tested against NYC first. Borough classification is only performed for NYC-inside points. Outside-NYC records are classified separately to state polygons and reported as New York, New Jersey, Connecticut, other, or unmatched. A separate state polygon audit on NYC points is used only for reconciliation: 15 NYC-inside points do not intersect a state polygon. They remain eligible for borough analysis and are unmatched in state totals. This preserves the different boundary definitions rather than forcing totals to agree."
)
add_line("### 3.6 Statistical Methods")
add_line(
    "Pearson chi-square tests assess selected count-table associations; weekday goodness-of-fit expected counts are adjusted to the number of observed dates per weekday. Cramér’s V and Cohen’s w accompany test statistics. Significance level is α=0.05. Tests are omnibus with no post-hoc pairwise comparisons. The millions of pickups are not an independent random sample; temporal and spatial clustering can make p-values too small. Effect sizes and observed counts are emphasized."
)
add_line("### 3.7 Visualization Methods")
add_line(
    "Spatial density is shown as a logarithmic hexbin over the observed extent. NYC maps use the supplied polygons. Average-daily charts adjust for calendar-date exposure; borough hourly profiles show proportions within borough."
)
add_line("## Chapter 4: Exploratory Data Analysis")
add_line("### 4.1 Overall Dataset Overview")
add_line(
    f"Of {total_records:,} records, {nyc_records:,} ({pct(nyc_records,total_records)}) are inside NYC and {outside_records:,} ({pct(outside_records,total_records)}) are outside."
)
add_line("### 4.2 Temporal Analysis")
add_line(
    f"September is highest by monthly total ({months[9]:,}) and April lowest ({months[4]:,}). Average daily pickups are highest in {['April','May','June','July','August','September'][int(monthly_day.idxmax())-4]} ({monthly_day.max():,.0f}) and lowest in {['April','May','June','July','August','September'][int(monthly_day.idxmin())-4]} ({monthly_day.min():,.0f}). Hour 17 has {hours[17]:,} records, the maximum; hour 2 has {hours[2]:,}, the minimum. Mean daily count is highest on {weekday_names[int(weekday_day.idxmax())]} ({weekday_day.max():,.0f}) and lowest on {weekday_names[int(weekday_day.idxmin())]} ({weekday_day.min():,.0f}). These are observed associations and do not identify causes."
)
for cap, file in [
    ("Average daily pickup volume by month", "monthly_demand.png"),
    ("Pickup count by hour", "hourly_demand.png"),
    ("Hourly pickups across weekdays", "day_hour_heatmap.png"),
    ("Average hourly count per date, weekday/weekend", "weekday_weekend.png"),
]:
    add_line(f"![{cap}](../outputs/figures/{file})")
add_line("### 4.3 Spatial Analysis")
add_line(
    "Pickups are concentrated around NYC. The log-scaled hexbin shows counts per cell over the observed coordinate extent, not population-adjusted rates. Outside NYC, New Jersey has the largest count, followed by New York and Connecticut; one record is in Massachusetts."
)
for cap, file in [
    ("USA pickup hexbin", "usa_pickup_hexbin.png"),
    ("Outside-NYC state distribution", "outside_nyc_states.png"),
    ("NYC boundary classification", "nyc_boundary_classification.png"),
]:
    add_line(f"![{cap}](../outputs/figures/{file})")
add_line("### 4.4 NYC Borough Analysis")
add_line("| Borough | Pickups | % of NYC pickups | % of all records |")
add_line("|---|---:|---:|---:|")
for b in results["boroughs"]:
    add_line(
        f"| {b['borough']} | {b['pickups']:,} | {b['pct_nyc']:.2f}% | {b['pct_all']:.2f}% |"
    )
add_line("")
add_line(
    "Manhattan has the most pickups. Brooklyn and Queens follow. Bronx and Staten Island counts are lower. Raw counts measure total observed volume; normalized hourly profiles compare timing shape while controlling for borough total size. Manhattan and Brooklyn peak at 17:00; Queens, Bronx, and Staten Island peak at 18:00."
)
for cap, file in [
    ("NYC borough choropleth", "nyc_borough_choropleth.png"),
    ("Normalized hourly profiles by borough", "borough_hourly_profiles.png"),
]:
    add_line(f"![{cap}](../outputs/figures/{file})")
add_line("### 4.5 Uber Base Analysis")
add_line(
    "| Base code | Provided label | Pickups | % of all records | Peak hour | Peak weekday |"
)
add_line("|---|---|---:|---:|---:|---|")
base_labels = {
    "B02512": "Unter",
    "B02598": "Hinter",
    "B02617": "Weiter",
    "B02682": "Schmecken",
    "B02764": "Danach-NY",
    "B02765": "Grun",
    "B02835": "Dreist",
    "B02836": "Drinnen",
}
for b in [
    "B02512",
    "B02598",
    "B02617",
    "B02682",
    "B02764",
    "B02765",
    "B02835",
    "B02836",
]:
    v = int(base_counts.get(b, 0))
    ph = int(base_hour[b].idxmax()) if b in base_hour and v else "—"
    peak_weekday = (
        weekday_names[int(base_weekday[b].idxmax())] if b in base_weekday and v else "—"
    )
    add_line(
        f"| {b} | {base_labels[b]} | {v:,} | {pct(v,total_records)} | {ph} | {peak_weekday} |"
    )
add_line("")
add_line(
    "B02617 has the largest observed total (1,458,853), followed by B02598 and B02682. The accompanying normalized hourly profile compares timing shape across bases; monthly counts are available in the reproducible output table. Three listed codes have zero rows. Base totals do not establish driver counts, fleet size, market share, or operational capacity."
)
add_line(
    "![Normalized hourly pickup profiles by Uber base](../outputs/figures/base_hourly_profiles.png)"
)
add_line("## Chapter 5: Statistical Analysis")
add_line("### 5.1–5.2 Hypotheses and Tests")
add_line(
    "For independence tests, H0 states the categorical variables are independent and H1 states they are associated. For weekday goodness-of-fit, H0 states the expected pickup counts are proportional to weekday-date exposure; H1 states at least one weekday rate differs. α=0.05."
)
add_line("### 5.3–5.4 Results and Effect Sizes")
add_line("| Question | Test statistic | pickups | p-value | Effect size |")
add_line("|---|---:|---:|---:|---:|")
for t in results["tests"]:
    v = t.get("cramers_v", t.get("effect_size_cohens_w"))
    label = "Cramér’s V" if "cramers_v" in t else "Cohen’s w"
    add_line(
        f"| {t['question']} | χ²={t['statistic']:,.2f} | {t['df']} | {pval(t['p_value'])} | {label}={v:.3f} |"
    )
add_line("")
add_line("### 5.5 Interpretation")
add_line(
    "All omnibus tests reject H0 at α=0.05 (p<0.001). Hour-by-weekday association has V=0.106; month-by-hour V=0.023; borough-by-hour V=0.052; base-by-borough V=0.030. Weekday effect size is w=0.142 after exposure adjustment. Month-hour and base-borough effects are small despite tiny p-values, illustrating why effect size matters with millions of rows. These event-level tests are descriptive; autocorrelation, clustered locations, and retained duplicates challenge independence. The dataset covers the full set of supplied rows, so confidence intervals for a probability sample are not reported and generalization beyond these months is not supported."
)
add_line("## Chapter 6: Results and Discussion")
add_line("### 6.1 Key Findings")
add_line(
    "The data are NYC-centered, with a strong Manhattan concentration and a late-afternoon hourly peak. September is highest by total and daily average. State totals reconcile when 64 state-polygon unmatched locations are retained as unmatched."
)
add_line("### 6.2 Temporal Demand Insights")
add_line(
    "The 17:00 peak and overnight low can guide further historical analysis. Weekday and weekend profiles differ, but the six-month 2014 profile should not be assumed to describe current travel."
)
add_line("### 6.3 Geographic Demand Insights and 6.4 Borough Differences")
add_line(
    "Manhattan has 3,443,457 pickups (78.05% of NYC pickups). Outside NYC, New Jersey has 92,649 records. These counts are not area- or population-normalized. Normalized hourly profiles reveal smaller differences in temporal shape than raw borough totals suggest."
)
add_line("### 6.5 Operational Implications")
add_line(
    "Historical planning could examine curb activity and congestion near Manhattan during late afternoon. The data do not indicate driver availability, wait times, or unmet demand, so they cannot determine dispatch needs. Any operational intervention requires linked supply and service outcomes."
)
add_line("### 6.6 Limitations")
add_line(
    "The analysis covers six months of 2014; duplicates are retained; boundary resolution affects edge classification; and base metadata is absent. Associations do not establish causation."
)
add_line("## Chapter 7: Conclusion and Recommendations")
add_line("### 7.1 Summary and 7.2 Answers to Research Questions")
add_line(
    "The executed analysis includes 4,534,327 rows, of which 4,411,894 are inside NYC. Manhattan has the highest borough count; activity peaks at 17:00; September leads total and average daily demand. Base records vary but cannot represent driver or fleet totals. Omnibus tests identify associations with small to modest effect sizes."
)
add_line("### 7.3 Recommendations")
add_line(
    "Use these patterns to prioritize follow-up measurement in Manhattan and late-afternoon periods. Combine pickups with driver availability, requests, service times, traffic, and weather before operational decisions. Preserve top-down geographic classification and validate boundary provenance. Re-run on newer and longer datasets before applying the profile to current conditions."
)
add_line("### 7.4 Limitations and 7.5 Future Research")
add_line(
    "Future analyses should use longer time series, exposure-adjusted spatial rates, daily models accounting for autocorrelation, and linked trip and service outcomes. Confirm duplicate provenance and boundary lineage."
)
add_line("## References")
add_line(
    "1. Uber Technologies. (2014). *Uber pickup data, New York City, April–September 2014* [CSV files provided with project]. The local project contains no source URL or attribution metadata for these files."
)
add_line(
    "2. U.S. Census Bureau. (2014). *Cartographic Boundary Shapefile, States, 1:500,000* [provided state boundary file]. https://www.census.gov/geographies/mapping-files/time-series/geo/carto-boundary-file.html"
)
add_line(
    "3. New York City borough boundaries. (2026 file version). *Borough_Boundaries_20261028.geojson* [provided file]. The file has no source or lineage metadata; source attribution should be confirmed by the team."
)
add_line(
    "4. Cohen, J. (1988). *Statistical Power Analysis for the Behavioral Sciences* (2nd ed.). Lawrence Erlbaum Associates."
)
add_line(
    "5. Pearson, K. (1900). On the criterion that a given system of deviations from the probable in the case of a correlated system of variables is such that it can be reasonably supposed to have arisen from random sampling. *Philosophical Magazine, 50*(302), 157–175."
)
add_line("## Appendices")
add_line("### Appendix A: Geographic Reconciliation")
add_line("| State category | Records | % of all records |")
add_line("|---|---:|---:|")
for st, v in results["states"].items():
    add_line(f"| {st} | {v:,} | {pct(v,total_records)} |")
add_line(f'| **Total** | **{sum(results["states"].values()):,}** | **100.00%** |')
add_line("")
add_line(
    "The single Massachusetts point is counted once. Unmatched total 64 comprises 49 outside NYC plus 15 inside NYC but unmatched to state polygons. The 15 are still borough-classified; no observations are discarded."
)
add_line("### Appendix B: Implementation")
add_line(
    "Code: `src/analysis.py`; classified data: `outputs/processed/pickups_classified.parquet`; tables: `outputs/tables/`; geography QA: `outputs/geographic/`; figures: `outputs/figures/`. Run `python src/analysis.py`, then `python src/build_report.py` from the project root."
)
# Keep PDF text portable across the standard Helvetica font set.
report_lines = [
    s.replace("χ²", "chi-square")
    .replace("α", "alpha")
    .replace("’", "'")
    .replace("–", "-")
    .replace("—", "-")
    .replace("−", "-")
    for s in report_lines
]
md = "\n".join(report_lines) + "\n"
(REPORT_DIR / "final_report.md").write_text(md)

# CommonMark subset renderer: headings, tables, images, and paragraphs.
doc = Document()
sec = doc.sections[0]
sec.top_margin = Inches(0.65)
sec.bottom_margin = Inches(0.65)
doc.styles["Normal"].font.name = "Aptos"
doc.styles["Normal"].font.size = Pt(9.5)
title_style = doc.styles["Title"]
title_ppr = title_style.element.pPr
if title_ppr is not None:
    for border in title_ppr.findall(
        "{http://schemas.openxmlformats.org/wordprocessingml/2006/main}pBdr"
    ):
        title_ppr.remove(border)
styles = getSampleStyleSheet()
styles.add(
    ParagraphStyle(
        name="H1x",
        parent=styles["Heading1"],
        fontSize=15,
        leading=18,
        spaceBefore=10,
        spaceAfter=6,
    )
)
styles.add(
    ParagraphStyle(
        name="H2x",
        parent=styles["Heading2"],
        fontSize=11,
        leading=14,
        spaceBefore=8,
        spaceAfter=4,
    )
)
styles.add(
    ParagraphStyle(
        name="Bodyx", parent=styles["BodyText"], fontSize=8.5, leading=11, spaceAfter=5
    )
)


def clean(s):
    return re.sub(
        r"\*\*(.*?)\*\*",
        r"<b>\1</b>",
        s.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;"),
    )


story = []
i = 0
while i < len(report_lines):
    s = report_lines[i]
    if not s.strip():
        i += 1
        continue
    if s.startswith("|"):
        rows = []
        while i < len(report_lines) and report_lines[i].startswith("|"):
            row = [x.strip() for x in report_lines[i].strip("|").split("|")]
            if not all(set(x) <= set("-: ") for x in row):
                rows.append(row)
            i += 1
        if rows:
            t = doc.add_table(rows=0, cols=len(rows[0]))
            t.style = "Light Shading Accent 1"
            for row in rows:
                cells = t.add_row().cells
                for j, v in enumerate(row):
                    cells[j].text = v.replace("**", "")
            data = [[clean(v) for v in row] for row in rows]
            table = Table(
                data,
                colWidths=[7.15 * inch / len(rows[0])] * len(rows[0]),
                repeatRows=1,
            )
            table.setStyle(
                TableStyle(
                    [
                        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#D9EAF7")),
                        ("GRID", (0, 0), (-1, -1), 0.3, colors.grey),
                        ("FONTSIZE", (0, 0), (-1, -1), 6.5),
                        ("VALIGN", (0, 0), (-1, -1), "TOP"),
                        ("LEFTPADDING", (0, 0), (-1, -1), 3),
                        ("RIGHTPADDING", (0, 0), (-1, -1), 3),
                    ]
                )
            )
            story.extend([table, Spacer(1, 6)])
        continue
    if s.startswith("# "):
        p = doc.add_paragraph(s[2:], style="Title")
        p.runs[0].font.color.rgb = __import__("docx").shared.RGBColor(0, 0, 0)
        p.runs[0].font.size = Pt(24)
        story.append(Paragraph(clean(s[2:]), styles["Title"]))
    elif s.startswith("## "):
        doc.add_heading(s[3:], 1)
        story.append(Paragraph(clean(s[3:]), styles["H1x"]))
    elif s.startswith("### "):
        doc.add_heading(s[4:], 2)
        story.append(Paragraph(clean(s[4:]), styles["H2x"]))
    elif s.startswith("!["):
        m = re.search(r"\]\((.*?)\)", s)
        if m:
            path = (REPORT_DIR / m.group(1)).resolve()
            if path.exists():
                doc.add_picture(str(path), width=Inches(6))
                story.extend(
                    [
                        Image(
                            str(path), width=6.5 * inch, height=3.4 * inch, kind="bound"
                        ),
                        Spacer(1, 4),
                    ]
                )
        caption = s[2 : s.find("]")]
        doc.add_paragraph(caption)
        story.append(Paragraph(clean(caption), styles["Bodyx"]))
    else:
        doc.add_paragraph(s.replace("**", "").replace("`", ""))
        story.append(Paragraph(clean(s.replace("**", "")), styles["Bodyx"]))
    i += 1
doc.save(REPORT_DIR / "final_report.docx")


def footer(canvas, doc):
    canvas.saveState()
    canvas.setFont("Helvetica", 7)
    canvas.setFillColor(colors.grey)
    canvas.drawString(
        0.65 * inch, 0.38 * inch, "Uber Pickup Demand Analysis | Course research report"
    )
    canvas.drawRightString(7.85 * inch, 0.38 * inch, str(doc.page))
    canvas.restoreState()


SimpleDocTemplate(
    str(REPORT_DIR / "final_report.pdf"),
    pagesize=letter,
    rightMargin=0.65 * inch,
    leftMargin=0.65 * inch,
    topMargin=0.62 * inch,
    bottomMargin=0.65 * inch,
    title="Uber Pickup Demand Analysis",
).build(story, onFirstPage=footer, onLaterPages=footer)
print("Generated final_report.md, final_report.docx, and final_report.pdf")

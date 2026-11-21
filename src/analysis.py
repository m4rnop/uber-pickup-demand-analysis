"""Validate, classify, analyze, and visualize the 2014 Uber pickup records."""

from __future__ import annotations

import json
import math
from pathlib import Path

import geopandas as gpd
import matplotlib
import numpy as np
import pandas as pd
import shapely

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import seaborn as sns

PROJECT_ROOT = Path(__file__).resolve().parents[1]
DATA_DIR = PROJECT_ROOT / "data"
OUTPUT_DIR = PROJECT_ROOT / "outputs"
FIGURE_DIR, TABLE_DIR, GEOGRAPHIC_DIR = (
    OUTPUT_DIR / "figures",
    OUTPUT_DIR / "tables",
    OUTPUT_DIR / "geographic",
)
MONTHS = ["apr", "may", "jun", "jul", "aug", "sep"]
MONTH_NUMBERS = {"apr": 4, "may": 5, "jun": 6, "jul": 7, "aug": 8, "sep": 9}
EXPECTED_ROWS = {
    "apr": 564516,
    "may": 652435,
    "jun": 663844,
    "jul": 796121,
    "aug": 829275,
    "sep": 1028136,
}
BOROUGH_ORDER = ["Manhattan", "Brooklyn", "Queens", "Bronx", "Staten Island"]
BASE_CODES = [
    "B02512",
    "B02598",
    "B02617",
    "B02682",
    "B02764",
    "B02765",
    "B02835",
    "B02836",
]

PICKUP_COLUMNS = ["Date/Time", "Lat", "Lon", "Base"]
PICKUP_TIMESTAMP_FORMAT = "%m/%d/%Y %H:%M:%S"


def pickup_sources():
    sources = {month: DATA_DIR / f"uber-raw-data-{month}14.csv" for month in MONTHS}
    missing = [path.name for path in sources.values() if not path.is_file()]
    if missing:
        raise FileNotFoundError(
            f"Missing monthly pickup files: {', '.join(missing)}. "
            "See data/README.md for download instructions."
        )
    return sources


def setup_output_directories():
    """Create output folders and configure a consistent chart style."""
    for p in (FIGURE_DIR, TABLE_DIR, GEOGRAPHIC_DIR, OUTPUT_DIR / "processed"):
        p.mkdir(parents=True, exist_ok=True)
    sns.set_theme(style="whitegrid")


def chi_square_survival_probability(statistic, degrees_of_freedom):
    """Chi-square survival probability via regularized upper incomplete gamma."""
    gamma_argument = statistic / 2
    gamma_shape = degrees_of_freedom / 2
    if statistic <= 0:
        return 1.0
    if gamma_argument < gamma_shape + 1:
        term = total = 1 / gamma_shape
        for n in range(1, 10000):
            term *= gamma_argument / (gamma_shape + n)
            total += term
            if abs(term) < abs(total) * 1e-14:
                break
        lower_tail = total * math.exp(
            -gamma_argument
            + gamma_shape * math.log(gamma_argument)
            - math.lgamma(gamma_shape)
        )
        return max(0.0, min(1.0, 1 - lower_tail))

    b_value = gamma_argument + 1 - gamma_shape
    c_value = 1e300
    d_value = 1 / b_value
    product = d_value
    for i in range(1, 10000):
        numerator = -i * (i - gamma_shape)
        b_value += 2
        d_value = numerator * d_value + b_value
        if abs(d_value) < 1e-300:
            d_value = 1e-300
        c_value = b_value + numerator / c_value
        if abs(c_value) < 1e-300:
            c_value = 1e-300
        d_value = 1 / d_value
        delta = d_value * c_value
        product *= delta
        if abs(delta - 1) < 1e-14:
            break
    probability = (
        math.exp(
            -gamma_argument
            + gamma_shape * math.log(gamma_argument)
            - math.lgamma(gamma_shape)
        )
        * product
    )
    return max(0.0, min(1.0, probability))


def load_boundaries():
    """Load borough and state polygons in longitude/latitude coordinates."""
    borough_frame = gpd.read_file(
        DATA_DIR / "Borough_Boundaries_20261028.geojson"
    ).to_crs(4326)
    state_frame = gpd.read_file(
        DATA_DIR / "boundaries/cb_2014_us_state_500k.shp"
    ).to_crs(4326)
    borough_geometries = {
        row.boroname: row.geometry for row in borough_frame.itertuples()
    }
    state_name_column = "NAME" if "NAME" in state_frame.columns else "name"
    state_geometries = {
        str(getattr(row, state_name_column)): row.geometry
        for row in state_frame.itertuples()
    }
    nyc_boundary = shapely.union_all(list(borough_geometries.values()))
    return nyc_boundary, borough_geometries, state_geometries


def classify_coordinates(longitudes, latitudes, nyc_boundary, boroughs, states):
    """Assign NYC membership first, then boroughs or outside-NYC states."""
    inside_nyc = shapely.contains_xy(nyc_boundary, longitudes, latitudes)
    # Preserve boundary behavior explicitly. A point on NYC boundary is treated as inside.
    boundary_point = ~inside_nyc & shapely.intersects_xy(
        nyc_boundary, longitudes, latitudes
    )
    inside_nyc |= boundary_point
    borough_labels = np.full(len(longitudes), "", dtype=object)
    for borough_name, geometry in boroughs.items():
        inside_borough = inside_nyc & shapely.contains_xy(
            geometry, longitudes, latitudes
        )
        on_borough_edge = (
            inside_nyc
            & ~inside_borough
            & shapely.intersects_xy(geometry, longitudes, latitudes)
        )
        unassigned = borough_labels == ""
        borough_labels[(inside_borough | on_borough_edge) & unassigned] = borough_name
    # NYC polygon is union of boroughs. Numerical/topology gaps remain explicitly unmatched.
    state_labels = np.full(len(longitudes), "", dtype=object)
    outside_nyc = ~inside_nyc
    for state_name, geometry in states.items():
        inside_state = outside_nyc & shapely.contains_xy(
            geometry, longitudes, latitudes
        )
        on_state_edge = (
            outside_nyc
            & ~inside_state
            & shapely.intersects_xy(geometry, longitudes, latitudes)
        )
        unassigned = state_labels == ""
        state_labels[(inside_state | on_state_edge) & unassigned] = state_name
    return inside_nyc, boundary_point, borough_labels, state_labels


def audit_nyc_states(longitudes, latitudes, inside_nyc, states):
    """Audit NYC points against state polygons for geographic reconciliation."""
    state_audit_labels = np.full(len(longitudes), "", dtype=object)
    # Only state polygons whose bounding boxes intersect the NYC bounding box are relevant.
    nyc_bounds = (-74.26, 40.49, -71.7, 45.02)
    for state_name, geometry in states.items():
        min_longitude, min_latitude, max_longitude, max_latitude = geometry.bounds
        if (
            max_longitude < nyc_bounds[0]
            or min_longitude > nyc_bounds[2]
            or max_latitude < nyc_bounds[1]
            or min_latitude > nyc_bounds[3]
        ):
            continue
        inside_state = inside_nyc & shapely.contains_xy(geometry, longitudes, latitudes)
        on_state_edge = (
            inside_nyc
            & ~inside_state
            & shapely.intersects_xy(geometry, longitudes, latitudes)
        )
        unassigned = state_audit_labels == ""
        state_audit_labels[(inside_state | on_state_edge) & unassigned] = state_name
    return state_audit_labels


def load_and_classify():
    """Read monthly files, validate them, and add temporal/geographic labels."""
    sources = pickup_sources()
    nyc_boundary, borough_geometries, state_geometries = load_boundaries()
    frames = []
    quality = []
    for month_key, source_path in sources.items():
        month_data = pd.read_csv(source_path, usecols=PICKUP_COLUMNS)
        month_data["month_file"] = month_key.title()
        # Exact duplicates are flagged, never discarded. April duplicates retained.
        duplicate_count = month_data.duplicated(
            subset=["Date/Time", "Lat", "Lon", "Base"]
        ).sum()
        missing_cells = int(month_data[PICKUP_COLUMNS].isna().sum().sum())
        timestamp = pd.to_datetime(
            month_data["Date/Time"], format=PICKUP_TIMESTAMP_FORMAT, errors="coerce"
        )
        for column in ("Lat", "Lon"):
            month_data[column] = pd.to_numeric(month_data[column], errors="coerce")
        invalid = (
            timestamp.isna()
            | ~month_data["Lat"].between(-90, 90)
            | ~month_data["Lon"].between(-180, 180)
            | ~month_data["Base"].isin(BASE_CODES)
        )
        wrong_month = timestamp.notna() & (
            timestamp.dt.year.ne(2014) | timestamp.dt.month.ne(MONTH_NUMBERS[month_key])
        )
        if invalid.any() or wrong_month.any():
            raise ValueError(
                f"{source_path.name}: {invalid.sum():,} invalid rows and "
                f"{wrong_month.sum():,} rows outside the expected month. "
                "Check the input against the original source in data/README.md."
            )
        month_data["Date/Time"] = timestamp
        quality.append(
            {
                "month": month_key.title(),
                "rows": len(month_data),
                "expected_rows": EXPECTED_ROWS[month_key],
                "duplicate_rows": int(duplicate_count),
                "missing_cells": missing_cells,
                "invalid_rows": int(invalid.sum()),
                "wrong_month_rows": int(wrong_month.sum()),
                "rows_match_expected": len(month_data) == EXPECTED_ROWS[month_key],
            }
        )
        longitudes = month_data["Lon"].to_numpy()
        latitudes = month_data["Lat"].to_numpy()
        inside_nyc, boundary_point, borough, outside_state = classify_coordinates(
            longitudes, latitudes, nyc_boundary, borough_geometries, state_geometries
        )
        state_audit = audit_nyc_states(
            longitudes, latitudes, inside_nyc, state_geometries
        )
        month_data["inside_nyc"] = inside_nyc
        month_data["nyc_boundary_point"] = boundary_point
        month_data["borough"] = borough
        month_data["state_outside_nyc"] = outside_state
        month_data["state_geometry_audit_inside_nyc"] = state_audit
        month_data["year"] = timestamp.dt.year
        month_data["month"] = timestamp.dt.month
        month_data["day"] = timestamp.dt.day
        month_data["hour"] = timestamp.dt.hour
        month_data["day_of_week"] = timestamp.dt.day_of_week
        month_data["date"] = timestamp.dt.date
        frames.append(month_data)
    all_df = pd.concat(frames, ignore_index=True)
    all_df.to_parquet(OUTPUT_DIR / "processed/pickups_classified.parquet", index=False)
    pd.DataFrame(quality).to_csv(TABLE_DIR / "monthly_data_quality.csv", index=False)
    return all_df, borough_geometries, quality


def savefig(name):
    """Save the current Matplotlib chart in the project's figures folder."""
    plt.tight_layout()
    plt.savefig(FIGURE_DIR / name, dpi=180, bbox_inches="tight")
    plt.close()


def charts(pickups, borough_geometries):
    """Create geographic and temporal charts from the classified pickup rows."""
    # full USA coverage: coordinate density on geographic axes, with bounds shown in title
    plt.figure(figsize=(10, 6))
    plt.hexbin(
        pickups.Lon, pickups.Lat, gridsize=100, mincnt=1, bins="log", cmap="viridis"
    )
    plt.colorbar(label="Pickup records per hexagon (log scale)")
    plt.xlabel("Longitude (degrees)")
    plt.ylabel("Latitude (degrees)")
    plt.title("USA-level Uber pickup distribution, April–September 2014")
    savefig("usa_pickup_hexbin.png")
    ext = pickups[~pickups.inside_nyc]
    plt.figure(figsize=(8, 5))
    ext.state_outside_nyc.replace("", "Unmatched").value_counts().plot.bar(
        color="#4472C4"
    )
    plt.ylabel("Pickup records")
    plt.xlabel("State classification (outside NYC only)")
    plt.title("Outside-NYC pickup counts by state")
    savefig("outside_nyc_states.png")
    fig, ax = plt.subplots(figsize=(8, 8))
    nyc_boundary = shapely.union_all(list(borough_geometries.values()))
    gpd.GeoSeries([nyc_boundary], crs=4326).boundary.plot(
        ax=ax, color="black", linewidth=1.4
    )
    ax.scatter(
        pickups.Lon,
        pickups.Lat,
        c=np.where(pickups.inside_nyc, "#d95f02", "#1b9e77"),
        s=0.12,
        alpha=0.3,
        rasterized=True,
    )
    ax.set(
        xlim=(-74.3, -73.65),
        ylim=(40.45, 41.05),
        xlabel="Longitude",
        ylabel="Latitude",
        title="NYC boundary classification (orange inside, green outside)",
    )
    savefig("nyc_boundary_classification.png")
    counts = (
        pickups[pickups.inside_nyc]
        .borough.value_counts()
        .reindex(BOROUGH_ORDER, fill_value=0)
    )
    borough_shapes = gpd.GeoDataFrame(
        {
            "boroname": list(borough_geometries),
            "geometry": list(borough_geometries.values()),
        },
        crs=4326,
    )
    borough_shapes["pickup_count"] = borough_shapes.boroname.map(counts).fillna(0)
    fig, ax = plt.subplots(figsize=(8, 8))
    borough_shapes.plot(
        column="pickup_count",
        cmap="OrRd",
        legend=True,
        edgecolor="white",
        linewidth=0.7,
        ax=ax,
        legend_kwds={"label": "Pickup records"},
    )
    ax.set_axis_off()
    ax.set_title("NYC pickups by borough, April–September 2014")
    savefig("nyc_borough_choropleth.png")
    counts.sort_values().plot.barh(figsize=(8, 4), color="#4472C4")
    plt.xlabel("Pickups (NYC records only)")
    plt.ylabel("Borough")
    plt.title("Pickup counts by NYC borough")
    savefig("borough_pickup_counts.png")
    plt.figure(figsize=(10, 5))
    pickups.groupby(["month", "date"]).size().groupby("month").mean().plot(marker="o")
    plt.xticks(range(4, 10), ["April", "May", "June", "July", "August", "September"])
    plt.xlabel("Month")
    plt.ylabel("Mean pickup records per calendar day")
    plt.title("Average daily pickup demand by month")
    savefig("monthly_demand.png")
    plt.figure(figsize=(9, 4))
    pickups.groupby("hour").size().reindex(range(24), fill_value=0).plot.bar(
        color="#4472C4"
    )
    plt.xlabel("Hour of day (local timestamp)")
    plt.ylabel("Pickup records")
    plt.title("Pickup demand by hour")
    savefig("hourly_demand.png")
    weekday_names = [
        "Monday",
        "Tuesday",
        "Wednesday",
        "Thursday",
        "Friday",
        "Saturday",
        "Sunday",
    ]
    average_by_weekday = (
        pickups.groupby(["day_of_week", "date"])
        .size()
        .groupby("day_of_week")
        .mean()
        .reindex(range(7))
    )
    plt.figure(figsize=(9, 4))
    average_by_weekday.plot.bar(color="#4472C4")
    plt.xticks(range(7), weekday_names, rotation=25, ha="right")
    plt.xlabel("Day of week")
    plt.ylabel("Mean pickups per calendar date")
    plt.title("Average daily pickups by weekday")
    savefig("weekday_demand.png")
    hm = pd.crosstab(pickups.day_of_week, pickups.hour).reindex(
        index=range(7), columns=range(24), fill_value=0
    )
    plt.figure(figsize=(12, 4))
    sns.heatmap(hm, cmap="mako")
    plt.xlabel("Hour")
    plt.ylabel("Day (Monday=0)")
    plt.title("Pickup count by day of week and hour")
    savefig("day_hour_heatmap.png")
    mh = pd.crosstab(pickups.month, pickups.hour).reindex(
        index=range(4, 10), columns=range(24), fill_value=0
    )
    plt.figure(figsize=(12, 4))
    sns.heatmap(mh, cmap="mako")
    plt.xlabel("Hour")
    plt.ylabel("Month")
    plt.title("Pickup count by month and hour")
    savefig("month_hour_heatmap.png")
    pickups["weekpart"] = np.where(pickups.day_of_week >= 5, "Weekend", "Weekday")
    daily_hour = (
        pickups.groupby(["weekpart", "date", "hour"])
        .size()
        .groupby(["weekpart", "hour"])
        .mean()
        .unstack(0)
    )
    daily_hour.plot(figsize=(10, 5))
    plt.xlabel("Hour")
    plt.ylabel("Mean pickups per calendar date")
    plt.title("Average hourly pickups per date: weekdays and weekends")
    savefig("weekday_weekend.png")
    ny = pickups[pickups.inside_nyc]
    hourly = pd.crosstab(ny.hour, ny.borough, normalize="columns").reindex(
        index=range(24), columns=BOROUGH_ORDER, fill_value=0
    )
    hourly.plot(figsize=(10, 5))
    plt.xlabel("Hour")
    plt.ylabel("Share of borough pickups")
    plt.title("Normalized hourly profile by NYC borough")
    savefig("borough_hourly_profiles.png")
    # monthly, daily, base outputs
    ny.groupby(["borough", "month"]).size().unstack(fill_value=0).reindex(
        BOROUGH_ORDER
    ).to_csv(TABLE_DIR / "borough_monthly_counts.csv")
    pd.crosstab(ny.borough, ny.day_of_week).reindex(BOROUGH_ORDER).to_csv(
        TABLE_DIR / "borough_weekday_counts.csv"
    )


def stats_and_tables(pickups, quality):
    """Write geographic, temporal, base, and statistical summary tables."""
    n = len(pickups)
    ny = pickups[pickups.inside_nyc]
    outside = pickups[~pickups.inside_nyc]
    b = ny.borough.value_counts().reindex(BOROUGH_ORDER, fill_value=0)
    borough = pd.DataFrame(
        {
            "borough": b.index,
            "pickups": b.values,
            "pct_nyc": b.values / len(ny) * 100,
            "pct_all": b.values / n * 100,
        }
    )
    borough.to_csv(TABLE_DIR / "borough_summary.csv", index=False)
    outside_counts = outside.state_outside_nyc.replace("", "Unmatched").value_counts()
    outside_counts.rename_axis("state").rename("records").to_csv(
        GEOGRAPHIC_DIR / "outside_nyc_state_counts.csv"
    )
    # State totals use the state polygon audit plus separately classified outside-NYC records.
    nyc_state = ny.state_geometry_audit_inside_nyc.replace(
        "", "Unmatched"
    ).value_counts()
    state_counts = pd.Series(
        {
            "New York": int(
                nyc_state.get("New York", 0) + outside_counts.get("New York", 0)
            ),
            "New Jersey": int(
                nyc_state.get("New Jersey", 0) + outside_counts.get("New Jersey", 0)
            ),
            "Connecticut": int(
                nyc_state.get("Connecticut", 0) + outside_counts.get("Connecticut", 0)
            ),
            "Massachusetts": int(
                nyc_state.get("Massachusetts", 0)
                + outside_counts.get("Massachusetts", 0)
            ),
            "Other classified states": int(
                sum(
                    v
                    for k, v in outside_counts.items()
                    if k
                    not in [
                        "New York",
                        "New Jersey",
                        "Connecticut",
                        "Massachusetts",
                        "Unmatched",
                    ]
                )
                + sum(
                    v
                    for k, v in nyc_state.items()
                    if k
                    not in [
                        "New York",
                        "New Jersey",
                        "Connecticut",
                        "Massachusetts",
                        "Unmatched",
                    ]
                )
            ),
            "Unmatched": int(
                outside_counts.get("Unmatched", 0) + nyc_state.get("Unmatched", 0)
            ),
        }
    )
    state_counts.to_csv(
        GEOGRAPHIC_DIR / "geographic_reconciliation.csv", header=["records"]
    )
    geo_quality = pd.DataFrame(
        [
            {
                "measure": "Total pickup records",
                "count": n,
                "denominator": "all records",
            },
            {
                "measure": "Inside NYC boundary",
                "count": len(ny),
                "denominator": "all records",
            },
            {
                "measure": "Outside NYC boundary",
                "count": len(outside),
                "denominator": "all records",
            },
            {
                "measure": "Inside NYC without borough match",
                "count": int((ny.borough == "").sum()),
                "denominator": "inside NYC",
            },
            {
                "measure": "Outside NYC unmatched to state",
                "count": int((outside.state_outside_nyc == "").sum()),
                "denominator": "outside NYC",
            },
            {
                "measure": "Inside NYC unmatched to 2014 state polygon",
                "count": int((ny.state_geometry_audit_inside_nyc == "").sum()),
                "denominator": "inside NYC",
            },
            {
                "measure": "NYC boundary points",
                "count": int(pickups.nyc_boundary_point.sum()),
                "denominator": "all records",
            },
            {
                "measure": "Suspicious geography total",
                "count": int(
                    state_counts.get("Unmatched", 0)
                    + state_counts.get("Massachusetts", 0)
                ),
                "denominator": "all records",
            },
        ]
    )
    geo_quality.to_csv(GEOGRAPHIC_DIR / "geographic_data_quality.csv", index=False)
    pd.DataFrame(quality).to_csv(TABLE_DIR / "monthly_data_quality.csv", index=False)
    weekday = pickups.day_of_week.value_counts().reindex(range(7), fill_value=0)
    hourday = pd.crosstab(pickups.day_of_week, pickups.hour).reindex(
        index=range(7), columns=range(24), fill_value=0
    )
    monthhour = pd.crosstab(pickups.month, pickups.hour).reindex(
        index=range(4, 10), columns=range(24), fill_value=0
    )
    # Pearson chi-square with Cramer's V; pickup events treated as counts, not causal evidence.
    tests = []

    def test(label, table):
        obs = np.asarray(table, dtype=float)
        exp = obs.sum(1, keepdims=True) @ obs.sum(0, keepdims=True) / obs.sum()
        x = float(((obs - exp) ** 2 / exp).sum())
        dof = (obs.shape[0] - 1) * (obs.shape[1] - 1)
        v = math.sqrt(x / (obs.sum() * min(obs.shape[0] - 1, obs.shape[1] - 1)))
        tests.append(
            {
                "question": label,
                "test": "Pearson chi-square independence",
                "statistic": x,
                "df": dof,
                "p_value": chi_square_survival_probability(x, dof),
                "cramers_v": v,
                "n": int(obs.sum()),
            }
        )

    test("Is hour associated with day of week?", hourday)
    test("Does month-hour distribution vary across months?", monthhour)
    test(
        "Does hourly pickup profile differ by borough?",
        pd.crosstab(ny.borough, ny.hour).reindex(BOROUGH_ORDER, fill_value=0),
    )
    test(
        "Are Uber base and borough pickup distributions associated?",
        pd.crosstab(ny.borough, ny.Base).reindex(BOROUGH_ORDER),
    )
    # Equal weekday counts goodness-of-fit, with Cohen w.
    obs = weekday.to_numpy(float)
    exposures = (
        pickups[["date", "day_of_week"]]
        .drop_duplicates()
        .groupby("day_of_week")
        .size()
        .reindex(range(7))
        .to_numpy(float)
    )
    exp = obs.sum() * exposures / exposures.sum()
    x = float(((obs - exp) ** 2 / exp).sum())
    tests.append(
        {
            "question": "Does mean demand per calendar date differ by weekday?",
            "test": "Chi-square goodness of fit adjusted for weekday-date exposure",
            "statistic": x,
            "df": 6,
            "p_value": chi_square_survival_probability(x, 6),
            "effect_size_cohens_w": math.sqrt(x / obs.sum()),
            "n": int(obs.sum()),
            "date_exposures": exposures.astype(int).tolist(),
        }
    )
    pd.DataFrame(tests).to_csv(TABLE_DIR / "statistical_tests.csv", index=False)
    # temporal/base summaries
    pickups.groupby("month").size().rename("pickups").to_csv(
        TABLE_DIR / "monthly_counts.csv"
    )
    pickups.groupby("hour").size().rename("pickups").to_csv(
        TABLE_DIR / "hourly_counts.csv"
    )
    pickups.groupby("day_of_week").size().rename("pickups").to_csv(
        TABLE_DIR / "weekday_counts.csv"
    )
    pickups.Base.value_counts().reindex(BASE_CODES, fill_value=0).rename(
        "pickups"
    ).to_csv(TABLE_DIR / "base_counts.csv")
    pickups.groupby(["Base", "month"]).size().unstack(fill_value=0).to_csv(
        TABLE_DIR / "base_monthly_counts.csv"
    )
    ny.groupby(["borough", "hour"]).size().unstack(fill_value=0).reindex(
        BOROUGH_ORDER
    ).to_csv(TABLE_DIR / "borough_hourly_counts.csv")
    ny.groupby(["borough", "Base"]).size().unstack(fill_value=0).reindex(
        BOROUGH_ORDER
    ).to_csv(TABLE_DIR / "borough_base_counts.csv")
    pickups.groupby(["Base", "hour"]).size().unstack(fill_value=0).to_csv(
        TABLE_DIR / "base_hourly_counts.csv"
    )
    pickups.groupby(["Base", "day_of_week"]).size().unstack(fill_value=0).to_csv(
        TABLE_DIR / "base_weekday_counts.csv"
    )
    base_hour = pd.crosstab(pickups.hour, pickups.Base, normalize="columns")
    base_hour.plot(figsize=(10, 5))
    plt.xlabel("Hour")
    plt.ylabel("Share of each base's pickups")
    plt.title("Normalized hourly pickup profiles by Uber base")
    savefig("base_hourly_profiles.png")
    return {
        "n": n,
        "nyc_n": len(ny),
        "outside_n": len(outside),
        "borough": borough,
        "states": state_counts,
        "tests": tests,
        "quality": quality,
        "hourly": pickups.groupby("hour").size(),
        "monthly": pickups.groupby("month").size(),
        "weekday": weekday,
        "bases": pickups.Base.value_counts().reindex(BASE_CODES, fill_value=0),
        "unmatched_inside": int((ny.borough == "").sum()),
        "outside_unmatched": int((outside.state_outside_nyc == "").sum()),
        "boundary_points": int(pickups.nyc_boundary_point.sum()),
        "inside_state_unmatched": int((ny.state_geometry_audit_inside_nyc == "").sum()),
    }


def main():
    """Run the complete analysis and save tables, figures, and results JSON."""
    setup_output_directories()
    pickups, borough_geometries, quality = load_and_classify()
    charts(pickups, borough_geometries)
    results = stats_and_tables(pickups, quality)
    # Core validation and machine-readable result snapshot.
    results_json = {
        k: (v.to_dict() if isinstance(v, (pd.Series, pd.DataFrame)) else v)
        for k, v in results.items()
        if k
        not in [
            "borough",
            "states",
            "tests",
            "quality",
            "hourly",
            "monthly",
            "weekday",
            "bases",
        ]
    }
    results_json.update(
        {
            "monthly_counts": {
                str(month): int(count) for month, count in results["monthly"].items()
            },
            "hour_counts": {
                str(hour): int(count) for hour, count in results["hourly"].items()
            },
            "weekday_counts": {
                str(day): int(count) for day, count in results["weekday"].items()
            },
            "boroughs": results["borough"].to_dict(orient="records"),
            "states": results["states"].to_dict(),
            "bases": {
                str(base): int(count) for base, count in results["bases"].items()
            },
            "tests": results["tests"],
            "quality": results["quality"],
        }
    )
    (TABLE_DIR / "results.json").write_text(
        json.dumps(results_json, indent=2, default=str)
    )
    print(json.dumps(results_json, indent=2, default=str))


if __name__ == "__main__":
    main()

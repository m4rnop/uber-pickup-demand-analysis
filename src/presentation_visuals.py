"""Build the Canva PNG collection from the six raw pickup files and local boundaries."""

import calendar
from itertools import cycle

import geopandas as gpd
import matplotlib
import numpy as np
import pandas as pd
import shapely
from PIL import Image, ImageDraw, ImageFont

matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.colors import LinearSegmentedColormap, LogNorm, Normalize
from matplotlib.text import Text
from matplotlib.ticker import FuncFormatter
from pyproj import Transformer

from analysis import BOROUGH_ORDER, DATA_DIR, MONTH_NUMBERS, MONTHS, OUTPUT_DIR, classify_coordinates

DEST = OUTPUT_DIR / "presentation_visuals"
COLUMNS = ["Date/Time", "Lat", "Lon", "Base"]
MONTHS_TITLE = [month.title() for month in MONTHS]
DPI = 300
SEED = 369
ORANGE = "#F59E0B"
INK = "#15263C"
BLUE = "#147E9D"
LAND = "#475A72"
DENSITY = LinearSegmentedColormap.from_list(
    "pickup_density", ["#254766", "#327F91", "#65CAB8", ORANGE, "#FFEB90"]
)
plt.rcParams.update({"font.family": "DejaVu Sans", "text.color": INK,
                     "axes.labelcolor": INK, "xtick.color": INK, "ytick.color": INK})


def load_pickups():
    frames, audit = [], []
    for key in MONTHS:
        path = DATA_DIR / f"uber-raw-data-{key}14.csv"
        frame = pd.read_csv(path, usecols=COLUMNS)
        timestamp = pd.to_datetime(frame["Date/Time"], format="%m/%d/%Y %H:%M:%S",
                                   errors="coerce")
        for column in ["Lat", "Lon"]:
            frame[column] = pd.to_numeric(frame[column], errors="coerce")
        valid_coordinates = frame.Lat.between(-90, 90) & frame.Lon.between(-180, 180)
        expected_date = timestamp.dt.year.eq(2014) & timestamp.dt.month.eq(MONTH_NUMBERS[key])
        keep = timestamp.notna() & expected_date & valid_coordinates
        audit.append({
            "source": path.relative_to(DATA_DIR.parent).as_posix(),
            "rows": len(frame),
            "missing_cells": int(frame.isna().sum().sum()),
            "invalid_timestamp": int(timestamp.isna().sum()),
            "wrong_month_or_year": int((timestamp.notna() & ~expected_date).sum()),
            "invalid_coordinates": int((~valid_coordinates).sum()),
            "duplicate_rows_retained": int(frame.loc[keep].duplicated().sum()),
            "excluded_rows": int((~keep).sum()),
        })
        cleaned = frame.loc[keep].copy()
        ts = timestamp.loc[keep]
        cleaned["Date/Time"] = ts
        cleaned["month"] = ts.dt.month.astype("int8")
        cleaned["month_name"] = pd.Categorical.from_codes(
            cleaned["month"] - 4, categories=MONTHS_TITLE
        )
        cleaned["day"] = ts.dt.day.astype("int8")
        cleaned["weekday_number"] = ts.dt.day_of_week.astype("int8")
        cleaned["day_name"] = pd.Categorical.from_codes(
            cleaned.weekday_number, categories=list(calendar.day_name)
        )
        cleaned["hour"] = ts.dt.hour.astype("int8")
        cleaned["date"] = ts.dt.normalize()
        frames.append(cleaned)
    return pd.concat(frames, ignore_index=True), pd.DataFrame(audit)


def read_boundary(path, name):
    frame = gpd.read_file(path).set_index(name)[["geometry"]]
    if frame.crs is None or frame.geometry.is_empty.any() or frame.geometry.isna().any():
        raise ValueError(f"Missing CRS or geometry in {path}")
    invalid = ~frame.is_valid
    if invalid.any():
        frame.loc[invalid, "geometry"] = frame.loc[invalid].geometry.make_valid()
        frame["geometry"] = frame.geometry.map(
            lambda geometry: shapely.union_all([
                part for part in shapely.get_parts(geometry)
                if part.geom_type in {"Polygon", "MultiPolygon"}
            ])
        )
    if frame.geometry.is_empty.any() or not frame.is_valid.all():
        raise ValueError(f"Could not prepare polygon boundaries in {path}")
    return frame, {"source": path.relative_to(DATA_DIR.parent).as_posix(),
                   "crs": frame.crs.to_string(), "features": len(frame),
                   "invalid_repaired": int(invalid.sum())}


def export(fig, category, name):
    for variant in ("white_bg", "transparent"):
        folder = DEST / category / variant
        folder.mkdir(parents=True, exist_ok=True)
        if variant == "transparent":
            for label in fig.findobj(Text):
                label.set_color("white")
        fig.savefig(folder / f"{name}.png", dpi=DPI, transparent=variant == "transparent",
                    facecolor="white" if variant == "white_bg" else "none")
    plt.close(fig)


def chart(title, subtitle):
    fig, ax = plt.subplots(figsize=(11, 6))
    fig.subplots_adjust(left=.105, right=.95, bottom=.15, top=.76)
    fig.text(.105, .90, title, fontsize=27, weight="bold")
    fig.text(.105, .83, subtitle, fontsize=12, color="#425670")
    return fig, ax


def count_charts(pickups):
    groups = [
        ("monthly", "Month", "month", range(4, 10), MONTHS_TITLE, ("bar", "line", "area")),
        ("weekday", "Day of week", "weekday_number", range(7),
         list(calendar.day_abbr), ("bar", "line")),
        ("hourly", "Hour of day", "hour", range(24), list(range(24)), ("bar", "line")),
    ]
    for name, label, column, keys, labels, kinds in groups:
        counts = pickups.groupby(column).size().reindex(keys, fill_value=0)
        x = np.arange(len(counts))
        peak = int(np.argmax(counts))
        for kind in kinds:
            fig, ax = chart(f"Uber pickups by {label.lower()}",
                            f"April–September 2014  •  {len(pickups):,} pickup records")
            if kind == "bar":
                ax.bar(x, counts, color=[ORANGE if i == peak else BLUE for i in x], zorder=3)
            else:
                if kind == "area":
                    ax.fill_between(x, counts, color=BLUE, alpha=.24)
                ax.plot(x, counts, color=BLUE, linewidth=3, zorder=3)
                ax.scatter(peak, counts.iloc[peak], color=ORANGE, s=65, zorder=4)
            ax.annotate(f"{counts.iloc[peak]:,}  ·  {counts.iloc[peak] / len(pickups):.1%}",
                        (peak, counts.iloc[peak]), xytext=(0, 10), textcoords="offset points",
                        ha="center", fontsize=10, weight="bold")
            ax.set(xlabel=label, ylabel="Pickup records",
                   ylim=(0, counts.max() * 1.23), xlim=(-.65, len(x) - .35))
            ax.set_xticks(x, labels)
            ax.yaxis.set_major_formatter(FuncFormatter(lambda val, _: f"{val:,.0f}"))
            ax.spines[["top", "right", "left"]].set_visible(False)
            ax.spines["bottom"].set_color("#B0BCCC")
            ax.tick_params(length=0, pad=7)
            ax.grid(axis="y", alpha=.2)
            export(fig, "charts", f"{name}_pickups_{kind}")


def base_charts(pickups):
    totals = pickups.groupby("Base").size().sort_values(ascending=False)
    totals = totals[totals > 0]
    palette = ["#147E9D", "#E07832", "#8B72C5", "#43A17C", "#CE5B86", "#AB8937"]
    colors = dict(zip(totals.index, cycle(palette)))
    period = "April–September 2014"
    fig, ax = chart("Uber pickups by dispatch base",
                    f"{period}  •  {len(totals)} base codes with recorded pickups")
    positions = np.arange(len(totals))
    bars = ax.barh(positions, totals, color=[colors[base] for base in totals.index])
    ax.bar_label(bars, labels=[f"{n:,}  ·  {n / totals.sum():.1%}" for n in totals],
                 padding=7, fontsize=10)
    ax.set_yticks(positions, totals.index)
    ax.invert_yaxis()
    ax.set(xlim=(0, totals.max() * 1.37), xlabel="Pickup records")
    ax.xaxis.set_major_formatter(FuncFormatter(lambda val, _: f"{val:,.0f}"))
    ax.spines[:].set_visible(False)
    ax.tick_params(length=0, pad=7)
    export(fig, "charts", "base_pickups_bar")

    for suffix, column, keys, labels, axis_label in [
        ("monthly", "month", range(4, 10), MONTHS_TITLE, "Month"),
        ("weekday", "weekday_number", range(7), list(calendar.day_abbr), "Day of week"),
        ("hourly", "hour", range(24), list(range(24)), "Hour of day"),
    ]:
        counts = (pickups.groupby([column, "Base"]).size().unstack(fill_value=0)
                  .reindex(index=keys, columns=totals.index, fill_value=0))
        fig, ax = chart(f"Uber pickups by base and {axis_label.lower()}", period)
        x = np.arange(len(keys))
        for base in counts:
            ax.plot(x, counts[base], label=base, color=colors[base], linewidth=2.5,
                    marker="o" if len(keys) < 8 else None, markersize=4)
        ax.set_xticks(x, labels)
        ax.set(xlabel=axis_label, ylabel="Pickup records", ylim=(0, counts.max().max() * 1.13))
        ax.yaxis.set_major_formatter(FuncFormatter(lambda val, _: f"{val:,.0f}"))
        ax.spines[["top", "right", "left"]].set_visible(False)
        ax.spines["bottom"].set_color("#B0BCCC")
        ax.tick_params(length=0, pad=7)
        ax.grid(axis="y", alpha=.2)
        ax.legend(loc="lower left", bbox_to_anchor=(0, 1.01), ncol=min(8, len(totals)),
                  frameon=False, borderaxespad=0)
        export(fig, "charts", f"base_pickups_{suffix}")


def time_heatmaps(pickups):
    specs = [
        ("hour_vs_weekday", "Pickups by hour and weekday", "hour", "weekday_number",
         range(24), range(7), list(calendar.day_abbr), "Hour of day"),
        ("hour_vs_month", "Pickups by hour and month", "hour", "month",
         range(24), range(4, 10), MONTHS_TITLE, "Hour of day"),
        ("day_vs_month", "Pickups by calendar day and month", "day", "month",
         range(1, 32), range(4, 10), MONTHS_TITLE, "Day of month"),
    ]
    for name, title, x_col, y_col, x, y, labels, axis_label in specs:
        matrix = (pickups.groupby([y_col, x_col]).size().unstack(fill_value=0)
                  .reindex(index=y, columns=x, fill_value=0).astype(float))
        subtitle = "April–September 2014  •  Total pickups per cell"
        if x_col == "day":
            for month in y:
                matrix.loc[month, calendar.monthrange(2014, month)[1] + 1:] = np.nan
            subtitle += "  •  Blank cells indicate dates outside the month"
        fig, ax = chart(title, subtitle)
        im = ax.imshow(matrix, cmap=DENSITY, vmin=0, aspect="auto", interpolation="nearest")
        step = 2 if x_col == "day" else 1
        ax.set_xticks(np.arange(len(x))[::step], list(x)[::step])
        ax.set_yticks(np.arange(len(y)), labels)
        ax.set_xlabel(axis_label)
        ax.tick_params(length=0, pad=7)
        ax.spines[:].set_visible(False)
        fig.colorbar(im, ax=ax, pad=.025, label="Pickup records",
                     format=FuncFormatter(lambda val, _: f"{val:,.0f}"))
        export(fig, "heatmaps", f"heatmap_{name}")


def padded(bounds, fraction=.05):
    left, bottom, right, top = bounds
    dx, dy = (right - left) * fraction, (top - bottom) * fraction
    return left - dx, bottom - dy, right + dx, top + dy


def map_canvas():
    fig = plt.figure(figsize=(12, 9))
    return fig, fig.add_axes([.025, .025, .95, .95])


def frame_map(ax, bounds):
    left, bottom, right, top = bounds
    ax.set(xlim=(left, right), ylim=(bottom, top), aspect="equal")
    ax.set_axis_off()


def draw_land(ax, shapes, color=LAND, width=.65, zorder=1):
    shapes.plot(ax=ax, color=color, edgecolor="white", linewidth=width, zorder=zorder)


def borough_choropleth(boroughs, counts, bounds):
    fig = plt.figure(figsize=(12, 9))
    ax = fig.add_axes([.04, .055, .78, .83])
    scale_ax = fig.add_axes([.84, .12, .022, .72])
    cmap = matplotlib.colormaps["OrRd"]
    norm = Normalize(vmin=0, vmax=max(1, counts.max()))
    draw_land(ax, boroughs, color=cmap(norm(counts.reindex(boroughs.index))), width=.85)
    frame_map(ax, bounds)
    fig.text(.43, .925, "NYC pickups by borough, April–September 2014",
             ha="center", fontsize=19, weight="bold")
    colorbar = fig.colorbar(matplotlib.cm.ScalarMappable(norm=norm, cmap=cmap),
                            cax=scale_ax,
                            format=FuncFormatter(lambda value, _: f"{value / 1_000_000:g}"))
    colorbar.set_label("Pickup records (millions)", labelpad=12)
    colorbar.outline.set_edgecolor("#B0BCCC")
    export(fig, "maps", "nyc_borough_choropleth")


def points(ax, coordinates, color, size, alpha):
    ax.scatter(*coordinates.T, c=color, s=size, alpha=alpha, linewidths=0, zorder=3)


def sample(coordinates, limit):
    if len(coordinates) <= limit:
        return coordinates
    indices = np.random.default_rng(SEED).choice(len(coordinates), limit, replace=False)
    return coordinates[indices]


def density_grid(ax, xy, bounds, cell, sigma=0, mask=None):
    left, bottom, right, top = bounds
    x = left + cell * np.arange(int(np.ceil((right - left) / cell)) + 1)
    y = bottom + cell * np.arange(int(np.ceil((top - bottom) / cell)) + 1)
    counts = np.histogram2d(xy[:, 0], xy[:, 1], bins=(x, y))[0].T
    if int(counts.sum()) != len(xy):
        raise ValueError("Density extent excluded input points")
    if sigma:
        offsets = np.arange(-3 * sigma, 3 * sigma + 1)
        kernel = np.exp(-.5 * (offsets / sigma) ** 2)
        kernel /= kernel.sum()
        for axis in (0, 1):
            counts = np.apply_along_axis(np.convolve, axis, counts, kernel, mode="same")
    cells = counts >= 1
    if mask is not None:
        xx, yy = np.meshgrid(x[:-1] + cell / 2, y[:-1] + cell / 2)
        cells &= shapely.intersects_xy(mask, xx, yy)
    ax.pcolormesh(x, y, np.ma.masked_where(~cells, counts), cmap=DENSITY,
                  norm=LogNorm(vmin=1, vmax=max(2, counts.max())), zorder=2)


def map_collection(pickups, boroughs, states):
    boroughs = boroughs.to_crs(4326)
    city = boroughs.geometry.union_all()
    if not city.is_valid:
        city = shapely.make_valid(city)
    lon, lat = pickups.Lon.to_numpy(), pickups.Lat.to_numpy()
    inside, _, borough_labels, _ = classify_coordinates(
        lon, lat, city, boroughs.geometry.to_dict(), {}
    )
    borough_counts = pd.Series(borough_labels).value_counts().reindex(BOROUGH_ORDER, fill_value=0)
    is_manhattan = borough_labels == "Manhattan"
    state_mask = np.zeros(len(pickups), dtype=bool)
    for polygon in states.to_crs(4326).geometry:
        left, bottom, right, top = polygon.bounds
        candidates = (~state_mask & (lon >= left) & (lon <= right)
                      & (lat >= bottom) & (lat <= top))
        state_mask[candidates] = shapely.intersects_xy(
            polygon, lon[candidates], lat[candidates]
        )

    geo = gpd.GeoDataFrame(
        pickups[["Lon", "Lat"]], geometry=gpd.points_from_xy(pickups.Lon, pickups.Lat),
        crs=4326,
    )
    metro = Transformer.from_crs(4326, 32618, always_xy=True)
    xy = np.column_stack(metro.transform(geo.Lon.to_numpy(), geo.Lat.to_numpy()))
    local_bounds = padded((geo.Lon.min(), geo.Lat.min(), geo.Lon.max(), geo.Lat.max()), .2)
    region = states.to_crs(4326).cx[
        local_bounds[0]:local_bounds[2], local_bounds[1]:local_bounds[3]
    ].to_crs(32618)
    zoom = padded((*xy.min(axis=0), *xy.max(axis=0)), .06)

    lower_48 = states.drop(index=[
        "Alaska", "Hawaii", "Puerto Rico", "Guam", "Commonwealth of the Northern Mariana Islands",
        "United States Virgin Islands", "American Samoa",
    ], errors="ignore")
    national = lower_48.to_crs(5070)
    fig, ax = map_canvas()
    draw_land(ax, national, width=.4)
    draw_land(ax, national.loc[["New York"]], color="#667B94", width=.5, zorder=2)
    national_xy = np.column_stack(Transformer.from_crs(4326, 5070, always_xy=True)
                                  .transform(geo.Lon.to_numpy(), geo.Lat.to_numpy()))
    points(ax, sample(national_xy, 60_000), ORANGE, .5, .5)
    frame_map(ax, padded(national.total_bounds, .025))
    for name, crs, position in [
        ("Alaska", 3338, [.055, .07, .19, .16]),
        ("Hawaii", 3759, [.25, .08, .105, .10]),
    ]:
        inset = fig.add_axes(position)
        shape = states.loc[[name]].to_crs(crs)
        draw_land(inset, shape, width=.4)
        frame_map(inset, padded(shape.total_bounds))
    export(fig, "point_maps", "usa_points_full")

    for name in ("usa_points_zoomed", "outside_nyc_map", "usa_density"):
        fig, ax = map_canvas()
        draw_land(ax, region)
        if name == "usa_density":
            density_grid(ax, xy, zoom, cell=1000)
        elif name == "outside_nyc_map":
            points(ax, sample(xy[inside], 60_000), "#71D7EA", .5, .34)
            points(ax, xy[~inside], ORANGE, .7, .7)
        else:
            points(ax, sample(xy[inside], 80_000), ORANGE, .6, .42)
            points(ax, xy[~inside], ORANGE, .6, .54)
        frame_map(ax, zoom)
        export(fig, "density_maps" if name == "usa_density" else "point_maps", name)

    boroughs = boroughs.to_crs(32618).loc[BOROUGH_ORDER]
    outline = gpd.GeoSeries([boroughs.geometry.union_all()], crs=boroughs.crs)
    city_bounds = padded(boroughs.total_bounds)
    borough_choropleth(boroughs, borough_counts, city_bounds)
    for name in ["nyc_boundary", "nyc_boroughs", *BOROUGH_ORDER]:
        fig, ax = map_canvas()
        if name == "nyc_boundary":
            draw_land(ax, outline, width=1.2)
        elif name == "nyc_boroughs":
            boroughs.plot(ax=ax, color=["#466F8C", "#307B81", "#567798", "#6F6584", "#505C73"],
                          edgecolor="white", linewidth=1.15)
        else:
            colors = [ORANGE if borough == name else LAND for borough in boroughs.index]
            draw_land(ax, boroughs, color=colors, width=1.05)
            name = f"highlight_{name.lower().replace(' ', '_')}"
        frame_map(ax, city_bounds)
        export(fig, "maps", name)

    manhattan = boroughs.loc[["Manhattan"]]
    for prefix, coords, shapes, bounds in [
        ("nyc", xy[inside], boroughs, city_bounds),
        ("manhattan", xy[is_manhattan], manhattan, padded(manhattan.total_bounds)),
    ]:
        for mode in ("points", "density", "hexbin", "hotspots") if prefix == "nyc" else (
            "points", "density"
        ):
            fig, ax = map_canvas()
            draw_land(ax, shapes)
            if mode == "points":
                points(ax, sample(coords, 160_000 if prefix == "nyc" else 90_000),
                       "#FFC65C", .48, .42)
            elif mode == "hexbin":
                ax.hexbin(*coords.T, gridsize=135, mincnt=1, bins="log", cmap=DENSITY,
                          linewidths=0, zorder=2)
            else:
                density_grid(ax, coords, bounds, cell=150 if mode == "hotspots" else 250,
                             sigma=2 if mode == "hotspots" else 0,
                             mask=shapes.geometry.union_all() if mode == "hotspots" else None)
            shapes.boundary.plot(ax=ax, color="white", linewidth=.65, zorder=4)
            frame_map(ax, bounds)
            export(fig, "point_maps" if mode == "points" else "density_maps", f"{prefix}_{mode}")

    return {"total": len(pickups), "inside": int(inside.sum()), "outside": int((~inside).sum()),
            "outside_unmatched": int((~inside & ~state_mask).sum()),
            "inside_unmatched": int((inside & ~state_mask).sum()),
            "manhattan": int(is_manhattan.sum()), "lon": (geo.Lon.min(), geo.Lon.max()),
            "lat": (geo.Lat.min(), geo.Lat.max())}


def preview_sheet(name, assets):
    tile_width = 560
    tile_height = 330 if name in {"charts_overview", "base_overview"} else 424
    sheet = Image.new("RGB", (tile_width * 2, tile_height * ((len(assets) + 1) // 2)), "#142238")
    draw = ImageDraw.Draw(sheet)
    font = ImageFont.truetype(matplotlib.get_data_path() + "/fonts/ttf/DejaVuSans.ttf", 20)
    for index, (category, asset, title) in enumerate(assets):
        left, top = index % 2 * tile_width, index // 2 * tile_height
        with Image.open(DEST / category / "transparent" / f"{asset}.png") as image:
            thumb = image.convert("RGBA")
            thumb.thumbnail((tile_width - 32, tile_height - 43), Image.Resampling.LANCZOS)
            sheet.paste(thumb, (left + (tile_width - thumb.width) // 2, top + 7), thumb)
        draw.text((left + 18, top + tile_height - 32), title, fill="white", font=font)
    folder = DEST / "previews"
    folder.mkdir(exist_ok=True)
    sheet.save(folder / f"{name}.png", dpi=(DPI, DPI))


def write_summary(audit, boundaries, stats):
    audit.to_csv(DEST / "input_quality.csv", index=False)
    previews = [
        ("base_overview", [
            ("charts", "base_pickups_bar", "Total pickups by dispatch base"),
            ("charts", "base_pickups_monthly", "Dispatch bases by month"),
            ("charts", "base_pickups_weekday", "Dispatch bases by weekday"),
            ("charts", "base_pickups_hourly", "Dispatch bases by hour"),
        ]),
        ("charts_overview", [
            ("charts", "monthly_pickups_bar", "Monthly pickup volume"),
            ("charts", "weekday_pickups_bar", "Pickup volume by weekday"),
            ("charts", "hourly_pickups_line", "Pickup volume by hour"),
            ("heatmaps", "heatmap_hour_vs_weekday", "Hour × weekday"),
            ("heatmaps", "heatmap_hour_vs_month", "Hour × month"),
            ("heatmaps", "heatmap_day_vs_month", "Calendar day × month"),
        ]),
        ("maps_overview", [
            ("point_maps", "usa_points_full", "United States"),
            ("point_maps", "outside_nyc_map", "Inside NYC (cyan) / outside NYC (orange)"),
            ("maps", "nyc_boroughs", "Five boroughs"),
            ("maps", "highlight_manhattan", "Manhattan highlight"),
            ("point_maps", "nyc_points", "NYC pickup points"),
            ("density_maps", "nyc_hotspots", "NYC pickup hotspots"),
        ]),
    ]
    for name, assets in previews:
        preview_sheet(name, assets)
    files = sorted(path.relative_to(DEST).as_posix() for path in DEST.rglob("*.png"))
    input_lines = "\n".join(f"- `{row.source}` ({row.rows:,} records)"
                            for row in audit.itertuples())
    boundary_lines = "\n".join(
        f"- `{item['source']}` ({item['crs']}, {item['features']} features, "
        f"{item['invalid_repaired']} repaired)" for item in boundaries
    )
    file_lines = "\n".join(f"- [{path}]({path})" for path in files)
    excluded = audit.excluded_rows.sum()
    duplicates = audit.duplicate_rows_retained.sum()
    (DEST / "README.md").write_text(f"""# Uber Pickup Demand Analysis | Presentation visuals

Run from the project root with `.venv/bin/python src/presentation_visuals.py`.

## Inputs

{input_lines}

{boundary_lines}

The source fields are `Date/Time`, `Lat`, `Lon`, and `Base`. The script derives
`month`, `month_name`, `day`, `day_name`, `hour`, `weekday_number` (Monday = 0),
and `date`. Separate New York State and NYC files are absent. New York State comes
from the Census shapefile and the NYC boundary is the union of the five boroughs.
Source geometries are aligned to EPSG:4326 for membership tests, then drawn in
projected coordinates (EPSG:5070 for the contiguous US and EPSG:32618 for regional maps).
Alaska and Hawaii use their own inset projections.

## Data quality and methods

- {stats['total']:,} records visualized, with {audit.missing_cells.sum():,} missing cells,
  {audit.invalid_coordinates.sum():,} invalid coordinates, and {excluded:,} excluded rows.
  {duplicates:,} exact duplicate rows are retained to preserve recorded pickup volume.
  The [per-file audit](input_quality.csv) contains validation details.
- {stats['inside']:,} inside NYC, {stats['outside']:,} outside NYC, and
  {stats['manhattan']:,} in Manhattan. NYC membership includes polygon boundaries.
  {stats['outside_unmatched']:,} outside-NYC records and {stats['inside_unmatched']:,}
  inside-NYC records fall outside the 2014 state polygons. All remain in the counts.
- The regional frame includes all recorded coordinates, spanning longitude
  {stats['lon'][0]:.4f} to {stats['lon'][1]:.4f} and latitude
  {stats['lat'][0]:.4f} to {stats['lat'][1]:.4f}. The regional point map draws all
  outside-NYC records and samples 80,000 inside-NYC records. The outside-NYC
  comparison draws all outside-NYC records in orange and samples 60,000 in NYC
  in cyan. The national, NYC and Manhattan point maps sample 60,000, 160,000 and
  90,000 records respectively. Samples use seed {SEED}, without replacement.
- Density layers use every record in their stated extent. The regional grid uses
  1 km cells, NYC and Manhattan grids use 250 m cells, and the hotspot map uses a
  150 m grid smoothed by a Gaussian kernel with a 300 m standard deviation.
  Hotspot display is masked by NYC at cell centers. NYC also has a hexbin map.
  Colors use a logarithmic scale per map and show relative concentration within
  each map. Color is independently scaled in each time heatmap.
- Charts and time heatmaps are 3300 × 1800 px. Maps are 3600 × 2700 px.
  The borough choropleth uses a linear color scale for total pickup records
  per borough, with all classified borough pickups included.
  All main PNGs are exported at 300 DPI. Borough highlights share identical
  framing and can be layered in Canva. Transparent PNGs use white text for
  dark slide backgrounds. Preview sheets show reduced-size images.

## PNG inventory ({len(files)})

{file_lines}
""", encoding="utf-8")


def main():
    pickups, audit = load_pickups()
    boroughs, borough_audit = read_boundary(DATA_DIR / "Borough_Boundaries_20261028.geojson",
                                            "boroname")
    states, state_audit = read_boundary(DATA_DIR / "boundaries/cb_2014_us_state_500k.shp",
                                        "NAME")
    print(f"Loaded {len(pickups):,} rows. Rendering charts.", flush=True)
    count_charts(pickups)
    base_charts(pickups)
    time_heatmaps(pickups)
    print("Rendering maps.", flush=True)
    stats = map_collection(pickups, boroughs, states)
    write_summary(audit, [borough_audit, state_audit], stats)
    print(f"Finished. {len(list(DEST.rglob('*.png')))} PNGs in {DEST}", flush=True)


if __name__ == "__main__":
    main()

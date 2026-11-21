# Uber Pickup Demand Analysis | Presentation visuals

Run from the project root with `python src/presentation_visuals.py`.

## Inputs

- `data/uber-raw-data-apr14.csv` (564,516 records)
- `data/uber-raw-data-may14.csv` (652,435 records)
- `data/uber-raw-data-jun14.csv` (663,844 records)
- `data/uber-raw-data-jul14.csv` (796,121 records)
- `data/uber-raw-data-aug14.csv` (829,275 records)
- `data/uber-raw-data-sep14.csv` (1,028,136 records)

- `data/Borough_Boundaries_20261028.geojson` (EPSG:4326, 5 features, 0 repaired)
- `data/boundaries/cb_2014_us_state_500k.shp` (EPSG:4269, 56 features, 0 repaired)

The source fields are `Date/Time`, `Lat`, `Lon`, and `Base`. The script derives
`month`, `month_name`, `day`, `day_name`, `hour`, `weekday_number` (Monday = 0),
and `date`. Separate New York State and NYC files are absent. New York State comes
from the Census shapefile and the NYC boundary is the union of the five boroughs.
Source geometries are aligned to EPSG:4326 for membership tests, then drawn in
projected coordinates (EPSG:5070 for the contiguous US and EPSG:32618 for regional maps).
Alaska and Hawaii use their own inset projections.

## Data quality and methods

- 4,534,327 records visualized, with 0 missing cells,
  0 invalid coordinates, and 0 excluded rows.
  82,581 exact duplicate rows are retained to preserve recorded pickup volume.
  The [per-file audit](input_quality.csv) contains validation details.
- 4,411,894 inside NYC, 122,433 outside NYC, and
  3,443,457 in Manhattan. NYC membership includes polygon boundaries.
  49 outside-NYC records and 15
  inside-NYC records fall outside the 2014 state polygons. All remain in the counts.
- The regional frame includes all recorded coordinates, spanning longitude
  -74.9290 to -72.0666 and latitude
  39.6569 to 42.1166. The regional point map draws all
  outside-NYC records and samples 80,000 inside-NYC records. The outside-NYC
  comparison draws all outside-NYC records in orange and samples 60,000 in NYC
  in cyan. The national, NYC and Manhattan point maps sample 60,000, 160,000 and
  90,000 records respectively. Samples use seed 369, without replacement.
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

## PNG inventory (67)

- [charts/transparent/base_pickups_bar.png](charts/transparent/base_pickups_bar.png)
- [charts/transparent/base_pickups_hourly.png](charts/transparent/base_pickups_hourly.png)
- [charts/transparent/base_pickups_monthly.png](charts/transparent/base_pickups_monthly.png)
- [charts/transparent/base_pickups_weekday.png](charts/transparent/base_pickups_weekday.png)
- [charts/transparent/hourly_pickups_bar.png](charts/transparent/hourly_pickups_bar.png)
- [charts/transparent/hourly_pickups_line.png](charts/transparent/hourly_pickups_line.png)
- [charts/transparent/monthly_pickups_area.png](charts/transparent/monthly_pickups_area.png)
- [charts/transparent/monthly_pickups_bar.png](charts/transparent/monthly_pickups_bar.png)
- [charts/transparent/monthly_pickups_line.png](charts/transparent/monthly_pickups_line.png)
- [charts/transparent/weekday_pickups_bar.png](charts/transparent/weekday_pickups_bar.png)
- [charts/transparent/weekday_pickups_line.png](charts/transparent/weekday_pickups_line.png)
- [charts/white_bg/base_pickups_bar.png](charts/white_bg/base_pickups_bar.png)
- [charts/white_bg/base_pickups_hourly.png](charts/white_bg/base_pickups_hourly.png)
- [charts/white_bg/base_pickups_monthly.png](charts/white_bg/base_pickups_monthly.png)
- [charts/white_bg/base_pickups_weekday.png](charts/white_bg/base_pickups_weekday.png)
- [charts/white_bg/hourly_pickups_bar.png](charts/white_bg/hourly_pickups_bar.png)
- [charts/white_bg/hourly_pickups_line.png](charts/white_bg/hourly_pickups_line.png)
- [charts/white_bg/monthly_pickups_area.png](charts/white_bg/monthly_pickups_area.png)
- [charts/white_bg/monthly_pickups_bar.png](charts/white_bg/monthly_pickups_bar.png)
- [charts/white_bg/monthly_pickups_line.png](charts/white_bg/monthly_pickups_line.png)
- [charts/white_bg/weekday_pickups_bar.png](charts/white_bg/weekday_pickups_bar.png)
- [charts/white_bg/weekday_pickups_line.png](charts/white_bg/weekday_pickups_line.png)
- [density_maps/transparent/manhattan_density.png](density_maps/transparent/manhattan_density.png)
- [density_maps/transparent/nyc_density.png](density_maps/transparent/nyc_density.png)
- [density_maps/transparent/nyc_hexbin.png](density_maps/transparent/nyc_hexbin.png)
- [density_maps/transparent/nyc_hotspots.png](density_maps/transparent/nyc_hotspots.png)
- [density_maps/transparent/usa_density.png](density_maps/transparent/usa_density.png)
- [density_maps/white_bg/manhattan_density.png](density_maps/white_bg/manhattan_density.png)
- [density_maps/white_bg/nyc_density.png](density_maps/white_bg/nyc_density.png)
- [density_maps/white_bg/nyc_hexbin.png](density_maps/white_bg/nyc_hexbin.png)
- [density_maps/white_bg/nyc_hotspots.png](density_maps/white_bg/nyc_hotspots.png)
- [density_maps/white_bg/usa_density.png](density_maps/white_bg/usa_density.png)
- [heatmaps/transparent/heatmap_day_vs_month.png](heatmaps/transparent/heatmap_day_vs_month.png)
- [heatmaps/transparent/heatmap_hour_vs_month.png](heatmaps/transparent/heatmap_hour_vs_month.png)
- [heatmaps/transparent/heatmap_hour_vs_weekday.png](heatmaps/transparent/heatmap_hour_vs_weekday.png)
- [heatmaps/white_bg/heatmap_day_vs_month.png](heatmaps/white_bg/heatmap_day_vs_month.png)
- [heatmaps/white_bg/heatmap_hour_vs_month.png](heatmaps/white_bg/heatmap_hour_vs_month.png)
- [heatmaps/white_bg/heatmap_hour_vs_weekday.png](heatmaps/white_bg/heatmap_hour_vs_weekday.png)
- [maps/transparent/highlight_bronx.png](maps/transparent/highlight_bronx.png)
- [maps/transparent/highlight_brooklyn.png](maps/transparent/highlight_brooklyn.png)
- [maps/transparent/highlight_manhattan.png](maps/transparent/highlight_manhattan.png)
- [maps/transparent/highlight_queens.png](maps/transparent/highlight_queens.png)
- [maps/transparent/highlight_staten_island.png](maps/transparent/highlight_staten_island.png)
- [maps/transparent/nyc_borough_choropleth.png](maps/transparent/nyc_borough_choropleth.png)
- [maps/transparent/nyc_boroughs.png](maps/transparent/nyc_boroughs.png)
- [maps/transparent/nyc_boundary.png](maps/transparent/nyc_boundary.png)
- [maps/white_bg/highlight_bronx.png](maps/white_bg/highlight_bronx.png)
- [maps/white_bg/highlight_brooklyn.png](maps/white_bg/highlight_brooklyn.png)
- [maps/white_bg/highlight_manhattan.png](maps/white_bg/highlight_manhattan.png)
- [maps/white_bg/highlight_queens.png](maps/white_bg/highlight_queens.png)
- [maps/white_bg/highlight_staten_island.png](maps/white_bg/highlight_staten_island.png)
- [maps/white_bg/nyc_borough_choropleth.png](maps/white_bg/nyc_borough_choropleth.png)
- [maps/white_bg/nyc_boroughs.png](maps/white_bg/nyc_boroughs.png)
- [maps/white_bg/nyc_boundary.png](maps/white_bg/nyc_boundary.png)
- [point_maps/transparent/manhattan_points.png](point_maps/transparent/manhattan_points.png)
- [point_maps/transparent/nyc_points.png](point_maps/transparent/nyc_points.png)
- [point_maps/transparent/outside_nyc_map.png](point_maps/transparent/outside_nyc_map.png)
- [point_maps/transparent/usa_points_full.png](point_maps/transparent/usa_points_full.png)
- [point_maps/transparent/usa_points_zoomed.png](point_maps/transparent/usa_points_zoomed.png)
- [point_maps/white_bg/manhattan_points.png](point_maps/white_bg/manhattan_points.png)
- [point_maps/white_bg/nyc_points.png](point_maps/white_bg/nyc_points.png)
- [point_maps/white_bg/outside_nyc_map.png](point_maps/white_bg/outside_nyc_map.png)
- [point_maps/white_bg/usa_points_full.png](point_maps/white_bg/usa_points_full.png)
- [point_maps/white_bg/usa_points_zoomed.png](point_maps/white_bg/usa_points_zoomed.png)
- [previews/base_overview.png](previews/base_overview.png)
- [previews/charts_overview.png](previews/charts_overview.png)
- [previews/maps_overview.png](previews/maps_overview.png)

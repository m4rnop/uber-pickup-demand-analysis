# Input data

## Uber pickup records

Download these six CSV files from [FiveThirtyEight’s TLC FOIL release](https://github.com/fivethirtyeight/uber-tlc-foil-response/tree/master/uber-trip-data) and place them directly in `data/`. The raw CSVs are excluded from Git. The analysis expects the original headers `Date/Time`, `Lat`, `Lon`, and `Base`.

| File | Data rows |
|---|---:|
| `uber-raw-data-apr14.csv` | 564,516 |
| `uber-raw-data-may14.csv` | 652,435 |
| `uber-raw-data-jun14.csv` | 663,844 |
| `uber-raw-data-jul14.csv` | 796,121 |
| `uber-raw-data-aug14.csv` | 829,275 |
| `uber-raw-data-sep14.csv` | 1,028,136 |

On macOS or Linux, run this from the repository root to download only missing files:

```sh
for month in apr may jun jul aug sep; do
  file="uber-raw-data-${month}14.csv"
  if [ ! -f "data/$file" ]; then
    curl --fail --location --output "data/$file.part" \
      "https://raw.githubusercontent.com/fivethirtyeight/uber-tlc-foil-response/master/uber-trip-data/$file" &&
      mv "data/$file.part" "data/$file" || break
  fi
done
```

## Geographic boundaries

- `Borough_Boundaries_20261028.geojson` is the NYC borough boundary snapshot used for this project. Its date is later than the pickup period. [NYC Open Data](https://data.cityofnewyork.us/City-Government/Borough-Boundaries/gthc-hcne)
- `boundaries/cb_2014_us_state_500k.*` is the 2014 U.S. state cartographic boundary shapefile and its companion files. Keep the shapefile components together. [U.S. Census Bureau](https://www.census.gov/geographies/mapping-files/time-series/geo/carto-boundary-file.2014.html)

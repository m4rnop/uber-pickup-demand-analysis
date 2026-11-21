"""Export the offline map, including its pickup data and local map boundaries."""
import base64
import gzip
import json
from pathlib import Path

import geopandas as gpd
import numpy as np
import pandas as pd
import shapely

from analysis import BOROUGH_ORDER, DATA_DIR, OUTPUT_DIR

SOURCE = Path(__file__).with_name("interactive_map.html")
DEST = OUTPUT_DIR / "interactive_map" / "index.html"
AREAS = [*BOROUGH_ORDER, "Outside NYC", "Unassigned NYC"]


def boundaries():
    boroughs = gpd.read_file(DATA_DIR / "Borough_Boundaries_20261028.geojson").to_crs(4326)
    states = gpd.read_file(DATA_DIR / "boundaries/cb_2014_us_state_500k.shp").to_crs(4326)
    extent = shapely.box(-76, 39, -71, 43)
    layers = []
    for frame, name_field, kind in [(states, "NAME", "state"),
                                    (boroughs, "boroname", "borough")]:
        for name, geometry in zip(frame[name_field], frame.geometry):
            if not geometry.intersects(extent):
                continue
            geometry = geometry.intersection(extent).simplify(.00035)
            polygons = [part for part in shapely.get_parts(geometry)
                        if part.geom_type == "Polygon"]
            rings = [[[[round(x, 5), round(y, 5)] for x, y, *_ in ring.coords]
                      for ring in [part.exterior, *part.interiors]] for part in polygons]
            if rings:
                layers.append({"name": name, "kind": kind, "polygons": rings})
    return layers


def main():
    data = pd.read_parquet(OUTPUT_DIR / "processed/pickups_classified.parquet",
                           columns=["Lon", "Lat", "Base", "borough", "inside_nyc",
                                    "month", "hour", "day_of_week"])
    bases = sorted(data.Base.unique())
    if (len(bases) * len(AREAS) * 24 * 7 * 6 > 65536
            or not data.month.between(4, 9).all()
            or not data.hour.between(0, 23).all()
            or not data.day_of_week.between(0, 6).all()
            or not data.Lon.between(-76, -71).all()
            or not data.Lat.between(39, 43).all()):
        raise ValueError("Dataset exceeds the map encoding range")
    areas = data.borough.where(data.borough.isin(BOROUGH_ORDER),
                              np.where(data.inside_nyc, "Unassigned NYC", "Outside NYC"))
    group = data.month.to_numpy() - 4
    for radix, codes in [(7, data.day_of_week), (24, data.hour),
                         (len(AREAS), pd.Categorical(areas, AREAS).codes),
                         (len(bases), pd.Categorical(data.Base, bases).codes)]:
        group = group.astype("int32") * radix + np.asarray(codes)
    x = np.rint((data.Lon.to_numpy() + 76) * 10000).astype("uint16")
    y = np.rint((data.Lat.to_numpy() - 39) * 10000).astype("uint16")
    order = np.lexsort((y, x, group))
    packed = np.column_stack((group[order], x[order], y[order])).astype("<u2")
    payload = base64.b64encode(gzip.compress(packed.tobytes(), compresslevel=6, mtime=0))
    metadata = {"bases": bases, "areas": AREAS, "count": len(data), "layers": boundaries()}
    html = SOURCE.read_text().replace("__METADATA__", json.dumps(metadata, separators=(",", ":")))
    DEST.parent.mkdir(parents=True, exist_ok=True)
    DEST.write_text(html.replace("__PICKUPS__", payload.decode("ascii")), encoding="utf-8")
    print(f"{len(data):,} pickups · {DEST.stat().st_size / 1e6:.1f} MB · {DEST}")


if __name__ == "__main__":
    main()

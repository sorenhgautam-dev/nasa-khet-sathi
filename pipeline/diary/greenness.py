"""Field greenness and bare days (CLAUDE.md "Field diary", build step 6a). Pure functions; the cached image
windows are read in scripts/run_diary.py.

- One image over the field: the mean NDVI of the field's pixels (centres inside the polygon) that are clear and
  hold NDVI, kept only when at least min_clear_fraction of the field's pixels are (rules.yaml greenness).
- Daily series: clear observations on the same day are averaged, then NDVI is interpolated linearly between
  them; no value before the first or after the last observation. gap_days is the distance between the two clear
  observations either side of a day (0 on an observation day), the measure of how sure the day's value is.
- Bare days: interpolated NDVI below bare_days.ndvi_max; a day is uncertain when its gap is longer than
  bare_days.uncertain_gap_days. Days without a value are neither bare nor green.
"""
import numpy as np
import pandas as pd

MODIS_SPHERE_M = 6371007.181          # MOD13Q1 sinusoidal grid sphere radius (the file's crs attribute)


def field_mask(shape, transform, crs, polygon_lonlat):
    """Boolean mask of the pixels whose centres lie inside the field polygon ([lon, lat] corners)."""
    from rasterio.features import geometry_mask
    from rasterio.warp import transform_geom
    ring = [list(p) for p in polygon_lonlat] + [list(polygon_lonlat[0])]
    geom = transform_geom("EPSG:4326", crs, {"type": "Polygon", "coordinates": [ring]})
    return geometry_mask([geom], out_shape=shape, transform=transform, invert=True, all_touched=False)


def field_observation(ndvi, clear, mask, min_clear_fraction):
    """{'ndvi': mean or None, 'clear_fraction': share of field pixels clear with NDVI, 'n_pixels'}."""
    mask = np.asarray(mask, bool)
    n = int(mask.sum())
    if n == 0:
        raise ValueError("the field mask holds no pixel: the field is smaller than the grid or outside it")
    v = np.asarray(ndvi, float)[mask]
    ok = np.asarray(clear, bool)[mask] & np.isfinite(v)
    frac = float(ok.sum()) / n
    return {"ndvi": float(v[ok].mean()) if ok.any() and frac >= min_clear_fraction else None,
            "clear_fraction": frac, "n_pixels": n}


def modis_pixel(lat, lon, ydim, xdim):
    """(row, col) of the MOD13Q1 sinusoidal pixel whose centre is nearest the point."""
    x = MODIS_SPHERE_M * np.radians(lon) * np.cos(np.radians(lat))
    y = MODIS_SPHERE_M * np.radians(lat)
    return int(np.abs(np.asarray(ydim) - y).argmin()), int(np.abs(np.asarray(xdim) - x).argmin())


def daily_series(obs, start, end):
    """obs: DataFrame [date, ndvi] of clear field observations -> DataFrame [date, ndvi, gap_days]."""
    o = obs.dropna(subset=["ndvi"]).assign(date=lambda d: pd.to_datetime(d["date"]).dt.normalize())
    o = o.groupby("date", as_index=True)["ndvi"].mean().sort_index()
    days = pd.date_range(start, end)
    s = o.reindex(o.index.union(days)).interpolate(method="time", limit_area="inside").reindex(days)
    obs_days = o.index.to_numpy()
    pos = np.searchsorted(obs_days, days.to_numpy(), side="left")
    gap = np.full(len(days), np.nan)
    for i, (d, p) in enumerate(zip(days.to_numpy(), pos)):
        if p < len(obs_days) and obs_days[p] == d:
            gap[i] = 0
        elif 0 < p < len(obs_days):
            gap[i] = (obs_days[p] - obs_days[p - 1]) / np.timedelta64(1, "D")
    return pd.DataFrame({"date": days, "ndvi": s.to_numpy(), "gap_days": gap})


def bare_days(daily, ndvi_max, uncertain_gap_days):
    """Per year and per month: bare days, days with a value, uncertain days (all counts of days)."""
    d = daily.assign(has=daily["ndvi"].notna(), bare=daily["ndvi"] < ndvi_max,
                     uncertain=daily["ndvi"].notna() & (daily["gap_days"] > uncertain_gap_days))
    out = {}
    for key, fmt in (("by_year", "%Y"), ("by_month", "%Y-%m")):
        g = d.groupby(d["date"].dt.strftime(fmt))
        out[key] = {k: {"bare_days": int(x["bare"].sum()), "days_with_value": int(x["has"].sum()),
                        "uncertain_days": int(x["uncertain"].sum())} for k, x in g}
    return out


def pair_observations(a, b, max_days):
    """Each observation in `a` with the nearest one in `b` within max_days: [date_a, ndvi_a, date_b, ndvi_b]."""
    a = a.dropna(subset=["ndvi"]).sort_values("date")
    b = b.dropna(subset=["ndvi"]).sort_values("date")
    m = pd.merge_asof(a.rename(columns={"date": "date_a", "ndvi": "ndvi_a"}),
                      b.rename(columns={"date": "date_b", "ndvi": "ndvi_b"}).assign(key=lambda x: x["date_b"]),
                      left_on="date_a", right_on="key", direction="nearest",
                      tolerance=pd.Timedelta(max_days, unit="D"))
    return m.dropna(subset=["ndvi_b"])[["date_a", "ndvi_a", "date_b", "ndvi_b"]].reset_index(drop=True)

"""HLS-VI greenness: clear-sky NDVI and monthly composites over the fetch box. Pure functions plus one
loader for the cached box windows (data/raw/hls_l30|hls_s30/<field>/*.tif, band 1 NDVI, band 2 Fmask).

Clear sky: HLS Fmask bits 0-5 all zero (cirrus, cloud, adjacent to cloud, cloud shadow, snow/ice, water),
from the bit list in each file's own 'Fmask description' tag; the aerosol level (bits 6-7) is not used.
Water (bit 5) counts as not clear. REVIEW_NOTES M12 asked whether that drops flooded-paddy observations at
transplanting. Checked on the cached granules, 2026-11-12 (1,471 granules, 2013-2025): over the demo field's
9 covering HLS pixels, no observation in June-August had the water bit set at all (0 of 2,916); the only
water-flagged, otherwise clear observations were 8 on one Sentinel-2 granule of 2017-01-01, all with NDVI
fill. Over the whole box's WorldCover cropland they are 13, 16 and 45 pixel-observations in June, July and
August, against 1.46, 0.54 and 1.21 million clear ones (0.001-0.004 %). So the definition is kept; re-check
it if the real field is a paddy that Fmask marks as water.
NDVI: int16, scale 0.0001, fill -19999 (file tags), so -1 to 1 after scaling (golden rule 12b).
"""
import json
import warnings
from pathlib import Path

import numpy as np

CLEAR_BITS = 0b00111111


def clear_mask(fmask):
    f = np.asarray(fmask, dtype=float)
    ok = np.isfinite(f) & (f != 255)
    fi = np.where(ok, f, 0).astype(np.uint16)
    return ok & ((fi & CLEAR_BITS) == 0)


def scale_ndvi(raw, fill, scale):
    a = np.asarray(raw, dtype=float).copy()
    a[a == fill] = np.nan
    a *= scale
    bad = np.isfinite(a) & (np.abs(a) > 1.0)
    if bad.any():
        raise ValueError(f"NDVI outside -1 to 1 after scaling: {a[bad][:5].tolist()}")
    return a


def monthly_median(stack, clear, months):
    keys = sorted(set(months))
    m = np.asarray(months)
    comp = np.full((len(keys),) + stack.shape[1:], np.nan)
    n = np.zeros((len(keys),) + stack.shape[1:], dtype=int)
    for k, key in enumerate(keys):
        sel = np.where(m == key)[0]
        vals = np.where(clear[sel], stack[sel], np.nan)
        n[k] = np.isfinite(vals).sum(axis=0)
        with warnings.catch_warnings():
            warnings.simplefilter("ignore", RuntimeWarning)          # all-cloudy pixels: an honest gap
            comp[k] = np.nanmedian(vals, axis=0)
    return comp, n, keys


def load_month_groups(dirs):
    """{'YYYY-MM': [file, ...]} from the cached granule windows' 'acquired' tags."""
    import rasterio
    groups = {}
    for d in dirs:
        for f in sorted(Path(d).glob("[!.]*.tif")):
            with rasterio.open(f) as src:
                groups.setdefault(src.tags()["acquired"][:7], []).append(f)
    return groups


def monthly_composites(dirs):
    """Monthly median clear NDVI for the whole box: (composites, clear counts, month keys, transform, crs)."""
    import rasterio
    groups = load_month_groups(dirs)
    comps, counts, keys, transform, crs, shape = [], [], [], None, None, None
    for key in sorted(groups):
        stack, clear = [], []
        for f in groups[key]:
            with rasterio.open(f) as src:
                if shape is None:
                    shape, transform, crs = src.shape, src.transform, src.crs
                if src.shape != shape or src.transform != transform:
                    raise ValueError(f"{f.name}: window grid differs from the first granule's")
                meta = json.loads(src.tags()["assets"])[".NDVI.tif"]
                stack.append(scale_ndvi(src.read(1), float(meta["nodata"]), float(meta["scale"])))
                clear.append(clear_mask(src.read(2)))
        c, n, _ = monthly_median(np.stack(stack), np.stack(clear), [key] * len(stack))
        comps.append(c[0]); counts.append(n[0]); keys.append(key)
    return np.stack(comps), np.stack(counts), keys, transform, crs


def build(field, data_dir=None):
    """Box-wide monthly composites (npz), the field's monthly series (parquet) and the HLS data card."""
    import pandas as pd
    import rasterio

    from pipeline.fetch import guards as g
    from pipeline.fetch.placeholder import sample_monthly

    repo = Path(__file__).resolve().parents[2]
    data = Path(data_dir) if data_dir else repo / "data"
    dirs = [data / "raw" / s / field["id"] for s in ("hls_l30", "hls_s30")]
    comp, counts, keys, t, crs = monthly_composites(dirs)
    clean = data / "clean" / field["id"]
    np.savez_compressed(clean / "hls_monthly_ndvi.npz", ndvi=comp.astype("float32"), clear_obs=counts.astype("int16"),
                        months=np.array(keys), transform=np.array(tuple(t)[:6]), crs=np.array(str(crs)))
    half = max(abs(p[0] - field["lon"]) for p in field["polygon"]) * 111195 * np.cos(np.radians(field["lat"]))
    s, npx = sample_monthly(comp, keys, t, crs, field["lon"], field["lat"], half)
    df = pd.DataFrame({"month": keys, "ndvi_field_mean": s.to_numpy()})
    df.to_parquet(clean / "hls_field_monthly.parquet", index=False)
    n_files = {d.parent.name: len(list(d.glob("[!.]*.tif"))) for d in dirs}
    with rasterio.open(sorted(dirs[0].glob("[!.]*.tif"))[0]) as src:
        meta = json.loads(src.tags()["assets"])
    card = g.make_card(
        dataset="hls", product="HLS Vegetation Indices (HLSL30_VI, HLSS30_VI)", version="2.0",
        variable=["NDVI", "Fmask"], units_in="NDVI int16 (scale 0.0001), Fmask bit flags", units_out="NDVI (unitless, -1 to 1)",
        scale_factor=0.0001, fill_values_removed={"NDVI -19999": "per pixel", "Fmask 255": "per pixel"},
        quality_flags_used="Fmask bits 0-5 all zero (cirrus, cloud, adjacent, shadow, snow/ice, water); aerosol bits not used",
        records_dropped=0, date_range=[keys[0], keys[-1]], time_zone="UTC acquisition times (about 10:30 local)",
        pixel_count=npx, source="NASA LP DAAC HLS-VI v2.0 (Landsat 8/9 and Sentinel-2 A/B/C), tile T45RUL; citation DOIs TODO-VERIFY",
        resolution="30 m", raw_attrs={"ndvi": {k: meta['.NDVI.tif'][k] for k in ('dtype', 'nodata', 'scale', 'offset')},
                                      "fmask_description": meta['.Fmask.tif']['tags'].get('Fmask description')},
        location={"box": field["fetch_box"], "field_polygon": field["polygon"], "granules": n_files},
        notes=(f"Monthly median of clear pixels, {len(keys)} months; clear-pixel share over the box "
               f"{float(np.isfinite(comp).mean()):.2f}. Field series: mean of the {npx} HLS pixel(s) whose centres lie in the field"
               + (" (PLACEHOLDER field)." if field.get("placeholder") else ".")))
    return {"card": g.write_card(card, data / "cards" / field["id"]), "months": len(keys), "pixels": npx, "files": n_files}


if __name__ == "__main__":
    import sys
    from pipeline.fetch.fields import load_field
    r = build(load_field(sys.argv[1] if len(sys.argv) > 1 else "demo"))
    print(r)

"""DATA_AUDIT section 2: the field outline over each gridded dataset's pixels, with the pixel count.

    .venv/bin/python scripts/plot_pixels.py --field demo

Writes data/plots/pixels/<field>/<dataset>.png and data/checks/<field>/field_pixels.json. Draws whatever
is downloaded (WorldCover, NASADEM, HLS, GPM, GRACE; MODIS, SMAP and ECOSTRESS once they arrive) and
lists the rest as not yet available. A pixel counts when its centre lies inside the field polygon.
"""
import argparse
import json
import sys
from pathlib import Path

import numpy as np

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO))
from pipeline.checks.pixels import count_pixels  # noqa: E402
from pipeline.fetch.fields import load_field  # noqa: E402

INK, MUTED, GRID = "#0b0b0b", "#898781", "#c3c2b7"


def _outline(ax, poly, crs, **kw):
    from rasterio.warp import transform as warp
    xs, ys = [p[0] for p in poly] + [poly[0][0]], [p[1] for p in poly] + [poly[0][1]]
    if str(crs) != "EPSG:4326":
        xs, ys = warp("EPSG:4326", crs, xs, ys)
    ax.plot(xs, ys, color=INK, lw=2.2, **kw)
    return np.mean(xs[:-1]), np.mean(ys[:-1])


def _raster(ax, arr, t, crs, poly, half, title, cmap, norm=None, grid=True):
    cx, cy = _outline(ax, poly, crs, label="field (placeholder)")
    ext = [t.c, t.c + t.a * arr.shape[1], t.f + t.e * arr.shape[0], t.f]
    im = ax.imshow(arr, extent=ext, cmap=cmap, norm=norm, interpolation="nearest", zorder=0)
    _outline(ax, poly, crs)
    hx = half if str(crs) != "EPSG:4326" else half / (111195 * np.cos(np.radians(cy)))
    hy = half if str(crs) != "EPSG:4326" else half / 111195
    ax.set_xlim(cx - hx, cx + hx); ax.set_ylim(cy - hy, cy + hy)
    if grid:
        for k in range(arr.shape[1] + 1):
            x = t.c + t.a * k
            if cx - hx <= x <= cx + hx:
                ax.axvline(x, color=GRID, lw=0.5)
        for k in range(arr.shape[0] + 1):
            y = t.f + t.e * k
            if cy - hy <= y <= cy + hy:
                ax.axhline(y, color=GRID, lw=0.5)
    if norm is None:                                   # continuous data: scale colours to the zoomed view
        cols = np.arange(arr.shape[1]); rows = np.arange(arr.shape[0])
        xc, yc = t.c + t.a * (cols + 0.5), t.f + t.e * (rows + 0.5)
        view = arr[np.ix_((yc >= cy - hy) & (yc <= cy + hy), (xc >= cx - hx) & (xc <= cx + hx))]
        if np.isfinite(view).any():
            im.set_clim(np.nanmin(view), np.nanmax(view))
    ax.ticklabel_format(useOffset=False, style="plain")
    n = count_pixels(arr.shape, t, crs, poly)
    ax.set_title(f"{title}\n{n} pixel centre(s) inside the field", loc="left", fontsize=9.5)
    ax.tick_params(labelsize=7)
    return im, n


def _cells(ax, lat_edges, lon_edges, field, box, title):
    for la in lat_edges:
        ax.axhline(la, color=MUTED, lw=0.8)
    for lo in lon_edges:
        ax.axvline(lo, color=MUTED, lw=0.8)
    bx = [box[0], box[2], box[2], box[0], box[0]]; by = [box[1], box[1], box[3], box[3], box[1]]
    ax.plot(bx, by, color=INK, lw=1, ls="--", label="fetch box")
    ax.plot(field["lon"], field["lat"], marker="s", color=INK, ms=6, label="field (placeholder, 60 m)")
    ax.set_xlim(min(lon_edges), max(lon_edges)); ax.set_ylim(min(lat_edges), max(lat_edges))
    ax.set_title(title, loc="left", fontsize=9.5); ax.legend(fontsize=7, loc="lower left"); ax.tick_params(labelsize=7)


def main(argv=None):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    import rasterio
    from matplotlib.colors import BoundaryNorm, ListedColormap

    ap = argparse.ArgumentParser()
    ap.add_argument("--field", default="demo")
    a = ap.parse_args(argv)
    f = load_field(a.field)
    fid, data, poly, box = f["id"], REPO / "data", f["polygon"], f["fetch_box"]
    out = data / "plots" / "pixels" / fid
    out.mkdir(parents=True, exist_ok=True)
    counts, missing = {}, []

    def save(fig, name):
        fig.tight_layout(); fig.savefig(out / f"{name}.png", dpi=110); plt.close(fig)

    wc = sorted((data / "raw" / "worldcover" / fid).glob("*_box.tif"))
    if wc:
        with rasterio.open(wc[0]) as s:
            arr, t, cm = s.read(1), s.transform, s.colormap(1)
        classes = [10, 20, 30, 40, 50, 60, 80]
        cmap = ListedColormap([tuple(c / 255 for c in cm[k][:3]) for k in classes])
        norm = BoundaryNorm([c - 0.5 for c in classes] + [80.5], len(classes))
        fig, ax = plt.subplots(figsize=(6, 6))
        _, counts["worldcover"] = _raster(ax, arr, t, "EPSG:4326", poly, 150, "ESA WorldCover 2021, 10 m (pink = cropland, red = built-up)", cmap, norm)
        save(fig, "worldcover")
    else:
        missing.append("worldcover")
    nd = data / "clean" / fid / "nasadem_box.tif"
    if nd.exists():
        with rasterio.open(nd) as s:
            el, sl, t = s.read(1), s.read(2), s.transform
        fig, axes = plt.subplots(1, 2, figsize=(11, 5.5))
        im, counts["nasadem"] = _raster(axes[0], el, t, "EPSG:4326", poly, 200, "NASADEM elevation (m), 1 arc-second", "Blues")
        fig.colorbar(im, ax=axes[0], shrink=0.7)
        im, _ = _raster(axes[1], sl, t, "EPSG:4326", poly, 200, "NASADEM slope (deg, Horn 1981)", "Oranges")
        fig.colorbar(im, ax=axes[1], shrink=0.7)
        save(fig, "nasadem")
    else:
        missing.append("nasadem")
    hm = data / "clean" / fid / "hls_monthly_ndvi.npz"
    if hm.exists():
        z = np.load(hm)
        from affine import Affine
        t = Affine(*z["transform"].tolist())
        crs = str(z["crs"])
        k = int(np.argmax([np.isfinite(m).mean() if mo.startswith("2025") else -1 for m, mo in zip(z["ndvi"], z["months"])]))
        fig, ax = plt.subplots(figsize=(6, 6))
        im, counts["hls"] = _raster(ax, z["ndvi"][k], t, crs, poly, 200, f"HLS NDVI, 30 m, monthly median {z['months'][k]}", "Greens")
        fig.colorbar(im, ax=ax, shrink=0.7)
        save(fig, "hls")
    else:
        missing.append("hls")
    gcard = data / "cards" / fid / "gpm.json"
    if gcard.exists():
        loc = json.loads(gcard.read_text())["location"]
        lon_e = [round(x - 0.05, 2) for x in loc["box_cells_lon"]] + [round(loc["box_cells_lon"][-1] + 0.05, 2)]
        lat_e = [round(x - 0.05, 2) for x in loc["box_cells_lat"]] + [round(loc["box_cells_lat"][-1] + 0.05, 2)]
        fig, ax = plt.subplots(figsize=(6, 6))
        _cells(ax, lat_e, lon_e, f, box, f"GPM IMERG 0.1 deg cells over the box ({len(lon_e) - 1} x {len(lat_e) - 1});\nthe field's rain is the cell holding it")
        counts["gpm"] = "inside one 0.1 deg cell"
        save(fig, "gpm")
    else:
        missing.append("gpm")
    rcard = data / "cards" / fid / "grace.json"
    if rcard.exists():
        cell = json.loads(rcard.read_text())["location"]["cell"]
        fig, ax = plt.subplots(figsize=(6, 6))
        _cells(ax, cell["lat_bounds"], cell["lon_bounds"], f, box,
               "GRACE 0.5 deg grid cell holding the field\n(the data's native size is a 3 deg mascon, about 330 km)")
        counts["grace"] = "inside one 0.5 deg cell (3 deg mascon)"
        save(fig, "grace")
    else:
        missing.append("grace")
    for name, d in (("modis", data / "raw" / "appeears" / fid / "modis"), ("smap", data / "raw" / "appeears" / fid / "smap_l3_am"),
                    ("ecostress", data / "raw" / "eco_lste" / fid)):
        if not d.exists() or not any(d.iterdir()):
            missing.append(name)
    res = {"field": f["name"], "polygon": poly, "pixel_counts": counts, "not_yet": missing}
    (data / "checks" / fid).mkdir(parents=True, exist_ok=True)
    (data / "checks" / fid / "field_pixels.json").write_text(json.dumps(res, indent=1) + "\n")
    print(json.dumps(res, indent=1))
    return 0


if __name__ == "__main__":
    sys.exit(main())

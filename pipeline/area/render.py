"""Class layers for the site: warped to Web Mercator for Leaflet's L.imageOverlay (rules.yaml area_map render),
written as small palette PNGs. Class codes: 0..n-1 the classes, -1 'not enough clear pictures', -2 not cropland
(transparent)."""
import numpy as np


def mercator_grid(bbox, ground_pixel_m):
    """(transform, width, height) of an EPSG:3857 grid whose edges are exactly the box [min_lon, min_lat, max_lon,
    max_lat], with pixels of about ground_pixel_m on the ground at the box centre."""
    from rasterio.transform import from_bounds
    from rasterio.warp import transform as warp
    xs, ys = warp("EPSG:4326", "EPSG:3857", [bbox[0], bbox[2]], [bbox[1], bbox[3]])
    lat = np.radians((bbox[1] + bbox[3]) / 2)
    step = ground_pixel_m / np.cos(lat)                  # Mercator units per ground metre at the centre
    w, h = int(round((xs[1] - xs[0]) / step)), int(round((ys[1] - ys[0]) / step))
    return from_bounds(xs[0], ys[0], xs[1], ys[1], w, h), w, h


def warp_classes(cls, src_transform, src_crs, dst_transform, shape):
    """Nearest-neighbour warp of class codes; outside the source = -2 (transparent)."""
    from rasterio.enums import Resampling
    from rasterio.warp import reproject
    src = (np.asarray(cls) + 3).astype(np.uint8)          # 1 = not cropland, 2 = no data, 3.. classes; 0 = outside
    dst = np.zeros(shape, np.uint8)
    reproject(src, dst, src_transform=src_transform, src_crs=src_crs, dst_transform=dst_transform,
              dst_crs="EPSG:3857", resampling=Resampling.nearest, src_nodata=0, dst_nodata=0)
    return np.where(dst == 0, -2, dst.astype(int) - 3)


def _rgb(h):
    h = h.lstrip("#")
    return [int(h[i:i + 2], 16) for i in (0, 2, 4)]


def write_png(cls, colours, no_data_colour, path):
    """Palette PNG: index 0 transparent (not cropland), 1 = no data, 2.. the classes in order."""
    from PIL import Image
    c = np.asarray(cls)
    idx = np.where(c <= -2, 0, np.where(c == -1, 1, c + 2)).astype(np.uint8)
    im = Image.fromarray(idx, mode="P")
    pal = [0, 0, 0] + _rgb(no_data_colour) + sum((_rgb(x) for x in colours), [])
    im.putpalette(pal + [0] * (768 - len(pal)))
    im.save(path, optimize=True, transparency=0)
    return path

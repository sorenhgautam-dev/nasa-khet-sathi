"""Data guards, CLAUDE.md golden rule 12. Every fetch/clean module uses these:

1. describe_raw_attrs()  -> print the raw variable's attributes BEFORE converting
2. mask_fill()           -> remove documented fill values and count them for the card
3. assert_in_range() / check_table() -> fail loudly after converting; never clip
4. make_card() + write_card() -> data/cards/<dataset>.json

The range checks are pure. write_card() does file I/O, which rule 7 allows inside fetch/.

xarray gotcha: when a file is opened with the default mask_and_scale=True, xarray moves
scale_factor, add_offset and _FillValue from .attrs into .encoding. Pass both dicts to
describe_raw_attrs(), or open with mask_and_scale=False, or the card will say ABSENT wrongly.
"""
import json
import logging
from pathlib import Path

import numpy as np

log = logging.getLogger("khet_sathi.guards")

# Sanity bounds set by the project owner in CLAUDE.md golden rule 12. They catch unit and scale
# mistakes; they are not science thresholds.
# Decision D2 (owner, 2026-11-11): when a product documents its own valid range, THAT is the hard
# limit; values outside these rule-12 bounds but inside the product's range are logged as warnings
# and counted in the data card (e.g. SMAP L4 soil moisture: valid 0 to 0.9, warning above 0.6).
RANGES = {
    "rain_mm": (0.0, 500.0),     # mm per day
    "temp_c": (-30.0, 50.0),     # deg C
    "ndvi": (-1.0, 1.0),
    "theta_m3m3": (0.0, 0.6),    # volumetric soil moisture
    "rh_pct": (0.0, 100.0),      # percent
}

RAW_ATTR_KEYS = ["units", "scale_factor", "add_offset", "_FillValue", "valid_range"]

CARD_FIELDS = [
    "dataset", "product", "version", "variable", "units_in", "units_out", "scale_factor",
    "fill_values_removed", "quality_flags_used", "records_dropped", "date_range", "time_zone",
    "pixel_count", "source", "resolution", "raw_attrs",
]
CARD_OPTIONAL = ["notes", "range_warnings", "segments",   # segments: product switches over time (D1)
                 "location",                               # {lat, lon, elevation_m, ...} of the cell or station
                 "corrections",                            # decision A: what was corrected, how, held-out error
                 "cross_source_flags"]                     # decision B: rain spike flags (never deletions)


class DataGuardError(ValueError):
    """Raised whenever data breaks a guard. Never caught to carry on silently."""


def _fail_outside(arr, lo, hi, column, label):
    below, above = arr < lo, arr > hi
    problems = []
    if below.any():
        problems.append(f"{int(below.sum())} value(s) below {lo} (lowest {np.nanmin(arr[below])})")
    if above.any():
        problems.append(f"{int(above.sum())} value(s) above {hi} (highest {np.nanmax(arr[above])})")
    if problems:
        raise DataGuardError(f"{column} [{label}]: " + "; ".join(problems) + ". Not clipped: fix the conversion.")


def assert_in_range(values, kind, column, valid_range=None):
    """Fail loudly on any value outside the hard limit; return how many values were only warned about.

    Hard limit: the product's documented valid_range (converted units) if given, else RANGES[kind].
    Warning: a value inside the product's range but outside RANGES[kind] is logged and counted.
    NaN (missing) is allowed; infinity is not. The input is never modified."""
    if kind not in RANGES:
        raise DataGuardError(f"{column}: no range defined for kind '{kind}' (known: {sorted(RANGES)})")
    arr = np.asarray(values, dtype=float)
    if np.isinf(arr).any():
        raise DataGuardError(f"{column}: {int(np.isinf(arr).sum())} infinite value(s)")
    lo, hi = RANGES[kind]
    if valid_range is None:
        _fail_outside(arr, lo, hi, column, kind)
        return 0
    _fail_outside(arr, valid_range[0], valid_range[1], column, f"{kind}, product valid range")
    outside_rule12 = (arr < lo) | (arr > hi)
    n = int(outside_rule12.sum())
    if n:
        log.warning("%s: %d value(s) outside the rule-12 range %s to %s but inside the product's valid "
                    "range %s to %s; kept and counted (decision D2)", column, n, lo, hi, *valid_range)
    return n


def assert_nonnegative(values, column):
    """Physical floor for quantities that cannot be negative (wind speed, radiation)."""
    arr = np.asarray(values, dtype=float)
    if np.isinf(arr).any():
        raise DataGuardError(f"{column}: {int(np.isinf(arr).sum())} infinite value(s)")
    neg = arr < 0
    if neg.any():
        raise DataGuardError(f"{column}: {int(neg.sum())} negative value(s) (lowest {np.nanmin(arr[neg])})")


def scaled_range(raw_range, scale_factor, add_offset=0.0):
    """Convert a documented raw valid range (stored integers) into physical units."""
    return tuple(v * scale_factor + add_offset for v in raw_range)


def check_table(df, kinds, valid_ranges=None):
    """Range-check each column in kinds ({column: kind}); valid_ranges ({column: (lo, hi)}) holds
    product ranges in converted units. Returns {column: number of values warned about}."""
    missing = [c for c in kinds if c not in df.columns]
    if missing:
        raise DataGuardError(f"columns missing from table: {missing}")
    valid_ranges = valid_ranges or {}
    return {column: assert_in_range(df[column].to_numpy(), kind, column, valid_ranges.get(column))
            for column, kind in kinds.items()}


def mask_fill(raw, fill_values):
    """Return (float copy with fill values set to NaN, number removed). Fill values are compared in
    the raw array's own dtype, so a float32 fill matches however the documentation writes it."""
    raw = np.asarray(raw)
    is_fill = np.zeros(raw.shape, dtype=bool)
    for fv in fill_values:
        is_fill |= raw == np.asarray(fv, dtype=raw.dtype)
    out = raw.astype(float)
    out[is_fill] = np.nan
    return out, int(is_fill.sum())


def describe_raw_attrs(attrs, encoding=None):
    """The five attributes rule 12 asks for, from attrs and (xarray) encoding; ABSENT if neither has one."""
    merged = {**(encoding or {}), **(attrs or {})}
    out = {k: merged.get(k, "ABSENT") for k in RAW_ATTR_KEYS}
    if out["valid_range"] == "ABSENT" and "valid_min" in merged and "valid_max" in merged:
        out["valid_range"] = [merged["valid_min"], merged["valid_max"]]
    for k, v in out.items():
        if isinstance(v, np.generic):
            out[k] = v.item()
        elif isinstance(v, np.ndarray):
            out[k] = v.tolist()
    return out


def make_card(**fields):
    missing = [k for k in CARD_FIELDS if k not in fields]
    if missing:
        raise DataGuardError(f"data card missing fields: {missing}")
    unknown = [k for k in fields if k not in CARD_FIELDS + CARD_OPTIONAL]
    if unknown:
        raise DataGuardError(f"data card has unknown fields: {unknown}")
    return {k: fields[k] for k in CARD_FIELDS + CARD_OPTIONAL if k in fields}


def annotate_card(path, key, value):
    """Add or replace one optional field in an existing card file (e.g. spike flags found later)."""
    if key not in CARD_OPTIONAL:
        raise DataGuardError(f"cannot add '{key}' to a card; allowed: {CARD_OPTIONAL}")
    path = Path(path)
    card = json.loads(path.read_text())
    card[key] = value
    path.write_text(json.dumps(make_card(**card), indent=1, default=str) + "\n")
    return path


def write_card(card, cards_dir):
    """Write data/cards/<dataset>.json and return its path."""
    cards_dir = Path(cards_dir)
    cards_dir.mkdir(parents=True, exist_ok=True)
    path = cards_dir / f"{card['dataset']}.json"
    path.write_text(json.dumps(card, indent=1, default=str) + "\n")
    return path

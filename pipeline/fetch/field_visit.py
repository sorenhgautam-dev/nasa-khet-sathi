"""The field team's own measurements (owner's item 4): data/field_visit/<field>/field_capacity.csv, filled in by
notes/FIELD_CAPACITY_PROTOCOL.md. Reads the file, stops on an impossible tin, writes data/cards/<field>/field_capacity.json
and returns the median field capacity per depth (pipeline/twin/field_capacity.py), or None while there is no file."""
import json

import pandas as pd

from pipeline.twin import field_capacity as fcap

COLUMNS = ["part", "depth_cm", "tin", "tin_empty_g", "tin_volume_ml", "wet_with_tin_g", "dry_with_tin_g", "dried_how", "notes"]


def load_field_capacity(field_id, data_dir):
    path = data_dir / "field_visit" / field_id / "field_capacity.csv"
    if not path.exists():
        return None
    raw = pd.read_csv(path, dtype={"part": str, "depth_cm": str, "tin": str, "dried_how": str, "notes": str})
    print(f"[field_capacity raw] {path}: columns {list(raw.columns)}, {len(raw)} tins; units g and ml (1 g water = 1 ml)")
    missing = [c for c in COLUMNS if c not in raw.columns]
    if missing:
        raise ValueError(f"{path}: missing columns {missing}")
    tins = fcap.tin_values(raw)
    med = fcap.depth_medians(tins)
    card = {"product": "field team's tins (notes/FIELD_CAPACITY_PROTOCOL.md)", "file": str(path), "variable": "theta_fc_m3m3",
            "units_in": "g, ml", "units_out": "m3/m3, g/cm3", "records": len(tins), "records_dropped": 0,
            "dried_how": tins["dried_how"].fillna("").value_counts().to_dict(),
            "by_depth": med.to_dict(orient="records"),
            "by_part_and_depth": tins.groupby(["part", "depth_cm"])["theta_fc_m3m3"].median().round(4).reset_index().to_dict(orient="records"),
            "bulk_density_g_cm3_median": tins.groupby("depth_cm")["bulk_density_g_cm3"].median().round(3).to_dict()}
    cards = data_dir / "cards" / field_id
    cards.mkdir(parents=True, exist_ok=True)
    (cards / "field_capacity.json").write_text(json.dumps(card, indent=1, default=str) + "\n")
    return med

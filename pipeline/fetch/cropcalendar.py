"""A field's crop calendar from the FAO Crop Calendar (the global default of config/countries/default.yaml; owner's item 3,
2026-11-14: "FAO crop calendars by country"). Rules: config/rules.yaml crop_calendar.zone_from_fao and fao_crop_ids.

    .venv/bin/python -m pipeline.fetch.cropcalendar --field ambohidratrimo        # fetch, convert, write the card
    .venv/bin/python -m pipeline.fetch.cropcalendar --zones MG                    # list a country's zones (to pick the aez)

The field config names the zone: `fao_crop_calendar: {country: MG, aez: "004"}` (a person picks the zone from its
administrative units; never guessed) and may name each crop's default session by FAO's own label
(`crop_calendar_defaults: {rice: "Riz de saison de pluie ou vakiambiaty"}`). The API answer is cached in
data/raw/cropcalendar/<field>/, the converted windows go to data/clean/<field>/crop_calendar.json, read by
pipeline/fetch/cropslib.load_crops(field=...). A Nepal field keeps crops.json's own hand-made windows (its profile says so).
"""
import argparse
import copy
import json
import math
import re
import sys
import urllib.request
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
API = "https://api-cropcalendar.apps.fao.org/api/v1/countries"


# --- pure: FAO sessions -> crops.json windows ---

def _md(d):
    return f"{int(d['month']):02d}-{int(d['day']):02d}"


def _days(gp):
    """FAO growing_period {'period': 'days', 'value': '155 - 165'} -> [155, 165]; '150' -> [150]; anything else None."""
    if not gp or gp.get("period") != "days" or not str(gp.get("value", "")).strip():
        return None
    parts = [p.strip() for p in str(gp["value"]).split("-")]
    try:
        return [int(p) for p in parts if p]
    except ValueError:
        return None


def _note(session):
    """FAO's session label, and the water regime when FAO's comments open with it (the plan scorer flags 'irrigated'
    windows unless they say 'rainfed'; FAO writes 'Irrigated.', 'Not irrigated' or 'Unirrigated.')."""
    label = (session.get("additional_information") or "").strip()
    first = re.split(r"[.,]", (session.get("comments") or "").strip())[0].strip().lower()
    water = {"irrigated": "Irrigated (FAO)", "not irrigated": "rainfed (FAO: 'Not irrigated')",
             "unirrigated": "rainfed (FAO: 'Unirrigated')"}.get(first)
    return "; ".join(x for x in (label, water) if x)


def windows_from_fao(records, crop_ids, defaults=None):
    """{crop: {'windows': [...], 'default': i, 'fao_name', 'labels': [...], 'dropped': [...]}} for the library crops whose
    FAO id is in `records`. A session without a growing period in days is dropped (as in Nepal's transcription); days
    that cannot fit the window's own dates are recomputed from them (REVIEW_NOTES H4). The default is the session named
    in `defaults` (by FAO's label), else the first kept session. Pure."""
    from pipeline.twin.crops import window_day_span
    by_id = {}
    for r in records:
        by_id.setdefault(str(r["crop"]["id"]), []).append(r)
    out = {}
    for crop, fid in crop_ids.items():
        recs = by_id.get(str(fid))
        if not recs:
            continue
        windows, labels, dropped = [], [], []
        for r in recs:
            for s in r.get("sessions") or []:
                lab = (s.get("additional_information") or "").strip()
                days = _days(s.get("growing_period"))
                if days is None or not all(s.get(k) for k in ("early_sowing", "later_sowing", "early_harvest", "late_harvest")):
                    dropped.append({"label": lab, "why": "no growing period in days"})
                    continue
                w = {"sow": _md(s["early_sowing"]), "sow_end": _md(s["later_sowing"]), "harvest": _md(s["early_harvest"]),
                     "harvest_end": _md(s["late_harvest"]), "days": days, "note": _note(s)}
                lo, hi = window_day_span(w)
                if max(days) < lo or min(days) > hi:
                    w["note"] = (w["note"] + "; " if w["note"] else "") + \
                        f"days recomputed from this window's own dates: FAO lists {s['growing_period']['value']}"
                    w["days"] = [lo, hi]
                windows.append(w)
                labels.append(lab)
        if not windows:
            continue
        want = (defaults or {}).get(crop)
        if want is not None and want not in labels:
            raise ValueError(f"crop_calendar_defaults: {crop} has no FAO session {want!r}; its sessions: {labels}")
        out[crop] = {"windows": windows, "default": labels.index(want) if want is not None else 0,
                     "default_named": want is not None, "fao_name": recs[0]["crop"]["name"], "labels": labels,
                     "dropped": dropped}
    return out


def zone_stages(crop, default_window):
    """The twin's stage lengths in a zone (crops.json's rule, REVIEW_NOTES H4): FAO-56's (stages_fao56, else stages_days)
    when their total lies in the default window's days; else scaled to the middle of those days, rounded half up. Pure."""
    from pipeline.twin.crops import scale_stages
    base = crop.get("stages_fao56") or crop.get("stages_days")
    if not base:
        return None
    days = [int(d) for d in default_window["days"]]
    total = sum(base.values())
    if min(days) <= total <= max(days):
        return dict(base)
    return scale_stages(base, int(math.floor((min(days) + max(days)) / 2 + 0.5)))


def apply_zone(lib, zone):
    """The crop library with the zone's windows: each crop FAO lists takes its windows, default and stages; a crop FAO does
    not list in the zone gets no window and `simulate: false` (the twin never sows it there). Pure (copies)."""
    out = copy.deepcopy(lib)
    where = f"FAO Crop Calendar, {zone['country']} aez {zone['aez']} '{zone.get('aez_name')}'"
    for name, c in out.items():
        src = c.setdefault("sources", {})
        z = zone["crops"].get(name)
        if z is None:
            c["calendar"] = {"windows": [], "default": None}
            c["simulate"] = False
            src["simulate"] = f"not listed in the {where}"
            src["calendar"] = f"none: not listed in the {where}"
            continue
        c["calendar"] = {"windows": z["windows"], "default": z["default"]}
        src["calendar"] = (f"{where}, lastUpdated {zone.get('last_updated')}, {zone.get('url')} (read {zone.get('read')}), "
                           f"'{z['fao_name']}'; default session '{z['labels'][z['default']]}'"
                           + ("" if z.get("default_named") else " (the first listed: no default named in the field config)"))
        st = zone_stages(c, z["windows"][z["default"]])
        if st is not None:
            c["stages_days"] = st
            src["stages_days"] = (f"FAO-56 Table 11 stages {c.get('stages_fao56') or lib[name].get('stages_days')}, kept or scaled "
                                  f"to the middle of the zone's default window ({z['windows'][z['default']]['days']} d): {st} "
                                  "(rules.yaml crop_calendar.zone_from_fao)")
    return out


# --- I/O ---

def _get(url):
    req = urllib.request.Request(url, headers={"User-Agent": "khet-sathi-pipeline"})
    with urllib.request.urlopen(req, timeout=60) as r:
        return json.loads(r.read().decode())


def zones(country):
    return [{"aez": z["zone_id"], "name": z["name"], "units": z.get("administratrative_units")}
            for z in _get(f"{API}/{country}/aez?language=en")]


def zone_path(field_id, data_dir=REPO / "data"):
    return Path(data_dir) / "clean" / field_id / "crop_calendar.json"


def build(field, data_dir=REPO / "data", get=_get):
    import datetime as dt

    from pipeline.fetch.rules import load_rules
    cfg = field.get("fao_crop_calendar") or {}
    if not cfg.get("country") or not cfg.get("aez"):
        raise ValueError(f"config/fields/{field['id']}.yaml: fao_crop_calendar needs country and aez (a person picks the zone: "
                         f"python -m pipeline.fetch.cropcalendar --zones <ISO2>)")
    url = f"{API}/{cfg['country']}/cropCalendar?language=en&aez={cfg['aez']}"
    raw_dir = Path(data_dir) / "raw" / "cropcalendar" / field["id"]
    raw_dir.mkdir(parents=True, exist_ok=True)
    raw = raw_dir / f"{cfg['country']}_{cfg['aez']}.json"
    if not raw.exists():
        raw.write_text(json.dumps(get(url), ensure_ascii=False))
    records = json.loads(raw.read_text())
    if not records:
        raise ValueError(f"the FAO Crop Calendar has no entries for {cfg['country']} aez {cfg['aez']}")
    ids = load_rules()["crop_calendar"]["fao_crop_ids"]
    crops = windows_from_fao(records, ids, field.get("crop_calendar_defaults"))
    for c in field.get("current_rotation") or []:
        if c not in crops:
            raise ValueError(f"the field's current rotation grows {c}, which the FAO Crop Calendar does not list for "
                             f"{cfg['country']} aez {cfg['aez']}")
    zone = {"country": cfg["country"], "aez": cfg["aez"], "aez_name": records[0]["aez"]["name"],
            "last_updated": records[0].get("lastUpdated"), "url": url,
            "read": dt.datetime.fromtimestamp(raw.stat().st_mtime).date().isoformat(), "crops": crops,
            "not_listed": sorted(set(ids) - set(crops)), "rule": "rules.yaml crop_calendar.zone_from_fao"}
    out = zone_path(field["id"], data_dir)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(zone, indent=1, ensure_ascii=False) + "\n")
    card = Path(data_dir) / "cards" / field["id"] / "crop_calendar.json"
    card.parent.mkdir(parents=True, exist_ok=True)
    card.write_text(json.dumps({"dataset": "crop_calendar", "product": "FAO Crop Calendar (API v1)", "version": zone["last_updated"],
                                "source": url, "zone": f"{zone['country']} aez {zone['aez']} {zone['aez_name']}",
                                "crops": {k: {"fao_name": v["fao_name"], "sessions": v["labels"], "default": v["labels"][v["default"]],
                                              "default_named_in_config": v["default_named"], "dropped": v["dropped"]}
                                          for k, v in crops.items()},
                                "library_crops_not_listed": zone["not_listed"], "fetched": zone["read"]}, indent=1,
                               ensure_ascii=False) + "\n")
    return zone


def main(argv=None):
    from pipeline.fetch.fields import load_field
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--field")
    ap.add_argument("--zones", metavar="ISO2", help="list a country's FAO zones with their administrative units, and stop")
    a = ap.parse_args(argv)
    if a.zones:
        for z in zones(a.zones):
            print(f"{z['aez']}  {z['name']}: {z['units']}")
        return 0
    zone = build(load_field(a.field))
    for c, z in zone["crops"].items():
        print(f"{c:8s} {z['fao_name']:14s} default '{z['labels'][z['default']]}': " +
              "; ".join(f"{w['sow']}..{w['sow_end']} -> {w['harvest']}..{w['harvest_end']} {w['days']} d" for w in z["windows"]))
    print(f"not listed: {zone['not_listed']} -> {zone_path(a.field).relative_to(REPO)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())

"""The current plan's options (owner's answer 6 to REVIEW_2, 2026-11-13; rules.yaml plans.current_options). Pure.

Season timing from the satellite cannot always tell two crops apart (rice then potato or wheat on the demo field),
so the app asks the farmer and the export holds the current plan once for each answer. The first option is the
field's default rotation on its default dates. In another option, a crop the default does not grow is sown on the
date (start, middle or end of a calendar window the twin can simulate, not overlapping the option's other crops)
whose simulated season lies closest to the satellite's season of a slot: the median over the years of
    |detected start - (sowing + initial stage)| + |detected end - simulated harvest|   (days)
(FAO-56: the initial stage runs from planting to about 10% ground cover, where green-up shows). Ties go to the later
date. The crop's season length is the twin's own (its stage lengths), so a satellite season that is longer or later
than any calendar date still leaves a distance: it is reported, never hidden.
"""
import numpy as np
import pandas as pd

from pipeline.plans import generate as ge


def season_distance(season, spec, lib):
    """Days between one detected season and the option's simulated season, at the nearer of two anchor years."""
    ini = int(lib[spec["crop"]]["stages_days"]["ini"])
    best = None
    for year in (season["start"].year - 1, season["start"].year):
        sow, end = ge.season_in_year(spec, lib, year)
        d = abs((season["start"] - (sow + pd.Timedelta(ini, unit="D"))).days) + abs((season["end"] - end).days)
        best = d if best is None else min(best, d)
    return int(best)


def sowing_distance(seasons, spec, lib):
    """Median over the detected seasons of season_distance."""
    return float(np.median([season_distance(s, spec, lib) for s in seasons]))


def best_spec(seasons, crop, lib, positions, fixed_specs):
    """{'spec', 'distance_days', 'candidates'} for the crop's sowing date closest to the detected seasons, among
    the dates that fit beside fixed_specs; None when no date fits or there is no season to compare with."""
    if not seasons:
        return None
    cands = []
    for opt in ge.options(lib, [crop], positions):
        if ge.fits(list(fixed_specs) + [opt], lib):
            cands.append({"spec": opt, "distance_days": sowing_distance(seasons, opt, lib),
                          "sow": ge.season_in_year(opt, lib, ge.REF_YEAR)[0]})
    if not cands:
        return None
    low = min(c["distance_days"] for c in cands)
    best = max((c for c in cands if c["distance_days"] == low), key=lambda c: c["sow"])
    return {"spec": best["spec"], "distance_days": low,
            "candidates": [{"spec": c["spec"], "distance_days": c["distance_days"]} for c in cands]}


def option_specs(rotation, default_specs, seasons_by_slot, lib, positions):
    """(specs in sowing order, {crop: how its date was chosen}) for one rotation of current_rotation_options.
    Crops the default rotation grows keep its dates; each other crop takes its best date over the slots."""
    by_crop = {sp["crop"]: sp for sp in default_specs}
    kept = [by_crop[c] for c in rotation if c in by_crop]
    specs, why = list(kept), {}
    for crop in rotation:
        if crop in by_crop:
            continue
        found = None
        for slot, seasons in seasons_by_slot.items():
            b = best_spec(seasons, crop, lib, positions, specs)
            if b and (found is None or b["distance_days"] < found["distance_days"]):
                found = {**b, "slot": slot}
        if found is None:
            raise ValueError(f"no sowing date of {crop} fits beside {[s['crop'] for s in specs]}: the option cannot be simulated")
        specs.append(found["spec"])
        why[crop] = {"slot": found["slot"], "distance_days": found["distance_days"], "candidates": found["candidates"]}
    return ge.ordered(specs, lib), why

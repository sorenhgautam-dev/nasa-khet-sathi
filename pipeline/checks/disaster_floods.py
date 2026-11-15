"""Flood years from Nepal's disaster databases against our flood-year flag (owner, 2026-11-15, answer 4; rules.yaml
disaster_floods, committed before any score). Pure functions; the reading of files is in scripts/run_disaster_floods.py."""


def _n(v):
    try:
        return float(v or 0)
    except (TypeError, ValueError):
        return 0.0


def bipad_years(records_by_key, rule):
    """{year: [record ids]} for BIPAD records that count: the district, the flood hazards, a reported loss."""
    out = {}
    for key, recs in records_by_key.items():
        district, hazard = (int(x) for x in key.split("_"))
        if district != rule["place"]["value"]["bipad_district"] or hazard not in rule["type"]["value"]["bipad_hazards"]:
            continue
        for r in recs:
            loss = r.get("loss") or {}
            if any(_n(loss.get(f)) > 0 for f in rule["loss"]["value"]["bipad"]):
                out.setdefault(int(r["incidentOn"][:4]), []).append(r["id"])
    return out


def desinventar_years(records, rule):
    """{year: [serials]} for DesInventar records that count: the district, FLOOD (or RAINS whose words say flood or
    inundation), a reported loss."""
    t, out = rule["type"]["value"], {}
    for r in records:
        if r.get("name1") != rule["place"]["value"]["desinventar_name1"]:
            continue
        words = " ".join(str(r.get(k) or "") for k in ("lugar", "causa", "descausa", "otros", "di_comments")).lower()
        if not (r.get("evento") in t["desinventar_events"]
                or (r.get("evento") == "RAINS" and any(w in words for w in t["desinventar_rains_if_words"]))):
            continue
        if any(_n(r.get(f)) > 0 for f in rule["loss"]["value"]["desinventar"]):
            out.setdefault(int(r["fechano"]), []).append(r["serial"])
    return out


def score(db_years, flagged, replay_years, span, min_years):
    """The two counts over the replay years the database covers in full, or why it is not scored. Pure."""
    years = [y for y in replay_years if span[0] <= y <= span[1]]
    db = sorted(y for y in db_years if y in years)
    ours = sorted(y for y in flagged if y in years)
    out = {"span": [years[0], years[-1]] if years else None, "years": len(years), "db_flood_years": db, "flagged_years": ours}
    if len(db) < min_years:
        out.update(scored=False, why=f"only {len(db)} flood year{'s' if len(db) != 1 else ''} in {years[0]}-{years[-1]}; "
                                    f"at least {min_years} are needed")
        return out
    out.update(scored=True, db_also_flagged=[len([y for y in db if y in ours]), len(db)],
               flagged_with_record=[len([y for y in ours if y in db]), len(ours)])
    return out

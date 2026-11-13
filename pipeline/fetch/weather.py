"""Build the twin's daily weather table for one field: data/clean/<field>/weather.parquet.

    .venv/bin/python -m pipeline.fetch.weather --field demo

1. Temperature (decision A): if the field config names a nearby station (`validation_station`), fit a
   monthly POWER-minus-station correction for each column in rules.yaml, test it on held-out years,
   and apply it only where it lowered the held-out error. The label comes from `correction_label`
   (e.g. "Kathmandu-valley correction"). Without a station, POWER is used uncorrected and labelled so.
   The correction is applied BEFORE ET0 and frost. Owner, 2026-11-12: the monthly offset serves the
   twin's temperatures and ET0 (`tmin_c`); quantile-mapped Tmin serves frost only (`tmin_frost_c`), shown
   as risk bands, never as a count.
   A month with no fitted offset (or no quantile-mapping model) passes through uncorrected: a warning names
   it and the card records `months_uncorrected` (REVIEW_NOTES M8). Every day must have tmin_c and
   tmin_frost_c at or below tmax_c, or the build fails (golden rule 12c, REVIEW_NOTES M9).
2. Rain (D6, D): GPM IMERG (data/clean/<field>/gpm.parquet) with POWER as fill-in only; until GPM is
   fetched, rain is missing. POWER may fill at most rules.yaml power_rain.max_filled_fraction_per_year of
   any year's days inside GPM's own record, or the build fails (REVIEW_NOTES M2); counts per year in the card.
   GPM break (owner's decision 1, 2026-11-13; rules.yaml gpm_series.correction): IMERG Final days from
   2017-01-01 are scaled month by month back to GPM's own 2001-2016 level (rain_mm, the twin's rain;
   rain_break_corrected flags the days); the rain as published is kept as rain_uncorrected_mm for the second run.
3. Spikes (B): flags from every rain source pair, written to this card and to each source's card.
4. ET0 (step 3): FAO-56 Penman-Monteith from the corrected temperatures. Humidity (owner decision,
   2026-11-12, REVIEW_NOTES M6): the actual vapour pressure is held from POWER (RH2M with POWER's own
   temperatures), capped at e0 of the corrected Tmin (`ea_kpa`, `ea_capped`), for `et0_mm`; the RH-held
   alternative is kept as `et0_rh_held_mm` and both are compared in the card.
The card names each column's source and resolution (golden rule 12e).
"""
import argparse
import json
import sys
from pathlib import Path

import pandas as pd

from pipeline.checks.spikes import spike_days, vote
from pipeline.fetch import guards as g
from pipeline.fetch.fields import load_field
from pipeline.fetch.rules import load_rules
from pipeline.twin import bias, inputs, qmap
from pipeline.twin.et0 import et0_mm
from pipeline.twin.inputs import merge_rain

REPO = Path(__file__).resolve().parents[2]
MONTHS = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]
POWER_SRC = ("NASA POWER daily point API, community AG, model-based (MERRA-2 / GEOS-IT meteorology, "
             "CERES SYN1deg / FLASHFlux solar)")
POWER_MET_RES = "0.5 x 0.625 deg (POWER meteorology cell)"
POWER_SOLAR_RES = "1 x 1 deg (POWER solar cell)"


def warn(message):
    print(f"WARNING: {message}", file=sys.stderr, flush=True)


def month_names(months):
    return ", ".join(MONTHS[m - 1] for m in months)


def check_tmin_not_above_tmax(df, tmin_col, tmax_col="tmax_c"):
    """Golden rule 12c: fail loudly if any day has tmin_col above tmax_col; otherwise return 0, the count
    the card records."""
    bad = (df[tmin_col] > df[tmax_col]).to_numpy()
    if bad.any():
        days = df.loc[bad, "date"].dt.strftime("%Y-%m-%d").tolist()
        raise g.DataGuardError(f"{tmin_col} above {tmax_col} on {int(bad.sum())} day(s): {days[:10]}"
                               + (" ..." if len(days) > 10 else "") + ". Not clipped: check the correction.")
    return 0


def check_gpm_cell(card_path, lat, lon):
    """gpm.parquet holds the rain of the 0.1 deg cell the field was in when GPM was fetched (gpm.py). Stop
    loudly if the card is missing or the field now lies in another cell (REVIEW_NOTES H3: a moved field)."""
    from pipeline.fetch.gpm import cell_index
    if not Path(card_path).exists():
        raise ValueError(f"GPM rain exists but its card {card_path} does not, so its cell is unknown; refetch GPM")
    loc = json.loads(Path(card_path).read_text())["location"]
    i, j = loc["field_cell"]
    clon, clat = loc["box_cells_lon"][i], loc["box_cells_lat"][j]
    if cell_index(clat, clon) != cell_index(lat, lon):
        raise ValueError(f"GPM rain is for the cell centred {clat} N, {clon} E, but the field ({lat} N, {lon} E) "
                         "lies in another 0.1 deg cell; refetch GPM for the field")


def _read_card(path):
    return json.loads(Path(path).read_text()) if Path(path).exists() else {}


def column_sources(df, station_id, corrections, frost_method, gpm_card, n_filled, elev_m, break_info=None):
    """Golden rule 12e (REVIEW_NOTES M9): {column: source} and {column: resolution} for every column but date."""
    st = f"NOAA GHCN-Daily {station_id} (ground station)" if station_id else None

    def temp(col, param):
        c = corrections.get(col, {})
        if not c.get("applied"):
            return f"{POWER_SRC}, {param}; {c.get('label', 'uncorrected POWER')}"
        return f"{POWER_SRC}, {param}; {c['label']}: monthly offset fitted on {st}"

    flag = "pipeline flag (per day)"
    met_corr = POWER_MET_RES + (f", corrected per month from a point station ({station_id})" if station_id else "")
    if gpm_card is not None:
        g_res = gpm_card.get("resolution", "0.1 deg")
        rain = (f"{gpm_card.get('product', 'GPM IMERG')} {gpm_card.get('version', '')} ({gpm_card.get('source', '')}), "
                f"satellite-based; days GPM lacks are filled from {POWER_SRC}, PRECTOTCORR, never 2001-2003, each "
                f"flagged in rain_filled and rain_source ({n_filled} day(s))")
        rain_res = f"{g_res} (GPM); filled days {POWER_MET_RES}"
    else:
        rain = "none: GPM not fetched yet, so rain is missing (decision D: POWER never stands in for the whole series)"
        rain_res = "none (rain missing)"
    src = {
        "tmax_c_power": f"{POWER_SRC}, T2M_MAX, uncorrected", "tmin_c_power": f"{POWER_SRC}, T2M_MIN, uncorrected",
        "tmax_c": temp("tmax_c", "T2M_MAX"), "tmin_c": temp("tmin_c", "T2M_MIN"),
        "tmin_frost_c": f"{POWER_SRC}, T2M_MIN; {frost_method}",
        "tmax_corrected": flag + ": True where a fitted offset was applied",
        "tmin_corrected": flag + ": True where a fitted offset was applied",
        "tmin_frost_corrected": flag + ": True where a correction was applied to tmin_frost_c",
        "rh_pct": f"{POWER_SRC}, RH2M, not corrected (relative to POWER's own temperatures)",
        "ws2m_ms": f"{POWER_SRC}, WS2M", "rs_mj_m2_day": f"{POWER_SRC}, ALLSKY_SFC_SW_DWN",
        "rain_mm": rain + (("; IMERG Final days from " + str(break_info.get("from")) + " scaled month by month back to GPM's own "
                           f"{break_info.get('reference_years')} level (owner's decision 1, 2026-11-13; rules.yaml gpm_series.correction; "
                           "factors in corrections.rain_break)") if break_info else ""),
        "rain_uncorrected_mm": rain + "; as published, without the break correction (the uncorrected run)",
        "rain_break_corrected": flag + ": True where the GPM break correction scaled the day",
        "rain_source": flag + ": gpm, power_fill or missing", "rain_filled": flag + ": True where POWER filled",
        "ea_kpa": f"derived, model-based: from {POWER_SRC} RH2M, T2M_MAX, T2M_MIN (FAO-56 eq. 19), capped at e0(tmin_c)",
        "ea_capped": flag + ": True where ea_kpa is capped at e0(tmin_c)",
        "et0_mm": ("derived, model-based: FAO-56 Penman-Monteith (pipeline/twin/et0.py) from tmax_c, tmin_c, ea_kpa, "
                   f"ws2m_ms, rs_mj_m2_day at {elev_m} m"),
        "et0_rh_held_mm": "derived, model-based: as et0_mm but ea from rh_pct with the corrected temperatures; comparison only",
    }
    res = {"tmax_c_power": POWER_MET_RES, "tmin_c_power": POWER_MET_RES, "tmax_c": met_corr, "tmin_c": met_corr,
           "tmin_frost_c": met_corr, "rh_pct": POWER_MET_RES, "ws2m_ms": POWER_MET_RES, "rs_mj_m2_day": POWER_SOLAR_RES,
           "rain_mm": rain_res, "rain_uncorrected_mm": rain_res, "ea_kpa": POWER_MET_RES + " (corrected Tmin for the cap)",
           "et0_mm": f"mixed: {met_corr}; solar {POWER_SOLAR_RES}", "et0_rh_held_mm": f"mixed: {met_corr}; solar {POWER_SOLAR_RES}"}
    for k in ("tmax_corrected", "tmin_corrected", "tmin_frost_corrected", "ea_capped"):
        res[k] = "per day, as the column it flags"
    for k in ("rain_source", "rain_filled", "rain_break_corrected"):
        res[k] = "per day, as rain_mm"
    missing = [c for c in df.columns if c != "date" and (c not in src or c not in res)]
    if missing:
        raise g.DataGuardError(f"weather columns without a source or resolution (golden rule 12e): {missing}")
    return ({c: src[c] for c in df.columns if c != "date"}, {c: res[c] for c in df.columns if c != "date"})


def correct_gpm_break(rain, gpm, rule, field_id):
    """Owner's decision 1, 2026-11-13 (rules.yaml gpm_series.correction): the merged rain table gets
    rain_uncorrected_mm (as published) and rain_break_corrected; rain_mm becomes the corrected rain. GPM days of the
    products in correction_products are scaled; only days of the products in correction_factor_products set the
    factors (owner's answer 7 to REVIEW_2, 2026-11-13: the Late days take the Final factors). Returns (table, info)."""
    rain = rain.copy()
    rain["rain_uncorrected_mm"] = rain["rain_mm"]
    rain["rain_break_corrected"] = False
    if gpm is None:
        return rain, None
    if field_id not in rule["correction_fields"]:
        return rain, {"applied": False, "status": f"not applied: field '{field_id}' has no rain check B finding of the "
                                                  "break (rules.yaml gpm_series.correction_fields)"}
    d = pd.DatetimeIndex(rain["date"])
    prod = gpm.set_index("date")["product"].reindex(d).astype(str)
    gpm_day = rain["rain_source"].astype(str).to_numpy() == "gpm"
    use = gpm_day & prod.isin(rule["correction_products"]).to_numpy()
    factor_products = rule.get("correction_factor_products", rule["correction_products"])
    fit = gpm_day & prod.isin(factor_products).to_numpy()
    rs = pd.Series(rain["rain_mm"].to_numpy(float), index=d)
    ref = tuple(rule["correction_reference_years"])
    factors = inputs.break_factors(rs.where(fit), ref, rule["correction_from"])
    corrected, applied = inputs.apply_break_correction(rs, factors, rule["correction_from"], use)
    g.assert_in_range(corrected.to_numpy(), "rain_mm", "rain_mm (break-corrected)")
    rain["rain_mm"], rain["rain_break_corrected"] = corrected.to_numpy(), applied
    after = d >= pd.Timestamp(rule["correction_from"])
    yrs = sorted(set(d[after].year))
    info = {"applied": True, "method": rule["correction"], "decision": "Owner's decision 1, 2026-11-13 (VALIDATION 3.9b)",
            "from": rule["correction_from"], "reference_years": list(ref), "products": list(rule["correction_products"]),
            "factor_products": list(factor_products),
            "factors_by_month": {inputs.MONTH_NAMES[m - 1]: round(f, 3) for m, f in factors.items()},
            "days_scaled": int(applied.sum()),
            "days_not_scaled_after_start": {k: int(((~applied) & after & (prod.to_numpy() == k)).sum())
                                            for k in sorted(set(prod[after]))},
            "mean_yearly_mm_from_start": {"uncorrected": round(float(rs[after].sum() / len(yrs)), 1),
                                          "corrected": round(float(corrected[after].sum() / len(yrs)), 1)},
            "caveat": rule["trend_caveat"]}
    return rain, info


def build(field, data_dir=REPO / "data", rules=None):
    rules = rules or load_rules()
    fid, data_dir = field["id"], Path(data_dir)
    clean, cards = data_dir / "clean" / fid, data_dir / "cards" / fid
    power = pd.read_parquet(clean / "power.parquet")
    power_card = json.loads((cards / "power.json").read_text())
    station_id = field.get("validation_station")
    st_path = clean / f"ghcn_{station_id}.parquet" if station_id else None
    station = pd.read_parquet(st_path) if st_path and st_path.exists() else None

    df = pd.DataFrame({"date": power["date"]})
    corrections = {}
    tc = rules["temperature_correction"]
    for col in tc["columns"]:
        df[f"{col}_power"] = power[col]
        df[col], df[col.replace("_c", "_corrected")] = power[col], False
        if station is None:
            corrections[col] = {"label": "uncorrected POWER (no nearby station)", "applied": False,
                                "months_uncorrected": list(range(1, 13))}
            continue
        c = bias.build_correction(power, station, col, tc["min_shared_days_per_year"], tc["min_shared_days_per_month"])
        label = f"{field.get('correction_label', 'station-based correction')} (station {station_id})"
        uncorrected = list(range(1, 13))
        if c["apply"]:
            df[col] = bias.apply_offsets(power, col, c["offsets"]).to_numpy()
            has = df["date"].dt.month.map(lambda m: c["offsets"][m]["offset"] is not None)
            df[col.replace("_c", "_corrected")] = has.to_numpy()
            uncorrected = bias.months_without_offset(c["offsets"])
            if uncorrected:                         # REVIEW_NOTES M8: never silent
                warn(f"{col}: no fitted offset for {month_names(uncorrected)} (under {tc['min_shared_days_per_month']} "
                     f"shared station days); those months stay uncorrected POWER ({col.replace('_c', '_corrected')} False)")
        corrections[col] = {"label": label if c["apply"] else f"not applied: did not help on held-out years ({label})",
                            "applied": c["apply"], "method": "monthly offset" if c["apply"] else "none",
                            "months_uncorrected": uncorrected,
                            "fit_years": c["fit_years"], "test_years": c["test_years"],
                            "test": c["test"], "offsets_by_month": {m: o for m, o in c["offsets"].items()}}
        if col == "tmin_c" and c["apply"]:          # cold nights: owner, step-4 review item 1 (2026-11-12)
            cn = rules["cold_nights"]
            ch = qmap.compare_cold_night_methods(power, station, col, cn["seasons"], tc["min_shared_days_per_year"],
                                                 cn["min_shared_days_per_month"], cn["quantiles"], cn["frost_night_c"])
            corrections[col]["cold_night_comparison"] = {k: v for k, v in ch.items() if k != "qmap_models"}
            corrections[col]["roles"] = dict(cn["roles"])
            if cn["roles"]["frost"] == "quantile mapping":
                df["tmin_frost_c"] = qmap.apply_qmap(power, col, ch["qmap_models"]).to_numpy()
                df["tmin_frost_corrected"] = df["date"].dt.month.map(
                    lambda m: ch["qmap_models"][m] is not None).to_numpy()
                corrections[col]["qmap_models"] = ch["qmap_models"]
                frost_missing = sorted(int(m) for m, mod in ch["qmap_models"].items() if mod is None)
                corrections[col]["frost_months_uncorrected"] = frost_missing
                if frost_missing:
                    warn(f"tmin_frost_c: no quantile-mapping model for {month_names(frost_missing)} (too few shared "
                         "station days, even for the season); those months stay uncorrected POWER (tmin_frost_corrected False)")
            corrections[col]["frost caveat"] = (
                "Both corrections give too many cold nights on held-out years (nights below "
                f"{cn['frost_night_c']} C: see cold_night_comparison), so frost is shown only as risk bands with this "
                "caveat, never as a count (owner, 2026-11-12). " + cn["frost_display_note"])
    if "tmin_frost_c" not in df:                    # no station or no correction: frost uses the twin's Tmin
        df["tmin_frost_c"], df["tmin_frost_corrected"] = df["tmin_c"], df["tmin_corrected"]
        frost_method = "same as tmin_c (no quantile mapping)"
        if "tmin_c" in corrections:
            corrections["tmin_c"]["frost_months_uncorrected"] = corrections["tmin_c"]["months_uncorrected"]
    else:
        frost_method = f"quantile mapped onto NOAA GHCN-Daily {station_id} (ground station), for frost risk bands only"
    warned = g.check_table(df, {"tmax_c": "temp_c", "tmin_c": "temp_c", "tmin_frost_c": "temp_c"})
    corrections["tmin_not_above_tmax"] = {
        "rule": "every day must have tmin_c and tmin_frost_c at or below tmax_c, or the build fails (golden rule 12c)",
        "days": {c: check_tmin_not_above_tmax(df, c) for c in ("tmin_c", "tmin_frost_c")}}
    if station is None:
        rh_status = "check not possible: no nearby station"
    elif "rh_pct" not in station.columns:
        rh_status = "check not possible: the station records no humidity"
    else:
        rh_status = "station has humidity, but no RH correction is implemented yet (TODO)"
    corrections["rh_pct"] = {"applied": False, "status": rh_status}
    for col in ("rh_pct", "ws2m_ms", "rs_mj_m2_day"):
        df[col] = power[col]

    gpm_path = clean / "gpm.parquet"
    gpm = pd.read_parquet(gpm_path) if gpm_path.exists() else None
    if gpm is not None:
        check_gpm_cell(cards / "gpm.json", field["lat"], field["lon"])
    rain = merge_rain(df["date"], None if gpm is None else gpm.set_index("date")["rain_mm"],
                      power.set_index("date")["rain_mm"], rules["power_rain"]["never_fill_years"])
    max_fill = rules["power_rain"]["max_filled_fraction_per_year"]
    fills = inputs.fill_by_year(rain)
    breaches = inputs.fill_cap_breaches(fills["by_year"], max_fill)
    if breaches:                                    # REVIEW_NOTES M2: a partly failed GPM fetch must not pass
        raise g.DataGuardError(
            f"POWER would fill more than {max_fill:.0%} of a year's days inside the GPM record ("
            + "; ".join(f"{b['year']}: {b['filled']} of {b['days']} days, {b['fraction_filled']:.1%}" for b in breaches)
            + "). Refetch the missing GPM days; nothing written (rules.yaml power_rain.max_filled_fraction_per_year)")
    corrections["rain_mm"] = {
        "method": "GPM IMERG; POWER fills only days GPM lacks, never 2001-2003, each flagged (decisions D6, D)",
        "max_filled_fraction_per_year": max_fill,
        "status": "GPM rain with POWER fill-in" if gpm is not None else
                  "GPM not fetched yet: rain is missing on every day and nothing is filled (decision D)",
        "gpm_record": fills["primary_record"], "by_year": fills["by_year"],
        "filled_outside_gpm_record": fills["filled_outside_primary_record"]}
    rain, break_info = correct_gpm_break(rain, gpm, rules["gpm_series"], fid)
    corrections["rain_break"] = break_info or {"applied": False, "status": "no GPM record: nothing to correct"}
    df = df.merge(rain, on="date")

    sources = {"power": power[["date", "rain_mm"]]}
    if station is not None:
        sources["station"] = station[["date", "rain_mm"]]
    if gpm is not None:
        sources["gpm"] = gpm[["date", "rain_mm"]]
    flags = spike_days(sources, rules["rain_spike"]["min_mm"], rules["rain_spike"]["ratio"])
    if gpm is not None:                      # owner, 2026-11-12: the three sources vote on each flag
        flags = vote(flags, sources, rules["rain_spike"]["min_mm"], rules["rain_spike"]["ratio"])

    elev, elev_src = field.get("elevation_m"), "field config"
    if elev is None:
        elev, elev_src = power_card["location"]["elevation_m"], "POWER cell elevation (field elevation unknown until NASADEM)"
    # Humidity (owner decision, 2026-11-12, REVIEW_NOTES M6): hold ea from POWER, capped at e0(corrected Tmin)
    ea, ea_capped = inputs.ea_held_from_power_kpa(power["rh_pct"], power["tmax_c"], power["tmin_c"], df["tmin_c"])
    df["ea_kpa"], df["ea_capped"] = ea, ea_capped
    args = (df["tmax_c"], df["tmin_c"], df["ws2m_ms"], df["rs_mj_m2_day"], elev, field["lat"], df["date"].dt.day_of_year)
    df["et0_mm"] = et0_mm(*args, ea=ea)
    df["et0_rh_held_mm"] = et0_mm(*args, rh_mean=df["rh_pct"])
    for col in ("et0_mm", "et0_rh_held_mm"):
        g.assert_nonnegative(df[col].to_numpy(), col)
    cmp_ = inputs.et0_choice_summary(df["date"], df["et0_mm"], df["et0_rh_held_mm"], ea_capped)
    _, cap_if_uncorrected = inputs.ea_held_from_power_kpa(power["rh_pct"], power["tmax_c"], power["tmin_c"], power["tmin_c"])
    corrections["ea_kpa"] = {
        "method": ("actual vapour pressure held from POWER: RH2M / 100 x (e0(T2M_MAX) + e0(T2M_MIN)) / 2 with POWER's "
                   "own temperatures (FAO-56 eq. 19), capped at e0(tmin_c), the corrected Tmin; et0_mm uses it with "
                   "the corrected temperatures. et0_rh_held_mm holds RH instead (eq. 19 with the corrected "
                   "temperatures), kept for comparison only"),
        "decision": "Owner, 2026-11-12 (REVIEW_NOTES M6)",
        "cap_days": cmp_.pop("cap_days"), "cap_days_by_month": cmp_.pop("cap_days_by_month"),
        "cap_days_with_uncorrected_tmin": int(cap_if_uncorrected.sum()),
        "et0_compare": cmp_}

    out = clean / "weather.parquet"
    n_filled = int(df["rain_filled"].sum())
    source, resolution = column_sources(df, station_id if station is not None else None, corrections, frost_method,
                                        _read_card(cards / "gpm.json") if gpm is not None else None, n_filled, elev,
                                        break_info if (break_info or {}).get("applied") else None)
    df.to_parquet(out, index=False)
    card = g.make_card(
        dataset="weather", product="Twin input weather (derived from the sources below)", version="pipeline 2026-11-11",
        variable=list(df.columns), units_in="see source cards", units_out="unit in each column name",
        scale_factor=None, fill_values_removed="none here; see source cards", quality_flags_used="see source cards",
        records_dropped=0, date_range=[str(df["date"].min().date()), str(df["date"].max().date())],
        time_zone="POWER days: local solar time; IMERG days: UTC; station days: unknown (see VALIDATION.md)",
        pixel_count=1, source=source, resolution=resolution,
        raw_attrs="see source cards", range_warnings=warned, corrections=corrections, cross_source_flags=flags,
        location={"lat": field["lat"], "lon": field["lon"], "elevation_m": elev, "elevation_source": elev_src},
        notes=("source and resolution are given per column. Rain: GPM IMERG with POWER fill-in only (never 2001-2003); "
               + (f"{n_filled} day(s) filled from POWER." if gpm is not None else "GPM not fetched yet, so rain is missing.")
               + " ET0: FAO-56 Penman-Monteith (pipeline/twin/et0.py) from corrected temperatures, with the actual "
               "vapour pressure held from POWER and capped at e0(tmin_c) (corrections.ea_kpa)."))
    card_path = g.write_card(card, cards)
    for name, path in (("power", cards / "power.json"), ("station", cards / f"ghcn_{station_id}.json"),
                       ("gpm", cards / "gpm.json")):       # decision B: into EACH source's card (REVIEW_2 M9)
        if path.exists():
            g.annotate_card(path, "cross_source_flags", [f for f in flags if name in (f["high_source"], f["low_source"])])
    return {"table": out, "card": card_path, "card_data": card}


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--field", default="demo")
    out = build(load_field(ap.parse_args(argv).field))
    c = out["card_data"]
    for col in ("tmin_c", "tmax_c", "rh_pct"):
        info = c["corrections"].get(col, {})
        t = info.get("test")
        extra = f" held-out MAE {t['mae_before']:.2f} -> {t['mae_after']:.2f} C, bias {t['bias_before']:+.2f} -> {t['bias_after']:+.2f} C (n={t['n']})" if t else ""
        unc = info.get("months_uncorrected")
        print(f"{col}: {info.get('label', info.get('status'))}{extra}" + (f"; months uncorrected: {unc}" if unc else ""))
    e = c["corrections"]["ea_kpa"]
    print(f"ET0 mean annual: {e['et0_compare']['mean_annual_mm']['et0_mm']:.0f} mm (ea held from POWER, capped; used), "
          f"{e['et0_compare']['mean_annual_mm']['et0_rh_held_mm']:.0f} mm (RH held); cap binds on {e['cap_days']} day(s)")
    r = c["corrections"]["rain_mm"]
    b = c["corrections"]["rain_break"]
    if b.get("applied"):
        print(f"GPM break correction from {b['from']}: factors {b['factors_by_month']}; {b['days_scaled']} days scaled; "
              f"mean yearly rain from then {b['mean_yearly_mm_from_start']}; not scaled {b['days_not_scaled_after_start']}")
    print(f"rain: {r['status']}; POWER-filled days by year: "
          + str({y: v['filled'] for y, v in r['by_year'].items() if v['filled']}))
    print(f"Tmin above Tmax: {c['corrections']['tmin_not_above_tmax']['days']}")
    print(f"spike flags: {len(c['cross_source_flags'])}")
    for f in c["cross_source_flags"]:
        print(f"  {f}")
    print(f"-> {out['table']}\n-> {out['card']}")
    return 0


if __name__ == "__main__":
    sys.exit(main())

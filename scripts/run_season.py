"""Build step 4 test: one wheat-then-rice year for a field through the bucket, with a plot of root-zone
depletion (Dr).

    .venv/bin/python scripts/run_season.py --field demo --year 2016

TEMPORARY RAIN (owner, 2026-11-12): until GPM exists, rain is the field's validation station (GHCN-Daily)
for the test period; days the station lacks are filled from POWER and flagged. Step 5 switches to GPM.
ET0 comes from the twin's weather table (station-corrected temperatures). Writes:
  data/checks/<field>/season_<year>.json, data/clean/<field>/season_<year>_daily.parquet,
  data/plots/<field>/season_<year>_dr.png
"""
import argparse
import json
import sys
from pathlib import Path

import pandas as pd

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO))
from pipeline.fetch.cropslib import load_crops  # noqa: E402
from pipeline.fetch.fields import load_field  # noqa: E402
from pipeline.fetch.rules import load_rules  # noqa: E402
from pipeline.plans import simulate as sim  # noqa: E402
from pipeline.twin import season  # noqa: E402
from pipeline.twin.crops import sow_date  # noqa: E402
from pipeline.twin.evaporation import bare_soil_setting  # noqa: E402

INK, INK2, MUTED, GRID, SURFACE = "#0b0b0b", "#52514e", "#898781", "#e1e0d9", "#fcfcfb"
BLUE, ORANGE = "#2a78d6", "#eb6834"      # dataviz reference palette slots 1 and 2 (validated)


def build_inputs(field, year, data_dir):
    clean = data_dir / "clean" / field["id"]
    start, end = pd.Timestamp(f"{year - 1}-10-01"), pd.Timestamp(f"{year}-12-31")
    w = pd.read_parquet(clean / "weather.parquet")
    w = w[(w["date"] >= start) & (w["date"] <= end)][["date", "et0_mm"]].reset_index(drop=True)
    st = pd.read_parquet(clean / f"ghcn_{field['validation_station']}.parquet").set_index("date")["rain_mm"]
    pw = pd.read_parquet(clean / "power.parquet").set_index("date")["rain_mm"]
    w["rain_station_mm"] = w["date"].map(st)
    w["rain_filled"] = w["rain_station_mm"].isna()
    w["rain_mm"] = w["rain_station_mm"].fillna(w["date"].map(pw))
    return w


def plot(daily, summary, inputs, path, title):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    plt.rcParams.update({"font.size": 9, "axes.edgecolor": "#c3c2b7", "axes.labelcolor": INK2,
                         "xtick.color": MUTED, "ytick.color": MUTED, "axes.facecolor": SURFACE,
                         "figure.facecolor": SURFACE})
    fig, (a1, a2, a3) = plt.subplots(3, 1, figsize=(11, 7.2), sharex=True,
                                     gridspec_kw={"height_ratios": [1.1, 2.2, 1.0]})
    d = daily["date"]
    filled = inputs.set_index("date")["rain_filled"].reindex(d).to_numpy()
    a1.bar(d[~filled], daily["rain_mm"][~filled], width=1.0, color=BLUE, label="station rain (GHCN)")
    a1.bar(d[filled], daily["rain_mm"][filled], width=1.0, color=ORANGE, label="filled from POWER")
    a1.set_ylabel("rain\nmm/day")
    a1.legend(frameon=False, loc="upper left", labelcolor=INK2)
    a2.plot(d, daily["taw_mm"], color=MUTED, lw=1.2, ls="--")
    a2.plot(d, daily["raw_mm"], color=MUTED, lw=1.2, ls=":")
    a2.plot(d, daily["dr_mm"], color=BLUE, lw=1.6)
    a2.invert_yaxis()
    a2.set_ylabel("root-zone depletion Dr\nmm (down = drier)")
    last = daily.iloc[-1]
    for y, txt in ((last["taw_mm"], "TAW (wilting point)"), (last["raw_mm"], "RAW (stress starts)")):
        a2.annotate(txt, (d.iloc[-1], y), xytext=(4, 0), textcoords="offset points", color=INK2, va="center")
    a3.plot(d, daily["ks"], color=BLUE, lw=1.6)
    a3.set_ylim(-0.05, 1.08)
    a3.set_ylabel("stress Ks\n1 = none")
    for ax in (a1, a2, a3):
        ax.grid(axis="y", color=GRID, lw=0.6)
        ax.spines[["top", "right"]].set_visible(False)
        for crop in ("wheat", "rice"):
            s = summary[crop]
            ax.axvspan(pd.Timestamp(s["start"]), pd.Timestamp(s["end"]), color="#efeee9", zorder=0)
    for crop in ("wheat", "rice"):
        s = summary[crop]
        mid = pd.Timestamp(s["start"]) + (pd.Timestamp(s["end"]) - pd.Timestamp(s["start"])) / 2
        h = ("harvest n/a (" + s["harvest_note"] + ")" if s["harvest_pct"] is None else f"harvest {s['harvest_pct']:.0f}% of potential"
             + (" (Ky assumed)" if s.get("ky_assumed") else ""))
        a1.annotate(f"{crop}: {h}", (mid, 1.0), xycoords=("data", "axes fraction"), ha="center", va="bottom",
                    color=INK, fontsize=9)
    ponded = daily[daily["ponded"]]
    if len(ponded):
        a3.annotate("irrigated rice ponded (no stress)", (ponded["date"].iloc[len(ponded) // 2], 1.02), ha="center",
                    va="bottom", color=INK2, fontsize=8)
    fig.suptitle(title, x=0.01, ha="left", color=INK, fontsize=10.5)
    fig.tight_layout()
    path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(path, dpi=130)
    plt.close(fig)


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--field", default="demo")
    ap.add_argument("--year", type=int, default=2016)
    a = ap.parse_args(argv)
    field, rules, data_dir = load_field(a.field), load_rules(), REPO / "data"
    lib = load_crops(field=field)        # the field's country profile (config/countries/)
    inputs = build_inputs(field, a.year, data_dir)
    soil = pd.read_parquet(data_dir / "clean" / field["id"] / "soilgrids.parquet")
    plan = [("wheat", str(sow_date(lib["wheat"]["calendar"], a.year - 1).date())),
            ("rice", str(sow_date(lib["rice"]["calendar"], a.year).date()))]
    cover, by_cover = rules["curve_numbers"]["crop_cover"], rules["curve_numbers"]["by_cover"]
    cn = {"bare": by_cover["bare"], **{c: by_cover[cover[c]] for c, _ in plan}}
    irrigated = sim.export_case(field.get("water_source")) == "irrigated"   # unknown -> rain-fed (owner, 2026-11-12)
    daily, summary = season.simulate(inputs[["date", "et0_mm", "rain_mm"]], plan, lib, soil, cn,
                                     bare_soil_setting(rules["bare_soil"], soil), irrigated)
    n_filled = int(inputs["rain_filled"].sum())
    labels = {
        "rain": (f"TEMPORARY: station rain (GHCN-Daily {field['validation_station']}), {inputs['date'].min().date()} to "
                 f"{inputs['date'].max().date()}; {n_filled} missing day(s) filled from POWER and flagged. Step 5 uses GPM."),
        "et0": "FAO-56 Penman-Monteith from the twin's weather table (station-corrected temperatures)",
        "soil": "SoilGrids 2.0, the nearest cell with values to the field (distance in the data card)",
        "water_source": f"{field.get('water_source') or 'unknown'}; treated as {'irrigated' if irrigated else 'rain-only'}",
        "start": "Dr = 0 on the first day (end of the monsoon, FAO-56: after heavy rain the root zone is near field capacity)",
        "plan": plan, "curve_numbers": cn,
    }
    out = {"labels": labels, "summary": summary}
    (data_dir / "checks" / field["id"]).mkdir(parents=True, exist_ok=True)
    jpath = data_dir / "checks" / field["id"] / f"season_{a.year}.json"
    jpath.write_text(json.dumps(out, indent=1, default=str) + "\n")
    daily.to_parquet(data_dir / "clean" / field["id"] / f"season_{a.year}_daily.parquet", index=False)
    ppath = data_dir / "plots" / field["id"] / f"season_{a.year}_dr.png"
    plot(daily, summary, inputs, ppath, f"Demo field, wheat {plan[0][1]} then rice {plan[1][1]}: "
         f"soil water, model run with TEMPORARY station rain ({n_filled} days filled from POWER)")
    for crop in ("wheat", "rice"):
        s = summary[crop]
        print(f"{crop}: {s['start']} to {s['end']} ({s['days']} d) | ETc {s['sum_etc_mm']:.0f} mm, ETa {s['sum_eta_mm']:.0f} mm "
              f"(ratio {s['eta_over_etc']:.2f}) | dry days {s['dry_days']} | ponded days {s['ponded_days']} | rain {s['rain_mm']:.0f} mm "
              f"| irrigation {s['irrigation_mm']:.0f} mm (pond {s['pond_supply_mm']:.0f} mm) "
              f"| harvest {s['harvest_pct'] if s['harvest_pct'] is None else round(s['harvest_pct'], 1)} | TAW {s['taw_mm']} mm")
    print("balance residuals (mm):", {k: round(v["balance_residual_mm"], 6) for k, v in summary["segments"].items()})
    print(f"rain: {labels['rain']}")
    print(f"-> {jpath}\n-> {ppath}")
    return 0


if __name__ == "__main__":
    sys.exit(main())

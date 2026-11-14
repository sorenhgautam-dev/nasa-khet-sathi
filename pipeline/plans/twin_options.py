"""The twin's three switches, applied the same way by every runner that runs the twin for exported numbers
(scripts/run_replay.py, run_plans.py, run_memory.py, run_smap_check.py, run_twin_now.py, run_validation_checks.py and
pipeline/future/runs.py): rules.yaml bare_soil (2a: FAO-56's surface layer), season_dates (4a: the farmer's sowing from
the satellite's seasons) and paddy_rainfed (4c: rain-fed paddy waits for the land-preparation rain). Pure functions:
runners read the satellite's seasons (data/checks/<field>/diary_seasons.json) and attach them with attach().

Order (rules.yaml season_dates.with_paddy_rainfed): the farmer's plan takes the satellite's dates first; then, in the
rain-fed case only, each paddy season still on a calendar day waits for its land-preparation rain. A satellite-dated
paddy keeps its day: the observation already holds that year's delay. Suggested plans keep their calendar
(season_dates.suggested_plans). A runner may force a switch: rules[block]['force'] ('rules' follows apply)."""
from pipeline.plans import generate as ge
from pipeline.plans import simulate as sim
from pipeline.twin import evaporation as evap
from pipeline.twin import season


def bare_setting(rules, soil):
    """season.simulate's bare-soil argument: FAO-56's surface layer when bare_soil.apply is on, else the constant Kc."""
    return evap.bare_soil_setting(rules["bare_soil"], soil, rules["bare_soil"].get("force", "rules"))


def paddy_rule(rules):
    """The rain-fed paddy rule when its switch is on (or forced with 'proposal'), else None."""
    pr = rules.get("paddy_rainfed") or {}
    force = pr.get("force", "rules")
    if force == "off" or (force == "rules" and not pr.get("apply")):
        return None
    if "prep_mm" not in pr:
        raise ValueError("paddy_rainfed is on but rules.yaml has no paddy_rainfed values")
    return pr


def season_dates_on(rules):
    sd = rules.get("season_dates") or {}
    force = sd.get("force", "rules")
    return force == "hls" or (force == "rules" and bool(sd.get("apply")))


def hls_seasons(seasons_json):
    """The chosen season method's seasons with source 'hls' from a loaded diary_seasons.json."""
    return [x for rows in seasons_json["chosen"]["seasons_by_year"].values() for x in rows if x["source"] == "hls"]


def attach(rules, seasons, farmer_ids):
    """Runner setup: the satellite's seasons and the ids of the farmer's plans (the current plan and the current
    options), kept in rules['season_dates'] for evaluate() and plan_run()."""
    sd = rules.setdefault("season_dates", {})
    sd["_seasons"], sd["_farmer_ids"] = seasons, set(farmer_ids)
    return rules


def seasons_of(rules):
    return (rules.get("season_dates") or {}).get("_seasons")


def is_farmer(specs, rules):
    return ge.plan_id(specs) in ((rules.get("season_dates") or {}).get("_farmer_ids") or ())


def dated_plan(plan, lib, rules, w, irrigated, farmer=False, seasons=None, last_day=None):
    """(plan, 4a info, 4c info): the farmer's plan on the satellite's dates (season_dates), then, rain-fed only, every
    paddy still on a calendar day moved to its land-preparation rain (paddy_rainfed). last_day: the end of the run."""
    end = last_day or w["date"].max()
    info4a, seasons = [], seasons if seasons is not None else seasons_of(rules)
    if farmer and season_dates_on(rules) and seasons:
        plan, info4a = season.plan_from_seasons(plan, seasons, lib, end)
    rule = None if irrigated else paddy_rule(rules)
    info4c = []
    if rule is not None:
        keep = {(x["crop"], x["sow"]) for x in info4a if x["source"] == "hls" and not x["dropped"]}
        plan, info4c = season.paddy_transplant(plan, w["date"], w["rain_mm"], lib, rule, keep=keep, last_day=end)
    return plan, info4a, info4c


def replay(w, crops, lib, soil, cn, rules, irrigated, plan=None, farmer=False, seasons=None, last_day=None):
    """One replay with every switch. plan: [(crop, 'YYYY-MM-DD')] (None = the calendar rotation plan of `crops`);
    farmer: the plan is the farmer's (season dates apply); seasons: the satellite's (default: attached ones);
    last_day: the end of the run (default the weather's last day). The result is plans.simulate.replay's, plus 'plan'
    (the dates run), 'season_dates' (4a info) and 'paddy_info' (4c info, rain-fed only)."""
    w = w.reset_index(drop=True)
    if plan is None:
        plan = sim.rotation_plan(crops, lib, w["date"].min(), w["date"].max())
    plan, info4a, info4c = dated_plan(plan, lib, rules, w, irrigated, farmer, seasons, last_day)
    kw = dict(bare_kc=bare_setting(rules, soil), kc_climate=rules["kc_climate"]["apply"])
    res = sim.replay(w, crops, lib, soil, cn, irrigated=irrigated, plan=plan, **kw)
    if info4c:
        res["seasons"] = season.paddy_outcome(res["seasons"], info4c)
        res["years"] = sim.yearly(res["seasons"])
        res["partial_years"] = {str(y["year"]): y["crops"] for y in res["years"] if sorted(y["crops"]) != sorted(crops)}
    res["plan"], res["season_dates"], res["paddy_info"] = plan, info4a, info4c
    return res

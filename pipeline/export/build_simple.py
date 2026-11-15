"""The three farmer cards (owner, 2026-11-14 evening; rules.yaml simple_cards) -> site/data/simple/<field>.json.

Read from the field's own feature files only (the Replay and Field Pulse files); nothing new is simulated:
- replay_card: per answer to "What do you grow in winter?", the suggested crop's past winters against the farmer's own
  crop, each winter better, same or worse; faces per ten; a plain verdict. "Can you water?" yes compares every winter
  as the same (the twin meets every crop's water need when watered).
- trial_card: the crop to try in one corner (the replay card's suggestion).
- pulse_card: the satellite's typical growing periods (pulse typical), for the 12-month strip.

    .venv/bin/python -m pipeline.export.build_simple --field demo
"""
import argparse
import json
import math
import sys
from datetime import date, timedelta
from statistics import median
from pathlib import Path

from pipeline.export.build_replay import plans_of
from pipeline.fetch.rules import load_rules

REPO = Path(__file__).resolve().parents[2]
KINDS = ("better", "same", "worse")


def compare(cand, cur, better_by, worse_by):
    """Counts of past winters in which the suggested crop's score is at least better_by above the farmer's crop's
    (better), at least worse_by below (worse), or neither (same)."""
    out = dict.fromkeys(KINDS, 0)
    for c, f in zip(cand, cur):
        out["better" if c - f >= better_by else "worse" if f - c >= worse_by else "same"] += 1
    return out


def per_ten(counts, n):
    """Faces out of 10 by largest remainder; ties go to better, then same, then worse."""
    raw = {k: 10 * counts[k] / n for k in KINDS}
    out = {k: math.floor(raw[k]) for k in KINDS}
    for k in sorted(KINDS, key=lambda k: (-(raw[k] - out[k]), KINDS.index(k)))[:10 - sum(out.values())]:
        out[k] += 1
    return out


def verdict(counts, n):
    b, s, w = counts["better"], counts["same"], counts["worse"]
    if 2 * b >= n and b > w:
        return "better"
    if 2 * w >= n and w > b:
        return "worse"
    return "same" if 2 * s >= n else "mixed"


def _scores(replay, plan_id, window, start):
    p = next(p for p in replay["plans"] if p["id"] == plan_id)
    return {sq["year"]: sq["score"] for sq in p["results"][window][start]}, p["crops_in_window"][window][-1]["crop"]


def replay_cards(replay, answers, rules):
    """answers: {winter crop: the Replay plan that grows it}. For each answer, the best other crop among the suggested
    plans (cover_gap, safest) by better minus worse winters (ties: fewer worse, then the plans' order)."""
    window = rules["replay_window"]
    start = replay["start_default"] if rules["start"] == "start_default" else rules["start"]
    by, wb = rules["compare"]["better_by"], rules["compare"]["worse_by"]
    out = {}
    for crop, own_plan in answers.items():
        own, _ = _scores(replay, own_plan, window, start)
        best = None
        for i, pid in enumerate(("cover_gap", "safest")):
            if not any(p["id"] == pid for p in replay["plans"]):
                continue
            cand, cand_crop = _scores(replay, pid, window, start)
            if cand_crop == crop:
                continue
            years = sorted(set(own) & set(cand))
            c = compare([cand[y] for y in years], [own[y] for y in years], by, wb)
            key = (c["better"] - c["worse"], -c["worse"], -i)
            if best is None or key > best[0]:
                best = (key, pid, cand_crop, c, len(years))
        if best is None:
            continue
        _, pid, cand_crop, c, n = best
        same = {"better": 0, "same": n, "worse": 0}
        out[crop] = {w: {"plan": pid, "crop": cand_crop, "counts": cc, "per_ten": per_ten(cc, n), "verdict": verdict(cc, n)}
                     for w, cc in (("water_no", c), ("water_yes", same))}
    return out


def plan_lines(replay, answers, rules):
    """For the plans screen (owner, 2026-11-14 evening: each plan with one line from the Replay, 'did better than now in X
    of 10 winters'): per winter-crop answer, each suggested plan whose winter crop differs from the answer, compared with
    the farmer's own crop by the same rule as the Replay card (rain-fed)."""
    window = rules["replay_window"]
    start = replay["start_default"] if rules["start"] == "start_default" else rules["start"]
    by, wb = rules["compare"]["better_by"], rules["compare"]["worse_by"]
    out = {}
    for crop, own_plan in answers.items():
        own, _ = _scores(replay, own_plan, window, start)
        out[crop] = {}
        for pid in ("cover_gap", "safest"):
            if not any(p["id"] == pid for p in replay["plans"]):
                continue
            cand, cand_crop = _scores(replay, pid, window, start)
            if cand_crop == crop:
                continue
            years = sorted(set(own) & set(cand))
            c = compare([cand[y] for y in years], [own[y] for y in years], by, wb)
            out[crop][pid] = {"crop": cand_crop, "counts": c, "per_ten": per_ten(c, len(years))}
    return out


def winter_answers(field_doc, replay):
    """{winter crop: Replay plan}: the field's current options (their last crop), else its current plan."""
    ids = {p["id"] for p in replay["plans"]}
    opts = (field_doc.get("current_options") or {}).get("options") or []
    out = {o["crops"][-1]["crop"]: o["id"] for o in opts if o["id"] in ids}
    if not out:
        cur = next(p for p in field_doc["plans"] if p["id"] == "current")
        out = {cur["crops"][-1]["crop"]: "current"}
    return out


# ---------- farmer answers (rules.yaml farmer_answers, owner 2026-11-14 evening) ----------
KEYS = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]
MONSOON_BLOCKS = {"Jun", "Jul", "Aug", "Sep", "Oct"}       # rice is the farmer's crop in these blocks (weather_ahead.rank)


def bs_key(mmdd, start_day=15):
    """The approximate Bikram Sambat month of a day, by the Gregorian month key it starts in (weather_ahead.blocks)."""
    m, d = (int(x) for x in mmdd.split("-"))
    return KEYS[m - 1] if d >= start_day else KEYS[(m - 2) % 12]


def _verb(crop):
    return "plant" if crop == "rice" else "sow"


def _doy(mmdd):
    """Day of a non-leap year (2001) for 'MM-DD'."""
    return date(2001, *(int(x) for x in mmdd.split("-"))).timetuple().tm_yday


def calendar_end(crop, start, calendars):
    """The calendar's harvest day ('MM-DD') for a crop sown on `start`: the first calendar window of the crop whose sowing
    period holds the day, and the day holding the same place in its harvest period (farmer_answers.actions_calendar_months;
    days counted in a non-leap year, the place rounded down). None when no window holds the day. Pure."""
    s = _doy(start)
    for w in ((calendars or {}).get(crop) or {}).get("windows") or []:
        a, b = _doy(w["sow"]), _doy(w["sow_end"])
        span = (b - a) % 365
        k = (s - a) % 365
        if k <= span:
            h0, h1 = _doy(w["harvest"]), _doy(w["harvest_end"])
            day = (h0 - 1 + math.floor(k / span * ((h1 - h0) % 365)) if span else h0 - 1) % 365
            return (date(2001, 1, 1) + timedelta(days=day)).strftime("%m-%d")
    return None


def actions(rotation, in_window, calendars=None):
    """The plan's calendar for the crops touching the window: sow (rice: plant) and harvest each; the last harvest joined
    with the rotation's next crop (farmer_answers.actions). With the field's crop calendars ({crop: {windows}}), each
    harvest month is the calendar's (actions_calendar_months) and says where it came from ('month_from')."""
    def end(c):
        if calendars is None:
            return {"month": bs_key(c["end"])}
        day = calendar_end(c["crop"], c["start"], calendars)
        return {"month": bs_key(day or c["end"]), "month_from": "calendar" if day else "model"}
    out = []
    for i, c in enumerate(in_window):
        out.append({"do": _verb(c["crop"]), "crop": c["crop"], "month": bs_key(c["start"])})
        if i < len(in_window) - 1:
            out.append({"do": "harvest", "crop": c["crop"], **end(c)})
            continue
        k = next((j for j, r in enumerate(rotation) if (r["crop"], r["start"]) == (c["crop"], c["start"])), None)
        nxt = rotation[(k + 1) % len(rotation)] if k is not None and len(rotation) > 1 else None
        if nxt is None:
            out.append({"do": "harvest", "crop": c["crop"], **end(c)})
        else:
            out.append({"do": "harvest_then", "crop": c["crop"], **end(c), "new_do": _verb(nxt["crop"]),
                        "new_crop": nxt["crop"], "new_month": bs_key(nxt["start"])})
    return out


def _soft(label):
    return label != "VERIFIED"


def action_lines(acts, label):
    """Text keys and fills, plain only when the output (plan_months) is VERIFIED (farmer_answers.wording)."""
    tail = "_usual" if _soft(label) else ""
    out = []
    for a in acts:
        if a["do"] in ("sow", "plant"):
            out.append({"text": f"farm.act_{a['do']}{tail}", "fill": {"crop": a["crop"], "sow_month": a["month"]}})
        else:
            out.append({"text": f"farm.act_harvest{tail}", "fill": {"crop": a["crop"], "harvest_month": a["month"]}})
            if a["do"] == "harvest_then":
                out.append({"text": f"farm.act_then_{a['new_do']}{tail}", "fill": {"new_crop": a["new_crop"], "sow_month": a["new_month"]}})
    return out


def plan_word(counts, n, label):
    """simple_cards.verdict as the plan's word against the farmer's own plan (farmer_answers.plan_word)."""
    v = verdict(counts, n)
    soft = _soft(label)
    text = {"better": "farm.word_better" + ("_usual" if soft else ""), "worse": "farm.word_worse" + ("_usual" if soft else ""),
            "same": "farm.word_same", "mixed": "farm.word_mixed"}[v]
    return {"verdict": v, "text": text}


def animation(scores, order, failed_below):
    """Green = a season that did not fail; the winner has the most green seasons (ties: higher median, then order)."""
    plans = []
    for pid in order:
        sc = scores[pid]
        green = [None if x is None else x >= failed_below for x in sc]
        vals = sorted(x for x in sc if x is not None)
        plans.append({"id": pid, "green": green, "green_count": sum(1 for g in green if g),
                      "median": median(vals) if vals else None})
    best = max(range(len(plans)), key=lambda i: (plans[i]["green_count"], plans[i]["median"] or -1, -i))
    return {"plans": plans, "winner": plans[best]["id"]}


def weather_line(block, crops, can_water):
    """One Weather ahead block for one farmer: usual words, the first danger of the farmer's crops (none: 'Usually no big
    danger.', never another crop's; no dry spells when they can water), its tip. Always soft (farmer_answers.wording)."""
    usual = {"text": "farm.wx_usual", "fill": {"month": block["key"], "rain_word": block["usual"]["rain"],
                                               "temp_word": block["usual"]["temp"]}}
    ds = [d for d in block["dangers"] if not (can_water and d["kind"] == "dry_spell")]
    d = next((d for d in ds if d["crop"] in crops), None)
    if d is None:
        return {"usual": usual, "danger": {"text": "farm.wx_calm"}, "tip": None}
    return {"usual": usual, "danger": {"text": f"farm.wx_hurt_{d['check']}", "fill": {"crop": d["crop"]}},
            "tip": {"text": f"weather.tip_{d['tip']}"}}


def _status(labels, output):
    return ((labels.get("outputs") or {}).get(output) or {}).get("status", "NOT YET VERIFIABLE")


def _bench_passed(path):
    """The soil stick's cup test passed (farmer_answers.wording.today): a real bench file whose proofs all hold."""
    if not path.exists():
        return False
    b = json.loads(path.read_text())
    real = not b.get("made_up", True) and "REHEARSAL" not in str(b.get("label", "")).upper() \
        and "fake_probe" not in b.get("sources", [])
    return real and all((b.get("proofs") or {}).get(k) is True for k in ("steady", "order", "temperature"))


def farmer_answers(field_doc, replay, answers, rules, labels=None, bench_path=None, calendars=None):
    """The farmer screens' final answers (rules.yaml farmer_answers): text keys and fills only, worded by each output's
    label. answers: {winter crop: its Replay plan}. calendars: the field's crop calendars ({crop: {windows}}), for the
    harvest months (actions_calendar_months); without them, the model's last days."""
    failed_below = load_rules()["window_replay"]["classes"]["failed_below"]
    by, wb = rules["compare"]["better_by"], rules["compare"]["worse_by"]
    lp = REPO / "site" / "data" / "labels" / f"{replay['field']}.json"
    labels = labels if labels is not None else (json.loads(lp.read_text()) if lp.exists() else {})
    st = {o: _status(labels, o) for o in ("plan_months", "replay_window", "rotation_guess", "probe_water", "part_status")}
    rplans = {p["id"]: p for p in replay["plans"]}
    rotation = {pid: crops for pid, _, crops in plans_of(field_doc)}
    windows = [w["id"] for w in replay["windows"]]
    starts = [x["id"] for x in replay["starts"]]
    shown = [p["id"] for p in field_doc["plans"]]

    def crops_of(pid, w):
        return [c["crop"] for c in rplans[pid]["crops_in_window"][w]]

    words = {}
    for crop, own in answers.items():
        words[crop] = {}
        for w in windows:
            words[crop][w] = {}
            for s0 in starts:
                own_sc = {q["year"]: q["score"] for q in rplans[own]["results"][w][s0]}
                row = {}
                for pid in shown:
                    if crops_of(pid, w) == crops_of(own, w):
                        row[pid] = {"now": True}
                        continue
                    sc = {q["year"]: q["score"] for q in rplans[pid]["results"][w][s0]}
                    yrs = sorted(y for y in set(own_sc) & set(sc) if own_sc[y] is not None and sc[y] is not None)
                    if not yrs:
                        continue
                    c = compare([sc[y] for y in yrs], [own_sc[y] for y in yrs], by, wb)
                    row[pid] = {"counts": c, **plan_word(c, len(yrs), st["replay_window"])}
                words[crop][w][s0] = row
    raw = {pid: {w: actions(rotation[pid], rplans[pid]["crops_in_window"][w], calendars) for w in windows}
           for pid in rplans if pid in rotation}
    acts = {pid: {w: action_lines(a, st["plan_months"]) for w, a in ws.items()} for pid, ws in raw.items()}
    model_kept = sorted({f"{pid}: {a['crop']}" for pid, ws in raw.items() for al in ws.values() for a in al
                         if a.get("month_from") == "model"})
    s0 = replay["start_default"]
    anim = animation({pid: [q["score"] for q in rplans[pid]["results"]["m6"][s0]] for pid in shown}, shown, failed_below)
    anim.update({"window": "m6", "start": s0, "seasons": replay["seasons"], "failed_below": failed_below})
    wx = {}
    blocks = (field_doc.get("weather") or {}).get("blocks") or []
    for crop in answers:
        wx[crop] = {}
        for water in ("no", "yes"):
            wx[crop][water] = {b["key"]: weather_line(b, {crop} | ({"rice"} if b["key"] in MONSOON_BLOCKS else set()),
                                                      water == "yes") for b in blocks}
    bench = bench_path or REPO / "data" / "checks" / "probe" / "bench.json"
    return {
        "labels_used": st,
        "today": {"mode": "band" if _bench_passed(bench) else "compare"},
        "guess": {"text": "farm.guess", "fill": {"guess_list": (field_doc.get("diary") or {}).get("guess") or []}},
        "plan_words": words, "actions": acts, "animation": anim, "weather_lines": wx,
        "action_months": {"sow": "the plan's sowing day",
                          "harvest": "the crop calendar's (rules.yaml farmer_answers.actions_calendar_months)" if calendars is not None
                          else "the model's last day", "model_kept": model_kept},
    }


def build(field_id, rules=None):
    rules = rules or load_rules()["simple_cards"]
    site = REPO / "site" / "data"
    field_doc = json.loads((site / "fields" / f"{field_id}.json").read_text())
    replay = json.loads((site / "replay" / f"{field_id}.json").read_text())
    pulse_p = site / "pulse" / f"{field_id}.json"
    pulse = json.loads(pulse_p.read_text()) if pulse_p.exists() else {}
    answers = winter_answers(field_doc, replay)
    cards = replay_cards(replay, answers, rules)
    first = next(iter(answers))
    default = (field_doc.get("current_options") or {}).get("default")
    default_crop = next((c for c, pid in answers.items() if pid == default), first)
    n = cards[default_crop]["water_no"]["counts"] if default_crop in cards else None
    return {
        "field": field_id, "placeholder": bool(replay.get("placeholder")),
        "made_by": "pipeline/export/build_simple.py (rules.yaml simple_cards)",
        "window": rules["replay_window"], "start": replay["start_default"],
        "winters": sum(n.values()) if n else replay.get("year_count"),
        "answers": {"winter": list(answers), "default_winter": default_crop},
        "replay_card": cards,
        "trial_card": {crop: {"plan": c["water_no"]["plan"], "crop": c["water_no"]["crop"]} for crop, c in cards.items()},
        "plan_lines": plan_lines(replay, answers, rules),
        "pulse_card": {"growing": [{"crop": t["crop"], "from": t["planting"], "to": t["harvest"]}
                                   for t in pulse.get("typical") or []],
                       "source": "the satellite's typical crop months (site/data/pulse/<field>.json typical; HLS 30 m)"},
        "label": {"sure": "estimate", "scale": (replay.get("label") or {}).get("scale", "valley")},
        "sources": replay.get("sources", []),
        **farmer_answers(field_doc, replay, answers, rules, calendars=calendars_of(field_id)),
    }


def calendars_of(field_id):
    """The field's crop calendars, {crop: {windows: [...]}}, from its crop library (its country profile: Nepal's Hill zone
    in crops.json, or the field's FAO zone abroad)."""
    from pipeline.fetch.cropslib import load_crops
    from pipeline.fetch.fields import load_field
    return {k: v["calendar"] for k, v in load_crops(field=load_field(field_id)).items() if v.get("calendar")}


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--field", required=True)
    a = ap.parse_args(argv)
    doc = build(a.field)
    out = REPO / "site" / "data" / "simple" / f"{a.field}.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(doc, indent=1, ensure_ascii=False) + "\n")
    print(f"wrote {out}: " + "; ".join(f"{k}: {v['water_no']['crop']} {v['water_no']['verdict']} {v['water_no']['per_ten']}"
                                       for k, v in doc["replay_card"].items()))
    return 0


if __name__ == "__main__":
    sys.exit(main())

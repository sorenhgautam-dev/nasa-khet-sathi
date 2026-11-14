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
from pathlib import Path

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
    }


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

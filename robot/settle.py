"""Settle, then measure (owner's probe brief, 2026-11-14, fix 1). Pure: no I/O.

Per part (or per bench push-in) the probe's good lines arrive every 2 s. The first `settle_lines` (20, 40 s) are
discarded while the probe and its temperature sensor settle; the next `measure_lines` (10, 20 s) are measured:

- moisture: their median, spread (max - min) and n; steady when the spread is at most repeat_spread_max_pct (3 points).
  Not steady: state 'test_again' and no number. A median of 0 or 100 is 'off the scale' (the sketch limits moisture to
  0..100), never shown as a value.
- temperature: the median and spread of the lines that have one ('Check wiring' lines have none but keep their
  moisture); steady when the spread is at most temp_spread_max_c (0.5 C); otherwise temp is null.
States: settling -> measuring -> done | test_again. Rules: config/rules.yaml probe.settle_lines, measure_lines,
repeat_spread_max_pct, temp_spread_max_c, off_scale_pct.
"""
import numpy as np

SETTLING, MEASURING, DONE, TEST_AGAIN = "settling", "measuring", "done", "test_again"


def summarise(measured, spread_max, temp_spread_max, off_scale):
    """The measured lines ({moisture_pct, temp_c}) -> the part's numbers and state."""
    m = np.array([float(x["moisture_pct"]) for x in measured])
    med, spread = float(np.median(m)), float(m.max() - m.min())
    steady = bool(spread <= spread_max)
    off = bool(med in {float(v) for v in off_scale})
    temps = np.array([float(x["temp_c"]) for x in measured if x.get("temp_c") is not None])
    t_med = float(np.median(temps)) if len(temps) else None
    t_spread = float(temps.max() - temps.min()) if len(temps) else None
    t_steady = None if t_spread is None else bool(t_spread <= temp_spread_max + 1e-9)
    return {"state": DONE if steady else TEST_AGAIN, "n": int(len(m)), "median_pct": med,
            "probe_pct": med if (steady and not off) else None, "spread_pct": spread, "steady": steady, "off_scale": off,
            "temp_c": t_med if t_steady else None, "temp_median_c": t_med, "temp_spread_c": t_spread,
            "temp_steady": t_steady, "temp_n": int(len(temps)), "wiring_lost": int(len(m) - len(temps))}


class Part:
    """One part (or push-in): feed it good lines with add(); it says its state and, at the end, its result."""

    def __init__(self, settle_lines, measure_lines, spread_max, temp_spread_max, off_scale):
        self.settle_n, self.measure_n = int(settle_lines), int(measure_lines)
        self.spread_max, self.temp_spread_max, self.off_scale = spread_max, temp_spread_max, off_scale
        self.lines, self._result = [], None

    @classmethod
    def from_rules(cls, probe_rules):
        r = probe_rules
        return cls(r["settle_lines"], r["measure_lines"], r["repeat_spread_max_pct"], r["temp_spread_max_c"], r["off_scale_pct"])

    @property
    def state(self):
        if self._result is not None:
            return self._result["state"]
        return SETTLING if len(self.lines) < self.settle_n else MEASURING

    def add(self, parsed):
        """Add one good line (probe.parse_line's dict); returns the state after it."""
        if self._result is None:
            self.lines.append({"moisture_pct": parsed["moisture_pct"], "temp_c": parsed.get("temp_c")})
            if len(self.lines) == self.settle_n + self.measure_n:
                self._result = summarise(self.lines[self.settle_n:], self.spread_max, self.temp_spread_max, self.off_scale)
        return self.state

    def result(self):
        return self._result

    def values(self):
        """Every good line's moisture so far, settling included (for the bench's settling time)."""
        return [x["moisture_pct"] for x in self.lines]

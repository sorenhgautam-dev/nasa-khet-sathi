"""24 years of soil at a glance (owner, 2026-11-15 evening; rules.yaml soil_years): each replayed year's calendar months
as the mean root-zone share 1 - Dr/TAW, in four steps fixed before drawing."""
import pandas as pd

from pipeline.diary import months as mo


def test_monthly_share_is_the_mean_of_one_minus_dr_over_taw():
    dates = pd.date_range("2002-01-01", "2003-12-31", freq="D")
    taw = pd.Series(100.0, index=dates)
    dr = pd.Series(50.0, index=dates)
    dr["2002-03-01":"2002-03-31"] = [90.0] * 16 + [10.0] * 15      # March 2002: (16 x 0.1 + 15 x 0.9) / 31 = 0.4871
    taw["2003-07-01":"2003-07-31"] = 80.0                           # July 2003: 1 - 50/80 = 0.375
    g = mo.monthly_wetness(dates, dr, taw, [2002, 2003])
    assert list(g) == [2002, 2003] and all(len(v) == 12 for v in g.values())
    assert g[2002][2] == round((16 * 0.1 + 15 * 0.9) / 31, 3) == 0.487
    assert g[2003][6] == 0.375 and g[2002][0] == 0.5


def test_four_steps_by_the_fixed_edges():
    edges = [0.25, 0.5, 0.75]
    assert [mo.wetness_step(x, edges) for x in (0.0, 0.249, 0.25, 0.4999, 0.5, 0.75, 1.0)] == [0, 0, 1, 1, 2, 3, 3]

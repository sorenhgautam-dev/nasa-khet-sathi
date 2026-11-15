"""Flood years from the disaster databases (rules.yaml disaster_floods, owner 2026-11-15, committed before any score).
Worked examples by hand."""
import yaml

from pipeline.checks import disaster_floods as df

RULE = yaml.safe_load(open("config/rules.yaml"))["disaster_floods"]


def test_bipad_counts_only_bhaktapur_floods_with_a_loss():
    recs = {"29_11": [{"id": 1, "incidentOn": "2013-06-24T00:00", "loss": {"infrastructureDestroyedHouseCount": 1}},
                      {"id": 2, "incidentOn": "2013-06-22T00:00", "loss": {"peopleDeathCount": 0}}],     # money only: no
            "29_28": [{"id": 3, "incidentOn": "2016-07-26T00:00", "loss": {"familyAffectedCount": 2}}],
            "29_25": [{"id": 4, "incidentOn": "2015-05-01T00:00", "loss": {"peopleDeathCount": 9}}],     # drought: no
            "27_11": [{"id": 5, "incidentOn": "2018-08-01T00:00", "loss": {"peopleDeathCount": 1}}]}     # Kathmandu: no
    assert df.bipad_years(recs, RULE) == {2013: [1], 2016: [3]}


def test_desinventar_counts_floods_and_rain_floods_with_a_loss_in_bhaktapur():
    recs = [{"name1": "Bhaktapur", "evento": "FLOOD", "fechano": "2009", "serial": "a", "afectados": "263"},
            {"name1": "Bhaktapur", "evento": "RAINS", "fechano": "2011", "serial": "b", "afectados": "52",
             "otros": "Paddy field and vegetable field was inundated."},
            {"name1": "Bhaktapur", "evento": "RAINS", "fechano": "2009", "serial": "c", "vivdest": "2", "lugar": "Ward No. 1"},
            {"name1": "Bhaktapur", "evento": "FLOOD", "fechano": "2010", "serial": "d"},                  # no loss
            {"name1": "Lalitpur", "evento": "FLOOD", "fechano": "2002", "serial": "e", "muertos": "3"}]
    assert df.desinventar_years(recs, RULE) == {2009: ["a"], 2011: ["b"]}


def test_how_we_know_shows_the_two_counts_the_unscored_database_and_the_caveat():
    from pipeline.export import build_story as bs
    dis = {"databases": {
        "bipad": {"span": [2012, 2025], "scored": True, "db_flood_years": [2013, 2024], "flagged_years": [2024],
                  "db_also_flagged": [1, 9], "flagged_with_record": [1, 1]},
        "desinventar": {"span": [2002, 2013], "scored": False, "db_flood_years": [2009, 2011]}}}
    n = bs.disaster_note(dis)
    assert "(BIPAD, 2012-2025): 9 flood years." in n["en"] and "We flag 1 of those 9." in n["en"]
    assert "1 of our 1 flood years there have a record." in n["en"]
    assert "DesInventar (2002-2013): only 2 flood years, too few to score." in n["en"]
    assert "These databases record reported damage." in n["en"] and "rough cross-check at district level" in n["en"]
    assert n["ne"] and bs.disaster_note(None) is None


def test_two_counts_over_the_years_covered_and_too_few_years_is_not_scored():
    replay = list(range(2002, 2026))
    s = df.score({2011: [1], 2013: [1], 2016: [1], 2024: [1]}, [2002, 2004, 2024], replay, [2012, 2025], 3)
    assert s["scored"] and s["db_flood_years"] == [2013, 2016, 2024] and s["flagged_years"] == [2024]
    assert s["db_also_flagged"] == [1, 3] and s["flagged_with_record"] == [1, 1]
    n = df.score({2009: [1], 2011: [1]}, [2002, 2004], replay, [2002, 2013], 3)
    assert not n["scored"] and n["why"] == "only 2 flood years in 2002-2013; at least 3 are needed"

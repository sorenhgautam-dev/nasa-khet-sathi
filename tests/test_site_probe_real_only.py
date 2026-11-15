"""The soil test shows real probe readings of the field with their date and no "Tested: n / N" count. Owner, 2026-11-15:
practice and indoor-bowl readings never show as the field's parts; the soil screen stays at "Readings come after our team
tests it" until the real test is published, and a garden or indoor test shows only on How we know, as bowls (rules.yaml
probe.live.practice_on_phone and garden_test). The site's rule for "real" is the bridge's: read from a serial port
(robot/bridge.py)."""
import re
from pathlib import Path

from robot import bridge

REPO = Path(__file__).resolve().parents[1]
APP = (REPO / "site" / "js" / "app.js").read_text()
FEATURES = (REPO / "site" / "js" / "features.js").read_text()


def _regex(name):
    return re.search(rf"function {name}\(.*?\) {{ return /(.+?)/\.test", APP).group(1)


def test_the_site_and_the_bridge_agree_on_what_a_real_reading_is():
    rule = _regex("isReal")
    for source in ("serial:/dev/cu.usbserial-0001", "serial:COM3", "fake_probe", "stdin", "pty:/dev/ttys004", "", "serial:"):
        assert bool(re.search(rule, source)) == (bridge.is_real(source) and len(source) > len("serial:")), source


def test_practice_readings_are_never_read():
    assert "isPractice" not in APP and "fake_probe" not in APP and "practice-banner" not in APP


def test_practice_and_garden_readings_never_stand_for_the_field():
    assert "function forField(pd) { return !!pd && !pd.test; }" in APP
    assert "} else if (d.kind === 'log' && forField(d)) {" in APP                 # the soil screen's walk
    assert "if (!forField(pd)) pd = { kind: 'none', parts: {} };" in APP        # Today's parts
    assert "sd.today.mode === 'band' && forField(pd)" in APP                  # the soil at the start
    assert "if (!forField(pd)) return;" in APP                                   # the Choose screen's dots
    assert "if (!K.forField(pd)) return null;" in FEATURES                       # the Replay's start band
    assert "TEST_LABEL = { garden_test: ['garden_on'], indoor_test: ['indoor_title', 'indoor_on'] }" in APP
    assert "test: TEST_LABEL[log.kind] ? log.kind : null" in APP


def test_a_stick_test_shows_on_how_we_know_as_bowls_and_field_readings_stay_not_ready():
    how = (REPO / "site" / "js" / "how.js").read_text()
    assert "return pd && pd.test ? section('stick', T('check_soil.prototype'), [K.recordedLine(pd), K.bowlLines(pd)]) : null;" in how
    assert "if (!pd || pd.kind === 'none' || !K.forField(pd)) items.push(T('your_plan.nr_readings'));" in how


def test_real_readings_carry_a_date_and_there_is_no_tested_count():
    reader = APP[APP.index("function probeData()"):APP.index("function anyTested(")]
    # in demo mode (phone as drone, hotspot only) live.json holds the pots and is not read as the field at all
    assert re.search(r"if \(lv && (?:!demo && )?isReal\(lv\.source\) &&", reader) and "isReal(x.source)" in reader
    assert "pd.live.time" in APP and "(pd.test ? TEST_LABEL[pd.test] : ['recorded_on'])" in APP
    assert not re.search(r"T\('check_soil\.tested'\) \+ ': '", APP)


def test_a_live_reading_can_never_be_pushed():
    assert "/site/data/live.json" in (REPO / ".gitignore").read_text().splitlines()

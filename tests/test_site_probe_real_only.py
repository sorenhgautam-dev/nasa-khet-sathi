"""The soil test shows only real probe readings, each with its date, and no "Tested: n / N" count (owner, 2026-11-14
night: remove the count that came from rehearsal or sample data; show only real recorded readings, labelled with their
date). The site's rule is the bridge's: a reading is real only when it was read from a serial port (robot/bridge.py)."""
import re
from pathlib import Path

from robot import bridge

APP = (Path(__file__).resolve().parents[1] / "site" / "js" / "app.js").read_text()


def test_the_site_and_the_bridge_agree_on_what_a_real_reading_is():
    rule = re.search(r"function isReal\(src\) \{ return /(.+?)/\.test", APP).group(1)
    for source in ("serial:/dev/cu.usbserial-0001", "serial:COM3", "fake_probe", "stdin", "pty:/dev/ttys004", "", "serial:"):
        assert bool(re.search(rule, source)) == (bridge.is_real(source) and len(source) > len("serial:")), source


def test_live_and_recorded_readings_pass_the_rule_and_carry_a_date():
    reader = APP[APP.index("function probeData()"):APP.index("function anyTested(")]
    assert "isReal(lv.source)" in reader and "isReal(x.source)" in reader
    assert "pd.live.time" in APP and "T('check_soil.recorded_on')" in APP


def test_no_tested_count_and_no_practice_chip():
    assert not re.search(r"T\('check_soil\.tested'\) \+ ': '", APP)
    assert "fake_probe" not in APP and "check_soil.practice" not in APP

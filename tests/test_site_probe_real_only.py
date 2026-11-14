"""The soil test shows real probe readings with their date and no "Tested: n / N" count; practice readings from the fake
probe only on the laptop's hotspot, under a big banner; a garden test labelled as one; neither practice nor garden ever
stands for the field (owner, 2026-11-14 night; rules.yaml probe.live.practice_on_phone and garden_test). The site's rule
for "real" is the bridge's: read from a serial port (robot/bridge.py)."""
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


def test_practice_readings_show_only_on_the_laptop_or_its_hotspot():
    rule = _regex("onHotspot")
    for host in ("localhost", "127.0.0.1", "192.168.1.5", "172.20.10.2", "10.0.0.4", "khet-laptop.local"):
        assert re.search(rule, host), host
    for host in ("khet-sathi.vercel.app", "example.com", "172.32.0.1", "8.8.8.8", "localhost.example.com", "10.vercel.app",
                 "192.168.1.5.example.com", "evil.local.example.com"):
        assert not re.search(rule, host), host
    assert "function isPractice(lv) { return !!lv && lv.source === 'fake_probe' && onHotspot(); }" in APP
    assert "class: 'practice-banner'" in APP and "T('check_soil.practice')" in APP


def test_practice_and_garden_readings_never_stand_for_the_field():
    assert "function forField(pd) { return !!pd && !pd.practice && !pd.garden; }" in APP
    assert "sd.today.mode === 'band' && forField(pd)" in APP                  # the soil at the start
    assert "if (!forField(pd)) return;" in APP                                   # the Choose screen's dots
    assert "if (!K.forField(pd)) return null;" in FEATURES                       # the Replay's start band
    assert "garden: log.kind === 'garden_test'" in APP and "'check_soil.garden_on'" in APP


def test_real_readings_carry_a_date_and_there_is_no_tested_count():
    reader = APP[APP.index("function probeData()"):APP.index("function anyTested(")]
    assert "isReal(lv.source) || isPractice(lv)" in reader and "isReal(x.source)" in reader
    assert "pd.live.time" in APP and "T(pd.garden ? 'check_soil.garden_on' : 'check_soil.recorded_on')" in APP
    assert not re.search(r"T\('check_soil\.tested'\) \+ ': '", APP)


def test_a_live_reading_can_never_be_pushed():
    assert "/site/data/live.json" in (REPO / ".gitignore").read_text().splitlines()

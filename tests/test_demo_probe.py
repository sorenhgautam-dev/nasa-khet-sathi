"""scripts/demo_probe.py: the live probe demo as one command (owner's launch brief, 2026-11-14). The local server is
started on a free port in a temporary folder; the bridge runs only with the fake probe, writing outside site/data."""
import json
import sys
import threading
import urllib.request
from pathlib import Path

import pytest

from scripts import demo_probe as dp

REPO = Path(__file__).resolve().parents[1]


def test_the_phone_gets_a_private_lan_address_not_the_loopback():
    assert dp.pick_addresses(["127.0.0.1", "172.20.10.3", "8.8.8.8", "192.168.1.20", "172.20.10.3", "169.254.3.3"]) == \
        ["172.20.10.3", "192.168.1.20"]
    assert dp.pick_addresses([]) == []
    assert all(isinstance(a, str) for a in dp.lan_addresses())


def test_the_real_probe_writes_the_live_file_in_site_data(tmp_path):
    cmd = dp.bridge_command(port="/dev/cu.usbserial-0001", fake=None, field="demo", sections="s1,s2,s3,s4",
                            live=REPO / "site" / "data" / "live.json", log_dir=None)
    assert cmd[1:3] == ["-m", "robot.bridge"] and "--port" in cmd and "/dev/cu.usbserial-0001" in cmd
    assert cmd[cmd.index("--out") + 1] == str(REPO / "site" / "data" / "live.json") and "--fake" not in cmd
    assert cmd[cmd.index("--sections") + 1] == "s1,s2,s3,s4" and "--log-dir" not in cmd


def test_the_fake_probe_never_writes_into_site_data_or_the_real_logs(tmp_path):
    cmd = dp.bridge_command(port=None, fake="settling", field="demo", sections=None, live=tmp_path / "live.json",
                            log_dir=tmp_path / "logs", fake_interval=0.5)
    assert cmd[cmd.index("--fake") + 1] == "settling" and cmd[cmd.index("--fake-interval") + 1] == "0.5"
    assert cmd[cmd.index("--out") + 1] == str(tmp_path / "live.json") and cmd[cmd.index("--log-dir") + 1] == str(tmp_path / "logs")
    with pytest.raises(ValueError, match="site/data"):
        dp.bridge_command(port=None, fake="settling", field="demo", sections=None,
                          live=REPO / "site" / "data" / "live.json", log_dir=tmp_path)


@pytest.fixture
def server(tmp_path):
    site = tmp_path / "site"
    (site / "data").mkdir(parents=True)
    (site / "index.html").write_text("<!doctype html><title>t</title>")
    (site / "data" / "index.json").write_text('{"fields": []}')
    (site / "data" / "live.json").write_text('{"from": "site"}')
    live = tmp_path / "rehearsal" / "live.json"
    srv = dp.make_server(site, live, host="127.0.0.1", port=0)
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    yield f"http://127.0.0.1:{srv.server_address[1]}", live
    srv.shutdown()


def _get(url):
    try:
        with urllib.request.urlopen(url, timeout=5) as r:
            return r.status, r.read(), r.headers
    except urllib.error.HTTPError as e:
        return e.code, b"", e.headers


def test_the_server_serves_the_site_and_never_lets_the_phone_cache(server):
    base, live = server
    status, body, headers = _get(base + "/data/index.json")
    assert status == 200 and body == b'{"fields": []}' and headers["Cache-Control"] == "no-store"
    assert _get(base + "/")[0] == 200


def test_data_live_json_comes_from_the_bridges_file(server):
    base, live = server
    assert _get(base + "/data/live.json")[0] == 404            # the bridge has not written yet: the site waits
    live.parent.mkdir(parents=True)
    live.write_text('{"section": "s1", "state": "settling"}')
    status, body, headers = _get(base + "/data/live.json?t=1")
    assert status == 200 and json.loads(body)["state"] == "settling" and headers["Content-Type"].startswith("application/json")


def test_the_server_does_not_serve_outside_the_site(server):
    base, _ = server
    assert _get(base + "/../../etc/passwd")[0] in (400, 404)


def test_the_whole_demo_runs_with_the_fake_probe(tmp_path, capsys):
    """Server and bridge together: the fake walk ends by itself (--no-wait), the server stops, nothing in site/data."""
    before = (REPO / "site" / "data" / "live.json").exists()
    code = dp.main(["--fake", "settling", "--sections", "s1", "--no-wait", "--fake-interval", "0", "--http-port", "0",
                    "--bind", "127.0.0.1", "--rehearsal-dir", str(tmp_path)])
    out = capsys.readouterr().out
    assert code == 0 and "http://" in out and "#/soil" in out and "FAKE" in out
    doc = json.loads((tmp_path / "live.json").read_text())
    assert doc["source"] == "fake_probe" and doc["section"] == "s1"
    assert (REPO / "site" / "data" / "live.json").exists() == before

"""The welcome on the loading curtain (owner, 2026-11-15): "Welcome" in the site's 7 languages, Nepali first, one after
another while the app loads; at most about 2 s slower than before; a tap skips it; once per visit; reduced motion shows
"स्वागत छ · Welcome" still; text only (no new image or font file); any failure opens the app as before. And the browser's
translate bar is told not to offer to translate an app that has its own languages."""
import json
import re
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
HTML = (REPO / "site" / "index.html").read_text()
APP = (REPO / "site" / "js" / "app.js").read_text()
CSS = (REPO / "site" / "css" / "app.css").read_text()
ORDER = ["ne", "en", "hi", "bn", "es", "fr", "sw"]


def _curtain_words():
    box = re.search(r'<p class="hello" aria-hidden="true" hidden>(.*?)</p>', HTML).group(1)
    return re.findall(r'<span lang="([a-z]+)">([^<]+)</span>', box)


def test_the_curtain_holds_the_owners_seven_words_nepali_first():
    assert _curtain_words() == [("ne", "स्वागत छ"), ("en", "Welcome"), ("hi", "स्वागत है"), ("bn", "স্বাগতম"),
                                ("es", "Bienvenidos"), ("fr", "Bienvenue"), ("sw", "Karibu")]


def test_the_words_are_the_reviewed_words_lists_and_the_nepali_is_marked_for_review():
    words = json.loads((REPO / "site" / "data" / "words.json").read_text())
    node = words["shared"]["welcome"]
    assert node["ne_review"] == "needs native-speaker review"
    assert _curtain_words() == [(lang, node[lang]) for lang in ORDER]
    assert [x["code"] for x in words["languages"]] == ORDER                  # the site's own language order


def test_it_never_slows_the_app_by_more_than_about_two_seconds_and_a_tap_skips_it():
    step, hold, still = (int(re.search(rf"{k} = (\d+)", APP).group(1)) for k in ("HELLO_STEP_MS", "HELLO_HOLD_MS", "HELLO_STILL_MS"))
    assert step * 7 + hold - 900 <= 2000 and still - 0 <= 2000             # against the old curtain: 900 ms (0 ms reduced)
    assert "setTimeout(lift, Math.max(0, Math.max(RM ? 0 : 900, wantMs) - (Date.now() - t0)));" in APP   # data first
    assert "cur.addEventListener('click', skip)" in APP and "D.addEventListener('keydown', skip, { once: true })" in APP


def test_once_per_visit_reduced_motion_still_and_any_failure_opens_the_app():
    body = APP[APP.index("function hello(cur) {"):APP.index("function init() {")]
    assert "ss.getItem('ks.hello')" in body and "ss.setItem('ks.hello', '1')" in body
    assert "if (RM) {" in body and "words[0].textContent + ' · ' + words[1].textContent" in body
    assert "} catch (e) { return 0; }" in body                               # 0: the curtain as before


def test_text_only_and_no_translate_bar():
    assert "<html lang=\"ne\" translate=\"no\">" in HTML and '<meta name="google" content="notranslate">' in HTML
    hello_css = "\n".join(line for line in CSS.splitlines() if ".hello" in line)
    assert "url(" not in hello_css and "@font-face" not in hello_css

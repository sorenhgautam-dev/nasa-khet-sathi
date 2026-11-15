"""Write pipeline/words/PREVIEW.md: every text as English | Nepali tables, for reviewers.

Grouped by screen (the five tabs and the tips sit under screen 8), then the words shared by many
screens, then the glossary, then the crop explainers. Run: .venv/bin/python -m pipeline.words.preview
tests/test_words.py fails if PREVIEW.md is out of date. The top of the page gives each word file's
review status (the "ne_review" marks); each table repeats it for its own lines.
"""
from collections import Counter
from pathlib import Path

from pipeline.words.texts import WORD_FILES, iter_text_nodes, load

OUT = Path(__file__).resolve().parent / "PREVIEW.md"
TAB_ORDER = ["why", "evidence", "benefits", "unknown", "check"]
FILE_LABELS = {"screens": "Screens, and the words shared by many screens",
               "tabs": "The five tabs and the tips (screen 8), and the method page's notes",
               "glossary": "Glossary", "crop_explainers": "Crop explainers"}


def cell(text):
    return text.replace("|", "\\|").replace("\n", " ")


def review_status(nodes):
    """The nodes' ne_review mark; if they differ, each mark with its count, most common first."""
    counts = Counter(n["ne_review"] for n in nodes)
    if len(counts) == 1:
        return next(iter(counts))
    return "; ".join(f"{c} {mark}" for mark, c in sorted(counts.items(), key=lambda kv: (-kv[1], kv[0])))


def status_line(nodes):
    return f"*Nepali: {review_status(nodes)}.*"


def _when(node, conditions):
    whens = [w for w in node.get("when", []) if w != "always"]
    parts = ["if nothing else applies" if w == "fallback" else conditions[w]["plain"] for w in whens]
    if node.get("repeat"):
        parts.append("one line for each source")
    return f" *({'; '.join(parts)})*" if parts else ""


def _row(node, conditions, bold=False):
    en, ne = cell(node["en"]), cell(node["ne"])
    if bold:
        en, ne = f"**{en}**", f"**{ne}**"
    return f"| {en}{_when(node, conditions)} | {ne} |"


def _table(rows, nodes):
    return [status_line(nodes), "", "| English | नेपाली |", "| --- | --- |", *rows, ""]


def _labels(labels, conditions):
    rows, nodes = [], []
    for group in labels.values():
        rows.append(f"| *{cell(group['about'])}* | |")
        rows += [_row(n, conditions) for n in group["items"].values()]
        nodes += list(group["items"].values())
    return rows, nodes


def render():
    screens, tabs, glossary, explainers = (load(n) for n in ("screens", "tabs", "glossary", "crop_explainers"))
    conditions = load("fill_registry")["conditions"]
    crop_names = screens["shared"]["crop_names"]
    tab_names = next(s for s in screens["screens"] if s["id"] == "what_to_grow")["labels"]["tab"]["items"]

    out = [
        "# Khet Sathi: every word on the site",
        "",
        "All Nepali text was drafted by SI (Claude) on 2026-11-12. Review status of the Nepali:",
        "",
        *[f"- {FILE_LABELS[name]} ({name}.json, {len(nodes)} texts): {review_status(nodes)}."
          for name, nodes in ((n, [node for _, node in iter_text_nodes(load(n))]) for n in WORD_FILES)],
        "",
        "Each table below starts with the review status of its own lines.",
        "Words in {curly brackets} are filled in later with numbers or names for each field.",
        "A line marked *(if ...)* is shown only in that case.",
        "This page is made from the word files in this folder; change those, not this page.",
        "",
        "## Screens",
        "",
    ]
    for s in screens["screens"]:
        out += [f"### {s['n']}. {cell(s['title']['en'])} / {cell(s['title']['ne'])}", ""]
        label_rows, label_nodes = _labels(s.get("labels", {}), conditions)
        nodes = [s["title"], *s["texts"], *label_nodes]
        rows = [_row(s["title"], conditions, bold=True)]
        rows += [_row(t, conditions) for t in s["texts"]]
        rows += label_rows
        out += _table(rows, nodes)
        if s["id"] == "what_to_grow":
            for tab in TAB_ORDER:
                name = tab_names[tab]
                out += [f"#### Tab: {cell(name['en'])} / {cell(name['ne'])}", ""]
                out += _table([_row(line, conditions) for line in tabs["tabs"][tab]], tabs["tabs"][tab])
            out += ["#### Tips / सुझाव", ""]
            out += _table([_row(line, conditions) for line in tabs["tips"]], tabs["tips"])
    out += ["## Method page", ""]
    for note, lines in tabs.get("method_page", {}).items():
        out += [f"### {note.replace('_', ' ').capitalize()}", ""]
        out += _table([_row(line, conditions) for line in lines], lines)

    shared = screens["shared"]
    out += ["### Words used on many screens", ""]
    groups = [("Buttons", shared["buttons"]), ("Crop names", list(crop_names.values())),
              ("Months", list(shared["months"].values())),
              ("Where a number comes from", list(shared["source_kinds"].values())),
              ("Joining words", list(shared["join"].values()))]
    groups += [(about, list(shared[k].values())) for k, about in (("weather", "Weather ahead"), ("twin", "How we test each plan"), ("farm", "Farmer answers"), ("fog", "The fog that clears where the soil stick tests"), ("bs_months", "Bikram Sambat months (English and Nepali)"))
               if k in shared]
    if "welcome" in shared:   # the loading curtain's welcome (owner, 2026-11-15)
        groups.append(("The welcome while the app loads", [shared["welcome"]]))
    rows, nodes = [], []
    for about, group in groups:
        rows += [f"| *{about}* | |", *[_row(n, conditions) for n in group]]
        nodes += group
    out += _table(rows, nodes)

    out += ["## Glossary", "", "Science words appear only here, never on the screens.", ""]
    rows = [f"| **{cell(t['term']['en'])}**: {cell(t['say']['en'])} | **{cell(t['term']['ne'])}**: {cell(t['say']['ne'])} |"
            for t in glossary["terms"]]
    out += _table(rows, [node for t in glossary["terms"] for node in (t["term"], t["say"])])

    out += ["## Crop explainers", ""]
    terms = {t["id"]: t for t in glossary["terms"]}
    for e in explainers["explainers"].values():
        term = terms[e["glossary_term"]]["term"]
        examples = ", ".join(f"{crop_names[c]['en']} / {crop_names[c]['ne']}" for c in e["examples"])
        out += [f"### {cell(e['title']['en'])} / {cell(e['title']['ne'])}", "",
                f"Glossary word: {cell(term['en'])} / {cell(term['ne'])}. Our examples: {examples}.", ""]
        out += _table([_row(e["title"], conditions, bold=True)] + [_row(c, conditions) for c in e["claims"]],
                      [e["title"], *e["claims"]])
        out += ["Sources:", ""]
        for i, c in enumerate(e["claims"], 1):
            src = c["source"]
            line = (f"{i}. {src['publisher']} ({src['year']}), {cell(src['title'])}, {cell(src['where'])}. "
                    f"Quote: \u201c{cell(src['quote'])}\u201d <{src['url']}>")
            if src.get("note"):
                line += f" Note: {cell(src['note'])}"
            out.append(line)
        out.append("")
    return "\n".join(out).rstrip("\n") + "\n"


def main():
    OUT.write_text(render(), encoding="utf-8")
    print(f"wrote {OUT}")


if __name__ == "__main__":
    main()

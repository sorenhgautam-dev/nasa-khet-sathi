"""The Nepali review spreadsheet (owner, 2026-11-14): pipeline/words/nepali_review.xlsx, one row per text, for a native
speaker: farmer-facing screens first, then the plans' tabs and tips, then the glossary and crop explainers, then the
texts the pipeline writes into site/data (How we know, monsoon words). Plain zip and XML, no spreadsheet library.

Write:  .venv/bin/python -m pipeline.words.review_sheet
Apply:  .venv/bin/python -m pipeline.words.review_sheet --apply <filled.xlsx> --name "<reviewer>" --date YYYY-MM-DD
then rebuild words.json, PREVIEW.md and the exports. A correction must keep every {placeholder}; texts made in code
(ids starting "site/") are listed for the integrator to change by hand."""
import argparse
import json
import re
import zipfile
import xml.etree.ElementTree as ET
from pathlib import Path
from xml.sax.saxutils import escape

from pipeline.export.build_words import iter_texts
from pipeline.words.texts import PLACEHOLDER

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[1]
OUT = HERE / "nepali_review.xlsx"
FILES = ("screens", "tabs", "glossary", "crop_explainers")
HEADER = ["id", "where it appears in the app", "English", "Nepali", "Correct? (yes/no)", "Corrected Nepali", "Comment"]
KEYS = ["id", "where", "en", "ne", "ok", "fix", "note"]
WIDTHS = [30, 30, 50, 50, 12, 50, 34]
NS = "{http://schemas.openxmlformats.org/spreadsheetml/2006/main}"
README = [
    ["How to review / कसरी जाँच्ने"],
    ["Read each Nepali text. Is it correct, natural Nepali that a farmer understands?"],
    ["हरेक नेपाली वाक्य पढ्नुहोस्। के यो किसानले बुझ्ने सही र सरल नेपाली हो?"],
    ["If yes: write yes in column E. If not: write no, and the better Nepali in column F."],
    ["ठिक छ भने E मा yes लेख्नुहोस्। छैन भने no लेखेर F मा राम्रो नेपाली लेख्नुहोस्।"],
    ["Words in {braces} are filled in by the app (a number, a crop, a month): keep them exactly as they are."],
    ["{कोष्ठक} भित्रका शब्द एपले भर्छ: तिनलाई जस्ताको तस्तै राख्नुहोस्।"],
    ["Screens should use short sentences (eight words or fewer). Column G is for any comment."],
]


def _load(d, f):
    return json.loads((Path(d) / f"{f}.json").read_text(encoding="utf-8"))


def _word_nodes(words):
    """(id, where, live node) for every text in the four word files, in the review order."""
    sc = words["screens"]
    for i, s in enumerate(sc["screens"], 1):
        title = s["title"]["en"] if isinstance(s.get("title"), dict) else s["id"]
        for k, n in iter_texts(s, f"screens.{s['id']}"):
            yield k, f"1. Screen {i}: {title}", n
    for k, n in iter_texts(sc["shared"], "shared"):
        yield k, "1. Many screens (buttons, months, crop names)", n
    for k, n in iter_texts(words["tabs"], "tabs"):
        yield k, "2. Plans: the five tabs and the tips", n
    for k, n in iter_texts(words["glossary"]["terms"], "glossary"):
        yield k, "3. Glossary", n
    for k, n in iter_texts(words["crop_explainers"]["explainers"], "crop_explainers"):
        yield k, "3. Crop explainers", n


def _site_pairs(obj, path):
    """(path, en, ne) for every {en, ne} pair (strings, or lists of equal length) in an exported file."""
    if isinstance(obj, dict):
        en, ne = obj.get("en"), obj.get("ne")
        if isinstance(en, str) and isinstance(ne, str):
            yield path, en, ne
        elif isinstance(en, list) and isinstance(ne, list) and len(en) == len(ne):
            yield from ((f"{path}.{i}", a, b) for i, (a, b) in enumerate(zip(en, ne)) if isinstance(a, str))
        for k, v in obj.items():
            if k not in ("en", "ne"):
                yield from _site_pairs(v, f"{path}.{k}")
    elif isinstance(obj, list):
        for i, v in enumerate(obj):
            yield from _site_pairs(v, f"{path}.{i}")


def rows(words_dir=HERE, site=REPO / "site" / "data"):
    words = {f: _load(words_dir, f) for f in FILES}
    out = [{"id": k, "where": w, "en": n["en"], "ne": n.get("ne", ""), "ok": "", "fix": "", "note": ""}
           for k, w, n in _word_nodes(words) if n["en"].strip()]
    seen = {(r["en"], r["ne"]) for r in out}
    for rel, where in (("fields/demo.json", "1. Screens: words made from the field's data"),
                       ("story.json", "4. How we know page")):
        p = Path(site) / rel
        for path, en, ne in (_site_pairs(json.loads(p.read_text()), f"site/{rel}:") if p.exists() else []):
            if en.strip() and ne.strip() and (en, ne) not in seen:
                seen.add((en, ne))
                out.append({"id": path, "where": where, "en": en, "ne": ne, "ok": "", "fix": "", "note": ""})
    return sorted(out, key=lambda r: r["where"][0])          # stable: keeps the app's order inside a section


def _col(i):
    s, i = "", i + 1
    while i:
        i, r = divmod(i - 1, 26)
        s = chr(65 + r) + s
    return s


def _sheet(table, widths, header_style, fill_cols=(), validate_col=None):
    def c(r, j, v):
        style = 1 if r == 1 and header_style else (3 if j in fill_cols else 2)
        if v == "":
            return f'<c r="{_col(j)}{r}" s="{style}"/>'
        return f'<c r="{_col(j)}{r}" t="inlineStr" s="{style}"><is><t xml:space="preserve">{escape(str(v))}</t></is></c>'
    body = "".join(f'<row r="{r}">' + "".join(c(r, j, v) for j, v in enumerate(row)) + "</row>"
                   for r, row in enumerate(table, 1))
    cols = "".join(f'<col min="{j}" max="{j}" width="{w}" customWidth="1"/>' for j, w in enumerate(widths, 1))
    dv = (f'<dataValidations count="1"><dataValidation type="list" allowBlank="1" sqref="{validate_col}2:{validate_col}'
          f'{len(table)}"><formula1>"yes,no"</formula1></dataValidation></dataValidations>' if validate_col else "")
    pane = ('<sheetViews><sheetView workbookViewId="0"><pane ySplit="1" topLeftCell="A2" activePane="bottomLeft" '
            'state="frozen"/></sheetView></sheetViews>' if header_style else "")
    return (f'<?xml version="1.0" encoding="UTF-8" standalone="yes"?><worksheet xmlns="{NS[1:-1]}">{pane}<cols>{cols}'
            f'</cols><sheetData>{body}</sheetData>{dv}</worksheet>')


def write_xlsx(review_rows, path=OUT):
    table = [HEADER] + [[r[k] for k in KEYS] for r in review_rows]
    rel = "http://schemas.openxmlformats.org/officeDocument/2006/relationships"
    ct = "application/vnd.openxmlformats-officedocument.spreadsheetml"
    styles = (f'<styleSheet xmlns="{NS[1:-1]}"><fonts count="2"><font><sz val="11"/><name val="Calibri"/></font><font><b/>'
              '<sz val="11"/><name val="Calibri"/></font></fonts><fills count="3"><fill><patternFill patternType="none"/>'
              '</fill><fill><patternFill patternType="gray125"/></fill><fill><patternFill patternType="solid"><fgColor '
              'rgb="FFFFF2CC"/></patternFill></fill></fills><borders count="1"><border><left/><right/><top/><bottom/>'
              '<diagonal/></border></borders><cellStyleXfs count="1"><xf numFmtId="0" fontId="0" fillId="0" borderId="0"/>'
              '</cellStyleXfs><cellXfs count="4"><xf numFmtId="0" fontId="0" fillId="0" borderId="0" xfId="0"/>'
              + "".join(f'<xf numFmtId="0" fontId="{f}" fillId="{fl}" borderId="0" xfId="0" applyFont="1" applyFill="1" '
                        'applyAlignment="1"><alignment wrapText="1" vertical="top"/></xf>' for f, fl in ((1, 0), (0, 0), (0, 2)))
              + "</cellXfs></styleSheet>")
    parts = {
        "[Content_Types].xml": '<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types"><Default '
        'Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/><Default Extension="xml" '
        f'ContentType="application/xml"/><Override PartName="/xl/workbook.xml" ContentType="{ct}.sheet.main+xml"/>'
        f'<Override PartName="/xl/worksheets/sheet1.xml" ContentType="{ct}.worksheet+xml"/><Override '
        f'PartName="/xl/worksheets/sheet2.xml" ContentType="{ct}.worksheet+xml"/><Override PartName="/xl/styles.xml" '
        f'ContentType="{ct}.styles+xml"/></Types>',
        "_rels/.rels": '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships"><Relationship '
        f'Id="rId1" Type="{rel}/officeDocument" Target="xl/workbook.xml"/></Relationships>',
        "xl/workbook.xml": f'<workbook xmlns="{NS[1:-1]}" xmlns:r="{rel}"><sheets><sheet name="Review" sheetId="1" '
        'r:id="rId1"/><sheet name="Read me" sheetId="2" r:id="rId2"/></sheets></workbook>',
        "xl/_rels/workbook.xml.rels": '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'
        + "".join(f'<Relationship Id="rId{i}" Type="{rel}/{t}" Target="{p}"/>' for i, t, p in
                  ((1, "worksheet", "worksheets/sheet1.xml"), (2, "worksheet", "worksheets/sheet2.xml"), (3, "styles", "styles.xml")))
        + "</Relationships>",
        "xl/styles.xml": styles,
        "xl/worksheets/sheet1.xml": _sheet(table, WIDTHS, True, fill_cols=(4, 5, 6), validate_col="E"),
        "xl/worksheets/sheet2.xml": _sheet(README, [110], False),
    }
    with zipfile.ZipFile(path, "w", zipfile.ZIP_DEFLATED) as z:
        for name, xml in parts.items():
            z.writestr(zipfile.ZipInfo(name, (2026, 1, 1, 0, 0, 0)), xml)   # fixed time: the same texts give the same file


def read_xlsx(path):
    """The first sheet's rows as dicts keyed by HEADER (works for files saved by Excel, LibreOffice or Google Sheets)."""
    z = zipfile.ZipFile(path)
    names = z.namelist()
    shared = ["".join(t.text or "" for t in si.iter(NS + "t"))
              for si in ET.fromstring(z.read("xl/sharedStrings.xml")).iter(NS + "si")] if "xl/sharedStrings.xml" in names else []
    rid = ET.fromstring(z.read("xl/workbook.xml")).find(f"{NS}sheets/{NS}sheet").get(
        "{http://schemas.openxmlformats.org/officeDocument/2006/relationships}id")
    target = next(r.get("Target") for r in ET.fromstring(z.read("xl/_rels/workbook.xml.rels")) if r.get("Id") == rid)
    target = target.lstrip("/") if target.lstrip("/").startswith("xl/") else "xl/" + target
    table = []
    for row in ET.fromstring(z.read(target)).iter(NS + "row"):
        vals = {}
        for c in row.iter(NS + "c"):
            col = sum((ord(ch) - 64) * 26 ** k for k, ch in enumerate(reversed(re.match(r"[A-Z]+", c.get("r")).group()))) - 1
            v = c.find(NS + "v")
            t = c.get("t")
            vals[col] = (shared[int(v.text)] if t == "s" else "".join(x.text or "" for x in c.iter(NS + "t"))
                         if t == "inlineStr" else (v.text or "") if v is not None else "")
        table.append([vals.get(j, "") for j in range(len(HEADER))])
    return [dict(zip(HEADER, r)) for r in table[1:] if any(r)]


def apply_review(sheet_rows, name, day, words_dir=HERE, mark_reviewed=True):
    """Mark 'yes' texts reviewed, replace corrected ones (placeholders must match the English), write the word files
    back. Returns counts and the rows to apply by hand (texts made in code) or set aside (the English changed since the
    sheet was made). mark_reviewed=False applies corrections but leaves every review mark as it is."""
    mark = f"reviewed by {name}, {day}"
    words = {f: _load(words_dir, f) for f in FILES}
    index = {k: n for k, _, n in _word_nodes(words)}
    out = {"marked": 0, "corrected": 0, "unanswered": 0, "said_no_without_fix": [], "by_hand": [], "stale": []}
    for r in sheet_rows:
        rid, ok, fix = r["id"].strip(), r[HEADER[4]].strip().lower(), r[HEADER[5]].strip()
        if not rid or not (ok or fix):
            out["unanswered"] += bool(rid)
            continue
        node = index.get(rid)
        if node is None:
            out["by_hand"].append(r)
        elif r[HEADER[2]].strip() and r[HEADER[2]].strip() != node["en"].strip():
            out["stale"].append(r)
        elif fix:
            need, got = sorted(set(PLACEHOLDER.findall(node["en"]))), sorted(set(PLACEHOLDER.findall(fix)))
            if need != got:
                raise ValueError(f"{rid}: the corrected Nepali must keep the placeholders {need}, it has {got}")
            node["ne"] = fix
            node["ne_review"] = mark if mark_reviewed else node["ne_review"]
            out["corrected"] += 1
        elif ok == "yes":
            node["ne_review"] = mark if mark_reviewed else node["ne_review"]
            out["marked"] += 1
        else:
            out["said_no_without_fix"].append(rid)
    for f in FILES:
        (Path(words_dir) / f"{f}.json").write_text(json.dumps(words[f], indent=1, ensure_ascii=False) + "\n", encoding="utf-8")
    return out


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--apply", help="the filled-in spreadsheet")
    ap.add_argument("--name")
    ap.add_argument("--date")
    ap.add_argument("--no-mark", action="store_true", help="apply corrections without marking anything reviewed")
    a = ap.parse_args(argv)
    if not a.apply:
        r = rows()
        write_xlsx(r)
        print(f"wrote {OUT} ({len(r)} texts)")
        return 0
    out = apply_review(read_xlsx(a.apply), a.name, a.date, mark_reviewed=not a.no_mark)
    print(json.dumps({k: v if isinstance(v, int) else len(v) for k, v in out.items()}),
          "\nnext: python -m pipeline.export.build_words; python -m pipeline.words.preview; re-export the fields")
    for kind in ("by_hand", "stale"):
        for r in out[kind]:
            print(kind.upper(), r["id"], "->", r[HEADER[5]] or r[HEADER[4]], "|", r[HEADER[6]])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

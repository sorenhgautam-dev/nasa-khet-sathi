"""Build review_pack/ and review_pack.zip from whatever exists, and say plainly what does not.

    .venv/bin/python scripts/make_review_pack.py

Never copies data/raw, .env or .netrc: it only copies named, known-safe items, then scans the pack
for the words password, token and key and prints every hit for a person to check.
"""
import re
import shutil
import subprocess
import sys
import zipfile
from pathlib import Path

import pandas as pd

REPO = Path(__file__).resolve().parents[1]

EXPECTED = {  # item in the pack -> where it comes from
    "DATA_AUDIT.md": "DATA_AUDIT.md",
    "VALIDATION.md": "records/checks.txt",
    "config/crops.json": "config/crops.json",
    "config/rules.yaml": "config/rules.yaml",
}
EXPECTED_DIRS = {  # pack folder -> (source folder, glob, what it is); per-field subfolders are kept
    "cards": ("data/cards", "**/*.json", "data cards (golden rule 12d)"),
    "checks": ("data/checks", "**/*.json", "validation checks and cross-checks (see records/checks.txt for what is still missing)"),
    "field_pixel_plots": ("data/plots/pixels", "**/*.png", "field outline over each gridded dataset's pixels"),
    "plots": ("data/plots", "*/*.png", "model plots (e.g. the season root-zone depletion plot)"),
    "switch_off": ("data/switch_off", "**/*.json", "switch-off test results"),
}
SECRET_WORDS = ["password", "token", "key"]


def _summarise(table, out_dir, name):
    df = pd.read_parquet(table)
    df.head(10).to_csv(out_dir / f"{name}_head.csv", index=False)
    rows = {}
    for col in df.columns:
        s = df[col]
        num = pd.api.types.is_numeric_dtype(s) and not pd.api.types.is_bool_dtype(s)
        rows[col] = {"count": int(s.count()), "missing": int(s.isna().sum()),
                     "min": s.min() if num or pd.api.types.is_datetime64_any_dtype(s) else "",
                     "max": s.max() if num or pd.api.types.is_datetime64_any_dtype(s) else "",
                     "mean": s.mean() if num else ""}
    pd.DataFrame.from_dict(rows, orient="index")[["count", "min", "max", "mean", "missing"]].to_csv(
        out_dir / f"{name}_summary.csv")
    return df


def _timeseries(df, name, out_dir):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    date_col = next((c for c in df.columns if pd.api.types.is_datetime64_any_dtype(df[c])), None)
    if date_col is None:
        return
    for col in df.columns:
        if col == date_col or not pd.api.types.is_numeric_dtype(df[col]):
            continue
        fig, ax = plt.subplots(figsize=(10, 3))
        ax.plot(df[date_col], df[col], lw=0.6)
        ax.set_title(f"{name}: {col}")
        ax.set_xlabel(date_col)
        ax.set_ylabel(col)
        fig.tight_layout()
        fig.savefig(out_dir / f"{name}__{col}.png", dpi=110)
        plt.close(fig)


def build(repo=REPO, run_tests=True):
    repo = Path(repo)
    pack = repo / "review_pack"
    if pack.exists():
        shutil.rmtree(pack)
    pack.mkdir()
    missing = []

    for dest, src in EXPECTED.items():
        if (repo / src).is_file():
            (pack / dest).parent.mkdir(parents=True, exist_ok=True)
            shutil.copy(repo / src, pack / dest)
        else:
            missing.append(f"- `{src}`: does not exist yet")

    for dest, (src, pattern, what) in EXPECTED_DIRS.items():
        root = repo / src
        files = sorted(p for p in root.glob(pattern) if p.is_file()) if root.is_dir() else []
        if not files:
            missing.append(f"- `{src}/`: no {what} yet")
        for f in files:
            target = pack / dest / f.relative_to(root)
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy(f, target)

    clean_root = repo / "data" / "clean"
    tables = sorted(clean_root.glob("**/*.parquet")) if clean_root.is_dir() else []
    if not tables:
        missing.append("- `data/clean/<field>/*.parquet`: no clean tables yet, so no head/summary/time-series files")
    for t in tables:
        name = "__".join(t.relative_to(clean_root).with_suffix("").parts)   # e.g. demo__power
        (pack / "clean_tables").mkdir(exist_ok=True)
        (pack / "timeseries").mkdir(exist_ok=True)
        _timeseries(_summarise(t, pack / "clean_tables", name), name, pack / "timeseries")

    if run_tests:
        res = subprocess.run([sys.executable, "-m", "pytest", "-v"], cwd=repo, capture_output=True, text=True)
        (pack / "pytest_output.txt").write_text(res.stdout + res.stderr)

    (pack / "MISSING.md").write_text("# What this pack does not contain yet\n\n"
                                     + ("\n".join(missing) if missing else "Nothing missing.") + "\n")
    return pack


def scan_for_secrets(folder):
    folder = Path(folder)
    hits = []
    for p in sorted(folder.rglob("*")):
        if not p.is_file() or p.suffix.lower() in {".png", ".zip"}:
            continue
        for n, line in enumerate(p.read_text(errors="replace").splitlines(), 1):
            for w in SECRET_WORDS:
                if re.search(w, line, re.IGNORECASE):
                    hits.append({"file": str(p.relative_to(folder)), "line": n, "word": w,
                                 "text": line.strip()[:160]})
    return hits


def zip_pack(pack):
    pack = Path(pack)
    zpath = pack.parent / "review_pack.zip"
    with zipfile.ZipFile(zpath, "w", zipfile.ZIP_DEFLATED) as z:
        for p in sorted(pack.rglob("*")):
            if p.is_file():
                z.write(p, Path("review_pack") / p.relative_to(pack))
    return zpath


if __name__ == "__main__":
    pack = build()
    forbidden = [p for p in pack.rglob("*") if "raw" in p.parts or p.name in {".env", ".netrc"}]
    if forbidden:
        sys.exit(f"refusing to zip, forbidden files in pack: {forbidden}")
    hits = scan_for_secrets(pack)
    print(f"secret-word scan: {len(hits)} hit(s)")
    for h in hits:
        print(f"  {h['file']}:{h['line']} [{h['word']}] {h['text']}")
    print(f"wrote {zip_pack(pack)}")

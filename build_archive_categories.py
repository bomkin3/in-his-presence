"""Generate archive_categories.js from the per-magazine archive_classification CSVs.

Each archive_classification_<magazine>.csv has Image Name, Primary_Category,
Secondary_Category, All_Categories, Justification. We collapse that into a
single JS map keyed by "library/<magazine>/|<filename>" so the archive page
can attach a Primary_Category to every document card.
"""
import csv
import json
import os
import re

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
CSV_DIR = os.path.join(BASE_DIR, "csv")
OUT_PATH = os.path.join(os.path.dirname(BASE_DIR), "archive_categories.js")

PREFIX = "archive_classification_"
SUFFIX = ".csv"

data = {}


def short_cat(name: str) -> str:
    """Strip the 'Remembering ' prefix so the JS filter keys match ('People', etc.)."""
    name = (name or "").strip()
    if name.startswith("Remembering "):
        return name[len("Remembering "):]
    return name


for fname in sorted(os.listdir(CSV_DIR)):
    if not (fname.startswith(PREFIX) and fname.endswith(SUFFIX)):
        continue
    magazine = fname[len(PREFIX):-len(SUFFIX)]
    folder_key = f"library/{magazine}/"
    path = os.path.join(CSV_DIR, fname)
    with open(path, "r", encoding="utf-8-sig", newline="") as f:
        reader = csv.DictReader(f)
        for row in reader:
            img = (row.get("Image Name") or "").strip()
            primary = short_cat(row.get("Primary_Category"))
            secondary = short_cat(row.get("Secondary_Category"))
            if not img or not primary or primary in ("ERROR", "Unknown"):
                continue
            key = f"{folder_key}|{img}"
            entry = {"primary": primary}
            if secondary and secondary.lower() != "none":
                entry["secondary"] = secondary
            data[key] = entry

# Stable ordering so diffs stay readable
ordered = {k: data[k] for k in sorted(data.keys())}

body = json.dumps(ordered, ensure_ascii=False, separators=(", ", ": "))

with open(OUT_PATH, "w", encoding="utf-8") as f:
    f.write("// auto-generated from library/csv/archive_classification_*.csv\n")
    f.write("// key: \"folder|file\"  value: { primary, secondary? }\n")
    f.write(f"window.ARCHIVE_CATEGORY_DATA = {body};\n")

print(f"Wrote {len(ordered)} entries to {OUT_PATH}")

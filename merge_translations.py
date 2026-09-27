#!/usr/bin/env python3
"""
Merge full-transcript file into translations.csv with extended 10-column schema.

Schema:
  filename, folder, arabic_text, translation,
  page_id, main_header_ar, main_header_en, key_quote_ar, key_quote_en, context_summary

Rules for mapping Page_ID -> filename/folder:
  - _L2 suffix: Al-ethnayn wa aldonya 2 (ethnayn2_NNNN.jpeg)
  - _L1 rows 2-14 (Page_IDs 0026-0038) OR row with header 'العلم' / 'Al-Alam': Al-alam (alam_NNNN.jpg)
  - All other _L1 (incl _p2, _alt variants): Al-ethnayn wa Aldonya (ethnayn_NNNN.jpg)
  - _alt and _p2 do not alter filename; they are separate rows for the same file.
"""

import csv
import re
from pathlib import Path

BASE = Path("/Users/alaaalami/Desktop/bezalel/שנה ד/סמסטר ב/Graduation projet/darwish alami library/library")
EXISTING = BASE / "csv" / "translations.csv"
NEW_FILE = BASE / "voice translation" / "full transcripy part 1.txt"
OUTPUT = BASE / "csv" / "translations.csv"  # overwrite in place

NEW_SCHEMA = [
    "filename", "folder", "arabic_text", "translation",
    "page_id", "main_header_ar", "main_header_en",
    "key_quote_ar", "key_quote_en", "context_summary"
]


def map_page_id(page_id: str, main_header_ar: str, main_header_en: str, row_idx: int):
    """Return (filename, folder) or (None, None) if cannot map."""
    m = re.match(r"^(\d+)_L([12])(.*)$", page_id)
    if not m:
        return None, None
    num, layer, suffix = m.group(1), m.group(2), m.group(3)
    # Determine magazine
    header_ar = main_header_ar.strip()
    header_en = main_header_en.strip()
    is_alam = (header_ar == "العلم" or header_en == "Al-Alam")

    if layer == "2":
        return f"ethnayn2_{num}.jpeg", "Al-ethnayn wa aldonya 2"
    # layer 1
    if is_alam:
        return f"alam_{num}.jpg", "Al-alam"
    # Fallback: numeric 0026-0038 with plain _L1 (no suffix) in Al-Alam batch (rows 2-14)
    if suffix == "" and 26 <= int(num) <= 38 and row_idx <= 14:
        return f"alam_{num}.jpg", "Al-alam"
    # Everything else is Al-ethnayn wa Aldonya
    return f"ethnayn_{num}.jpg", "Al-ethnayn wa Aldonya"


def main():
    # Read existing translations.csv
    with open(EXISTING, "r", encoding="utf-8", newline="") as f:
        reader = csv.reader(f)
        existing_header = next(reader)
        existing_rows = list(reader)
    print(f"Existing rows: {len(existing_rows)} (header: {existing_header})")

    # Read new transcript file
    with open(NEW_FILE, "r", encoding="utf-8", newline="") as f:
        reader = csv.reader(f)
        new_header = next(reader)
        new_rows = list(reader)
    print(f"New rows: {len(new_rows)} (header: {new_header})")

    # Build combined rows in new schema
    combined = []

    # Old rows: pad with empty new columns
    for r in existing_rows:
        if len(r) < 4:
            continue
        filename, folder, ar, en = r[0], r[1], r[2], r[3]
        combined.append([filename, folder, ar, en, "", "", "", "", "", ""])

    # New rows: map to filename/folder
    unmapped = []
    for idx, r in enumerate(new_rows, start=2):  # row idx in file (accounting for header)
        if len(r) < 6:
            continue
        page_id, hdr_ar, hdr_en, quote_ar, quote_en, ctx = r[0], r[1], r[2], r[3], r[4], r[5]
        filename, folder = map_page_id(page_id, hdr_ar, hdr_en, idx)
        if filename is None:
            unmapped.append(page_id)
            filename, folder = "", ""
        # arabic_text/translation left empty for new rows (info lives in header/quote/summary)
        combined.append([filename, folder, "", "", page_id, hdr_ar, hdr_en, quote_ar, quote_en, ctx])

    if unmapped:
        print(f"WARNING: {len(unmapped)} rows could not be mapped: {unmapped[:5]}...")

    # Write output
    with open(OUTPUT, "w", encoding="utf-8", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(NEW_SCHEMA)
        writer.writerows(combined)

    print(f"Wrote {len(combined)} rows to {OUTPUT}")


if __name__ == "__main__":
    main()

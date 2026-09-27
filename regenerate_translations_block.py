#!/usr/bin/env python3
"""
Regenerate the window.TRANSLATIONS JavaScript block inside index.html
and bronzewoman.html from the (now extended) csv/translations.csv.

Rules:
  - Key = 'folder/filename'
  - For old-format rows (arabic_text + translation): use them directly.
  - For new-format rows (key_quote_* + main_header_*):
      arabic  = key_quote_ar (falls back to main_header_ar)
      headline= key_quote_en (falls back to main_header_en)
      If key_quote is [unclear], fall back to main_header instead.
  - If multiple rows share a filename (e.g., _alt entries), join Arabic
    with ' / ' and English with ' / '.
  - Skip rows with empty filename.
"""

import csv
import json
import re
from pathlib import Path

BASE = Path("/Users/alaaalami/Desktop/bezalel/שנה ד/סמסטר ב/Graduation projet/darwish alami library/library")
CSV_PATHS = [
    BASE / "csv" / "translations.csv",           # human-verified (priority)
    BASE / "csv" / "translations_claude_pass.csv",  # AI first-pass (fallback)
]
TARGETS = [BASE / "index.html", BASE / "bronzewoman.html"]

BLOCK_START_MARK = "/* ── Translations (embedded from csv/translations.csv) ──────────────────── */"
BLOCK_START_PREFIX = "window.TRANSLATIONS = {"
BLOCK_END = "};"


def js_escape(s: str) -> str:
    """Escape a Python string for use inside a JS single-quoted string."""
    if s is None:
        return ""
    # json.dumps gives us proper escaping incl. unicode; strip surrounding quotes then convert
    encoded = json.dumps(s, ensure_ascii=False)
    # encoded is a JS-safe double-quoted string. We need it single-quoted with ' escaped.
    inner = encoded[1:-1]  # strip double quotes
    # Convert \" back to "  (since we won't be inside double quotes)
    inner = inner.replace('\\"', '"')
    # Escape single quotes
    inner = inner.replace("'", "\\'")
    return inner


def is_unclear(s: str) -> bool:
    if not s:
        return True
    s = s.strip().lower()
    return s in ("[unclear]", "unclear", "")


def load_entries():
    entries = {}  # key -> {arabic: [], headline: []}
    all_rows = []
    for path in CSV_PATHS:
        if not path.exists():
            continue
        with open(path, "r", encoding="utf-8", newline="") as f:
            reader = csv.DictReader(f)
            for row in reader:
                all_rows.append(row)

    for row in all_rows:
        filename = row.get("filename", "").strip()
        folder = row.get("folder", "").strip()
        if not filename or not folder:
            continue
        key = f"{folder}/{filename}"

        ar_old = (row.get("arabic_text") or "").strip()
        en_old = (row.get("translation") or "").strip()

        ar_quote = (row.get("key_quote_ar") or "").strip()
        en_quote = (row.get("key_quote_en") or "").strip()
        ar_head = (row.get("main_header_ar") or "").strip()
        en_head = (row.get("main_header_en") or "").strip()

        if ar_old or en_old:
            ar_val = ar_old
            en_val = en_old
        else:
            ar_val = ar_head if is_unclear(ar_quote) else ar_quote
            en_val = en_head if is_unclear(en_quote) else en_quote

        if not ar_val and not en_val:
            continue

        slot = entries.setdefault(key, {"arabic": [], "headline": []})
        if ar_val and ar_val not in slot["arabic"]:
            slot["arabic"].append(ar_val)
        if en_val and en_val not in slot["headline"]:
            slot["headline"].append(en_val)

    return entries


def build_block(entries) -> str:
    lines = [BLOCK_START_MARK, "window.TRANSLATIONS = {"]
    # Preserve stable ordering: sort by key
    keys = sorted(entries.keys())
    body = []
    for k in keys:
        e = entries[k]
        ar = " / ".join(e["arabic"])
        en = " / ".join(e["headline"])
        body.append(f"  '{js_escape(k)}': {{arabic:'{js_escape(ar)}',headline:'{js_escape(en)}'}}")
    lines.append(",\n".join(body))
    lines.append("};")
    return "\n".join(lines)


def replace_block_in_file(path: Path, new_block: str):
    text = path.read_text(encoding="utf-8")
    # Find the block start (using the comment marker for robustness) and its closing };
    start_idx = text.find(BLOCK_START_MARK)
    if start_idx == -1:
        print(f"  SKIP: could not find block marker in {path.name}")
        return False
    # Find the first "\n};" after the window.TRANSLATIONS = { that appears after the marker
    win_idx = text.find(BLOCK_START_PREFIX, start_idx)
    if win_idx == -1:
        print(f"  SKIP: no window.TRANSLATIONS opening in {path.name}")
        return False
    # Find the balanced closing };  (assume there is exactly one };\n after entries)
    end_idx = text.find("\n};", win_idx)
    if end_idx == -1:
        print(f"  SKIP: no closing }}; in {path.name}")
        return False
    end_idx += len("\n};")

    new_text = text[:start_idx] + new_block + text[end_idx:]
    path.write_text(new_text, encoding="utf-8")
    return True


def main():
    entries = load_entries()
    print(f"Loaded {len(entries)} unique filename keys")
    block = build_block(entries)

    for target in TARGETS:
        if not target.exists():
            print(f"{target.name}: not found, skipping")
            continue
        # Backup
        backup = target.with_suffix(target.suffix + ".pretranslate.bak")
        backup.write_bytes(target.read_bytes())
        ok = replace_block_in_file(target, block)
        status = "OK" if ok else "FAIL"
        print(f"{target.name}: {status} (backup at {backup.name})")


if __name__ == "__main__":
    main()

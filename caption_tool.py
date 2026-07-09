import os
import csv
import subprocess
from openai import OpenAI

client = OpenAI(api_key=os.environ.get("OPENAI_API_KEY", "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"))

BASE_DIR = "/Users/alaaalami/Desktop/bezalel/שנה ד/סמסטר ב/Graduation projet/darwish alami library/library"
CSV_DIR  = os.path.join(BASE_DIR, "csv")
OUTPUT   = os.path.join(CSV_DIR, "captions.csv")

FOLDER_MAP = {
    "women_analysis_Al-Kawakib.csv":              "Al-Kawakib",
    "women_analysis_Al-Mawed.csv":                "Al-Mawed",
    "women_analysis_Al-alam.csv":                 "Al-alam",
    "women_analysis_Al-Rissalah.csv":             "Al-Rissalah",
    "women_analysis_Al-Thqafa.csv":               "Al-Thqafa",
    "women_analysis_Al-ethnayn wa Aldonya.csv":   "Al-ethnayn wa Aldonya",
    "women_analysis_Al-ethnayn wa aldonya 2.csv": "Al-ethnayn wa aldonya 2",
    "women_analysis_Al-ethnayn wa aldonya 3.csv": "Al-ethnayn wa aldonya 3",
}

FIELDNAMES = ["Image Name", "Folder", "Visual Category", "Caption (Arabic)", "Caption (English)", "Gap Type", "Notes"]

GAP_TYPES = ["Corrected", "Promoted", "Redirected", "Match", "N/A"]


def translate(arabic_text):
    response = client.chat.completions.create(
        model="gpt-4o",
        messages=[
            {"role": "system", "content": "You are a precise Arabic-to-English translator. Translate the text literally and exactly. Do not paraphrase or summarize."},
            {"role": "user", "content": arabic_text}
        ],
        max_tokens=200
    )
    return response.choices[0].message.content.strip()


# Load all images with women from women_analysis CSVs
candidates = []
for fname, folder in FOLDER_MAP.items():
    fpath = os.path.join(CSV_DIR, fname)
    if not os.path.exists(fpath):
        continue
    seen = set()
    with open(fpath, encoding="utf-8-sig") as f:
        reader = csv.DictReader(f)
        for row in reader:
            img = row.get("Image Name", "").strip()
            if img in seen:
                continue
            seen.add(img)
            if row.get("Has Woman", "").strip() == "Yes":
                candidates.append({
                    "Image Name": img,
                    "Folder": folder,
                    "Visual Category": row.get("Visual Category", "").strip()
                })

# Load already-captioned images
done = set()
if os.path.exists(OUTPUT):
    with open(OUTPUT, encoding="utf-8-sig") as f:
        reader = csv.DictReader(f)
        for row in reader:
            key = f"{row.get('Folder')}|{row.get('Image Name')}"
            done.add(key)

remaining = [c for c in candidates if f"{c['Folder']}|{c['Image Name']}" not in done]

print(f"\n{len(candidates)} images with women — {len(done)} already captioned — {len(remaining)} remaining")
print("Controls: Enter to skip image · 'q' to quit\n")

file_exists = os.path.exists(OUTPUT)
with open(OUTPUT, "a", newline="", encoding="utf-8-sig") as csvfile:
    writer = csv.DictWriter(csvfile, fieldnames=FIELDNAMES)
    if not file_exists:
        writer.writeheader()

    for i, item in enumerate(remaining):
        img_path = os.path.join(BASE_DIR, item["Folder"], item["Image Name"])
        print(f"[{i+1}/{len(remaining)}] {item['Folder']} / {item['Image Name']}")
        print(f"  Visual: {item['Visual Category']}")

        # Open image
        subprocess.Popen(["open", img_path])

        # Get Arabic caption
        arabic = input("  Arabic caption (Enter to skip, q to quit): ").strip()
        if arabic.lower() == "q":
            print("Saved and quit.")
            break
        if not arabic:
            print("  Skipped.\n")
            continue

        # Translate
        print("  Translating...", end=" ", flush=True)
        english = translate(arabic)
        print(f"{english}")

        # Confirm
        confirm = input("  Save? (y/n): ").strip().lower()
        if confirm != "y":
            print("  Discarded.\n")
            continue

        # Gap type
        print(f"  Gap type? {' / '.join(GAP_TYPES)}")
        gap = input("  Enter gap type (or Enter to skip): ").strip()
        if gap not in GAP_TYPES:
            gap = ""

        # Notes
        notes = input("  Any notes? (Enter to skip): ").strip()

        writer.writerow({
            "Image Name": item["Image Name"],
            "Folder": item["Folder"],
            "Visual Category": item["Visual Category"],
            "Caption (Arabic)": arabic,
            "Caption (English)": english,
            "Gap Type": gap,
            "Notes": notes
        })
        csvfile.flush()
        print("  Saved.\n")

print(f"\nDone! Captions saved to: {OUTPUT}")

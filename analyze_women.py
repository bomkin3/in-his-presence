import os
import csv
import base64
import json
import time
from openai import OpenAI, RateLimitError

client = OpenAI(api_key=os.environ.get("OPENAI_API_KEY", "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"))

# --- Choose the folder to analyze ---
BASE_DIR = "/Users/alaaalami/Desktop/bezalel/שנה ד/סמסטר ב/Graduation projet/darwish alami library/library"
TARGET_FOLDER = os.path.join(BASE_DIR, "Al-Kawakib")
# ------------------------------------

folder_name = os.path.basename(os.path.normpath(TARGET_FOLDER))
OUTPUT_FILE = os.path.join(BASE_DIR, "csv", f"women_analysis_{folder_name}.csv")

PROMPT = """
You are analyzing a page from an Arabic magazine published between 1930 and 1960.

Look at the image visually — ignore any text on the page.
Determine if a woman is present, and if so, how she is visually presented.

Categorize using ONLY these categories (pick all that apply):
- "The Modern Face"      -> woman used to signal progress, education, urban modernity
- "The Traditional Body" -> woman used to signal cultural continuity, tradition, virtue
- "The Before & After"   -> explicit visual contrast between old and new Arab woman on the same page
- "The Advertisement"    -> woman's image used to sell a product or an idea of modernity
- "The Professional"     -> woman as actress, journalist, doctor, teacher — proof of achievement
- "The Borrowed Image"   -> Western-style pose or dress that remains distinctly Arab in context
- "None"                 -> no woman present, or image does not fit any category above

Return ONLY a valid JSON object with these exact keys:
{
  "has_woman": true or false,
  "visual_categories": ["category1", "category2"],
  "notes": "one sentence on anything visually notable, or empty string"
}
"""

FIELDNAMES = ["Image Name", "Has Woman", "Visual Category", "Notes"]


def encode_image(path):
    with open(path, "rb") as f:
        return base64.b64encode(f.read()).decode("utf-8")


def analyze_image(img_path):
    base64_image = encode_image(img_path)
    response = client.chat.completions.create(
        model="gpt-4o",
        response_format={"type": "json_object"},
        messages=[
            {
                "role": "user",
                "content": [
                    {"type": "text", "text": PROMPT},
                    {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{base64_image}"}}
                ]
            }
        ],
        max_tokens=150
    )
    return json.loads(response.choices[0].message.content)


def format_categories(cats):
    if isinstance(cats, list) and cats:
        return " | ".join(cats)
    return "None"


if not os.path.exists(TARGET_FOLDER):
    print(f"Error: folder [{TARGET_FOLDER}] not found.")
    exit()

os.makedirs(os.path.dirname(OUTPUT_FILE), exist_ok=True)

images = sorted([
    f for f in os.listdir(TARGET_FOLDER)
    if f.lower().endswith(('.jpg', '.jpeg', '.png', '.webp'))
])

processed = set()
if os.path.exists(OUTPUT_FILE):
    with open(OUTPUT_FILE, "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            if row.get("Image Name"):
                processed.add(row["Image Name"])

print(f"[{folder_name}] {len(images)} images — {len(processed)} already processed")

file_exists = os.path.exists(OUTPUT_FILE)
with open(OUTPUT_FILE, "a", newline="", encoding="utf-8-sig") as csvfile:
    writer = csv.DictWriter(csvfile, fieldnames=FIELDNAMES)
    if not file_exists:
        writer.writeheader()

    for img_name in images:
        if img_name in processed:
            print(f"  Skipping [{img_name}]")
            continue

        img_path = os.path.join(TARGET_FOLDER, img_name)
        print(f"  Analyzing [{img_name}]...", end=" ", flush=True)

        while True:
            try:
                result = analyze_image(img_path)

                row = {
                    "Image Name": img_name,
                    "Has Woman": "Yes" if result.get("has_woman") else "No",
                    "Visual Category": format_categories(result.get("visual_categories")),
                    "Notes": result.get("notes", "")
                }

                writer.writerow(row)
                csvfile.flush()
                print(f"OK  {row['Has Woman']} | {row['Visual Category']}")
                break

            except RateLimitError as e:
                wait = 60
                msg = str(e)
                if "Please try again in" in msg:
                    try:
                        wait = float(msg.split("Please try again in")[1].split("s")[0].strip()) + 2
                    except Exception:
                        pass
                print(f"\n  Rate limit hit, waiting {wait:.0f}s...")
                time.sleep(wait)

            except Exception as e:
                print(f"\n  Error: {type(e).__name__}: {str(e)[:80]}")
                writer.writerow({
                    "Image Name": img_name,
                    "Has Woman": "Error",
                    "Visual Category": f"{type(e).__name__}: {str(e)[:60]}",
                    "Notes": ""
                })
                csvfile.flush()
                break

print(f"\nDone! Results saved to: {OUTPUT_FILE}")

import os
import csv
import base64
import json
import time
from openai import OpenAI, RateLimitError

client = OpenAI(api_key=os.environ.get("OPENAI_API_KEY", "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"))

BASE_DIR = "/Users/alaaalami/Desktop/bezalel/שנה ד/סמסטר ב/Graduation projet/darwish alami library/library"

VALID_CATEGORIES = [
    "Remembering People",
    "Remembering Desires",
    "Remembering Leisure",
    "Remembering Street"
]

FIELDNAMES = ["Image Name", "Primary_Category", "Secondary_Category", "All_Categories", "Justification"]

PROMPT = """You are an expert archivist analyzing scanned pages from mid-20th century Arab print magazines (1930s–1960s).

Classify the image into the following taxonomy. Assign a Primary Category (required) and a Secondary Category only if the image genuinely overlaps two categories.

CATEGORIES:

1. "Remembering People"
   Core Subject: Close-up portraits, magazine cover faces, studio headshots, human profiles, fashion/garment close-ups where the individual is the sole focus.
   Key Elements: Clean background, studio lighting, strong focus on facial expressions, hairstyles, and cosmetics.

2. "Remembering Desires"
   Core Subject: Commercial advertisements, product showcase, high-society lifestyle features.
   Key Elements: Domestic appliances (refrigerators, washing machines), consumer goods (cosmetics, soaps, cigarettes), luxury cars posed with people, celebrities at glamorous indoor banquets, explicit ad typography integrated with products.

3. "Remembering Leisure"
   Core Subject: Escapism, public relaxation, non-work temporalities.
   Key Elements: Summer beach scenes, swimming pools, people sunbathing, cinema halls, theater stages, concerts/musicians performing, cafes, nightlife/parties.

4. "Remembering Street"
   Core Subject: The public sphere, urban infrastructure, civic movement, and labor.
   Key Elements: Political demonstrations, street signage/posters, active workplaces/factories, laborers, open city squares, modernist architecture, traffic, general street photography capturing daily public life and political/social movement.

Return ONLY a valid JSON object with these exact keys:
{
  "primary_category": "<one of the 4 categories above>",
  "secondary_category": "<one of the 4 categories, or null if no meaningful overlap>",
  "justification": "<one sentence describing the observable visual elements that justify the classification>"
}
"""


def encode_image(path):
    with open(path, "rb") as f:
        return base64.b64encode(f.read()).decode("utf-8")


def classify_image(img_path):
    base64_image = encode_image(img_path)
    response = client.chat.completions.create(
        model="gpt-4o",
        response_format={"type": "json_object"},
        messages=[
            {
                "role": "user",
                "content": [
                    {"type": "text", "text": PROMPT},
                    {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{base64_image}", "detail": "high"}}
                ]
            }
        ],
        max_tokens=200
    )
    return json.loads(response.choices[0].message.content)


def build_row(img_name, result):
    primary = result.get("primary_category", "").strip()
    secondary = result.get("secondary_category")
    justification = result.get("justification", "").strip()

    if primary not in VALID_CATEGORIES:
        primary = "Unknown"

    if secondary and secondary not in VALID_CATEGORIES:
        secondary = None

    all_cats = [primary]
    if secondary and secondary != primary:
        all_cats.append(secondary)

    return {
        "Image Name": img_name,
        "Primary_Category": primary,
        "Secondary_Category": secondary if secondary else "None",
        "All_Categories": ";".join(all_cats),
        "Justification": justification
    }


# --- Collect all magazine folders ---
magazine_folders = sorted([
    d for d in os.listdir(BASE_DIR)
    if os.path.isdir(os.path.join(BASE_DIR, d)) and not d.startswith(".")
])

print(f"Found {len(magazine_folders)} magazine folders: {magazine_folders}\n")

os.makedirs(os.path.join(BASE_DIR, "csv"), exist_ok=True)

for magazine in magazine_folders:
    folder_path = os.path.join(BASE_DIR, magazine)
    output_file = os.path.join(BASE_DIR, "csv", f"archive_classification_{magazine}.csv")

    images = sorted([
        f for f in os.listdir(folder_path)
        if f.lower().endswith(".jpg") or f.lower().endswith(".jpeg")
    ])

    if not images:
        continue

    # Load already-processed images for resume support
    processed = set()
    if os.path.exists(output_file):
        with open(output_file, "r", encoding="utf-8-sig") as f:
            reader = csv.DictReader(f)
            for row in reader:
                if row.get("Image Name"):
                    processed.add(row["Image Name"])

    print(f"[{magazine}] {len(images)} images — {len(processed)} already processed")

    file_exists = os.path.exists(output_file)
    with open(output_file, "a", newline="", encoding="utf-8-sig") as csvfile:
        writer = csv.DictWriter(csvfile, fieldnames=FIELDNAMES)
        if not file_exists:
            writer.writeheader()

        for img_name in images:
            if img_name in processed:
                print(f"  Skipping [{img_name}]")
                continue

            img_path = os.path.join(folder_path, img_name)
            print(f"  Classifying [{img_name}]...", end=" ", flush=True)

            while True:
                try:
                    result = classify_image(img_path)
                    row = build_row(img_name, result)
                    writer.writerow(row)
                    csvfile.flush()
                    print(f"OK  {row['Primary_Category']} | {row['Secondary_Category']}")
                    break

                except RateLimitError as e:
                    wait = 60
                    msg = str(e)
                    if "Please try again in" in msg:
                        try:
                            wait = float(msg.split("Please try again in")[1].split("s")[0].strip()) + 2
                        except Exception:
                            pass
                    print(f"\n  Rate limit hit — waiting {wait:.0f}s...")
                    time.sleep(wait)

                except Exception as e:
                    print(f"\n  Error: {type(e).__name__}: {str(e)[:80]}")
                    writer.writerow({
                        "Image Name": img_name,
                        "Primary_Category": "ERROR",
                        "Secondary_Category": "None",
                        "All_Categories": "ERROR",
                        "Justification": f"{type(e).__name__}: {str(e)[:80]}"
                    })
                    csvfile.flush()
                    break

    print()

print("Done! All results saved to the csv/ folder.")

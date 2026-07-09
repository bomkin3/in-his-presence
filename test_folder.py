import os
import csv
import base64
import json
import time
from openai import OpenAI, RateLimitError

# إعداد عميل الـ API
client = OpenAI(api_key="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")

# المجلدات المتاحة في المشروع:
# Al-Kawakib | Al-Mawed | Al-Rissalah | Al-Thqafa | Al-alam | Al-ethnayn wa Aldonya | Al-ethnayn wa aldonya 2

BASE_DIR = "/Users/alaaalami/Desktop/bezalel/שנה ד/סמסטר ב/Graduation projet/darwish alami library/library"
TARGET_FOLDER = os.path.join(BASE_DIR, "Al-ethnayn wa aldonya 3")

# الحصول على اسم المجلد تلقائياً لتسمية ملف النتائج به
folder_name = os.path.basename(os.path.normpath(TARGET_FOLDER))
OUTPUT_FILE = os.path.join(BASE_DIR, f"results_{folder_name}.csv")

def encode_image(image_path):
    with open(image_path, "rb") as image_file:
        return base64.b64encode(image_file.read()).decode('utf-8')

# قراءة الصور وترتيبها تلقائياً من المجلد المحدد
if not os.path.exists(TARGET_FOLDER):
    print(f"خطأ: المجلد [{TARGET_FOLDER}] غير موجود. تأكد من المسار.")
    exit()

ordered_images = [
    f for f in os.listdir(TARGET_FOLDER)
    if f.lower().endswith(('.png', '.jpg', '.jpeg', '.webp'))
]
ordered_images.sort()

print(f"تم العثور على {len(ordered_images)} صورة في مجلد [{folder_name}]. جاري بدء الفحص بالترتيب...")

# معرفة أين توقفنا سابقاً (لدعم الاستئناف)
processed_images = set()
if os.path.exists(OUTPUT_FILE):
    with open(OUTPUT_FILE, "r", encoding="utf-8") as f:
        reader = csv.reader(f)
        next(reader, None)
        for row in reader:
            if row:
                processed_images.add(row[0])

# معالجة الصور وكتابة النتائج فوراً
file_exists = os.path.exists(OUTPUT_FILE)
with open(OUTPUT_FILE, "a", newline="", encoding="utf-8-sig") as csvfile:
    writer = csv.writer(csvfile)
    if not file_exists:
        writer.writerow(["Image Name", "Has Woman", "Category"])

    for img_name in ordered_images:
        if img_name in processed_images:
            print(f"تخطي [{img_name}] (معالج مسبقاً)")
            continue

        img_path = os.path.join(TARGET_FOLDER, img_name)
        print(f"تحليل [{img_name}]...")

        while True:
            try:
                base64_image = encode_image(img_path)

                response = client.chat.completions.create(
                    model="gpt-4o-mini",
                    response_format={"type": "json_object"},
                    messages=[
                        {
                            "role": "user",
                            "content": [
                                {
                                    "type": "text",
                                    "text": (
                                        "Analyze this magazine page/image and return a JSON object with exactly two keys:\n"
                                        "1. 'has_woman': boolean (true if a woman is visibly present, otherwise false).\n"
                                        "2. 'categories': array of strings. Select ALL categories that apply from this list:\n"
                                        "   - 'Advertising'  → advertisements, product promotions, commercial announcements\n"
                                        "   - 'Romantic'     → romantic stories, love scenes, couples, sentimental content\n"
                                        "   - 'Headlines'    → text-heavy pages, article titles, headlines, table of contents\n"
                                        "   - 'Politics'     → politics, war, military, conflicts, world events, national leaders\n"
                                        "   - 'Illustration' → illustrations, drawings, cartoons, caricatures, painted artwork\n"
                                        "   - 'Daily Life'   → daily life, home, cooking, fashion, health, social topics\n"
                                        "   - 'Cinema'       → movies, film stars, theater, entertainment, actors, actresses\n"
                                        "   - 'Modeling'     → fashion models, photo shoots, beauty, glamour, model portraits\n"
                                        "   - 'Other'        → ONLY if none of the above apply at all\n"
                                        "Be generous — prefer specific categories over 'Other'. Use 'Other' only as a last resort.\n"
                                        "Output format example: {\"has_woman\": true, \"categories\": [\"Cinema\", \"Modeling\"]}"
                                    )
                                },
                                {
                                    "type": "image_url",
                                    "image_url": {"url": f"data:image/jpeg;base64,{base64_image}"}
                                }
                            ]
                        }
                    ],
                    max_tokens=150
                )

                result = json.loads(response.choices[0].message.content)
                has_woman = "نعم" if result.get("has_woman") else "لا"
                categories = result.get("categories", [])
                if isinstance(categories, list):
                    category = " | ".join(categories) if categories else "غير محدد"
                else:
                    category = str(categories)

                writer.writerow([img_name, has_woman, category])
                csvfile.flush()
                break  # نجح الطلب، انتقل للصورة التالية

            except RateLimitError as e:
                wait = 60  # افتراضي إذا لم تحدد الـ API وقتاً
                msg = str(e)
                if "Please try again in" in msg:
                    try:
                        # استخراج الرقم من رسالة مثل: "Please try again in 34.5s"
                        wait = float(msg.split("Please try again in")[1].split("s")[0].strip()) + 2
                    except Exception:
                        pass
                print(f"⏳ تجاوز حد الطلبات، انتظار {wait:.0f} ثانية ثم إعادة المحاولة...")
                time.sleep(wait)

            except Exception as e:
                error_type = type(e).__name__
                error_msg = str(e)[:80]  # أول 80 حرف من رسالة الخطأ
                print(f"خطأ في الصورة {img_name}: [{error_type}] {error_msg}")
                writer.writerow([img_name, "Error", f"{error_type}: {error_msg}"])
                csvfile.flush()
                break  # خطأ حقيقي، تخطى هذه الصورة

print(f"\nتم الانتهاء! النتائج محفوظة في: {OUTPUT_FILE}")

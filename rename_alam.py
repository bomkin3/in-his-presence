import os

TARGET_FOLDER = "/Users/alaaalami/Desktop/bezalel/שנה ד/סמסטר ב/Graduation projet/darwish alami library/library/Al-alam"

if not os.path.exists(TARGET_FOLDER):
    print("المجلد غير موجود!")
    exit()

images = [f for f in os.listdir(TARGET_FOLDER) if f.lower().endswith(('.png', '.jpg', '.jpeg', '.webp'))]
images.sort()

print(f"جاري إعادة تسمية {len(images)} صورة في مجلد العالم...")

for index, img_name in enumerate(images, start=1):
    ext = os.path.splitext(img_name)[1].lower()
    new_name = f"alam_{index:04d}{ext}"
    old_path = os.path.join(TARGET_FOLDER, img_name)
    new_path = os.path.join(TARGET_FOLDER, new_name)
    os.rename(old_path, new_path)

print("تمت إعادة تسمية جميع الصور بنجاح!")

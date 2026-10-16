import os
import re
import json
import random
import datetime
import requests
from pathlib import Path
from PIL import Image
from google import genai
from google.genai import types

def strip_phone_and_urls_for_gbp(text: str) -> str:
    """
    Strictly removes any accidental phone numbers or URLs from the Google Business Profile
    summary text so Google's automated spam filter never rejects the post.
    """
    text = re.sub(r'https?://\S+|www\.\S+|habiboil\.store', '', text, flags=re.IGNORECASE)
    text = re.sub(r'(?:\+92|0092|0)?\s*3\d{2}[\s\-]?\d{7}', '', text)
    text = re.sub(r'\n{3,}', '\n\n', text)
    return text.strip()

def main():
    api_key = os.environ.get("GEMINI_API_KEY")
    if not api_key:
        raise ValueError("Missing GEMINI_API_KEY environment variable. Add it in GitHub Settings -> Secrets.")

    client = genai.Client(api_key=api_key)

    bottle_dir = Path("assets/bottles")
    bottle_files = [
        p for p in bottle_dir.glob("*")
        if p.suffix.lower() in {".png", ".jpg", ".jpeg", ".webp"}
    ]
    if not bottle_files:
        raise FileNotFoundError("No bottle images found in assets/bottles/. Please upload at least one photo.")

    custom_bottle = os.environ.get("CUSTOM_BOTTLE_FILENAME", "").strip()
    if custom_bottle and (bottle_dir / custom_bottle).exists():
        chosen_bottle_path = bottle_dir / custom_bottle
    else:
        real_bottles = [p for p in bottle_files if p.name != "sample_habiboil_bottle.png"]
        chosen_bottle_path = random.choice(real_bottles) if real_bottles else bottle_files[0]

    print(f"Using bottle reference image: {chosen_bottle_path}")
    bottle_img = Image.open(chosen_bottle_path)

    THEMES = [
        "Heart health & cholesterol control benefits of cooking with pure Kachi Ghani mustard oil on a traditional KPK kitchen counter",
        "Pure golden mustard oil bottle surrounded by fresh yellow sarson (mustard) flowers in Rustam Mardan morning sunlight",
        "Traditional Pakistani achar (pickle) glass jar and spices next to the HabibOil bottle on a rustic wooden table",
        "Winter joint relief, massage, and strong immunity with pure organic mustard oil in warm cozy sunlight",
        "Crispy traditional Pakistani pakoras and parathas cooked in pure HabibOil mustard oil, appetizing food photography",
        "Natural hair growth and glowing skin care benefits of pure cold-pressed sarson ka tail, clean botanical setting",
        "Direct from Rustam Mardan kolhu (mill) to your home: 100% chemical-free, unrefined pure mustard oil"
    ]
    custom_theme = os.environ.get("CUSTOM_THEME", "").strip()
    today_theme = custom_theme if custom_theme else random.choice(THEMES)
    print(f"Selected Theme: {today_theme}")

    today_str = datetime.date.today().isoformat()
    os.makedirs("generated", exist_ok=True)
    output_img_path = Path(f"generated/habiboil_{today_str}.png")

    image_prompt = (
        f"Keep the exact HabibOil bottle and label from the reference image completely intact, legible, and sharp. "
        f"Place this exact bottle naturally into a professional commercial product photography scene: {today_theme}. "
        f"Photorealistic, 8k resolution, warm natural lighting, shallow depth of field, high-end food marketing aesthetic."
    )

    try:
        print("Generating custom product scene with gemini-2.5-flash-image...")
        img_response = client.models.generate_content(
            model="gemini-2.5-flash-image",
            contents=[bottle_img, image_prompt],
            config=types.GenerateContentConfig(
                response_modalities=["IMAGE"]
            )
        )
        saved_image = False
        for part in img_response.candidates[0].content.parts:
            if part.inline_data:
                with open(output_img_path, "wb") as f:
                    f.write(part.inline_data.data)
                saved_image = True
                print(f"Saved generated image to {output_img_path}")
                break
        if not saved_image:
            raise RuntimeError("No inline image returned by model.")
    except Exception as e:
        print(f"Image generation fallback triggered ({e}). Copying original bottle image for today's post.")
        bottle_img.save(output_img_path)

    caption_prompt = f"""
You are the expert Urdu SEO Social Media Manager for 'HabibOil' (located at Jamia Masjid Ada, Rustam, Mardan, KPK, Pakistan).
Write a daily promotional post based on today's theme: "{today_theme}".

Naturally weave in high-ranking local SEO keywords:
خالص سرسوں کا تیل, Kachi Ghani Mustard Oil, HabibOil Rustam Mardan, Pure Cooking Oil, Sarson Ka Tail.

Output EXACTLY two sections separated by ===SPLIT===:

[Section 1: Facebook Page Caption]
- Engaging, persuasive Urdu copy with emojis and bullet points
- Include full contact details:
  📞 Call: 0334-6328047
  💬 WhatsApp: 0304-8907756
  🌐 Website: https://habiboil.store
  📍 Address: Jamia Masjid Ada, Rustam, Mardan
- 8 relevant Urdu and English SEO hashtags

===SPLIT===

[Section 2: Google Business Profile Summary]
- Engaging Urdu SEO copy with emojis (100 to 180 words)
- STRICT GOOGLE POLICY RULE: DO NOT include ANY phone numbers, WhatsApp numbers, or website URLs anywhere in this section (Google automatically rejects posts with phone numbers in the text).
- Instead, invite the customer to click the 'Call Now' or 'Order Online' button below.
- 5 SEO hashtags
"""

    print("Generating Urdu SEO captions with gemini-2.5-flash...")
    text_response = client.models.generate_content(
        model="gemini-2.5-flash",
        contents=caption_prompt
    )
    raw_text = text_response.text or ""
    parts = raw_text.split("===SPLIT===")
    fb_caption = parts[0].replace("[Section 1: Facebook Page Caption]", "").strip()
    gbp_caption_raw = parts[1].replace("[Section 2: Google Business Profile Summary]", "").strip() if len(parts) > 1 else fb_caption

    gbp_caption = strip_phone_and_urls_for_gbp(gbp_caption_raw)

    with open("generated/fb_caption.txt", "w", encoding="utf-8") as f:
        f.write(fb_caption)
    with open("generated/gbp_caption.txt", "w", encoding="utf-8") as f:
        f.write(gbp_caption)

    metadata = {
        "date": today_str,
        "theme": today_theme,
        "source_bottle": str(chosen_bottle_path),
        "generated_image": str(output_img_path)
    }
    with open("generated/latest_metadata.json", "w", encoding="utf-8") as f:
        json.dump(metadata, f, ensure_ascii=False, indent=2)

    fb_page_id = os.environ.get("FB_PAGE_ID", "").strip()
    fb_token = os.environ.get("FB_PAGE_ACCESS_TOKEN", "").strip()
    if fb_page_id and fb_token:
        print(f"Publishing photo & Urdu caption to Facebook Page ({fb_page_id})...")
        fb_url = f"https://graph.facebook.com/v21.0/{fb_page_id}/photos"
        with open(output_img_path, "rb") as img_file:
            fb_res = requests.post(
                fb_url,
                data={"caption": fb_caption, "access_token": fb_token},
                files={"source": img_file},
                timeout=60
            )
        print("Facebook API Status:", fb_res.status_code, fb_res.text)
        fb_res.raise_for_status()
    else:
        print("Skipping Facebook publish (FB_PAGE_ID or FB_PAGE_ACCESS_TOKEN not set).")

if __name__ == "__main__":
    main()

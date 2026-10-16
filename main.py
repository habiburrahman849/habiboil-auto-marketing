import datetime
import os
import random
from pathlib import Path

import requests
from google import genai
from google.genai import types
from PIL import Image


# 1. Initialize Gemini Client
client = genai.Client(api_key=os.environ["GEMINI_API_KEY"])

# 2. Pick a real HabibOil bottle photo & today's theme
bottle_files = list(Path("assets/bottles").glob("*.[pj][np]g"))
chosen_bottle_path = random.choice(bottle_files)
bottle_img = Image.open(chosen_bottle_path)

THEMES = [
    "Heart health benefits of cooking with pure Kachi Ghani mustard oil on a traditional KPK kitchen counter",
    "Pure golden mustard oil bottle surrounded by fresh yellow sarson flowers in Rustam Mardan sunlight",
    "Traditional Pakistani achar (pickle) jar next to the HabibOil bottle on a rustic wooden table",
    "Winter joint relief and immunity boost with pure organic mustard oil, warm cozy lighting",
    "Crispy traditional Pakistani pakoras and parathas cooked in pure HabibOil mustard oil",
]
custom_theme = os.environ.get("CUSTOM_THEME", "").strip()
today_theme = custom_theme if custom_theme else random.choice(THEMES)

# 3. Generate Custom Product Scene with Your Real Bottle
image_prompt = (
    "Keep the exact HabibOil bottle and label from the reference image completely unchanged and sharp. "
    f"Place this exact bottle naturally into a professional commercial product photography scene: {today_theme}. "
    "Photorealistic, 8k, warm natural lighting, shallow depth of field."
)

img_response = client.models.generate_content(
    model="gemini-2.5-flash-image",
    contents=[bottle_img, image_prompt],
    config=types.GenerateContentConfig(response_modalities=["IMAGE"]),
)

today_str = datetime.date.today().isoformat()
output_img_path = f"generated/habiboil_{today_str}.png"
os.makedirs("generated", exist_ok=True)

for part in img_response.candidates[0].content.parts:
    if part.inline_data:
        with open(output_img_path, "wb") as f:
            f.write(part.inline_data.data)
        break

# 4. Generate Dual Urdu SEO Captions (Facebook vs Google Policy-Compliant)
caption_prompt = f"""
Write a highly engaging Urdu marketing post for 'HabibOil' (located in Jamia Masjid Ada, Rustam, Mardan) based on this theme: {today_theme}.
Include local SEO keywords naturally: خالص سرسوں کا تیل, Kachi Ghani Mustard Oil, HabibOil Rustam Mardan, Pure Cooking Oil.

Output EXACTLY in this format separated by ===SPLIT===:
[Part 1: Facebook Caption]
- Engaging Urdu text with emojis
- Include call to action with Phone: 0334-6328047, WhatsApp: 0304-8907756, and Website: https://habiboil.store
- 8 SEO hashtags in Urdu & English

===SPLIT===

[Part 2: Google Business Profile Summary]
- Engaging Urdu text with emojis and SEO keywords
- STRICT RULE: DO NOT include ANY phone numbers, WhatsApp numbers, or URLs in the text body (Google rejects posts with phone numbers in text).
- End by telling customers to click the button below to order or call.
- 5 SEO hashtags
"""

text_response = client.models.generate_content(model="gemini-2.5-flash", contents=caption_prompt)
parts = text_response.text.split("===SPLIT===")
fb_caption = parts[0].strip()
gbp_caption = parts[1].strip() if len(parts) > 1 else parts[0].strip()

# 5. Publish Photo + Urdu Caption to Facebook Page
fb_page_id = os.environ["FB_PAGE_ID"]
fb_token = os.environ["FB_PAGE_ACCESS_TOKEN"]
fb_url = f"https://graph.facebook.com/v21.0/{fb_page_id}/photos"

with open(output_img_path, "rb") as img_file:
    fb_res = requests.post(
        fb_url,
        data={"caption": fb_caption, "access_token": fb_token},
        files={"source": img_file},
    )
print("Facebook Publish Status:", fb_res.status_code, fb_res.text)

# 6. Save GBP caption for the workflow / webhook step
with open("generated/gbp_caption.txt", "w", encoding="utf-8") as f:
    f.write(gbp_caption)

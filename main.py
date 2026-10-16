import os
import re
import json
import random
import datetime
import requests
from pathlib import Path
from PIL import Image, ImageOps
from google import genai
from google.genai import types

def strip_phone_and_urls_for_gbp(text: str) -> str:
    """Strictly removes phone numbers and URLs for Google Business Profile compliance."""
    text = re.sub(r'https?://\S+|www\.\S+|habiboil\.store', '', text, flags=re.IGNORECASE)
    text = re.sub(r'(?:\+92|0092|0)?\s*3\d{2}[\s\-]?\d{7}', '', text)
    text = re.sub(r'\n{3,}', '\n\n', text)
    return text.strip()

def apply_logo_watermark(image_path: Path, logo_dir: Path):
    """Overlays the brand logo from assets/logo/ onto the top corner of the generated image."""
    logo_files = [p for p in logo_dir.glob("*") if p.suffix.lower() in {".png", ".jpg", ".jpeg"}]
    if not logo_files:
        print("No logo found in assets/logo/. Skipping watermark.")
        return
    
    try:
        base_img = Image.open(image_path).convert("RGBA")
        logo_img = Image.open(logo_files[0]).convert("RGBA")
        
        base_w, base_h = base_img.size
        logo_w = int(base_w * 0.18)
        aspect = logo_img.height / logo_img.width
        logo_h = int(logo_w * aspect)
        logo_img = logo_img.resize((logo_w, logo_h), Image.Resampling.LANCZOS)
        
        padding = int(base_w * 0.04)
        position = (base_w - logo_w - padding, padding)
        
        base_img.paste(logo_img, position, logo_img)
        base_img.convert("RGB").save(image_path, "PNG")
        print(f"Successfully applied logo watermark from {logo_files[0].name}")
    except Exception as e:
        print(f"Failed to apply logo watermark: {e}")

def main():
    api_key = os.environ.get("GEMINI_API_KEY")
    if not api_key:
        raise ValueError("Missing GEMINI_API_KEY environment variable. Add it in GitHub Settings -> Secrets.")

    client = genai.Client(api_key=api_key)

    bottle_dir = Path("assets/bottles")
    influencer_dir = Path("assets/influenser")
    logo_dir = Path("assets/logo")

    bottle_files = [p for p in bottle_dir.glob("*") if p.suffix.lower() in {".png", ".jpg", ".jpeg", ".webp"}]
    influencer_files = [p for p in influencer_dir.glob("*") if p.suffix.lower() in {".png", ".jpg", ".jpeg", ".webp"}]

    if not bottle_files:
        raise FileNotFoundError("No bottle images found in assets/bottles/.")

    chosen_bottle = random.choice([p for p in bottle_files if p.name != "sample_habiboil_bottle.png"] or bottle_files)
    print(f"Using bottle reference: {chosen_bottle}")
    contents = [Image.open(chosen_bottle)]

    influencer_prompt_part = ""
    if influencer_files:
        chosen_influencer = random.choice(influencer_files)
        print(f"Using influencer reference: {chosen_influencer}")
        contents.append(Image.open(chosen_influencer))
        influencer_prompt_part = "Include the person from the second reference image naturally holding or presenting the HabibOil bottle. "

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
    story_img_path = Path(f"generated/habiboil_story_{today_str}.png")

    image_prompt = (
        f"Keep the exact HabibOil bottle and label from the reference image completely intact, legible, and sharp. "
        f"{influencer_prompt_part}"
        f"Place this naturally into a professional commercial product photography scene: {today_theme}. "
        f"Photorealistic, 8k resolution, warm natural lighting, shallow depth of field, high-end food marketing aesthetic."
    )

    try:
        print("Generating standard feed image with gemini-2.5-flash-image...")
        img_response = client.models.generate_content(
            model="gemini-2.5-flash-image",
            contents=contents + [image_prompt],
            config=types.GenerateContentConfig(response_modalities=["IMAGE"])
        )
        saved = False
        for part in img_response.candidates[0].content.parts:
            if part.inline_data:
                with open(output_img_path, "wb") as f:
                    f.write(part.inline_data.data)
                saved = True
                break
        if not saved:
            Image.open(chosen_bottle).save(output_img_path)
    except Exception as e:
        print(f"Feed image generation fallback: {e}")
        Image.open(chosen_bottle).save(output_img_path)

    apply_logo_watermark(output_img_path, logo_dir)

    story_prompt = (
        f"Create a vertical 9:16 Instagram/Facebook Story promotional banner for 'HabibOil'. "
        f"Show the exact HabibOil bottle prominently in the center with background theme: {today_theme}. "
        f"Leave clean vertical space at the top and bottom for overlay text, vibrant high-converting social media aesthetic."
    )
    try:
        print("Generating vertical Story image with gemini-2.5-flash-image...")
        story_response = client.models.generate_content(
            model="gemini-2.5-flash-image",
            contents=contents + [story_prompt],
            config=types.GenerateContentConfig(response_modalities=["IMAGE"])
        )
        saved_story = False
        for part in story_response.candidates[0].content.parts:
            if part.inline_data:
                with open(story_img_path, "wb") as f:
                    f.write(part.inline_data.data)
                saved_story = True
                break
        if not saved_story:
            Image.open(output_img_path).save(story_img_path)
    except Exception as e:
        print(f"Story image generation fallback: {e}")
        Image.open(output_img_path).save(story_img_path)

    apply_logo_watermark(story_img_path, logo_dir)

    caption_prompt = f"""
You are the expert Urdu SEO Social Media Manager for 'HabibOil' (located at Jamia Masjid Ada, Rustam, Mardan, KPK, Pakistan).
Write promotional content based on theme: "{today_theme}".

Naturally weave in high-ranking local SEO keywords:
خالص سرسوں کا تیل, Kachi Ghani Mustard Oil, HabibOil Rustam Mardan, Pure Cooking Oil, Sarson Ka Tail.

Output EXACTLY three sections separated by ===SPLIT===:

[Section 1: Facebook/Instagram Feed Caption]
- Engaging Urdu copy with emojis and bullet points
- Contact details: Call 0334-6328047, WhatsApp 0304-8907756, Website https://habiboil.store, Address Rustam Mardan
- 8 SEO hashtags

===SPLIT===

[Section 2: Google Business Profile Summary]
- Engaging Urdu SEO copy (100 to 180 words)
- STRICT POLICY RULE: DO NOT include ANY phone numbers, WhatsApp numbers, or URLs in this section.
- 5 SEO hashtags

===SPLIT===

[Section 3: Story Text Overlay / Sticker Caption]
- Short, punchy Urdu text optimized for a quick Story view (e.g. "خالص سرسوں کا تیل - آج ہی آرڈر کریں! 🌿")
- Call to action sticker text and 3 short hashtags
"""

    print("Generating Urdu SEO captions with gemini-2.5-flash...")
    text_response = client.models.generate_content(
        model="gemini-2.5-flash",
        contents=caption_prompt
    )
    raw_text = text_response.text or ""
    parts = raw_text.split("===SPLIT===")
    fb_caption = parts[0].replace("[Section 1: Facebook/Instagram Feed Caption]", "").strip()
    gbp_caption_raw = parts[1].replace("[Section 2: Google Business Profile Summary]", "").strip() if len(parts) > 1 else fb_caption
    story_caption = parts[2].replace("[Section 3: Story Text Overlay / Sticker Caption]", "").strip() if len(parts) > 2 else "خالص سرسوں کا تیل - HabibOil"

    gbp_caption = strip_phone_and_urls_for_gbp(gbp_caption_raw)

    with open("generated/fb_caption.txt", "w", encoding="utf-8") as f:
        f.write(fb_caption)
    with open("generated/gbp_caption.txt", "w", encoding="utf-8") as f:
        f.write(gbp_caption)
    with open("generated/story_caption.txt", "w", encoding="utf-8") as f:
        f.write(story_caption)

    fb_page_id = os.environ.get("FB_PAGE_ID", "").strip()
    fb_token = os.environ.get("FB_PAGE_ACCESS_TOKEN", "").strip()
    if fb_page_id and fb_token:
        print(f"Publishing feed post to Facebook Page ({fb_page_id})...")
        fb_url = f"https://graph.facebook.com/v21.0/{fb_page_id}/photos"
        with open(output_img_path, "rb") as img_file:
            res = requests.post(fb_url, data={"caption": fb_caption, "access_token": fb_token}, files={"source": img_file}, timeout=60)
        print("Facebook Feed API Status:", res.status_code, res.text)

        print("Publishing Story to Facebook Page...")
        story_url = f"https://graph.facebook.com/v21.0/{fb_page_id}/photo_stories"
        with open(story_img_path, "rb") as story_file:
            story_res = requests.post(story_url, data={"access_token": fb_token}, files={"source": story_file}, timeout=60)
        print("Facebook Story API Status:", story_res.status_code, story_res.text)
    else:
        print("Skipping Facebook publishing (Credentials not set).")

if __name__ == "__main__":
    main()

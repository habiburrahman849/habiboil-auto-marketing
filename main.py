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
    Strictly removes phone numbers and website URLs from Google Business Profile
    summaries so Google's spam filter never rejects the post.
    """
    text = re.sub(r'https?://\S+|www\.\S+|habiboil\.store', '', text, flags=re.IGNORECASE)
    text = re.sub(r'(?:\+92|0092|0)?\s*3\d{2}[\s\-]?\d{7}', '', text)
    text = re.sub(r'\n{3,}', '\n\n', text)
    return text.strip()

def apply_logo_watermark(image_path: Path, logo_dir: Path):
    """
    Overlays the brand logo from assets/logo/ onto the top-right corner of the generated image.
    Prioritizes 'logo bes.png' (transparent PNG) over JPEG files.
    """
    if not logo_dir.exists():
        return
    logo_files = sorted(
        [p for p in logo_dir.glob("*") if p.suffix.lower() in {".png", ".jpg", ".jpeg"}],
        key=lambda x: (0 if "logo bes" in x.name.lower() else 1 if x.suffix.lower() == ".png" else 2)
    )
    if not logo_files:
        print("No logo found in assets/logo/. Skipping watermark.")
        return

    try:
        base_img = Image.open(image_path).convert("RGBA")
        logo_img = Image.open(logo_files[0]).convert("RGBA")

        base_w, base_h = base_img.size
        logo_w = int(base_w * 0.18)
        aspect = logo_img.height / max(logo_img.width, 1)
        logo_h = int(logo_w * aspect)
        logo_img = logo_img.resize((logo_w, logo_h), Image.Resampling.LANCZOS)

        padding = int(base_w * 0.04)
        position = (base_w - logo_w - padding, padding)

        base_img.paste(logo_img, position, logo_img)
        base_img.convert("RGB").save(image_path, "PNG")
        print(f"Applied logo watermark using: {logo_files[0].name}")
    except Exception as e:
        print(f"Logo watermark warning: {e}")

def resolve_page_access_token(token: str, page_id: str) -> str:
    """
    If the user accidentally provided a User Access Token instead of a Page Access Token,
    automatically attempts to exchange it for the target Page Access Token via /me/accounts.
    """
    try:
        res = requests.get(
            f"https://graph.facebook.com/v21.0/{page_id}",
            params={"fields": "access_token,name", "access_token": token},
            timeout=20
        )
        if res.status_code == 200 and "access_token" in res.json():
            print(f"Resolved Page Access Token for {res.json().get('name', page_id)}")
            return res.json()["access_token"]
    except Exception as e:
        print(f"Token resolution note: {e}")
    return token

def publish_to_facebook_with_first_comment(
    page_id: str,
    raw_token: str,
    feed_image_path: Path,
    story_image_path: Path,
    feed_caption: str,
    first_comment_text: str
):
    """
    1. Publishes the daily AI bottle photo + SEO Urdu caption to the Facebook Page Feed.
    2. Immediately posts the First Comment under that exact post (with website & WhatsApp links
       so Facebook's algorithm doesn't penalize organic reach for external links in the main caption!).
    3. Publishes the vertical 9:16 photo to Facebook Page Stories.
    """
    token = resolve_page_access_token(raw_token, page_id)

    # Step A: Publish Photo to Page Feed
    print(f"Publishing main photo post to Facebook Page ({page_id})...")
    feed_url = f"https://graph.facebook.com/v21.0/{page_id}/photos"
    with open(feed_image_path, "rb") as img_file:
        feed_res = requests.post(
            feed_url,
            data={"caption": feed_caption, "access_token": token},
            files={"source": img_file},
            timeout=60
        )
    print("Facebook Feed Response:", feed_res.status_code, feed_res.text)
    feed_res.raise_for_status()
    feed_data = feed_res.json()

    # Extract post_id (or photo id) to attach the First Comment
    post_target_id = feed_data.get("post_id") or feed_data.get("id")
    photo_id = feed_data.get("id")

    # Step B: First Comment Manager (Post the first comment immediately after publishing)
    if post_target_id and first_comment_text:
        print(f"Posting automatic First Comment on post ({post_target_id})...")
        comment_url = f"https://graph.facebook.com/v21.0/{post_target_id}/comments"
        comment_res = requests.post(
            comment_url,
            data={"message": first_comment_text, "access_token": token},
            timeout=30
        )
        # Fallback to photo_id if post_target_id comment endpoint requires photo node
        if comment_res.status_code != 200 and photo_id and photo_id != post_target_id:
            comment_url_fallback = f"https://graph.facebook.com/v21.0/{photo_id}/comments"
            comment_res = requests.post(
                comment_url_fallback,
                data={"message": first_comment_text, "access_token": token},
                timeout=30
            )
        print("First Comment Response:", comment_res.status_code, comment_res.text)

    # Step C: Publish Vertical Photo to Facebook Page Story
    if story_image_path.exists():
        print("Publishing vertical 9:16 Story to Facebook Page...")
        story_url = f"https://graph.facebook.com/v21.0/{page_id}/photo_stories"
        with open(story_image_path, "rb") as story_file:
            story_res = requests.post(
                story_url,
                data={"access_token": token},
                files={"source": story_file},
                timeout=60
            )
        print("Facebook Story Response:", story_res.status_code, story_res.text)

def main():
    api_key = os.environ.get("GEMINI_API_KEY", "").strip()
    if not api_key:
        raise ValueError("Missing GEMINI_API_KEY environment variable. Add it in GitHub Settings -> Secrets.")

    client = genai.Client(api_key=api_key)

    bottle_dir = Path("assets/bottles")
    influencer_dir = Path("assets/influenser")
    logo_dir = Path("assets/logo")

    bottle_files = [
        p for p in bottle_dir.glob("*")
        if p.suffix.lower() in {".png", ".jpg", ".jpeg", ".webp"}
    ]
    influencer_files = [
        p for p in influencer_dir.glob("*")
        if p.suffix.lower() in {".png", ".jpg", ".jpeg", ".webp"}
    ]

    if not bottle_files:
        raise FileNotFoundError(
            "No bottle images found in assets/bottles/. Please add your HabibOil bottle photos."
        )

    custom_bottle = os.environ.get("CUSTOM_BOTTLE_FILENAME", "").strip()
    if custom_bottle and (bottle_dir / custom_bottle).exists():
        chosen_bottle = bottle_dir / custom_bottle
    else:
        real_bottles = [p for p in bottle_files if "sample_" not in p.name.lower()]
        chosen_bottle = random.choice(real_bottles) if real_bottles else bottle_files[0]

    print(f"Selected Bottle Image: {chosen_bottle}")
    contents = [Image.open(chosen_bottle)]

    use_influencer_env = os.environ.get("USE_INFLUENCER", "auto").strip().lower()
    influencer_prompt_part = ""
    if influencer_files and use_influencer_env != "false":
        chosen_influencer = random.choice(influencer_files)
        print(f"Selected Influencer Reference: {chosen_influencer}")
        contents.append(Image.open(chosen_influencer))
        influencer_prompt_part = (
            "Include the person from the second reference image naturally holding or presenting "
            "this exact HabibOil bottle with a warm, trustworthy expression. "
        )

    THEMES = [
        "Heart health & cholesterol control benefits of cooking with pure Kachi Ghani mustard oil on a traditional KPK kitchen counter",
        "Pure golden mustard oil bottle surrounded by fresh yellow sarson (mustard) flowers in Rustam Mardan morning sunlight",
        "Traditional Pakistani achar (pickle) glass jar and whole spices next to the HabibOil bottle on a rustic wooden table",
        "Winter joint relief, massage, and strong family immunity with pure organic mustard oil in warm golden sunlight",
        "Crispy traditional Pakistani pakoras and parathas cooked in pure HabibOil mustard oil, appetizing food photography",
        "Natural hair growth and glowing skin care benefits of pure cold-pressed sarson ka tail, clean botanical setting",
        "Direct from Rustam Mardan kolhu (mill) to your home: 100% chemical-free, unrefined pure mustard oil"
    ]
    custom_theme = os.environ.get("CUSTOM_THEME", "").strip()
    today_theme = custom_theme if custom_theme else random.choice(THEMES)
    print(f"Today's Marketing Theme: {today_theme}")

    today_str = datetime.date.today().isoformat()
    os.makedirs("generated", exist_ok=True)
    output_img_path = Path(f"generated/habiboil_{today_str}.png")
    story_img_path = Path(f"generated/habiboil_story_{today_str}.png")

    # 1. Generate Main Feed Image
    image_prompt = (
        f"Keep the exact HabibOil bottle, yellow cap, and green label from the first reference image completely intact, legible, and sharp. "
        f"{influencer_prompt_part}"
        f"Place this naturally into a professional commercial product photography scene: {today_theme}. "
        f"Photorealistic, 8k resolution, warm natural lighting, shallow depth of field, high-end food marketing aesthetic."
    )

    try:
        print("Generating Feed Image with gemini-2.5-flash-image...")
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
        print(f"Feed image generation fallback triggered: {e}")
        Image.open(chosen_bottle).save(output_img_path)

    apply_logo_watermark(output_img_path, logo_dir)

    # 2. Generate Vertical 9:16 Story Image
    story_prompt = (
        f"Create a vertical 9:16 Facebook/Instagram Story promotional poster for 'HabibOil'. "
        f"Keep the exact HabibOil bottle and green label sharp and centered with background scene: {today_theme}. "
        f"Leave clean composition space at the top and bottom, vibrant commercial lighting."
    )
    try:
        print("Generating Vertical 9:16 Story Image with gemini-2.5-flash-image...")
        story_response = client.models.generate_content(
            model="gemini-2.5-flash-image",
            contents=[Image.open(chosen_bottle), story_prompt],
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
        print(f"Story image fallback triggered: {e}")
        Image.open(output_img_path).save(story_img_path)

    apply_logo_watermark(story_img_path, logo_dir)

    # 3. Generate SEO Urdu Captions + Automatic First Comment
    caption_prompt = f"""
You are the expert Urdu Local SEO Social Media Manager for 'HabibOil' (located at Jamia Masjid Ada, Rustam, Mardan, KPK, Pakistan).
Bottle featured today: "{chosen_bottle.stem}"
Today's marketing theme: "{today_theme}"

Naturally weave in high-ranking local SEO keywords:
خالص سرسوں کا تیل, کچی گھانی سرسوں کا تیل, Kachi Ghani Mustard Oil, HabibOil Rustam Mardan, Pure Cooking Oil, Sarson Ka Tail.

Output EXACTLY FOUR sections separated by ===SPLIT===:

[Section 1: Facebook Feed Caption]
- High-converting, emotional and benefit-driven Urdu copy with emojis and bullet points.
- PRO FACEBOOK SEO TIP: Do NOT put raw https:// links in this main caption (we put links in the First Comment so Facebook's algorithm gives maximum organic reach!).
- End the caption with: "👇 آرڈر کرنے، قیمت جاننے اور ہوم ڈیلیوری کے لیے پہلا کمنٹ (First Comment) چیک کریں!"
- Include 8 high-ranking Urdu & English SEO hashtags.

===SPLIT===

[Section 2: Facebook First Comment (Auto-Comment)]
- Write a pinned-style First Comment in Urdu & English that gives instant ordering links and sizes available (250g, 500ml, 1 Liter, 5 Liter):
  🛒 ابھی آن لائن آرڈر کریں (Website): https://habiboil.store
  💬 واٹس ایپ پر آرڈر کریں (WhatsApp): https://wa.me/923048907756 (0304-8907756)
  📞 ڈائریکٹ کال: 0334-6328047
  📍 پتہ: جامع مسجد اڈہ، رستم، مردان (Jamia Masjid Ada, Rustam, Mardan)
  ✨ 100% خالص کچی گھانی سرسوں کا تیل — پورے پاکستان میں ہوم ڈیلیوری دستیاب ہے!

===SPLIT===

[Section 3: Google Business Profile Summary]
- Engaging Urdu SEO copy (100 to 160 words) highlighting HabibOil Rustam Mardan and pure mustard oil benefits.
- STRICT GOOGLE POLICY RULE: DO NOT include ANY phone numbers, WhatsApp numbers, or website URLs anywhere in this section.
- 5 local SEO hashtags.

===SPLIT===

[Section 4: Story Caption]
- Short, punchy 2-line Urdu hook for Stories with 3 hashtags.
"""

    print("Generating Urdu SEO Captions & First Comment with gemini-2.5-flash...")
    text_response = client.models.generate_content(
        model="gemini-2.5-flash",
        contents=caption_prompt
    )
    raw_text = text_response.text or ""
    parts = [p.strip() for p in raw_text.split("===SPLIT===")]

    fb_caption = parts[0].replace("[Section 1: Facebook Feed Caption]", "").strip() if len(parts) > 0 else ""
    first_comment = parts[1].replace("[Section 2: Facebook First Comment (Auto-Comment)]", "").strip() if len(parts) > 1 else (
        "🛒 ابھی آن لائن آرڈر کریں: https://habiboil.store\n"
        "💬 واٹس ایپ: https://wa.me/923048907756 (0304-8907756)\n"
        "📞 کال: 0334-6328047\n"
        "📍 جامع مسجد اڈہ، رستم، مردان"
    )
    gbp_caption_raw = parts[2].replace("[Section 3: Google Business Profile Summary]", "").strip() if len(parts) > 2 else fb_caption
    story_caption = parts[3].replace("[Section 4: Story Caption]", "").strip() if len(parts) > 3 else "خالص سرسوں کا تیل - HabibOil Rustam Mardan"

    gbp_caption = strip_phone_and_urls_for_gbp(gbp_caption_raw)

    # Save all generated text artifacts
    with open("generated/fb_caption.txt", "w", encoding="utf-8") as f:
        f.write(fb_caption)
    with open("generated/fb_first_comment.txt", "w", encoding="utf-8") as f:
        f.write(first_comment)
    with open("generated/gbp_caption.txt", "w", encoding="utf-8") as f:
        f.write(gbp_caption)
    with open("generated/story_caption.txt", "w", encoding="utf-8") as f:
        f.write(story_caption)

    metadata = {
        "date": today_str,
        "theme": today_theme,
        "bottle_used": chosen_bottle.name,
        "feed_image": str(output_img_path),
        "story_image": str(story_img_path)
    }
    with open("generated/latest_metadata.json", "w", encoding="utf-8") as f:
        json.dump(metadata, f, ensure_ascii=False, indent=2)

    # 4. Publish to Facebook Page + Auto First Comment + Story
    fb_page_id = os.environ.get("FB_PAGE_ID", "61578353751886").strip()
    fb_token = os.environ.get("FB_PAGE_ACCESS_TOKEN", "").strip()
    if fb_page_id and fb_token:
        publish_to_facebook_with_first_comment(
            page_id=fb_page_id,
            raw_token=fb_token,
            feed_image_path=output_img_path,
            story_image_path=story_img_path,
            feed_caption=fb_caption,
            first_comment_text=first_comment
        )
    else:
        print("Skipping live Facebook publish (FB_PAGE_ACCESS_TOKEN not set).")

if __name__ == "__main__":
    main()

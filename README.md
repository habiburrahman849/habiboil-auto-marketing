# HabibOil Auto-Marketing (`habiboil-auto-marketing`)

Automated daily AI product photography and Urdu Local SEO publisher for **HabibOil** (Jamia Masjid Ada, Rustam, Mardan).

## Folder Structure
- `.github/workflows/daily_post.yml` — Runs daily at 10:00 AM PKT (`05:00 UTC`) + manual trigger
- `assets/bottles/` — Upload your real 1L, 5L HabibOil bottle photos here
- `generated/` — Stores daily AI-generated photos and Urdu captions
- `main.py` — Gemini image + Urdu SEO generator & Facebook Page publisher
- `publish_gbp.py` — Google Business Profile publisher (Webhook or OAuth)
- `requirements.txt` — Python dependencies

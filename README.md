# HabibOil Daily AI Marketing Autopilot (`habiboil-auto-marketing`)

Complete GitHub Actions automation for **HabibOil** (Jamia Masjid Ada, Rustam, Mardan).

## Key Features
1. **Real Bottle + Influencer Blending (`gemini-2.5-flash-image`):**
   - Automatically selects your real bottle photos (`1 liter`, `5 liter`, `500ML`, `250 gram`) from `assets/bottles/` and blends them with your influencer photo (`assets/influenser/me.jpg`).
2. **Automatic Transparent Logo Watermark:**
   - Stamps `assets/logo/logo bes.png` onto the top-right corner of every generated Feed and Story image.
3. **Pro Facebook Reach Optimization (Caption + Automatic First Comment Manager):**
   - **Main Post Caption:** High-converting Urdu SEO copy without external links (so Facebook's algorithm gives you maximum organic reach) and a callout pointing to the First Comment.
   - **Automatic First Comment:** Immediately after publishing the photo, the bot comments on its own post with your clickable ordering link WhatsApp link (`https://wa.me/923048907756`), phone number , and available bottle sizes.
4. **Automatic Facebook Page Story Uploader:**
   - Generates a vertical 9:16 Story banner and publishes it to `/photo_stories`.

## Full Folder Structure
```text
habiboil-auto-marketing/
├── .github/
│   └── workflows/
│       └── daily_post.yml                  # Runs daily at 10:00 AM PKT + manual trigger
├── assets/
│   ├── bottles/                            # Place your 1L, 5L, 500ML, 250g bottle PNGs here
│   ├── influenser/                         # Place me.jpg or model photos here
│   └── logo/                               # Place logo bes.png here
├── generated/                              # Stores daily generated images & Urdu captions
├── .gitignore
├── main.py                                 # Unified AI Generator + FB Post + First Comment + Story Manager
├── publish_gbp.py                          # Optional Google Business Profile publisher
├── requirements.txt                        # Python packages
└── README.md
```

import os
import datetime
import requests

def publish_via_webhook(webhook_url: str, image_url: str, summary: str):
    print("Sending post payload to Google Business Profile Webhook...")
    payload = {
        "location_name": "locations/2767179596888125758",
        "business_title": "HabibOil",
        "image_url": image_url,
        "summary": summary,
        "action_type": "CALL",
        "website_url": "https://habiboil.store"
    }
    res = requests.post(webhook_url, json=payload, timeout=30)
    print("Webhook Status:", res.status_code, res.text)
    res.raise_for_status()

def publish_via_google_oauth(client_id: str, client_secret: str, refresh_token: str, account_id: str, location_id: str, image_url: str, summary: str):
    print("Authenticating directly with Google OAuth 2.0...")
    token_res = requests.post(
        "https://oauth2.googleapis.com/token",
        data={
            "client_id": client_id,
            "client_secret": client_secret,
            "refresh_token": refresh_token,
            "grant_type": "refresh_token",
        },
        timeout=30
    )
    token_res.raise_for_status()
    access_token = token_res.json()["access_token"]

    gbp_endpoint = f"https://mybusiness.googleapis.com/v4/accounts/{account_id}/locations/{location_id}/localPosts"
    post_body = {
        "languageCode": "ur",
        "summary": summary,
        "topicType": "STANDARD",
        "callToAction": {
            "actionType": "CALL"
        },
        "media": [
            {
                "mediaFormat": "PHOTO",
                "sourceUrl": image_url
            }
        ]
    }
    headers = {
        "Authorization": f"Bearer {access_token}",
        "Content-Type": "application/json"
    }
    res = requests.post(gbp_endpoint, headers=headers, json=post_body, timeout=30)
    print("Google Business Profile API Status:", res.status_code, res.text)
    res.raise_for_status()

def main():
    today_str = datetime.date.today().isoformat()
    repo = os.environ.get("GITHUB_REPOSITORY", "habiburrahman849/habiboil-auto-marketing")
    branch = os.environ.get("GITHUB_REF_NAME", "main")
    raw_img_url = f"https://raw.githubusercontent.com/{repo}/{branch}/generated/habiboil_{today_str}.png"

    with open("generated/gbp_caption.txt", "r", encoding="utf-8") as f:
        summary = f.read().strip()

    print(f"Public Image URL for GBP: {raw_img_url}")

    webhook_url = os.environ.get("GBP_WEBHOOK_URL", "").strip()
    if webhook_url:
        publish_via_webhook(webhook_url, raw_img_url, summary)
        return

    client_id = os.environ.get("GBP_CLIENT_ID", "").strip()
    client_secret = os.environ.get("GBP_CLIENT_SECRET", "").strip()
    refresh_token = os.environ.get("GBP_REFRESH_TOKEN", "").strip()
    account_id = os.environ.get("GBP_ACCOUNT_ID", "").strip()
    location_id = os.environ.get("GBP_LOCATION_ID", "2767179596888125758").strip()

    if client_id and client_secret and refresh_token and account_id:
        publish_via_google_oauth(
            client_id, client_secret, refresh_token,
            account_id, location_id, raw_img_url, summary
        )
    else:
        print("Notice: Neither GBP_WEBHOOK_URL nor GBP OAuth credentials were set. Caption and image are saved in generated/.")

if __name__ == "__main__":
    main()

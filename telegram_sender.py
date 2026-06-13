import os
import requests
import html
from dotenv import load_dotenv

# Load environment variables
load_dotenv(override=True)

def send_telegram_alert(platform, title, company, deadline, eligibility, summary, link):
    """
    Sends a beautifully formatted HTML alert to the configured Telegram channel.
    """
    token = os.getenv("TELEGRAM_BOT_TOKEN")
    channel_id = os.getenv("TELEGRAM_CHANNEL_ID")
    
    if not token or not channel_id or token == "your_telegram_bot_token_here" or channel_id == "your_telegram_channel_or_chat_id_here":
        print(f"[Telegram Alert] Warning: Credentials not set. Logging message local-only:")
        print(f"  [{platform}] {title} by {company} - Link: {link}")
        return False

    # Escape dynamic fields to prevent HTML parsing errors on Telegram
    safe_title = html.escape(str(title))
    safe_company = html.escape(str(company))
    safe_platform = html.escape(str(platform))
    safe_deadline = html.escape(str(deadline))
    safe_eligibility = html.escape(str(eligibility))
    safe_summary = html.escape(str(summary))
    safe_link = html.escape(str(link))

    # Construct the message payload in HTML
    message = (
        f"🔔 <b>New Opportunity Found!</b>\n\n"
        f"🚀 <b>Title:</b> {safe_title}\n"
        f"🏢 <b>Company:</b> {safe_company}\n"
        f"🌐 <b>Platform:</b> {safe_platform}\n"
        f"⏳ <b>Deadline:</b> {safe_deadline}\n"
        f"🎓 <b>Eligibility:</b> {safe_eligibility}\n\n"
        f"📝 <b>Summary:</b>\n<i>{safe_summary}</i>\n\n"
        f"🔗 <a href='{safe_link}'>Click here to Apply</a>\n"
        f"───────────────────"
    )

    url = f"https://api.telegram.org/bot{token}/sendMessage"
    payload = {
        "chat_id": channel_id,
        "text": message,
        "parse_mode": "HTML",
        "disable_web_page_preview": False
    }

    try:
        response = requests.post(url, json=payload, timeout=10)
        data = response.json()
        if response.status_code == 200 and data.get("ok"):
            print(f"[Telegram Alert] Notification sent successfully for: {title}")
            return True
        else:
            print(f"[Telegram Alert] Failed to send message. Telegram response: {data}")
            return False
    except Exception as e:
        print(f"[Telegram Alert] Error sending alert to Telegram: {e}")
        return False

if __name__ == "__main__":
    # Local quick test
    print("Running Telegram sender test...")
    send_telegram_alert(
        platform="TestPlatform",
        title="Software Engineer Intern",
        company="Google",
        deadline="June 30, 2026",
        eligibility="Open to all pre-final year students",
        summary="Work on highly scalable search index pipelines using Go/Python. Collaborate with core engineering teams.",
        link="https://google.com/careers"
    )

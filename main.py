import os
import json
import time
from scraper import scrape_all
from gemini_filter import evaluate_opportunity, evaluate_opportunities_batch
from telegram_sender import send_telegram_alert
from dotenv import load_dotenv

# Load environment variables
load_dotenv(override=True)

DB_FILE = "notified_opportunities.json"

def load_processed_ids():
    """Loads already processed opportunity IDs from database."""
    if not os.path.exists(DB_FILE):
        return set()
    try:
        with open(DB_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
            return set(data.get("processed_ids", []))
    except Exception as e:
        print(f"[Orchestrator] Error loading database: {e}")
        return set()

def save_processed_ids(processed_ids):
    """Saves processed opportunity IDs to database."""
    try:
        with open(DB_FILE, "w", encoding="utf-8") as f:
            json.dump({"processed_ids": sorted(list(processed_ids))}, f, indent=2)
        print(f"[Orchestrator] Saved {len(processed_ids)} processed IDs to database.")
    except Exception as e:
        print(f"[Orchestrator] Error saving database: {e}")

def main():
    print("[Orchestrator] HackAlert Bot Starting...")
    
    # 1. Load database
    processed_ids = load_processed_ids()
    is_first_run = len(processed_ids) == 0
    print(f"[Orchestrator] Loaded {len(processed_ids)} processed IDs.")
    
    # 2. Scrape opportunities
    opportunities = scrape_all()
    
    if is_first_run:
        print("\n[Orchestrator] [Cold Start Detection]")
        print("[Orchestrator] This is the first run of the bot. Seeding database silently to prevent spamming the channel...")
        for opp in opportunities:
            processed_ids.add(opp["id"])
        save_processed_ids(processed_ids)
        print("[Orchestrator] Seeding complete. Subsequent runs will monitor and alert for new listings.")
        return
        
    # 3. Filter for new opportunities
    new_opportunities = [o for o in opportunities if o["id"] not in processed_ids]
    print(f"\n[Orchestrator] Found {len(new_opportunities)} new opportunities to process.")
    
    # Limit number of AI evaluations per run to prevent rate limits
    MAX_EVALUATIONS = 30
    if len(new_opportunities) > MAX_EVALUATIONS:
        print(f"[Orchestrator] Warning: Too many new opportunities ({len(new_opportunities)}). Limiting to first {MAX_EVALUATIONS} to avoid rate limits.")
        new_opportunities = new_opportunities[:MAX_EVALUATIONS]
        
    # 4. Evaluate with Gemini in batches and alert if it matches
    BATCH_SIZE = 10
    for i in range(0, len(new_opportunities), BATCH_SIZE):
        batch = new_opportunities[i:i+BATCH_SIZE]
        print(f"\n[Orchestrator] Evaluating batch of {len(batch)} opportunities (items {i+1} to {i+len(batch)})...")
        
        # Call Gemini AI batch filter
        batch_evaluations = evaluate_opportunities_batch(batch)
        
        # Process results
        for opp, evaluation in zip(batch, batch_evaluations):
            # If the evaluation of the whole batch or this item failed, fallback to sequential evaluation for this item
            if not evaluation.get("success", True):
                print(f"  [Orchestrator] Batch evaluation failed for '{opp['title']}'. Falling back to sequential evaluation...")
                evaluation = evaluate_opportunity(opp["platform"], opp["title"], opp["raw_context"])
                
                # If sequential fallback also failed, skip this item (retry on next run)
                if not evaluation.get("success", True):
                    print(f"  [SKIPPED] Sequential fallback evaluation also failed. Will retry on next run.")
                    continue
            
            # Determine if we are running in local-only mode (credentials not configured)
            token = os.getenv("TELEGRAM_BOT_TOKEN")
            channel_id = os.getenv("TELEGRAM_CHANNEL_ID")
            is_local_only = (
                not token 
                or not channel_id 
                or token == "your_telegram_bot_token_here" 
                or channel_id == "your_telegram_channel_or_chat_id_here"
            )
            
            if evaluation.get("is_match"):
                print(f"  [MATCH FOUND] Title: {opp['title']} | Reason: {evaluation.get('reason')}")
                # Send alert to Telegram
                alert_sent = send_telegram_alert(
                    platform=opp["platform"],
                    title=evaluation.get("title", opp["title"]),
                    company=evaluation.get("company", "N/A"),
                    deadline=evaluation.get("deadline", "N/A"),
                    eligibility=evaluation.get("eligibility", "Open to all"),
                    summary=evaluation.get("summary", "No summary provided."),
                    key_requirements=evaluation.get("key_requirements", "N/A"),
                    benefits=evaluation.get("benefits", "N/A"),
                    event_mode=evaluation.get("event_mode", "Online"),
                    link=opp["link"]
                )
                if alert_sent or is_local_only:
                    processed_ids.add(opp["id"])
                    if alert_sent:
                        # Sleep to avoid hitting Telegram spam limits
                        time.sleep(2.5)
                else:
                    print(f"  [FAILED] Telegram alert failed to send due to network issue. Will retry on next run.")
            else:
                print(f"  [NO MATCH] Title: {opp['title']} | Reason: {evaluation.get('reason')}")
                processed_ids.add(opp["id"])
            
    # 5. Save updated state
    save_processed_ids(processed_ids)
    print("\n[Orchestrator] HackAlert Bot execution finished successfully!")

if __name__ == "__main__":
    main()

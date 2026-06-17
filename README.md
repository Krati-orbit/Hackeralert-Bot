# HackAlert Bot 🔔

An AI-powered automated opportunity aggregator that monitors online developer platforms, filters listings against a custom student profile using Gemini AI, and broadcasts matches to a Telegram channel in real-time.

---

## 🌟 Key Features

* **Multi-Platform Scrapers:** Scrapes active hackathons, coding contests, and internships from:
  * **Devfolio** (API scraper)
  * **Unstop** (API scraper)
  * **Internshala** (BeautifulSoup HTML parser)
  * **HackerEarth** (Headless Playwright browser runner with resource-block optimizations)
* **High-Speed Execution:** Runs all scraping workers concurrently using a Python Thread Pool.
* **Smart AI Filtering:** Uses the Google Gemini (`gemini-2.5-flash`) model to evaluate each opportunity's relevance against a customizable student profile in batches.
* **Resilient Architecture:** Automatically degrades from batch API calls to single-opportunity analysis on failure, and incorporates exponential backoff for handling Gemini API rate limits (HTTP 429).
* **Beautiful Alerts:** Automatically formats matching opportunities into rich HTML Telegram cards and publishes them directly to your Telegram channel.
* **Silent Seeding (Cold Start):** Protects your Telegram channel from alert floods by seeding existing listings silently during the initial run.

---

## 📐 System Architecture

To understand how the components interact and how data flows, check out the following resources:
- **[ARCHITECTURE.md](file:///d:/New%20project%20-%20Bot/ARCHITECTURE.md):** Detailed guide of the component design, data flow, and architecture diagram.
- **[diagram.mermaid](file:///d:/New%20project%20-%20Bot/diagram.mermaid):** The raw Mermaid source code representing the system diagram.


---

## 🚀 Getting Started

### 1. Prerequisites
- Python 3.9 or higher
- [Playwright browser binaries](https://playwright.dev/python/) (automatically set up during installation)

### 2. Installation
Clone this repository and install the dependencies:
```bash
# Install required Python packages
pip install -r requirements.txt

# Install Playwright browser dependencies (required for HackerEarth)
playwright install chromium
```

### 3. Configuration
Copy the `.env.example` file to `.env` and fill in your custom configurations:
```bash
cp .env.example .env
```

Open `.env` and configure the following variables:
- `GEMINI_API_KEY`: Your Google Gemini API Key.
- `TELEGRAM_BOT_TOKEN`: The API token from your Telegram Bot (via BotFather).
- `TELEGRAM_CHANNEL_ID`: Your channel handle (e.g. `@my_alerts_channel`) or numeric Chat ID.
- `STUDENT_PROFILE`: A description of what types of opportunities the bot should filter in (e.g. *"Undergraduate Computer Science student in India interested in software engineering, AI/ML, web development..."*).

> **Note:** If you do not configure Telegram credentials, the bot will run in **local-only mode**, logging alerts directly to the console instead of sending them to Telegram.

---

## 🛠️ Usage

Simply run the main orchestrator script to check for new listings:
```bash
python main.py
```

### Automation (Cron / Task Scheduler)
To run the bot continuously (e.g., every 3 hours), you can schedule it using your operating system's scheduler:
- **Linux/macOS (Cron):**
  ```bash
  0 */3 * * * cd /path/to/project && /path/to/venv/bin/python main.py >> bot.log 2>&1
  ```
- **Windows (Task Scheduler):** Create a basic task that runs `python.exe` with `main.py` as an argument and the project folder as the starting directory.

---

## 📁 File Structure

```text
├── main.py                     # Orchestrator: manages state, loops and triggers filters/alerts
├── scraper.py                  # Scraper engine: concurrently queries platform APIs and HTML
├── gemini_filter.py            # AI logic: queries Gemini 2.5 Flash with batch & fallback logic
├── telegram_sender.py          # Alert sender: formats HTML cards and posts via Telegram Bot API
├── notified_opportunities.json # Local database storing already processed listing IDs
├── ARCHITECTURE.md             # Detailed engineering and component diagrams
├── README.md                   # This file: general guide and setup walkthrough
├── .env                        # Local configurations (ignored by git)
└── requirements.txt            # Python dependencies list
```

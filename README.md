# Scholarship Scraper - System Documentation

## Overview

This is an automated **multi-source scholarship aggregation system** that continuously scrapes the internet for scholarship opportunities and stores them in a centralized database. The system runs 24/7 on a cloud server and presents the data via a React frontend.

---

## Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                        CLOUD SERVER (VPS)                       │
│                      64.23.231.89 (DigitalOcean)                │
├─────────────────────────────────────────────────────────────────┤
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐              │
│  │   FastAPI   │  │   Celery    │  │   Celery    │              │
│  │   (Web)     │  │   (Worker)  │  │   (Beat)    │              │
│  │   :8000     │  │   Tasks     │  │   Scheduler │              │
│  └──────┬──────┘  └──────┬──────┘  └──────┬──────┘              │
│         │                │                │                     │
│         └────────────────┼────────────────┘                     │
│                          │                                      │
│                   ┌──────┴──────┐                               │
│                   │   Redis     │                               │
│                   │   (Queue)   │                               │
│                   └─────────────┘                               │
│                          │                                      │
│                   ┌──────┴──────┐                               │
│                   │   SQLite    │                               │
│                   │   (Database)│                               │
│                   └─────────────┘                               │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│                    LOCAL MACHINE (Optional)                     │
├─────────────────────────────────────────────────────────────────┤
│  ┌─────────────────────────────────────────────────────────┐    │
│  │   local_agent.py                                        │    │
│  │   - Runs Instagram scraper using Home IP (Residential)  │    │
│  │   - Syncs results to Cloud API                          │    │
│  └─────────────────────────────────────────────────────────┘    │
└─────────────────────────────────────────────────────────────────┘
```

---

## Components

### 1. Backend API (`scholarship_scraper/app/`)

| File | Purpose |
|------|---------|
| `main.py` | FastAPI application with REST endpoints |
| `models.py` | SQLAlchemy database models (ScholarshipModel) |
| `database.py` | Database connection and session management |
| `tasks.py` | Celery task definitions and scheduler configuration |

**API Endpoints:**
- `GET /` - Health check
- `GET /scholarships/` - List all scholarships (with pagination)
- `POST /scholarships/` - Create new scholarship (for external sync)
- `POST /scrape/general` - Trigger web directory scrape
- `POST /scrape/reddit` - Trigger Reddit scrape
- `POST /scrape/instagram` - Trigger Instagram scrape
- `POST /enrich` - Trigger deep research on existing scholarships

---

### 2. Scrapers (`scholarship_scraper/scrapers/`)

| File | Source | Method |
|------|--------|--------|
| `general_search.py` | DuckDuckGo, Bing, Direct Directories | Playwright browser automation |
| `reddit.py` | Reddit (via 10+ mirror sites) | Playwright with mirror rotation |
| `instagram.py` | Instagram #scholarships | Instaloader library |

**Direct Directory Sources (Fallback):**
- Unigo.com
- Scholarships.com
- CareerOneStop.org
- Niche.com
- StudentScholarships.org
- BigFuture.CollegeBoard.org
- Cappex.com
- Petersons.com

---

### 3. Processors (`scholarship_scraper/processors/`)

| File | Purpose |
|------|---------|
| `content_analyzer.py` | Calculates relevance score, extracts amounts |
| `enrichment.py` | Deep research: visits URLs to extract deadlines, amounts |

---

### 4. Frontend (`scholarship-frontend/`)

React application displaying the scholarship database.
- Runs on `localhost:5173` during development
- Fetches from `http://64.23.231.89:8000/scholarships/`

---

## Scheduled Tasks

| Task | Frequency | Description |
|------|-----------|-------------|
| `run_general_scrape` | Every 5 mins | Searches web directories for new scholarships |
| `run_reddit_scrape` | Every 5 mins | Scrapes 5 subreddits for scholarship links |
| `run_enrichment_task` | Every 10 mins | Deep researches existing entries for deadlines/amounts |
| `run_instagram_scrape` | Every hour | Attempts Instagram (often blocked on cloud) |

---

## Important Files

| File | Description |
|------|-------------|
| `deploy_vps.py` | Deploys code to cloud server via SSH |
| `check_logs.py` | Views worker logs from cloud server |
| `local_agent.py` | Runs Instagram locally to bypass IP blocks |
| `docker-compose.yml` | Container orchestration for production |
| `requirements.txt` | Python dependencies |

---

## Credentials & Environment Variables

Stored in `.env` on the server:

```
INSTAGRAM_USERNAME=parthzanwar112@gmail.com
INSTAGRAM_PASSWORD=Parthtanish00!
DATABASE_URL=sqlite:///./scholarships.db
REDIS_URL=redis://redis:6379/0
```

---

## Known Limitations

1. **Instagram Blocked**: Cloud server IPs are blacklisted by Instagram. Use `local_agent.py` from home network as workaround.

2. **Reddit Mirrors Unreliable**: Most Libreddit/Redlib mirrors are down or blocking. System falls back to curated list.

3. **Search Engine Timeouts**: DuckDuckGo and Bing sometimes block automated queries. System falls back to direct site scraping.

---

## How to Deploy Updates

1. Make changes locally
2. Commit and push to GitHub:
   ```bash
   git add . && git commit -m "Your message" && git push origin main
   ```
3. Run the deployment script:
   ```bash
   ./venv/bin/python deploy_vps.py
   ```

---

## How to Run Locally (For Development)

```bash
# Backend
cd scholarship_scraper
./venv/bin/pip install -r requirements.txt
./venv/bin/uvicorn scholarship_scraper.app.main:app --reload

# Frontend
cd scholarship-frontend
npm install
npm run dev
```

---

## Statistics (As of Last Check)

- **Total Scholarships in Database:** 46
- **Sources Active:** General Search, Reddit (Fallback), Enrichment
- **Sources Blocked:** Instagram (Requires Local Agent)

---

## Contact / Repository

- **GitHub:** https://github.com/ParthZanwar01/scholarship-scraper
- **Server IP:** 64.23.231.89
- **Server Password:** (See deploy_vps.py)

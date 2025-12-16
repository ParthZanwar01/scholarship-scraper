from celery import Celery
from celery.schedules import crontab
import os
from .database import SessionLocal
from .models import ScholarshipModel
from scholarship_scraper.scrapers.general_search import GeneralSearchScraper
from scholarship_scraper.scrapers.instagram import InstagramScraper
from scholarship_scraper.processors.content_analyzer import ContentAnalyzer
from datetime import datetime

# Redis URL from env or localhost
REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379/0")

celery_app = Celery("scholarship_tasks", broker=REDIS_URL, backend=REDIS_URL)

celery_app.conf.beat_schedule = {
    "scrape-general-5min": {
        "task": "scholarship_scraper.app.tasks.run_general_scrape",
        "schedule": crontab(minute="*/5"),
        "options": {"expires": 290} # Expire if queue is backed up
    },
    "scrape-reddit-5min": {
        "task": "scholarship_scraper.app.tasks.run_reddit_scrape",
        "schedule": crontab(minute="*/5"),
        "options": {"expires": 290}
    },
    # Deep Research / Enrichment Task (Every 10 mins)
    "enrich-scholarships-10min": {
        "task": "scholarship_scraper.app.tasks.run_enrichment_task",
        "schedule": crontab(minute="*/10"),
    },
    # Keep Instagram less frequent as it is fragile/security-heavy
    "scrape-instagram-hourly": {
        "task": "scholarship_scraper.app.tasks.run_instagram_scrape",
        "schedule": crontab(minute=15, hour="*/1"),
    },
    # TikTok Video Scraper (Every 30 mins - heavy due to transcription)
    "scrape-tiktok-30min": {
        "task": "scholarship_scraper.app.tasks.run_tiktok_scrape",
        "schedule": crontab(minute="*/30"),
        "options": {"expires": 1740}  # 29 min expiry
    },
    # RSS Feed Scraper (Every 15 mins - reliable and lightweight)
    "scrape-rss-15min": {
        "task": "scholarship_scraper.app.tasks.run_rss_scrape",
        "schedule": crontab(minute="*/15"),
    },
    # Tor-based Social Scraper (Every 20 mins - uses Tor for IP rotation)
    "scrape-tor-social-20min": {
        "task": "scholarship_scraper.app.tasks.run_tor_social_scrape",
        "schedule": crontab(minute="*/20"),
        "options": {"expires": 1140}  # 19 min expiry
    },
}


analyzer = ContentAnalyzer()

def save_scholarship_to_db(scholarship_obj):
    db = SessionLocal()
    try:
        # Check if exists
        exists = db.query(ScholarshipModel).filter(ScholarshipModel.source_url == scholarship_obj.source_url).first()
        if not exists:
            # Analyze
            relevance = analyzer.calculate_relevance_score(scholarship_obj.description or "")
            if relevance <= 0:
                print(f"Skipping low relevance item: {scholarship_obj.title}")
                return False

            extracted_amount = analyzer.extract_amount(scholarship_obj.description or "")
            
            db_item = ScholarshipModel(
                title=scholarship_obj.title,
                source_url=scholarship_obj.source_url,
                description=scholarship_obj.description,
                amount=extracted_amount or scholarship_obj.amount, # Prefer extracted if original is null
                deadline=scholarship_obj.deadline,
                platform=scholarship_obj.platform,
                raw_text=scholarship_obj.description # Reuse description for raw text for now
            )
            db.add(db_item)
            db.commit()
            return True
        return False
    except Exception as e:
        print(f"DB Error: {e}")
        db.rollback()
        return False
    finally:
        db.close()

@celery_app.task
def run_general_scrape(query=None, limit=10):
    import random
    
    # Diverse query pool
    queries = [
        "scholarships 2025",
        "engineering scholarships",
        "nursing scholarships",
        "scholarships for women",
        "minority scholarships",
        "financial aid grants",
        "computer science scholarships",
        "scholarships for high school seniors",
        "undergraduate scholarships",
        # Social Media X-Ray Queries
        'site:linkedin.com/jobs "scholarship application"',
        'site:tiktok.com "scholarship deadline"',
        'site:facebook.com "scholarship opportunity"',
        'site:instagram.com "scholarship link in bio"'
    ]
    
    if not query:
        query = random.choice(queries)
        
    print(f"Starting General Scrape: {query}")
    scraper = GeneralSearchScraper(headless=True)
    results = scraper.search_duckduckgo(query, num_results=limit)
    
    count = 0
    for item in results:
        if save_scholarship_to_db(item):
            count += 1
    
    return f"General Scrape Complete. Saved {count} new scholarships."

@celery_app.task
def run_instagram_scrape(hashtag="scholarships", limit=5):
    print(f"Starting Instagram Scrape: {hashtag}")
    
    username = os.getenv("INSTAGRAM_USERNAME")
    password = os.getenv("INSTAGRAM_PASSWORD")
    
    scraper = InstagramScraper(username=username, password=password, headless=True)
    results = scraper.scrape_hashtag(hashtag, num_posts=limit)
    
    count = 0
    for item in results:
        if save_scholarship_to_db(item):
            count += 1
            
    return f"Instagram Scrape Complete. Saved {count} new scholarships."

@celery_app.task
def run_reddit_scrape(limit=20): # Increased limit and removed single subreddit arg
    from scholarship_scraper.scrapers.reddit import RedditScraper
    
    # Expand search to multiple relevant subreddits
    subreddits = ["scholarships", "college", "financialaid", "studentloans", "ApplyingToCollege"]
    
    total_new = 0
    scraper = RedditScraper()
    
    for sub in subreddits:
        print(f"Starting Reddit Scrape: r/{sub}")
        try:
            results = scraper.scrape_subreddit(sub, limit=limit)
            for item in results:
                if save_scholarship_to_db(item):
                    total_new += 1
        except Exception as e:
            print(f"Failed to scrape r/{sub}: {e}")
            
    return f"Multi-Reddit Scrape Complete. Saved {total_new} new scholarships from {subreddits}."

@celery_app.task
def run_enrichment_task(limit=5):
    from scholarship_scraper.processors.enrichment import EnrichmentProcessor
    db = SessionLocal()
    updater = EnrichmentProcessor()
    
    try:
        # Find candidates needing enrichment (Rule: missing amount OR deadline, and hasn't been enriched yet)
        # Note: We don't have an 'enriched' flag yet, so we just check for nulls.
        # Ideally we should add a flag, but for now we'll process those with nulls.
        # To avoid infinite loops on failed ones, we'd need a flag or 'last_checked'. 
        # For this MVP, we will pick 5 random ones with NULL amount to try to improve them.
        import random
        candidates = db.query(ScholarshipModel).filter(ScholarshipModel.amount == None).all()
        
        if not candidates:
            return "No candidates for enrichment."
            
        # Shuffle to avoid getting stuck on same failed ones
        selection = random.sample(candidates, min(len(candidates), limit))
        
        count = 0
        for sch in selection:
            res = updater.enrich_url(sch.source_url)
            
            updated = False
            if res.get('amount') and sch.amount is None:
                sch.amount = res['amount']
                updated = True
                
            if res.get('deadline') and sch.deadline is None:
                sch.deadline = res['deadline']
                updated = True
            
            # Append full text description if current is short
            if res.get('full_text') and (not sch.description or len(sch.description) < 100):
                sch.description = (res['full_text'][:500] + "...")
                updated = True

            if updated:
                db.commit()
                count += 1
                
        return f"Enrichment Complete. Updated details for {count} scholarships."
        
    except Exception as e:
        db.rollback()
        return f"Enrichment Error: {e}"
    finally:
        db.close()

@celery_app.task
def run_tiktok_scrape(hashtag="scholarship", limit=3):
    """
    TikTok Video Scraper Task
    
    Downloads TikTok videos, transcribes audio using Whisper,
    and extracts scholarship information.
    """
    from scholarship_scraper.scrapers.tiktok import TikTokScraper
    
    print(f"Starting TikTok Scrape: #{hashtag}")
    
    try:
        # Use tiny model on cloud for speed (base is more accurate but slower)
        scraper = TikTokScraper(whisper_model="tiny")
        results = scraper.scrape(hashtag, num_videos=limit)
        
        count = 0
        for item in results:
            if save_scholarship_to_db(item):
                count += 1
        
        return f"TikTok Scrape Complete. Saved {count} new scholarships from {len(results)} videos."
        
    except Exception as e:
        print(f"TikTok Scrape Error: {e}")
        return f"TikTok Scrape Failed: {e}"

@celery_app.task
def run_rss_scrape(limit_per_feed=5):
    """
    RSS Feed Scraper Task
    
    Scrapes scholarship RSS feeds from known sources.
    Most reliable and least likely to be blocked.
    """
    from scholarship_scraper.scrapers.rss_feeds import RSSScholarshipScraper
    
    print("Starting RSS Feed Scrape")
    
    try:
        scraper = RSSScholarshipScraper()
        results = scraper.scrape_all(limit_per_feed=limit_per_feed)
        
        count = 0
        for item in results:
            if save_scholarship_to_db(item):
                count += 1
        
        return f"RSS Scrape Complete. Saved {count} new scholarships from {len(results)} feed items."
        
    except Exception as e:
        print(f"RSS Scrape Error: {e}")
        return f"RSS Scrape Failed: {e}"

@celery_app.task
def run_tor_social_scrape(hashtags=None):
    """
    Tor-Based Social Media Scraper with Media Processing
    
    Enhanced scraper that:
    1. Uses Tor for IP rotation
    2. Downloads images and runs OCR to extract text
    3. Downloads videos and transcribes audio
    4. Parses extracted text for scholarship info
    """
    import subprocess
    import time
    import requests
    
    if hashtags is None:
        hashtags = ['scholarship', 'scholarships']
    
    print("Starting Tor-based Media Scrape...")
    
    # Start Tor service
    try:
        subprocess.Popen(['tor'], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        time.sleep(15)  # Wait for Tor to bootstrap
    except Exception as e:
        print(f"Warning: Could not start Tor: {e}")
    
    # Test Tor connection
    session = requests.Session()
    session.proxies = {
        'http': 'socks5h://127.0.0.1:9050',
        'https': 'socks5h://127.0.0.1:9050'
    }
    
    try:
        resp = session.get('https://check.torproject.org/api/ip', timeout=30)
        ip_info = resp.json()
        if ip_info.get('IsTor'):
            print(f"✓ Tor connected via IP: {ip_info.get('IP')}")
        else:
            print("Warning: Not going through Tor")
            return "Tor Social Scrape Failed: Not connected to Tor"
    except Exception as e:
        print(f"Tor test failed: {e}")
        return "Tor Social Scrape Failed: Cannot connect to Tor"
    
    # Use the enhanced Tor Media Scraper
    try:
        from scholarship_scraper.scrapers.tor_media_scraper import run_single_scrape
        
        results = run_single_scrape(hashtags)
        
        if isinstance(results, str):
            return results  # Error message
        
        count = 0
        for sch_data in results:
            from scholarship_scraper.models.scholarship import Scholarship
            
            sch = Scholarship(
                title=sch_data.get('title', 'Social Media Scholarship')[:200],
                source_url=sch_data.get('source_url', ''),
                description=sch_data.get('description', '')[:500],
                amount=sch_data.get('amount'),
                deadline=sch_data.get('deadline'),
                platform=sch_data.get('platform', 'social-media'),
                date_posted=sch_data.get('date_posted', datetime.now())
            )
            
            if save_scholarship_to_db(sch):
                count += 1
        
        return f"Tor Media Scrape Complete. Saved {count} scholarships from {len(results)} media items."
        
    except ImportError as e:
        print(f"Import error: {e}")
        # Fallback to simple meta tag extraction
        count = 0
        for hashtag in hashtags:
            try:
                url = f"https://www.instagram.com/explore/tags/{hashtag}/"
                headers = {
                    'User-Agent': 'Mozilla/5.0 (iPhone; CPU iPhone OS 14_0 like Mac OS X)',
                }
                
                resp = session.get(url, headers=headers, timeout=30)
                
                if resp.status_code == 200:
                    from bs4 import BeautifulSoup
                    soup = BeautifulSoup(resp.text, 'html.parser')
                    
                    og_desc = soup.find('meta', property='og:description')
                    if og_desc:
                        content = og_desc.get('content', '')
                        if 'scholarship' in content.lower():
                            from scholarship_scraper.models.scholarship import Scholarship
                            
                            sch = Scholarship(
                                title=f"Instagram #{hashtag}",
                                source_url=url,
                                description=content[:500],
                                platform="instagram-tor",
                                date_posted=datetime.now()
                            )
                            
                            if save_scholarship_to_db(sch):
                                count += 1
                
                time.sleep(5)
                
            except Exception as e:
                print(f"Error scraping #{hashtag}: {e}")
        
        return f"Tor Social Scrape (Fallback). Saved {count} scholarships."
    
    except Exception as e:
        print(f"Tor Media Scrape Error: {e}")
        return f"Tor Media Scrape Failed: {e}"


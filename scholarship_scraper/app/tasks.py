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


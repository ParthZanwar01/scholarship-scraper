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
    "scrape-google-every-6-hours": {
        "task": "app.tasks.run_general_scrape",
        "schedule": crontab(minute=0, hour="*/6"),
    },
    "scrape-instagram-every-6-hours": {
        "task": "app.tasks.run_instagram_scrape",
        "schedule": crontab(minute=30, hour="*/6"),
    },
    "scrape-reddit-every-12-hours": {
        "task": "app.tasks.run_reddit_scrape",
        "schedule": crontab(minute=45, hour="*/12"),
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
def run_general_scrape(query="scholarships 2024", limit=10):
    print(f"Starting General Scrape: {query}")
    scraper = GeneralSearchScraper(headless=True)
    results = scraper.search_google(query, num_results=limit)
    
    count = 0
    for item in results:
        if save_scholarship_to_db(item):
            count += 1
    
    return f"General Scrape Complete. Saved {count} new scholarships."

@celery_app.task
def run_instagram_scrape(hashtag="scholarships", limit=5):
    print(f"Starting Instagram Scrape: {hashtag}")
    scraper = InstagramScraper(headless=True)
    results = scraper.scrape_hashtag(hashtag, num_posts=limit)
    
    count = 0
    for item in results:
        if save_scholarship_to_db(item):
            count += 1
            
    return f"Instagram Scrape Complete. Saved {count} new scholarships."

@celery_app.task
def run_reddit_scrape(subreddit="scholarships", limit=10):
    import asyncio
    from scholarship_scraper.scrapers.reddit import RedditScraper
    
    print(f"Starting Reddit Scrape: {subreddit}")
    scraper = RedditScraper()
    # Run async in sync celery task
    results = asyncio.run(scraper.scrape_subreddit(subreddit, limit))
    
    count = 0
    for item in results:
        if save_scholarship_to_db(item):
            count += 1
            
    return f"Reddit Scrape Complete. Saved {count} new scholarships."

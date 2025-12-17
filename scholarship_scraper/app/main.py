from fastapi import FastAPI, Depends, HTTPException
from sqlalchemy.orm import Session
from .database import engine, Base, get_db
from .models import ScholarshipModel
from .tasks import run_general_scrape, run_instagram_scrape, run_reddit_scrape, celery_app

# Create DB tables
Base.metadata.create_all(bind=engine)

app = FastAPI(title="Scholarship Scraper API")

from fastapi.middleware.cors import CORSMiddleware

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Allows all origins
    allow_credentials=False, # Must be False if origins is "*"
    allow_methods=["*"],  # Allows all methods
    allow_headers=["*"],  # Allows all headers
)

@app.get("/")
def read_root():
    return {"message": "Scholarship Scraper API is running. Visit /docs for endpoints."}

@app.get("/scholarships/")
def read_scholarships(skip: int = 0, limit: int = 100, db: Session = Depends(get_db)):
    scholarships = db.query(ScholarshipModel).order_by(ScholarshipModel.created_at.desc()).offset(skip).limit(limit).all()
    return [s.to_dict() for s in scholarships]

@app.post("/scrape/general")
def trigger_general_scrape(query: str = "scholarships", limit: int = 5):
    task = run_general_scrape.delay(query, limit)
    return {"message": "General scrape triggered", "task_id": str(task.id)}

@app.post("/scrape/instagram")
def trigger_instagram_scrape(hashtag: str = "scholarships", limit: int = 5):
    task = run_instagram_scrape.delay(hashtag, limit)
    return {"message": "Instagram scrape triggered", "task_id": str(task.id)}

@app.post("/scrape/reddit")
def trigger_reddit_scrape(limit: int = 20):
    # Task now self-manages subreddits
    task = run_reddit_scrape.delay(limit=limit)
    return {"message": "Reddit scrape triggered (Multi-Subreddit)", "task_id": str(task.id)}

@app.post("/enrich")
def trigger_enrichment(limit: int = 5):
    from scholarship_scraper.app.tasks import run_enrichment_task
    task = run_enrichment_task.delay(limit)
    return {"message": "Deep research (Enrichment) triggered", "task_id": str(task.id)}

@app.post("/scrape/tiktok")
def trigger_tiktok_scrape(hashtag: str = "scholarship", limit: int = 3):
    from scholarship_scraper.app.tasks import run_tiktok_scrape
    task = run_tiktok_scrape.delay(hashtag, limit)
    return {"message": "TikTok video scrape triggered", "task_id": str(task.id)}

@app.post("/scholarships/")
def create_scholarship(item: dict, db: Session = Depends(get_db), skip_validation: bool = False):
    """
    Create a new scholarship entry.
    
    By default, uses AI to validate the URL content first.
    Set skip_validation=True to bypass AI check.
    """
    source_url = item.get("source_url", "")
    
    # Check if already exists
    exists = db.query(ScholarshipModel).filter(ScholarshipModel.source_url == source_url).first()
    if exists:
        return {"message": "Scholarship already exists", "id": exists.id}
    
    # --- AI CONTENT VALIDATION ---
    if source_url and not skip_validation:
        try:
            from scholarship_scraper.processors.content_classifier import ContentClassifier
            classifier = ContentClassifier()
            result = classifier.classify_url(source_url)
            
            classification = result.get("classification", "UNKNOWN")
            is_worth_saving = result.get("is_worth_saving", False)
            
            if not is_worth_saving:
                return {
                    "message": "Rejected: Not a scholarship page",
                    "classification": classification,
                    "reason": result.get("reason", "Unknown"),
                    "saved": False
                }
            
            # Use AI-extracted title if better
            if result.get("scholarship_name"):
                item["title"] = result["scholarship_name"]
            
            # Use direct apply URL if found
            if result.get("direct_apply_url"):
                item["source_url"] = result["direct_apply_url"]
                
        except Exception as e:
            # If AI fails, continue with save (fail-open)
            print(f"AI validation error (saving anyway): {e}")
    
    # --- SAVE TO DATABASE ---
    new_sch = ScholarshipModel(
        title=item.get("title"),
        source_url=item.get("source_url", source_url),
        description=item.get("description"),
        amount=item.get("amount"),
        deadline=item.get("deadline"),
        platform=item.get("platform", "external"),
        raw_text=item.get("description")
    )
    db.add(new_sch)
    db.commit()
    db.refresh(new_sch)
    return {"message": "Scholarship created", "id": new_sch.id, "saved": True}

@app.delete("/scrape/reddit")
def clear_reddit_data():
    from scholarship_scraper.app.database import SessionLocal
    from scholarship_scraper.app.models import ScholarshipModel
    db = SessionLocal()
    try:
        count = db.query(ScholarshipModel).filter(ScholarshipModel.platform == 'reddit').delete()
        db.commit()
        return {"message": f"Deleted {count} Reddit entries"}
    except Exception as e:
        db.rollback()
        return {"error": str(e)}
    finally:
        db.close()


@app.post("/filter/cleanup")
def cleanup_article_links():
    """
    Remove existing scholarships that have article/blog URLs.
    Uses URL pattern matching to identify and delete article entries.
    """
    from scholarship_scraper.app.database import SessionLocal
    from scholarship_scraper.app.models import ScholarshipModel
    
    try:
        from scholarship_scraper.processors.url_filter import filter_url
    except ImportError:
        return {"error": "URL filter module not found"}
    
    db = SessionLocal()
    try:
        all_scholarships = db.query(ScholarshipModel).all()
        deleted_count = 0
        deleted_urls = []
        
        for sch in all_scholarships:
            if sch.source_url:
                is_valid, reason = filter_url(sch.source_url)
                if not is_valid and 'blocked' in reason.lower():
                    deleted_urls.append({
                        "url": sch.source_url[:80],
                        "reason": reason
                    })
                    db.delete(sch)
                    deleted_count += 1
        
        db.commit()
        return {
            "message": f"Cleaned up {deleted_count} article-based entries",
            "deleted": deleted_urls[:20]  # Show first 20
        }
    except Exception as e:
        db.rollback()
        return {"error": str(e)}
    finally:
        db.close()


@app.get("/filter/stats")
def get_filter_stats():
    """
    Get statistics about current scholarship URLs - how many would pass/fail the filter.
    """
    from scholarship_scraper.app.database import SessionLocal
    from scholarship_scraper.app.models import ScholarshipModel
    
    try:
        from scholarship_scraper.processors.url_filter import filter_url
    except ImportError:
        return {"error": "URL filter module not found"}
    
    db = SessionLocal()
    try:
        all_scholarships = db.query(ScholarshipModel).all()
        
        stats = {
            "total": len(all_scholarships),
            "would_keep": 0,
            "would_filter": 0,
            "no_url": 0,
            "sample_filtered": []
        }
        
        for sch in all_scholarships:
            if not sch.source_url:
                stats["no_url"] += 1
            else:
                is_valid, reason = filter_url(sch.source_url)
                if is_valid:
                    stats["would_keep"] += 1
                else:
                    stats["would_filter"] += 1
                    if len(stats["sample_filtered"]) < 10:
                        stats["sample_filtered"].append({
                            "url": sch.source_url[:80],
                            "reason": reason
                        })
        
        return stats
    finally:
        db.close()


@app.post("/filter/analyze")
def analyze_url_with_ai(url: str):
    """
    Use AI to analyze a specific URL and determine if it's a scholarship application or article.
    """
    try:
        from scholarship_scraper.processors.content_classifier import ContentClassifier
        classifier = ContentClassifier()
        result = classifier.classify_url(url)
        return result
    except ImportError:
        return {"error": "Content classifier module not found"}
    except Exception as e:
        return {"error": str(e)}


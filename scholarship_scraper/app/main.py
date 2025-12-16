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

@app.post("/scholarships/")
def create_scholarship(item: dict, db: Session = Depends(get_db)):
    # Simple create/deduplicate logic
    exists = db.query(ScholarshipModel).filter(ScholarshipModel.source_url == item.get("source_url")).first()
    if exists:
        return {"message": "Scholarship already exists", "id": exists.id}
    
    new_sch = ScholarshipModel(
        title=item.get("title"),
        source_url=item.get("source_url"),
        description=item.get("description"),
        amount=item.get("amount"),
        deadline=item.get("deadline"), # Pass string, DB handles datetime conv if needed, or valid iso
        platform=item.get("platform", "external"),
        raw_text=item.get("description")
    )
    db.add(new_sch)
    db.commit()
    db.refresh(new_sch)
    return {"message": "Scholarship created", "id": new_sch.id}

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

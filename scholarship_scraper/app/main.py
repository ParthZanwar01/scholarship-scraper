from fastapi import FastAPI, Depends, HTTPException
from sqlalchemy.orm import Session
from .database import engine, Base, get_db
from .models import ScholarshipModel
from .tasks import run_general_scrape, run_instagram_scrape, celery_app

# Create DB tables
Base.metadata.create_all(bind=engine)

app = FastAPI(title="Scholarship Scraper API")

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

from scholarship_scraper.app.database import SessionLocal
from scholarship_scraper.app.models import ScholarshipModel

def clear_reddit():
    db = SessionLocal()
    try:
        deleted = db.query(ScholarshipModel).filter(ScholarshipModel.platform == 'reddit').delete()
        db.commit()
        print(f"Deleted {deleted} Reddit entries.")
    except Exception as e:
        print(e)
        db.rollback()
    finally:
        db.close()

if __name__ == "__main__":
    clear_reddit()

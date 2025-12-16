import os
import requests
import time
from scholarship_scraper.scrapers.instagram import InstagramScraper
from datetime import datetime

# Configuration
# NOTE: Using credentials provided by user for local execution.
USERNAME = os.getenv("INSTAGRAM_USERNAME", "parthzanwar112@gmail.com") 
PASSWORD = os.getenv("INSTAGRAM_PASSWORD", "Parthtanish00!")
API_URL = "http://64.23.231.89:8000/scholarships/"

def sync_to_cloud(scholarship):
    """Sends a found scholarship to the cloud database."""
    payload = {
        "title": scholarship.title,
        "source_url": scholarship.source_url,
        "description": scholarship.description,
        "amount": scholarship.amount,
        "deadline": scholarship.deadline.isoformat() if scholarship.deadline else None,
        "platform": "instagram"
    }
    
    try:
        print(f"  -> Syncing {scholarship.source_url} to Cloud...")
        # Note: The API expects scholarship data. Since the POST /scholarships endpoint 
        # might require a specific schema, we should align with it.
        # However, for simplicity, we can also use the /enrich endpoint or just insert directly if we had DB access.
        # But we don't have remote DB access. We have API access.
        # Let's assume there is a POST /scholarships endpoint (standard CRUD).
        # We need to make sure the schema matches ScholarshipCreate.
        
        response = requests.post(API_URL, json=payload)
        if response.status_code in [200, 201]:
            print("  [SUCCESS] Synced!")
            return True
        else:
            print(f"  [FAILED] Cloud rejected: {response.status_code} - {response.text}")
            return False
    except Exception as e:
        print(f"  [ERROR] Sync failed: {e}")
        return False

def run_agent():
    print("------------------------------------------------")
    print("   SCHOLARSHIP SCRAPER - HYBRID LOCAL AGENT     ")
    print("------------------------------------------------")
    print(f"Running on Local Machine (Home IP)")
    print(f"Target: Instagram #scholarships")
    print(f"Sync Target: {API_URL}")
    print("------------------------------------------------")
    
    scraper = InstagramScraper(username=USERNAME, password=PASSWORD, headless=True)
    
    # We will loop continuously or just run once?
    # For now, let's run a batch of 10.
    print("Starting Scrape...")
    results = scraper.scrape_hashtag("scholarships", num_posts=10)
    
    print(f"\nFound {len(results)} posts. Starting Sync...")
    
    synced_count = 0
    for sch in results:
        if sync_to_cloud(sch):
            synced_count += 1
            
    print("------------------------------------------------")
    print(f"Job Complete. Synced {synced_count}/{len(results)} scholarships to the cloud.")
    print("------------------------------------------------")

if __name__ == "__main__":
    run_agent()

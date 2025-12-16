from scholarship_scraper.scrapers.instagram import InstagramScraper
import os
from dotenv import load_dotenv

load_dotenv()

username = os.getenv("INSTAGRAM_USERNAME")
password = os.getenv("INSTAGRAM_PASSWORD")

print(f"Testing Scraper with User: {username}")

try:
    scraper = InstagramScraper(username=username, password=password, headless=True)
    results = scraper.scrape_hashtag("scholarships", num_posts=1)
    print(f"Success! Found {len(results)} posts.")
    for res in results:
        print(f"Post: {res.title} - {res.source_url}")
except Exception as e:
    print(f"Scraper Failed: {e}")

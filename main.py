import argparse
import json
import os
from datetime import datetime
from scholarship_scraper.scrapers.general_search import GeneralSearchScraper
from scholarship_scraper.scrapers.instagram import InstagramScraper

DATA_FILE = "scholarship_scraper/data/results.json"

def load_data():
    if os.path.exists(DATA_FILE):
        with open(DATA_FILE, "r") as f:
            try:
                return json.load(f)
            except json.JSONDecodeError:
                return []
    return []

def save_data(new_results):
    existing_data = load_data()
    # Deduplicate by URL
    existing_urls = {item['source_url'] for item in existing_data}
    
    added_count = 0
    for item in new_results:
        item_dict = item.to_dict()
        if item_dict['source_url'] not in existing_urls:
            existing_data.append(item_dict)
            existing_urls.add(item_dict['source_url'])
            added_count += 1
    
    os.makedirs(os.path.dirname(DATA_FILE), exist_ok=True)
    with open(DATA_FILE, "w") as f:
        json.dump(existing_data, f, indent=4)
    
    print(f"Saved {added_count} new scholarships. Total database size: {len(existing_data)}")

def main():
    parser = argparse.ArgumentParser(description="Scholarship Web Scraper")
    parser.add_argument("--mode", choices=["general", "instagram", "all"], default="general", help="Scraping mode")
    parser.add_argument("--query", type=str, default="scholarships for students 2024", help="Search query or hashtag")
    parser.add_argument("--limit", type=int, default=5, help="Number of results to fetch")
    parser.add_argument("--headless", action="store_true", help="Run in headless mode")
    
    args = parser.parse_args()
    
    results = []

    if args.mode in ["general", "all"]:
        print(f"Starting General Search for: {args.query}")
        gen_scraper = GeneralSearchScraper(headless=args.headless)
        results.extend(gen_scraper.search_google(args.query, args.limit))

    if args.mode in ["instagram", "all"]:
        # For Instagram, query is treated as a hashtag (remove # if present)
        hashtag = args.query.replace("#", "").replace(" ", "")
        print(f"Starting Instagram Scraping for tag: {hashtag}")
        ig_scraper = InstagramScraper(headless=args.headless)
        results.extend(ig_scraper.scrape_hashtag(hashtag, args.limit))

    if results:
        save_data(results)
    else:
        print("No scholarships found.")

if __name__ == "__main__":
    main()

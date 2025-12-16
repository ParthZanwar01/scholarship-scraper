"""
SCHOLARSHIP SCRAPER - HYBRID LOCAL AGENT

This script runs on your local machine (home network) to scrape platforms
that block cloud server IPs:
- Instagram: Uses Instaloader with your credentials
- TikTok: Uses yt-dlp + Whisper for video transcription

All found scholarships are synced to your cloud database.
"""

import os
import sys
import requests
import time
from datetime import datetime

# Configuration
API_URL = os.getenv("API_URL", "http://64.23.231.89:8000/scholarships/")
INSTAGRAM_USERNAME = os.getenv("INSTAGRAM_USERNAME", "parthzanwar112@gmail.com")
INSTAGRAM_PASSWORD = os.getenv("INSTAGRAM_PASSWORD", "Parthtanish00!")

def sync_to_cloud(scholarship, platform="unknown"):
    """Sends a found scholarship to the cloud database."""
    payload = {
        "title": scholarship.title,
        "source_url": scholarship.source_url,
        "description": scholarship.description or "",
        "amount": scholarship.amount,
        "deadline": scholarship.deadline.isoformat() if scholarship.deadline else None,
        "platform": platform
    }
    
    try:
        response = requests.post(API_URL, json=payload, timeout=10)
        if response.status_code in [200, 201]:
            print(f"  ✓ Synced: {scholarship.title[:40]}...")
            return True
        else:
            print(f"  ✗ Failed: {response.status_code}")
            return False
    except Exception as e:
        print(f"  ✗ Error: {e}")
        return False


def run_instagram_scrape():
    """Scrape Instagram using Instaloader (requires home IP)."""
    print("\n" + "="*60)
    print("INSTAGRAM SCRAPER")
    print("="*60)
    
    try:
        from scholarship_scraper.scrapers.instagram import InstagramScraper
    except ImportError:
        print("Instagram scraper not available. Install instaloader.")
        return 0
    
    print(f"Username: {INSTAGRAM_USERNAME}")
    print(f"Target: #scholarships")
    print("-"*60)
    
    scraper = InstagramScraper(
        username=INSTAGRAM_USERNAME,
        password=INSTAGRAM_PASSWORD,
        headless=True
    )
    
    results = scraper.scrape_hashtag("scholarships", num_posts=10)
    print(f"\nFound {len(results)} posts from Instagram.")
    
    synced = 0
    for sch in results:
        if sync_to_cloud(sch, "instagram"):
            synced += 1
    
    return synced


def run_tiktok_scrape():
    """Scrape TikTok videos and transcribe them using Whisper."""
    print("\n" + "="*60)
    print("TIKTOK VIDEO SCRAPER (with Whisper Transcription)")
    print("="*60)
    
    try:
        from scholarship_scraper.scrapers.tiktok import TikTokScraper
    except ImportError:
        print("TikTok scraper not available. Install yt-dlp.")
        return 0
    
    # Check if Whisper is available
    try:
        import whisper
        whisper_model = "base"  # Better quality for local
        print(f"Whisper: ✓ Available (using '{whisper_model}' model)")
    except ImportError:
        whisper_model = "tiny"
        print("Whisper: Not installed. Transcription will be skipped.")
    
    print(f"Target: #scholarship")
    print("-"*60)
    
    scraper = TikTokScraper(whisper_model=whisper_model)
    results = scraper.scrape("scholarship", num_videos=5)
    
    print(f"\nFound {len(results)} scholarships from TikTok videos.")
    
    synced = 0
    for sch in results:
        if sync_to_cloud(sch, "tiktok"):
            synced += 1
    
    return synced


def main():
    print("="*60)
    print("SCHOLARSHIP SCRAPER - LOCAL AGENT")
    print("="*60)
    print(f"Running from: Local Machine (Home IP)")
    print(f"Cloud API: {API_URL}")
    print(f"Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    # Test cloud connection
    try:
        r = requests.get(API_URL.replace("/scholarships/", "/"), timeout=5)
        if r.status_code == 200:
            print(f"Cloud Status: ✓ Connected")
        else:
            print(f"Cloud Status: ✗ Error {r.status_code}")
            return
    except Exception as e:
        print(f"Cloud Status: ✗ Cannot connect - {e}")
        return
    
    total_synced = 0
    
    # Choose what to scrape
    print("\nWhat would you like to scrape?")
    print("1. Instagram only")
    print("2. TikTok only (with video transcription)")
    print("3. Both Instagram and TikTok")
    print("4. Exit")
    
    choice = input("\nEnter choice (1-4): ").strip()
    
    if choice == "1":
        total_synced += run_instagram_scrape()
    elif choice == "2":
        total_synced += run_tiktok_scrape()
    elif choice == "3":
        total_synced += run_instagram_scrape()
        total_synced += run_tiktok_scrape()
    elif choice == "4":
        print("Exiting...")
        return
    else:
        print("Invalid choice. Running both...")
        total_synced += run_instagram_scrape()
        total_synced += run_tiktok_scrape()
    
    print("\n" + "="*60)
    print(f"COMPLETE! Synced {total_synced} total scholarships to cloud.")
    print("="*60)


if __name__ == "__main__":
    main()

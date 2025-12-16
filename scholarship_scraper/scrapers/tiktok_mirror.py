"""
TikTok Mirror Scraper (ProxiTok)

Uses ProxiTok instances to scrape TikTok without direct API access.
ProxiTok is an open-source TikTok frontend that allows anonymous viewing.
"""

from playwright.sync_api import sync_playwright
import re
import time
from datetime import datetime
from scholarship_scraper.models.scholarship import Scholarship


class TikTokMirrorScraper:
    """Scrapes TikTok via ProxiTok mirror instances."""
    
    # List of known ProxiTok instances (updated August 2024)
    PROXITOK_INSTANCES = [
        "https://proxitok.pabloferreiro.es",
        "https://proxitok.pussthecat.org",
        "https://tok.habedieeh.re",
        "https://proxitok.esmailelbob.xyz",
        "https://proxitok.lunar.icu",
        "https://proxitok.privacydev.net",
        "https://proxitok.adminforge.de",
    ]
    
    def __init__(self, headless=True):
        self.headless = headless
        
    def scrape_hashtag(self, hashtag: str = "scholarship", limit: int = 10):
        """Scrape TikTok hashtag via ProxiTok instances."""
        print(f"Scraping TikTok #{hashtag} via ProxiTok...")
        
        scholarships = []
        
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=self.headless)
            context = browser.new_context(
                user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
            )
            page = context.new_page()
            
            for instance in self.PROXITOK_INSTANCES:
                if len(scholarships) >= limit:
                    break
                
                # ProxiTok uses /tag/{hashtag} format
                url = f"{instance}/tag/{hashtag}"
                print(f"Trying ProxiTok: {url}")
                
                try:
                    page.goto(url, timeout=15000)
                    page.wait_for_load_state("domcontentloaded")
                    time.sleep(2)  # Let content load
                    
                    content = page.content()
                    
                    # Check if blocked or error
                    if "error" in content.lower()[:500] or "captcha" in content.lower():
                        print(f"  Instance blocked/error, trying next...")
                        continue
                    
                    # Look for video cards/items
                    # ProxiTok typically has video divs with descriptions
                    video_cards = page.query_selector_all("div.video-card, article, div[class*='video']")
                    
                    if not video_cards:
                        # Try generic approach - find all links and text
                        links = page.query_selector_all("a[href*='/video/'], a[href*='/@']")
                        descriptions = page.query_selector_all("p, span, div.description")
                        
                        # Get all text content
                        all_text = page.inner_text("body")
                        
                        # Check if page has relevant content
                        if 'scholarship' in all_text.lower() or 'grant' in all_text.lower():
                            # Extract lines mentioning scholarships
                            lines = all_text.split('\n')
                            for line in lines:
                                line = line.strip()
                                if len(line) > 30 and any(kw in line.lower() for kw in ['scholarship', 'grant', 'apply now', 'deadline']):
                                    sch = Scholarship(
                                        title=f"TikTok: {line[:50]}...",
                                        source_url=url,
                                        description=line[:500],
                                        platform="tiktok",
                                        date_posted=datetime.now()
                                    )
                                    scholarships.append(sch)
                                    if len(scholarships) >= limit:
                                        break
                    else:
                        for card in video_cards[:limit]:
                            try:
                                text = card.inner_text()
                                if 'scholarship' in text.lower() or 'grant' in text.lower():
                                    # Try to get video link
                                    link = card.query_selector("a")
                                    video_url = link.get_attribute("href") if link else url
                                    
                                    if not video_url.startswith("http"):
                                        video_url = f"{instance}{video_url}"
                                    
                                    sch = Scholarship(
                                        title=f"TikTok Scholarship Video",
                                        source_url=video_url,
                                        description=text[:500],
                                        platform="tiktok",
                                        date_posted=datetime.now()
                                    )
                                    scholarships.append(sch)
                            except Exception as e:
                                continue
                    
                    print(f"  Found {len(scholarships)} videos so far from this instance")
                    
                    if scholarships:
                        break  # Success, no need to try other instances
                        
                except Exception as e:
                    print(f"  Instance error: {e}")
                    continue
            
            browser.close()
            
        print(f"\nTikTok ProxiTok Scrape Complete. Found {len(scholarships)} scholarships.")
        return scholarships


if __name__ == "__main__":
    scraper = TikTokMirrorScraper(headless=False)  # Show browser for testing
    results = scraper.scrape_hashtag("scholarship", limit=5)
    
    for s in results:
        print(f"Title: {s.title}")
        print(f"URL: {s.source_url}")
        print(f"Description: {s.description[:100]}...")
        print("-" * 40)

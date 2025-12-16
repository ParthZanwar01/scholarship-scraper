"""
Instagram Mirror Scraper

Uses mirror sites like Dumpor/Inflact to scrape Instagram without login.
These sites cache Instagram content and allow anonymous viewing.
"""

from playwright.sync_api import sync_playwright
import re
import time
from datetime import datetime
from scholarship_scraper.models.scholarship import Scholarship


class InstagramMirrorScraper:
    """Scrapes Instagram via mirror sites that don't require login."""
    
    MIRRORS = [
        {
            "name": "Dumpor",
            "url": "https://dumpor.com/t/{hashtag}",
            "post_selector": "div.post, article",
            "caption_selector": "p.desc, div.content",
            "link_selector": "a[href*='/c/']",
        },
        {
            "name": "Inflact",
            "url": "https://inflact.com/profiles/instagram/hashtag/{hashtag}/",
            "post_selector": "div.post-card, div.post-item",
            "caption_selector": "p.caption, div.text",
            "link_selector": "a[href*='instagram.com/p/']",
        },
        {
            "name": "Picuki",
            "url": "https://www.picuki.com/tag/{hashtag}",
            "post_selector": "div.post-image, li.post",
            "caption_selector": "div.photo-description",
            "link_selector": "a[href*='/media/']",
        },
    ]
    
    def __init__(self, headless=True):
        self.headless = headless
        
    def scrape_hashtag(self, hashtag: str = "scholarships", limit: int = 10):
        """Scrape Instagram hashtag via mirror sites."""
        print(f"Scraping Instagram #{hashtag} via mirrors...")
        
        scholarships = []
        
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=self.headless)
            context = browser.new_context(
                user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
            )
            page = context.new_page()
            
            for mirror in self.MIRRORS:
                if len(scholarships) >= limit:
                    break
                    
                url = mirror["url"].format(hashtag=hashtag)
                print(f"Trying {mirror['name']}: {url}")
                
                try:
                    page.goto(url, timeout=15000)
                    page.wait_for_load_state("domcontentloaded")
                    time.sleep(2)  # Let JS render
                    
                    # Look for post content
                    content = page.content()
                    
                    # Check if we got actual content (not blocked)
                    if "blocked" in content.lower() or "captcha" in content.lower():
                        print(f"  {mirror['name']} blocked/captcha")
                        continue
                    
                    # Try to find captions/descriptions
                    captions = page.query_selector_all(mirror["caption_selector"])
                    
                    if not captions:
                        # Fallback: try to extract text from the page
                        all_text = page.inner_text("body")
                        
                        # Look for scholarship keywords
                        if any(kw in all_text.lower() for kw in ['scholarship', 'grant', 'apply', 'deadline']):
                            # Extract potential scholarship mentions
                            lines = all_text.split('\n')
                            for line in lines:
                                line = line.strip()
                                if len(line) > 50 and 'scholarship' in line.lower():
                                    sch = Scholarship(
                                        title=f"Instagram: {line[:50]}...",
                                        source_url=url,
                                        description=line[:500],
                                        platform="instagram",
                                        date_posted=datetime.now()
                                    )
                                    scholarships.append(sch)
                                    if len(scholarships) >= limit:
                                        break
                    else:
                        for caption in captions[:limit]:
                            text = caption.inner_text()
                            if 'scholarship' in text.lower() or 'grant' in text.lower():
                                sch = Scholarship(
                                    title=f"Instagram: {text[:40]}...",
                                    source_url=url,
                                    description=text[:500],
                                    platform="instagram",
                                    date_posted=datetime.now()
                                )
                                scholarships.append(sch)
                    
                    print(f"  Found {len(scholarships)} posts so far from {mirror['name']}")
                    
                    if scholarships:
                        break  # Success, no need to try other mirrors
                        
                except Exception as e:
                    print(f"  {mirror['name']} error: {e}")
                    continue
            
            browser.close()
            
        print(f"\nInstagram Mirror Scrape Complete. Found {len(scholarships)} scholarships.")
        return scholarships


if __name__ == "__main__":
    scraper = InstagramMirrorScraper(headless=False)  # Show browser for testing
    results = scraper.scrape_hashtag("scholarships", limit=5)
    
    for s in results:
        print(f"Title: {s.title}")
        print(f"Description: {s.description[:100]}...")
        print("-" * 40)

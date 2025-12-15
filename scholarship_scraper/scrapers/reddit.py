from playwright.sync_api import sync_playwright
import os
from datetime import datetime
from scholarship_scraper.models.scholarship import Scholarship
import asyncio

class RedditScraper:
    def __init__(self, client_id=None, client_secret=None, user_agent="Mozilla/5.0", headless=True):
        # We ignore client_id/secret as we are using web scraping now
        self.headless = headless

    def scrape_subreddit(self, subreddit_name="scholarships", limit=10):
        # List of Redlib/Libreddit instances to try
        mirrors = [
            "https://redlib.catsarch.com",
            "https://libreddit.offer.space.tr",
            "https://redlib.tux.pizza",
            "https://snoo.habedieeh.re",
            "https://libreddit.northboot.xyz",
            "https://old.reddit.com" # Keep original as last resort
        ]
        
        scholarships = []
        
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=self.headless)
            context = browser.new_context(user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36")
            page = context.new_page()
            
            for base_url in mirrors:
                try:
                    print(f"Attempting valid mirror: {base_url}...")
                    url = f"{base_url}/r/{subreddit_name}/new/"
                    
                    try:
                        page.goto(url, timeout=20000)
                    except:
                        print(f"Timeout/Error visiting {base_url}")
                        continue

                    # Check for 403/Block
                    title = page.title()
                    if "Blocked" in title or "Too Many Requests" in title or "403" in title:
                        print(f"Mirror {base_url} blocked.")
                        continue
                        
                    # Check for 18+ gate
                    if "over18" in page.url:
                        try:
                             # Try clicking generic "yes" buttons usually found on these frontends
                             page.click("text=Yes", timeout=2000) 
                        except:
                            pass
                        page.wait_for_load_state("networkidle")

                    # Selectors for Libreddit/Redlib are different from old.reddit
                    # They usually just have post titles in <a> tags
                    
                    if "old.reddit" in base_url:
                        posts = page.locator("#siteTable .thing.link").all()
                    else:
                        # Generic selector for Redlib instances
                        # usually .post_title or inside a feed div
                        posts = page.locator(".post_title").all()
                        if not posts:
                             # Fallback for other themes
                             posts = page.locator("a[href^='/r/']").all()

                    print(f"Found {len(posts)} posts on {base_url}")
                    
                    if len(posts) > 0:
                        count = 0
                        for post in posts:
                            try:
                                title_text = post.inner_text().strip()
                                href = post.get_attribute("href")
                                
                                # Skip invalid or empty results
                                if not title_text or not href:
                                    continue
                                
                                # Fix relative URL
                                if href.startswith("/"):
                                    full_url = base_url + href
                                else:
                                    full_url = href

                                if "scholarship" in title_text.lower() or "grant" in title_text.lower() or "fund" in title_text.lower():
                                    scholarship = Scholarship(
                                        title=f"Reddit: {title_text}",
                                        source_url=full_url,
                                        description=title_text,
                                        amount=None,
                                        platform="reddit",
                                        date_posted=datetime.now()
                                    )
                                    scholarships.append(scholarship)
                                    count += 1
                                    if count >= limit:
                                        break
                            except:
                                continue
                        
                        if scholarships:
                            print(f"Successfully scraped {len(scholarships)} from {base_url}")
                            break # Found data, stop iterating mirrors
                            
                except Exception as e:
                     print(f"Error on mirror {base_url}: {e}")
            
            browser.close()
            
        return scholarships
            
        print(f"Extracted {len(scholarships)} scholarships from r/{subreddit_name}")
        return scholarships

if __name__ == "__main__":
    # Test
    scraper = RedditScraper(headless=False)
    res = scraper.scrape_subreddit()
    print(res)

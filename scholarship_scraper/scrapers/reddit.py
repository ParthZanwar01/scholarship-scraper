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
        print(f"Scraping r/{subreddit_name} via old.reddit.com...")
        scholarships = []
        
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=self.headless)
            context = browser.new_context(user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36")
            page = context.new_page()
            
            try:
                url = f"https://old.reddit.com/r/{subreddit_name}/new/"
                page.goto(url, timeout=60000)
                
                # Check for 18+ gate
                if "over18" in page.url:
                    page.click("button[name='over18'][value='yes']")
                    page.wait_for_load_state("networkidle")

                # specific selectors for old.reddit
                posts = page.locator("#siteTable .thing.link").all()
                
                print(f"Found {len(posts)} posts on r/{subreddit_name}")

                if not posts:
                    print(f"DEBUG: Title: {page.title()}")
                    print(f"DEBUG: URL: {page.url}")
                    # print(f"DEBUG: Content excerpt: {page.content()[:500]}") # Too noisy for logs? Maybe just title is enough.
                    content = page.content()
                    if "Blocked" in content or "Too Many Requests" in content:
                        print("DEBUG: Potentially blocked.")
                    elif "gate" in page.url or "over18" in page.url:
                        print("DEBUG: Stuck at age gate?")
                
                for post in posts[:limit]:
                    try:
                        title = post.locator("a.title").first.inner_text()
                        link = post.locator("a.title").first.get_attribute("href")
                        
                        # Handle relative links
                        if link.startswith("/"):
                            link = "https://old.reddit.com" + link
                            
                        # Extract date
                        time_element = post.locator("time").first
                        date_posted = datetime.now() # Fallback
                        if time_element.count() > 0:
                            timestamp = time_element.get_attribute("datetime")
                            # Simple parse if needed, or just use now
                        
                        # Heuristic: Filter for scholarship-like titles
                        if "scholarship" in title.lower() or "grant" in title.lower() or "fund" in title.lower():
                             scholarship = Scholarship(
                                title=f"Reddit: {title}",
                                source_url=link,
                                description=title, # Reddit titles are descriptive
                                amount=None, # Hard to extract reliable amount from title
                                platform="reddit",
                                date_posted=date_posted
                            )
                             scholarships.append(scholarship)
                    except Exception as e:
                        print(f"Error parsing post: {e}")
                        
            except Exception as e:
                print(f"Failed to scrape r/{subreddit_name}: {e}")
            
            browser.close()
            
        print(f"Extracted {len(scholarships)} scholarships from r/{subreddit_name}")
        return scholarships

if __name__ == "__main__":
    # Test
    scraper = RedditScraper(headless=False)
    res = scraper.scrape_subreddit()
    print(res)

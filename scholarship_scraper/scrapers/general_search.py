from playwright.sync_api import sync_playwright
from bs4 import BeautifulSoup
import time
import random
from scholarship_scraper.models.scholarship import Scholarship
from datetime import datetime

class GeneralSearchScraper:
    def __init__(self, headless=True):
        self.headless = headless

    def search_google(self, query: str, num_results: int = 10):
        results = []
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=self.headless)
            page = browser.new_page()
            
            # Navigate to Google
            page.goto("https://www.google.com")
            
            # Handle potential cookie consent (basic/common selectors)
            # This is highly variable by region, simplified for now
            try:
                page.locator("button:has-text('Accept all')").click(timeout=2000)
            except:
                pass

            # Search
            page.fill('textarea[name="q"]', query)
            page.press('textarea[name="q"]', "Enter")
            page.wait_for_selector("#search")

            # Extract links
            links = page.locator("#search .g a").all()
            found_urls = []
            for link in links:
                url = link.get_attribute("href")
                if url and "http" in url and "google" not in url:
                    found_urls.append(url)
                    if len(found_urls) >= num_results:
                        break
            
            print(f"Found {len(found_urls)} URLs to scrape.")

            for url in found_urls:
                print(f"Scraping: {url}")
                try:
                    # Visit each page to get details
                    # A new page/context might be safer to prevent detection cross-contamination
                    scholarship = self.scrape_page(page, url) 
                    if scholarship:
                        results.append(scholarship)
                    time.sleep(random.uniform(1, 3)) # Polite delay
                except Exception as e:
                    print(f"Failed to scrape {url}: {e}")

            browser.close()
        return results

    def scrape_page(self, page, url):
        try:
            page.goto(url, timeout=10000)
            content = page.content()
            soup = BeautifulSoup(content, 'html.parser')
            
            # Heuristic extraction
            title = soup.title.string.strip() if soup.title else "Unknown Title"
            text = soup.get_text(" ", strip=True)
            
            # Simple keyword extraction (to be improved)
            amount = None
            if "$" in text:
                # Very naive amount extraction, finding first $ sequence
                import re
                amounts = re.findall(r'\$\d+(?:,\d+)?', text)
                if amounts:
                    amount = amounts[0]

            scholarship = Scholarship(
                title=title,
                source_url=url,
                description=text[:200] + "...", # Store snippet
                amount=amount,
                platform="general",
                date_posted=datetime.now()
            )
            return scholarship
        except Exception as e:
            print(f"Error visiting {url}: {e}")
            return None

if __name__ == "__main__":
    scraper = GeneralSearchScraper(headless=False)
    data = scraper.search_google("computer science scholarships 2024", num_results=3)
    print(data)

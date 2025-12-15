from playwright.sync_api import sync_playwright
from bs4 import BeautifulSoup
import time
import random
from scholarship_scraper.models.scholarship import Scholarship
from datetime import datetime

class GeneralSearchScraper:
    def __init__(self, headless=True):
        self.headless = headless

    def search_duckduckgo(self, query: str, num_results: int = 10):
        print(f"Adding Social Media context to query: {query}")
        results = []
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=self.headless)
            # Use a real user agent to avoid detection/different layouts
            context = browser.new_context(user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36")
            page = context.new_page()
            
            try:
                # Navigate to DuckDuckGo (HTML version is lighter/faster/less bot-detected)
                page.goto("https://html.duckduckgo.com/html/", timeout=60000)
                
                # Search
                page.fill('input[name="q"]', query, timeout=30000)
                page.press('input[name="q"]', "Enter")
                
                # Wait for results container (more robust)
                try:
                    page.wait_for_selector(".result", timeout=10000)
                except:
                    print("DuckDuckGo results not found by selector '.result', dumping content for debug if local...")

                # Extract links - simpler strategy finding all links in results
                links = page.locator(".result a.result__a").all()
                if not links:
                     # Fallback for different HTML structure
                     links = page.locator(".result .result__title").all()
                found_urls = []
                for link in links:
                    url = link.get_attribute("href")
                    # Filter out ads and internal links
                    if url and "http" in url and "duckduckgo" not in url:
                        found_urls.append(url)
                        if len(found_urls) >= num_results:
                            break
            
            except Exception as e:
                print(f"DuckDuckGo search failed ({e}), failing over to Bing...")
                try:
                    found_urls = self.search_bing_fallback(page, query, num_results)
                except:
                    print("Bing also failed. Failing over to Direct Sites...")
                    found_urls = self.search_direct_fallback(page)
            
            print(f"Found {len(found_urls)} URLs.")

            for url in found_urls:
                print(f"Scraping: {url}")
                try:
                    # Visit each page to get details
                    scholarship = self.scrape_page(page, url) 
                    if scholarship:
                        results.append(scholarship)
                    time.sleep(random.uniform(1, 3)) 
                except Exception as e:
                    print(f"Failed to scrape {url}: {e}")

            browser.close()
        return results

    def search_direct_fallback(self, page):
        # List of friendly scholarship sites to scrape directly
        # focused on aggregators that might list multiple
        urls = [
            # CareerOneStop (US Dept of Labor) - usually bot friendly
            "https://www.careeronestop.org/Toolkit/Training/find-scholarships.aspx",
            # Simple list sites
            "https://www.scholarships.com/financial-aid/college-scholarships/scholarship-directory",
            "https://www.unigo.com/scholarships/our-scholarships"
        ]
        return urls

    def search_bing_fallback(self, page, query, num_results):
        try:
            print("Attempting search via Bing...")
            page.goto("https://www.bing.com", timeout=60000)
            
            # Simple Bing search
            page.fill('input[name="q"]', query)
            page.press('input[name="q"]', "Enter")
            page.wait_for_selector("ol#b_results")
            
            links = page.locator("ol#b_results li.b_algo h2 a").all()
            
            urls = []
            for link in links:
                url = link.get_attribute("href")
                if url:
                    urls.append(url)
                    if len(urls) >= num_results:
                        break
            return urls
        except Exception as e:
            print(f"Bing Fallback failed: {e}")
            return []

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
    data = scraper.search_duckduckgo("computer science scholarships 2024", num_results=3)
    print(data)

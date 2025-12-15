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
                found_urls = self.search_bing_fallback(page, query, num_results)
                
                if not found_urls:
                    print("Bing returned no results. Failing over to Direct Sites...")
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
        # Fallback to direct scholarship directory scraping
        direct_urls = [
            "https://www.unigo.com/scholarships/our-scholarships",
            "https://www.scholarships.com/financial-aid/college-scholarships/scholarship-directory/age/age-17",
            "https://www.careeronestop.org/Toolkit/Training/find-scholarships.aspx", # New
            "https://www.niche.com/colleges/scholarships/", # New
            "https://studentscholarships.org/scholarship.php" # New
        ]
        
        found_urls = []
        for d_url in direct_urls:
            try:
                print(f"Direct Scraping Source: {d_url}")
                page.goto(d_url, timeout=30000)
                page.wait_for_timeout(3000)
                
                # Generic link extraction for these directories
                # Identify links that look like scholarship detail pages
                links = page.locator("a").all()
                count = 0 
                for link in links:
                    try:
                        href = link.get_attribute("href")
                        if not href:
                            continue
                            
                        # Filtering logic
                        is_relevant = False
                        if "scholarship" in href.lower() or "grant" in href.lower() or "fund" in href.lower():
                            is_relevant = True
                        if len(href) < 15: # Ignore short nav links
                            is_relevant = False

                        if is_relevant:
                             # Normalize URL
                             if href.startswith("/"):
                                 # Need base domain
                                 from urllib.parse import urlparse
                                 parsed_uri = urlparse(d_url)
                                 base = '{uri.scheme}://{uri.netloc}'.format(uri=parsed_uri)
                                 full_url = base + href
                             elif href.startswith("http"):
                                 full_url = href
                             else:
                                 continue
                             
                             # Avoid adding the directory page itself or duplicates
                             if full_url not in found_urls and full_url != d_url:
                                 found_urls.append(full_url)
                                 count += 1
                                 if count >= 6: # Extract top 6 from each site to stay diverse
                                     break
                    except:
                        continue
            except Exception as e:
                print(f"Failed to scrape direct source {d_url}: {e}")
        
        return found_urls

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
    # data = scraper.search_duckduckgo("computer science scholarships 2024", num_results=3)
    urls = scraper.search_direct_fallback(scraper.search_bing_fallback) # Hacky way to pass page? No wait.
    # search_direct_fallback takes 'page'. I need to init the page.
    # Actually I can just look at how it's called in the class.
    # It takes 'page'.
    
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=False)
        page = browser.new_page()
        urls = scraper.search_direct_fallback(page)
        print("Found URLs:", urls)
        browser.close()

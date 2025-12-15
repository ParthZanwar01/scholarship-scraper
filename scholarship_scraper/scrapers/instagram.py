from playwright.sync_api import sync_playwright
from scholarship_scraper.models.scholarship import Scholarship
from scholarship_scraper.processors.ocr_utils import extract_text_from_image
import time
import os
import requests
from datetime import datetime

class InstagramScraper:
    def __init__(self, headless=True):
        self.headless = headless
        self.download_dir = "downloads/instagram_images"
        os.makedirs(self.download_dir, exist_ok=True)

    def scrape_hashtag(self, hashtag: str, num_posts: int = 5):
        results = []
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=self.headless)
            context = browser.new_context(
                user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
            )
            page = context.new_page()

            # Go to hashtag page
            url = f"https://www.instagram.com/explore/tags/{hashtag}/"
            print(f"Navigating to {url}")
            page.goto(url)
            time.sleep(5) # Wait for load

            # Handle login prompt or cookie banner if it appears (basic)
            # Instagram often blocks unauthenticated hashtag viewing. 
            # If blocked, this returns empty, which is expected without login.
            
            # Collect post links
            # Only first few posts usually visible without login
            links = page.locator("a[href^='/p/']").all()
            post_urls = set()
            for link in links:
                href = link.get_attribute("href")
                if href:
                    post_urls.add(f"https://www.instagram.com{href}")
                if len(post_urls) >= num_posts:
                    break
            
            print(f"Found {len(post_urls)} posts.")

            for post_url in post_urls:
                try:
                    print(f"Scraping post: {post_url}")
                    scholarship = self.scrape_post(page, post_url)
                    if scholarship:
                        results.append(scholarship)
                    time.sleep(3)
                except Exception as e:
                    print(f"Error scraping post {post_url}: {e}")

            browser.close()
        return results

    def scrape_post(self, page, url):
        page.goto(url)
        time.sleep(3)

        # Extract textual content from caption
        try:
            # Metadata description often contains the caption
            description_meta = page.locator("meta[property='og:description']").get_attribute("content")
            caption = description_meta if description_meta else ""
        except:
            caption = ""

        # Extract Image for OCR
        try:
            image_url = page.locator("meta[property='og:image']").get_attribute("content")
            if image_url:
                local_filename = f"{self.download_dir}/{url.split('/')[-2]}.jpg"
                self.download_image(image_url, local_filename)
                ocr_text = extract_text_from_image(local_filename)
                
                # Combine caption and OCR text for full context
                full_text = f"Caption: {caption}\nOCR Text: {ocr_text}"
                
                # Heuristic for detecting if it's a scholarship
                if "scholarship" in full_text.lower() or "grant" in full_text.lower():
                     return Scholarship(
                        title=f"Instagram Post from {url.split('/')[-2]}",
                        source_url=url,
                        description=full_text,
                        platform="instagram",
                        date_posted=datetime.now()
                    )
        except Exception as e:
            print(f"Error processing image for {url}: {e}")

        return None

    def download_image(self, url, path):
        response = requests.get(url)
        if response.status_code == 200:
            with open(path, "wb") as f:
                f.write(response.content)

if __name__ == "__main__":
    scraper = InstagramScraper(headless=False)
    data = scraper.scrape_hashtag("scholarships", num_posts=2)
    print(data)

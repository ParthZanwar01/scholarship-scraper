import instaloader
from scholarship_scraper.models.scholarship import Scholarship
# from scholarship_scraper.processors.ocr_utils import extract_text_from_image # Optional: Re-enable if OCR is needed later
import time
import os
from datetime import datetime

class InstagramScraper:
    def __init__(self, username=None, password=None, headless=True):
        self.L = instaloader.Instaloader()
        # Create download dir if needed, though instaloader handles its own
        self.download_dir = "downloads/instagram_images"
        os.makedirs(self.download_dir, exist_ok=True)
        
        if username and password:
            try:
                print(f"Attempting login for {username}...")
                self.L.login(username, password)
                print("Login successful!")
            except Exception as e:
                print(f"Login failed: {e}")
                print("Proceeding without login (rate limits will be tighter).")

    def scrape_hashtag(self, hashtag: str, num_posts: int = 5):
        print(f"Scraping Instagram hashtag: #{hashtag} using Instaloader...")
        results = []
        count = 0
        
        try:
            posts = instaloader.NodeIterator(
                self.L.context, "9566063666579",
                lambda d: instaloader.Post(self.L.context, d),
                lambda n: instaloader.Instaloader.get_hashtag_posts(self.L, hashtag, max_count=num_posts),
            )
            
            # Simple iteration - Instaloader generators can be tricky, using basic loop
            # get_hashtag_posts returns an iterator of Post objects
            post_iterator = instaloader.Instaloader.get_hashtag_posts(self.L, hashtag)

            for post in post_iterator:
                if count >= num_posts:
                    break
                
                try:
                    print(f"Processing post: {post.shortcode}")
                    
                    # 1. Get Caption
                    caption = post.caption if post.caption else ""
                    
                    # 2. Get OCR text (Optional - skipping download for speed for now, relying on caption)
                    # To enable OCR: download image -> run tesseract -> append to text
                    
                    full_text = caption
                    
                    # 3. Create Scholarship Object
                    # Note: Instaloader provides high quality metadata
                    scholarship = Scholarship(
                        title=f"Instagram Post @{post.owner_username}",
                        source_url=f"https://www.instagram.com/p/{post.shortcode}/",
                        description=full_text,
                        platform="instagram",
                        date_posted=post.date_local or datetime.now()
                    )
                    
                    results.append(scholarship)
                    count += 1
                    
                    # Respect rate limits
                    time.sleep(2) 

                except Exception as e:
                    print(f"Error processing post {post.shortcode}: {e}")
                    continue

        except Exception as e:
            print(f"Instaloader Error: {e}")

        print(f"Instagram Scrape Complete. Found {len(results)} posts.")
        return results

if __name__ == "__main__":
    scraper = InstagramScraper()
    # Test run
    data = scraper.scrape_hashtag("scholarships", num_posts=2)
    for s in data:
        print(f"Title: {s.title}")
        print(f"Desc: {s.description[:100]}...")


"""
Session-Based Instagram Scraper

Uses Instaloader with saved sessions for authenticated access.
Implements proper rate limiting and respects platform ToS.
"""

import os
import time
import random
from datetime import datetime
from scholarship_scraper.models.scholarship import Scholarship

try:
    import instaloader
    INSTALOADER_AVAILABLE = True
except ImportError:
    INSTALOADER_AVAILABLE = False


class InstagramSessionScraper:
    """
    Instagram scraper using authenticated sessions.
    
    SETUP:
    1. Run once interactively to create session:
       python -c "from scholarship_scraper.scrapers.instagram_session import InstagramSessionScraper; s = InstagramSessionScraper(); s.interactive_login('your_username')"
    2. Session will be saved for future use
    """
    
    def __init__(self, username=None, session_dir=None):
        if not INSTALOADER_AVAILABLE:
            raise ImportError("instaloader not installed. Run: pip install instaloader")
        
        self.username = username
        self.session_dir = session_dir or os.path.expanduser("~/.instaloader")
        
        # Initialize with conservative settings
        self.loader = instaloader.Instaloader(
            download_pictures=False,
            download_videos=False,
            download_video_thumbnails=False,
            save_metadata=False,
            quiet=True,
            max_connection_attempts=1
        )
        
        # Try to load existing session
        if username:
            self._load_session()
    
    def _load_session(self):
        """Load saved session if available."""
        session_file = os.path.join(self.session_dir, f"session-{self.username}")
        
        if os.path.exists(session_file):
            try:
                self.loader.load_session_from_file(self.username, session_file)
                print(f"✓ Loaded session for {self.username}")
                return True
            except Exception as e:
                print(f"✗ Failed to load session: {e}")
        else:
            print(f"No saved session found for {self.username}")
            print("Run interactive_login() first to create a session")
        
        return False
    
    def interactive_login(self, username):
        """
        Interactive login to create and save session.
        Run this once, then future runs will use saved session.
        """
        self.username = username
        
        try:
            print(f"Logging in as {username}...")
            print("You may be prompted for password and 2FA...")
            
            self.loader.interactive_login(username)
            
            # Save session for future use
            os.makedirs(self.session_dir, exist_ok=True)
            session_file = os.path.join(self.session_dir, f"session-{username}")
            self.loader.save_session_to_file(session_file)
            
            print(f"✓ Login successful! Session saved to {session_file}")
            print("Future runs will use this saved session.")
            return True
            
        except Exception as e:
            print(f"✗ Login failed: {e}")
            return False
    
    def scrape_hashtag(self, hashtag="scholarships", limit=20):
        """
        Scrape posts from a hashtag.
        Implements rate limiting and respectful delays.
        """
        if not self.loader.context.is_logged_in:
            print("Not logged in. Please run interactive_login() first.")
            return []
        
        print(f"\nScraping Instagram #{hashtag}...")
        print("(Using rate limiting to avoid blocks)")
        
        scholarships = []
        
        try:
            hashtag_obj = instaloader.Hashtag.from_name(self.loader.context, hashtag)
            posts = hashtag_obj.get_posts()
            
            for i, post in enumerate(posts):
                if i >= limit:
                    break
                
                try:
                    # Get post data
                    caption = post.caption or ""
                    
                    # Filter for scholarship content
                    caption_lower = caption.lower()
                    if any(kw in caption_lower for kw in ['scholarship', 'grant', 'funding', 'financial aid']):
                        
                        scholarship = Scholarship(
                            title=f"Instagram: {caption[:50]}..." if caption else f"Post by @{post.owner_username}",
                            source_url=f"https://instagram.com/p/{post.shortcode}",
                            description=caption[:500],
                            platform="instagram",
                            date_posted=post.date_local
                        )
                        
                        scholarships.append(scholarship)
                        print(f"  Found: {scholarship.title[:40]}...")
                    
                    # Respectful delay between posts
                    time.sleep(random.uniform(2, 4))
                    
                except Exception as e:
                    print(f"  Error processing post: {e}")
                    continue
            
            # Log progress
            print(f"\nProcessed {min(i+1, limit)} posts, found {len(scholarships)} scholarships")
            
        except instaloader.exceptions.LoginRequiredException:
            print("Login required. Run interactive_login() first.")
        except instaloader.exceptions.QueryReturnedBadRequestException as e:
            print(f"Rate limited or blocked: {e}")
            print("Wait a few hours before trying again.")
        except Exception as e:
            print(f"Error: {e}")
        
        return scholarships
    
    def scrape_multiple_hashtags(self, hashtags, limit_per_hashtag=10):
        """Scrape multiple hashtags with delays between each."""
        all_scholarships = []
        
        for hashtag in hashtags:
            print(f"\n{'='*40}")
            results = self.scrape_hashtag(hashtag, limit=limit_per_hashtag)
            all_scholarships.extend(results)
            
            # Longer delay between hashtags
            if hashtag != hashtags[-1]:
                delay = random.uniform(15, 30)
                print(f"Waiting {delay:.0f}s before next hashtag...")
                time.sleep(delay)
        
        return all_scholarships


if __name__ == "__main__":
    # First run: Create session
    # Uncomment and run once:
    # scraper = InstagramSessionScraper()
    # scraper.interactive_login("your_username")
    
    # After session is saved:
    USERNAME = os.getenv("INSTAGRAM_USERNAME", "parthzanwar112@gmail.com")
    
    scraper = InstagramSessionScraper(username=USERNAME)
    
    hashtags = ["scholarship", "scholarships", "studyabroad"]
    results = scraper.scrape_multiple_hashtags(hashtags, limit_per_hashtag=5)
    
    print(f"\n{'='*60}")
    print(f"Total scholarships found: {len(results)}")
    for s in results:
        print(f"  - {s.title}")

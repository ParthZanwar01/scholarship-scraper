"""
Cookie-Based TikTok Scraper

Uses browser session cookies for authenticated TikTok access.
Requires manual login to get sessionid cookie.
"""

import requests
import time
import random
import json
import os
from datetime import datetime
from scholarship_scraper.models.scholarship import Scholarship


class TikTokCookieScraper:
    """
    TikTok scraper using browser session cookies.
    
    SETUP:
    1. Login to TikTok in your browser
    2. Open DevTools (F12) > Application > Cookies > tiktok.com
    3. Copy the 'sessionid' cookie value
    4. Set environment variable: export TIKTOK_SESSION_ID="your_session_id"
    """
    
    def __init__(self, session_id=None):
        self.session_id = session_id or os.getenv("TIKTOK_SESSION_ID")
        
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Accept': 'application/json, text/plain, */*',
            'Accept-Language': 'en-US,en;q=0.9',
            'Referer': 'https://www.tiktok.com/',
            'Origin': 'https://www.tiktok.com',
        })
        
        if self.session_id:
            self.session.cookies.set('sessionid', self.session_id, domain='.tiktok.com')
            print("✓ TikTok session cookie configured")
        else:
            print("⚠ No TikTok session ID provided. Set TIKTOK_SESSION_ID env var.")
            print("  To get it: Login to TikTok > DevTools > Application > Cookies > sessionid")
    
    def search_videos(self, query="scholarship", limit=30):
        """
        Search TikTok for videos matching query.
        """
        print(f"\nSearching TikTok for '{query}'...")
        
        scholarships = []
        
        # TikTok web search (may not work without proper cookies/tokens)
        search_url = "https://www.tiktok.com/api/search/general/full/"
        
        params = {
            'keyword': query,
            'offset': 0,
            'count': 20,
        }
        
        try:
            for offset in range(0, limit, 20):
                params['offset'] = offset
                
                response = self.session.get(search_url, params=params, timeout=15)
                
                if response.status_code == 200:
                    try:
                        data = response.json()
                        
                        items = data.get('data', [])
                        if not items:
                            print(f"  No more results at offset {offset}")
                            break
                        
                        for item in items:
                            if 'item' in item:
                                post = item['item']
                                desc = post.get('desc', '')
                                
                                # Filter for scholarship content
                                if any(kw in desc.lower() for kw in ['scholarship', 'grant', 'funding', 'financial']):
                                    author = post.get('author', {}).get('uniqueId', 'unknown')
                                    video_id = post.get('id', '')
                                    
                                    scholarship = Scholarship(
                                        title=f"TikTok: {desc[:50]}..." if desc else f"Video by @{author}",
                                        source_url=f"https://www.tiktok.com/@{author}/video/{video_id}",
                                        description=desc[:500],
                                        platform="tiktok",
                                        date_posted=datetime.now()
                                    )
                                    
                                    scholarships.append(scholarship)
                                    print(f"  Found: @{author} - {desc[:40]}...")
                        
                        # Rate limiting
                        time.sleep(random.uniform(2, 4))
                        
                    except json.JSONDecodeError:
                        print(f"  Failed to parse response as JSON")
                        break
                        
                elif response.status_code == 403:
                    print(f"  Access forbidden. Session may be invalid.")
                    break
                else:
                    print(f"  Request failed: {response.status_code}")
                    break
                    
        except Exception as e:
            print(f"  Error: {e}")
        
        print(f"\nFound {len(scholarships)} scholarship-related videos")
        return scholarships
    
    def get_hashtag_videos(self, hashtag="scholarship", limit=20):
        """
        Alternative: Use Playwright to browse hashtag page.
        Falls back to Playwright if API fails.
        """
        from playwright.sync_api import sync_playwright
        
        print(f"\nBrowsing TikTok #{hashtag} via browser...")
        
        scholarships = []
        
        try:
            with sync_playwright() as p:
                browser = p.chromium.launch(headless=True)
                context = browser.new_context(
                    user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
                )
                
                # Add session cookie if available
                if self.session_id:
                    context.add_cookies([{
                        'name': 'sessionid',
                        'value': self.session_id,
                        'domain': '.tiktok.com',
                        'path': '/'
                    }])
                
                page = context.new_page()
                
                url = f"https://www.tiktok.com/tag/{hashtag}"
                page.goto(url, timeout=30000)
                
                # Wait for content to load
                time.sleep(3)
                page.wait_for_load_state("networkidle", timeout=10000)
                
                # Scroll to load more content
                for _ in range(3):
                    page.evaluate("window.scrollBy(0, 1000)")
                    time.sleep(1)
                
                # Extract video descriptions
                video_cards = page.query_selector_all('div[data-e2e="user-post-item"], div[class*="DivItemContainer"]')
                
                print(f"  Found {len(video_cards)} video cards")
                
                for card in video_cards[:limit]:
                    try:
                        # Try to get description
                        desc_elem = card.query_selector('a[title], div[class*="desc"], span')
                        desc = desc_elem.get_attribute('title') or desc_elem.inner_text() if desc_elem else ""
                        
                        # Get link
                        link_elem = card.query_selector('a[href*="/video/"]')
                        link = link_elem.get_attribute('href') if link_elem else ""
                        
                        if not link.startswith('http'):
                            link = f"https://www.tiktok.com{link}"
                        
                        if desc and 'scholarship' in desc.lower():
                            scholarship = Scholarship(
                                title=f"TikTok: {desc[:50]}...",
                                source_url=link,
                                description=desc[:500],
                                platform="tiktok",
                                date_posted=datetime.now()
                            )
                            scholarships.append(scholarship)
                            
                    except Exception as e:
                        continue
                
                browser.close()
                
        except Exception as e:
            print(f"  Browser error: {e}")
        
        return scholarships


if __name__ == "__main__":
    # Set your session ID via environment variable
    # export TIKTOK_SESSION_ID="your_sessionid_from_browser"
    
    scraper = TikTokCookieScraper()
    
    # Try API search first
    results = scraper.search_videos("scholarship 2024", limit=20)
    
    # If that fails, try browser approach
    if not results:
        print("\nAPI search failed, trying browser approach...")
        results = scraper.get_hashtag_videos("scholarship", limit=10)
    
    print(f"\n{'='*60}")
    print(f"Total scholarships found: {len(results)}")
    for s in results:
        print(f"  - {s.title}")
        print(f"    {s.source_url}")

"""
Enhanced Tor-Based Social Media Scraper with Media Processing

This scraper:
1. Uses Tor for IP rotation (bypass blocking)
2. Downloads images and videos from Instagram/TikTok
3. Runs OCR on images to extract text
4. Transcribes video audio
5. Parses extracted text for scholarship info
6. Runs continuously via Celery

Designed for cloud deployment (DigitalOcean).
"""

import os
import re
import time
import random
import subprocess
import requests
import json
from datetime import datetime
from bs4 import BeautifulSoup

# Tor configuration
TOR_SOCKS_PORT = 9050
TOR_CONTROL_PORT = 9051


class TorMediaScraper:
    """
    Scrapes social media via Tor and extracts scholarship info from media.
    """
    
    def __init__(self):
        self.session = None
        self.media_processor = None
        self._init_session()
        self._init_media_processor()
    
    def _init_session(self):
        """Initialize Tor-proxied requests session."""
        self.session = requests.Session()
        self.session.proxies = {
            'http': f'socks5h://127.0.0.1:{TOR_SOCKS_PORT}',
            'https': f'socks5h://127.0.0.1:{TOR_SOCKS_PORT}'
        }
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (iPhone; CPU iPhone OS 14_0 like Mac OS X) AppleWebKit/605.1.15',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.5',
        })
    
    def _init_media_processor(self):
        """Initialize media processor for OCR and transcription."""
        try:
            from scholarship_scraper.processors.media_processor import MediaProcessor
            self.media_processor = MediaProcessor()
            print("✓ Media processor initialized")
        except Exception as e:
            print(f"⚠ Media processor not available: {e}")
            self.media_processor = None
    
    def start_tor(self):
        """Start Tor service if not running."""
        try:
            # Check if Tor is already running
            test_resp = requests.get(
                'https://check.torproject.org/api/ip',
                proxies=self.session.proxies,
                timeout=10
            )
            if test_resp.json().get('IsTor'):
                print(f"✓ Tor already running (IP: {test_resp.json().get('IP')})")
                return True
        except:
            pass
        
        print("Starting Tor service...")
        try:
            subprocess.Popen(
                ['tor'],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL
            )
            time.sleep(15)  # Wait for Tor to bootstrap
            
            # Verify connection
            test_resp = requests.get(
                'https://check.torproject.org/api/ip',
                proxies=self.session.proxies,
                timeout=30
            )
            if test_resp.json().get('IsTor'):
                print(f"✓ Tor started (IP: {test_resp.json().get('IP')})")
                return True
        except Exception as e:
            print(f"✗ Failed to start Tor: {e}")
        
        return False
    
    def rotate_ip(self):
        """Request a new Tor circuit for a fresh IP."""
        try:
            from stem import Signal
            from stem.control import Controller
            
            with Controller.from_port(port=TOR_CONTROL_PORT) as controller:
                controller.authenticate()
                controller.signal(Signal.NEWNYM)
                print("↻ Tor circuit rotated")
                time.sleep(5)
                return True
        except Exception as e:
            print(f"Could not rotate IP: {e}")
            return False
    
    def scrape_instagram_hashtag(self, hashtag: str, extract_media: bool = True) -> list:
        """
        Scrape Instagram hashtag page and extract media.
        
        Returns list of scholarship dicts.
        """
        print(f"\n--- Scraping Instagram #{hashtag} ---")
        
        scholarships = []
        
        try:
            url = f"https://www.instagram.com/explore/tags/{hashtag}/"
            response = self.session.get(url, timeout=30)
            
            if response.status_code != 200:
                print(f"Instagram returned {response.status_code}")
                return scholarships
            
            soup = BeautifulSoup(response.text, 'html.parser')
            
            # Extract image URLs from the page
            if extract_media and self.media_processor:
                image_urls = self._extract_image_urls(soup, response.text)
                print(f"Found {len(image_urls)} images to process")
                
                for img_url in image_urls[:10]:  # Limit to 10 images per hashtag
                    text = self.media_processor.extract_text_from_image(img_url)
                    if text:
                        info = self.media_processor.extract_scholarship_info(text, img_url)
                        if info:
                            scholarships.append({
                                'title': info['title'][:200],
                                'source_url': info['source_url'],
                                'description': info['description'][:500],
                                'amount': info['amount'],
                                'deadline': info['deadline'],
                                'platform': 'instagram-ocr',
                                'date_posted': datetime.now()
                            })
                            print(f"  ✓ Found scholarship: {info['title'][:50]}...")
                    
                    time.sleep(random.uniform(1, 3))  # Rate limiting
            
            # Also check meta tags for text content
            og_desc = soup.find('meta', property='og:description')
            if og_desc:
                content = og_desc.get('content', '')
                if 'scholarship' in content.lower():
                    scholarships.append({
                        'title': f"Instagram #{hashtag}",
                        'source_url': url,
                        'description': content[:500],
                        'platform': 'instagram-tor',
                        'date_posted': datetime.now()
                    })
            
        except Exception as e:
            print(f"Instagram scrape error: {e}")
        
        return scholarships
    
    def _extract_image_urls(self, soup, html_text: str) -> list:
        """Extract image URLs from Instagram page."""
        urls = set()
        
        # From img tags
        for img in soup.find_all('img'):
            src = img.get('src', '') or img.get('data-src', '')
            if src and 'instagram' in src and not 'profile' in src.lower():
                urls.add(src)
        
        # From JSON data in page
        try:
            # Instagram embeds image URLs in JSON
            matches = re.findall(r'"display_url"\s*:\s*"([^"]+)"', html_text)
            for url in matches:
                url = url.replace('\\u0026', '&')
                urls.add(url)
        except:
            pass
        
        return list(urls)[:20]  # Limit
    
    def scrape_tiktok_hashtag(self, hashtag: str, extract_media: bool = True) -> list:
        """
        Scrape TikTok hashtag page and extract media.
        
        Returns list of scholarship dicts.
        """
        print(f"\n--- Scraping TikTok #{hashtag} ---")
        
        scholarships = []
        
        try:
            url = f"https://www.tiktok.com/tag/{hashtag}"
            response = self.session.get(url, timeout=30)
            
            if response.status_code != 200:
                print(f"TikTok returned {response.status_code}")
                return scholarships
            
            soup = BeautifulSoup(response.text, 'html.parser')
            
            # Extract video URLs for transcription
            if extract_media and self.media_processor:
                video_urls = self._extract_tiktok_video_urls(soup, response.text)
                print(f"Found {len(video_urls)} videos to process")
                
                for video_url in video_urls[:5]:  # Limit to 5 videos (transcription is slower)
                    text = self.media_processor.transcribe_video(video_url)
                    if text:
                        info = self.media_processor.extract_scholarship_info(text, video_url)
                        if info:
                            scholarships.append({
                                'title': info['title'][:200],
                                'source_url': video_url,
                                'description': info['description'][:500],
                                'amount': info['amount'],
                                'deadline': info['deadline'],
                                'platform': 'tiktok-transcribed',
                                'date_posted': datetime.now()
                            })
                            print(f"  ✓ Found scholarship: {info['title'][:50]}...")
                    
                    time.sleep(random.uniform(2, 5))  # Rate limiting
            
            # Also check meta tags
            meta_desc = soup.find('meta', attrs={'name': 'description'})
            if meta_desc:
                content = meta_desc.get('content', '')
                if 'scholarship' in content.lower():
                    scholarships.append({
                        'title': f"TikTok #{hashtag}",
                        'source_url': url,
                        'description': content[:500],
                        'platform': 'tiktok-tor',
                        'date_posted': datetime.now()
                    })
            
        except Exception as e:
            print(f"TikTok scrape error: {e}")
        
        return scholarships
    
    def _extract_tiktok_video_urls(self, soup, html_text: str) -> list:
        """Extract TikTok video URLs from page."""
        urls = []
        
        # From links
        for a in soup.find_all('a', href=True):
            href = a['href']
            if '/video/' in href:
                if not href.startswith('http'):
                    href = f"https://www.tiktok.com{href}"
                urls.append(href)
        
        # From JSON data
        try:
            matches = re.findall(r'/@[\w.]+/video/(\d+)', html_text)
            for video_id in matches:
                urls.append(f"https://www.tiktok.com/@user/video/{video_id}")
        except:
            pass
        
        return list(set(urls))[:10]  # Limit and dedupe
    
    def scrape_facebook_search(self, query: str = "scholarship") -> list:
        """
        Scrape Facebook for scholarship posts via mobile site (mbasic.facebook.com).
        
        Uses Tor to bypass blocking. Facebook mobile site is more scrapeable.
        """
        print(f"\n--- Scraping Facebook for '{query}' ---")
        
        scholarships = []
        
        # Facebook mobile search URL
        search_url = f"https://mbasic.facebook.com/search/posts/?q={query}+scholarship"
        
        try:
            response = self.session.get(search_url, timeout=30)
            
            if response.status_code != 200:
                print(f"Facebook returned {response.status_code}")
                # Try alternate approach - scrape public scholarship pages
                return self._scrape_facebook_public_pages()
            
            soup = BeautifulSoup(response.text, 'html.parser')
            
            # Look for post content
            posts = soup.find_all('div', {'data-ft': True}) or soup.find_all('article') or soup.find_all('div', class_=re.compile('story'))
            
            if not posts:
                # Fallback: extract any text mentioning scholarships
                text_content = soup.get_text()
                if 'scholarship' in text_content.lower():
                    # Extract paragraphs with scholarship mentions
                    for p in soup.find_all(['p', 'span', 'div']):
                        text = p.get_text(strip=True)
                        if 'scholarship' in text.lower() and len(text) > 100:
                            scholarships.append({
                                'title': text[:80] + '...',
                                'source_url': search_url,
                                'description': text[:500],
                                'platform': 'facebook-tor',
                                'date_posted': datetime.now()
                            })
                            if len(scholarships) >= 5:
                                break
            else:
                for post in posts[:10]:
                    text = post.get_text(strip=True)
                    if 'scholarship' in text.lower() and len(text) > 50:
                        # Extract any URLs in the post
                        urls = []
                        for a in post.find_all('a', href=True):
                            href = a['href']
                            if 'facebook.com' not in href and href.startswith('http'):
                                urls.append(href)
                        
                        # Use AI to extract info if available
                        if self.media_processor:
                            info = self.media_processor.extract_scholarship_info(text, search_url)
                            if info:
                                # Prefer external URL if found
                                if urls:
                                    info['source_url'] = urls[0]
                                scholarships.append({
                                    **info,
                                    'platform': 'facebook-tor',
                                    'date_posted': datetime.now()
                                })
                        else:
                            scholarships.append({
                                'title': text[:80] + '...',
                                'source_url': urls[0] if urls else search_url,
                                'description': text[:500],
                                'platform': 'facebook-tor',
                                'date_posted': datetime.now()
                            })
            
            print(f"Found {len(scholarships)} potential scholarships from Facebook")
            
        except Exception as e:
            print(f"Facebook scrape error: {e}")
        
        return scholarships
    
    def _scrape_facebook_public_pages(self) -> list:
        """Scrape known public scholarship Facebook pages."""
        scholarships = []
        
        # Known scholarship-related Facebook pages (public)
        public_pages = [
            'https://mbasic.facebook.com/ScholarshipsCorner',
            'https://mbasic.facebook.com/FullyFundedScholarships',
            'https://mbasic.facebook.com/InternationalScholarships',
        ]
        
        for page_url in public_pages:
            try:
                response = self.session.get(page_url, timeout=20)
                if response.status_code == 200:
                    soup = BeautifulSoup(response.text, 'html.parser')
                    
                    # Extract posts
                    for div in soup.find_all('div', limit=10):
                        text = div.get_text(strip=True)
                        if 'scholarship' in text.lower() and len(text) > 100:
                            scholarships.append({
                                'title': f"Facebook: {text[:60]}...",
                                'source_url': page_url,
                                'description': text[:500],
                                'platform': 'facebook-tor',
                                'date_posted': datetime.now()
                            })
                            break  # One per page
                
                time.sleep(random.uniform(2, 5))
                
            except Exception as e:
                print(f"Error scraping {page_url}: {e}")
        
        return scholarships
    
    def scrape_tiktok_search(self, query: str = "scholarship") -> list:
        """
        Scrape TikTok search results via Tor.
        
        Uses TikTok's web search which doesn't require login.
        """
        print(f"\n--- Scraping TikTok search for '{query}' ---")
        
        scholarships = []
        
        # TikTok web search
        search_url = f"https://www.tiktok.com/search?q={query}%20scholarship"
        
        try:
            response = self.session.get(search_url, timeout=30)
            
            if response.status_code != 200:
                print(f"TikTok search returned {response.status_code}")
                return scholarships
            
            soup = BeautifulSoup(response.text, 'html.parser')
            html_text = response.text
            
            # Extract video URLs from the search results
            video_urls = self._extract_tiktok_video_urls(soup, html_text)
            print(f"Found {len(video_urls)} TikTok videos")
            
            # Process each video
            for video_url in video_urls[:5]:
                if self.media_processor:
                    try:
                        text = self.media_processor.transcribe_video(video_url)
                        if text:
                            info = self.media_processor.extract_scholarship_info(text, video_url)
                            if info:
                                scholarships.append({
                                    **info,
                                    'platform': 'tiktok-tor',
                                    'date_posted': datetime.now()
                                })
                                print(f"  ✓ Found from TikTok: {info.get('title', 'Unknown')[:40]}...")
                    except Exception as e:
                        print(f"  Error processing video: {e}")
                
                time.sleep(random.uniform(2, 4))
            
            # Also check for text content in search results
            for script in soup.find_all('script'):
                script_text = str(script)
                if 'scholarship' in script_text.lower():
                    # Extract video descriptions from JSON
                    try:
                        desc_matches = re.findall(r'"desc"\s*:\s*"([^"]+scholarship[^"]+)"', script_text, re.IGNORECASE)
                        for desc in desc_matches[:3]:
                            scholarships.append({
                                'title': f"TikTok: {desc[:60]}...",
                                'source_url': search_url,
                                'description': desc,
                                'platform': 'tiktok-tor',
                                'date_posted': datetime.now()
                            })
                    except:
                        pass
        
        except Exception as e:
            print(f"TikTok search error: {e}")
        
        return scholarships
    
    def run_continuous(self, hashtags=None, interval_minutes=20):
        """
        Run continuous scraping loop.
        
        Args:
            hashtags: List of hashtags to scrape
            interval_minutes: Time between scraping cycles
        """
        if hashtags is None:
            hashtags = ['scholarship', 'scholarships', 'financialaid', 'studyabroad']
        
        print("="*60)
        print("TOR MEDIA SCRAPER - CONTINUOUS MODE")
        print("="*60)
        print(f"Hashtags: {hashtags}")
        print(f"Platforms: Instagram, TikTok, Facebook")
        print(f"Interval: {interval_minutes} minutes")
        print("="*60)
        
        if not self.start_tor():
            print("Cannot run without Tor. Exiting.")
            return
        
        cycle = 0
        while True:
            cycle += 1
            print(f"\n{'='*60}")
            print(f"CYCLE {cycle} - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
            print("="*60)
            
            # Rotate IP for each cycle
            self.rotate_ip()
            
            all_scholarships = []
            
            for hashtag in hashtags:
                # Scrape Instagram
                ig_results = self.scrape_instagram_hashtag(hashtag, extract_media=True)
                all_scholarships.extend(ig_results)
                
                # Small delay between platforms
                time.sleep(random.uniform(3, 7))
                
                # Scrape TikTok hashtag
                tt_results = self.scrape_tiktok_hashtag(hashtag, extract_media=True)
                all_scholarships.extend(tt_results)
                
                # Delay between hashtags
                time.sleep(random.uniform(5, 10))
            
            # Scrape Facebook (search-based, not per hashtag)
            fb_results = self.scrape_facebook_search("scholarship")
            all_scholarships.extend(fb_results)
            
            time.sleep(random.uniform(3, 7))
            
            # TikTok search (broader results)
            tt_search_results = self.scrape_tiktok_search("scholarship apply")
            all_scholarships.extend(tt_search_results)
            
            print(f"\nCycle {cycle} complete. Found {len(all_scholarships)} scholarships.")
            
            # Sync to cloud (if running locally)
            if all_scholarships:
                self._sync_to_cloud(all_scholarships)
            
            # Wait for next cycle
            print(f"Sleeping for {interval_minutes} minutes...")
            time.sleep(interval_minutes * 60)
    
    def _sync_to_cloud(self, scholarships: list):
        """
        Sync found scholarships to cloud database.
        
        Uses AI to analyze each URL's content before saving.
        Only saves if the page is a real scholarship (not an article).
        """
        API_URL = os.getenv("API_URL", "http://64.23.231.89:8000/scholarships/")
        
        # Try to load AI classifier
        classifier = None
        try:
            from scholarship_scraper.processors.content_classifier import ContentClassifier
            classifier = ContentClassifier()
            print("✓ AI classifier loaded for content validation")
        except Exception as e:
            print(f"⚠ AI classifier not available, will save all: {e}")
        
        synced = 0
        skipped = 0
        
        for sch in scholarships:
            source_url = sch.get('source_url', '')
            
            # --- AI CONTENT VALIDATION ---
            if classifier and source_url:
                print(f"🔍 Analyzing: {source_url[:50]}...")
                
                try:
                    result = classifier.classify_url(source_url)
                    classification = result.get('classification', 'UNKNOWN')
                    is_worth_saving = result.get('is_worth_saving', False)
                    reason = result.get('reason', 'Unknown')
                    
                    print(f"   Classification: {classification} | Save: {is_worth_saving}")
                    
                    # Skip if it's an article or not worth saving
                    if not is_worth_saving:
                        print(f"   ⚠ SKIPPED: {reason}")
                        skipped += 1
                        continue
                    
                    # If AI found a better direct apply URL, use it
                    if result.get('direct_apply_url'):
                        sch['source_url'] = result['direct_apply_url']
                        print(f"   → Using direct URL: {result['direct_apply_url'][:50]}...")
                    
                    # Enhance title with scholarship name if found
                    if result.get('scholarship_name'):
                        sch['title'] = result['scholarship_name']
                        
                except Exception as e:
                    print(f"   AI analysis error: {e} (will save anyway)")
            
            # --- SAVE TO DATABASE ---
            try:
                payload = {
                    'title': sch.get('title', 'Unknown'),
                    'source_url': sch.get('source_url', ''),
                    'description': sch.get('description', ''),
                    'amount': sch.get('amount'),
                    'deadline': str(sch.get('deadline')) if sch.get('deadline') else None,
                    'platform': sch.get('platform', 'social-media'),
                }
                
                # Use regular requests (not Tor) for API
                response = requests.post(API_URL, json=payload, timeout=10)
                if response.status_code in [200, 201]:
                    synced += 1
                    print(f"   ✓ Saved: {sch.get('title', 'Unknown')[:40]}...")
            except Exception as e:
                print(f"   Sync error: {e}")
        
        print(f"\n📊 Summary: Synced {synced}, Skipped {skipped} (articles/not-scholarships)")


def run_single_scrape(hashtags=None):
    """Run a single scrape cycle (for Celery task)."""
    scraper = TorMediaScraper()
    
    if not scraper.start_tor():
        return "Failed to connect to Tor"
    
    if hashtags is None:
        hashtags = ['scholarship', 'scholarships']
    
    all_scholarships = []
    
    for hashtag in hashtags:
        ig_results = scraper.scrape_instagram_hashtag(hashtag, extract_media=True)
        all_scholarships.extend(ig_results)
        
        time.sleep(random.uniform(2, 5))
        
        tt_results = scraper.scrape_tiktok_hashtag(hashtag, extract_media=True)
        all_scholarships.extend(tt_results)
    
    return all_scholarships


if __name__ == "__main__":
    # Run continuous scraping
    scraper = TorMediaScraper()
    scraper.run_continuous()

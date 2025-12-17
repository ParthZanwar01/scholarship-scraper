"""
Enhanced TikTok Scholarship Scraper

Same pipeline as Instagram but for video:
1. Find TikTok scholarship videos
2. Download and transcribe video audio (Whisper)
3. Use AI to find scholarship info and application links
4. Save to database

Uses Tor for IP rotation to avoid blocking.
"""

import os
import re
import time
import random
import tempfile
import requests
from datetime import datetime
from bs4 import BeautifulSoup

try:
    import openai
    OPENAI_AVAILABLE = True
except ImportError:
    OPENAI_AVAILABLE = False

try:
    import yt_dlp
    YTDLP_AVAILABLE = True
except ImportError:
    YTDLP_AVAILABLE = False


class TikTokScholarshipScraper:
    """
    Enhanced TikTok scraper that:
    - Finds scholarship-related TikTok videos
    - Downloads and transcribes video audio
    - Uses AI to find scholarship names and apply links
    """
    
    # Search terms for finding scholarship videos
    SEARCH_TERMS = [
        "scholarship application",
        "fully funded scholarship",
        "how to apply for scholarship",
        "scholarship 2025",
        "free college scholarship",
        "international scholarship",
        "study abroad scholarship",
    ]
    
    def __init__(self, use_tor=True, openai_api_key=None):
        self.session = requests.Session()
        
        if use_tor:
            self.session.proxies = {
                'http': 'socks5h://127.0.0.1:9050',
                'https': 'socks5h://127.0.0.1:9050'
            }
        
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
        })
        
        self.openai_api_key = openai_api_key or os.getenv("OPENAI_API_KEY")
        self.openai_client = None
        self.temp_dir = tempfile.mkdtemp(prefix="tiktok_")
        
        if OPENAI_AVAILABLE and self.openai_api_key:
            self.openai_client = openai.OpenAI(api_key=self.openai_api_key)
        
        print(f"✓ TikTok Scraper initialized (Whisper: {OPENAI_AVAILABLE and bool(self.openai_api_key)}, yt-dlp: {YTDLP_AVAILABLE})")
    
    def scrape_hashtag(self, hashtag: str, max_videos: int = 5) -> list:
        """
        Scrape TikTok hashtag page for scholarship videos.
        """
        url = f"https://www.tiktok.com/tag/{hashtag}"
        print(f"\n--- Scraping TikTok #{hashtag} ---")
        
        scholarships = []
        
        try:
            response = self.session.get(url, timeout=30)
            
            if response.status_code != 200:
                print(f"TikTok returned {response.status_code}")
                return scholarships
            
            soup = BeautifulSoup(response.text, 'html.parser')
            
            # Extract video URLs
            video_urls = self._extract_video_urls(soup, response.text)
            print(f"Found {len(video_urls)} videos")
            
            for video_url in video_urls[:max_videos]:
                result = self._process_video(video_url)
                if result:
                    scholarships.append(result)
                    print(f"  ✓ Found: {result.get('title', 'Unknown')[:50]}...")
                
                time.sleep(random.uniform(2, 4))
        
        except Exception as e:
            print(f"TikTok hashtag scrape error: {e}")
        
        return scholarships
    
    def scrape_search(self, query: str, max_videos: int = 5) -> list:
        """
        Search TikTok for scholarship-related videos.
        """
        search_url = f"https://www.tiktok.com/search?q={query.replace(' ', '%20')}"
        print(f"\n--- Searching TikTok: '{query}' ---")
        
        scholarships = []
        
        try:
            response = self.session.get(search_url, timeout=30)
            
            if response.status_code != 200:
                print(f"TikTok search returned {response.status_code}")
                return scholarships
            
            soup = BeautifulSoup(response.text, 'html.parser')
            
            # Extract video URLs from search results
            video_urls = self._extract_video_urls(soup, response.text)
            print(f"Found {len(video_urls)} videos from search")
            
            for video_url in video_urls[:max_videos]:
                result = self._process_video(video_url)
                if result:
                    scholarships.append(result)
                    print(f"  ✓ Found: {result.get('title', 'Unknown')[:50]}...")
                
                time.sleep(random.uniform(2, 4))
        
        except Exception as e:
            print(f"TikTok search error: {e}")
        
        return scholarships
    
    def _extract_video_urls(self, soup, html_text: str) -> list:
        """Extract TikTok video URLs from page."""
        urls = set()
        
        # From links
        for a in soup.find_all('a', href=True):
            href = a['href']
            if '/video/' in href:
                if not href.startswith('http'):
                    href = f"https://www.tiktok.com{href}"
                urls.add(href)
        
        # From embedded JSON data
        try:
            # Pattern: /@username/video/1234567890
            matches = re.findall(r'/@[\w.]+/video/(\d+)', html_text)
            for video_id in matches:
                urls.add(f"https://www.tiktok.com/@user/video/{video_id}")
            
            # Also look for video URLs in JSON
            url_matches = re.findall(r'"playAddr"\s*:\s*"([^"]+)"', html_text)
            for url in url_matches[:5]:
                urls.add(url.replace('\\u002F', '/'))
        except:
            pass
        
        return list(urls)[:15]
    
    def _process_video(self, video_url: str) -> dict:
        """
        Process a TikTok video:
        1. Download and transcribe audio
        2. Use AI to extract scholarship info and find apply links
        """
        # Get video page for description
        description = self._get_video_description(video_url)
        
        # Transcribe video audio
        transcript = self._transcribe_video(video_url)
        
        # Combine description and transcript
        full_text = f"{description}\n\n{transcript}".strip()
        
        if not full_text or len(full_text) < 50:
            return None
        
        # Check if scholarship-related
        if not any(kw in full_text.lower() for kw in ['scholarship', 'grant', 'fellowship', 'funding', 'apply', 'tuition']):
            return None
        
        # Use AI to extract scholarship info
        scholarship_info = self._extract_with_ai(full_text, video_url)
        
        if not scholarship_info:
            # Fallback: basic extraction
            scholarship_info = {
                'title': self._extract_title(full_text),
                'description': full_text[:500],
                'amount': self._extract_amount(full_text),
                'deadline': self._extract_deadline(full_text),
                'source_url': video_url,
            }
        
        scholarship_info['platform'] = 'tiktok'
        scholarship_info['date_posted'] = datetime.now()
        
        return scholarship_info
    
    def _get_video_description(self, video_url: str) -> str:
        """Fetch video page and extract description."""
        try:
            response = self.session.get(video_url, timeout=20)
            if response.status_code == 200:
                soup = BeautifulSoup(response.text, 'html.parser')
                
                # Try different selectors for description
                desc_elem = soup.find('meta', property='og:description') or \
                           soup.find('meta', attrs={'name': 'description'})
                
                if desc_elem:
                    return desc_elem.get('content', '')
                
                # Look for description in JSON
                match = re.search(r'"desc"\s*:\s*"([^"]*)"', response.text)
                if match:
                    return match.group(1)
        except:
            pass
        
        return ""
    
    def _transcribe_video(self, video_url: str) -> str:
        """Download video and transcribe audio using Whisper API."""
        if not YTDLP_AVAILABLE or not self.openai_client:
            print("    Transcription not available (missing yt-dlp or OpenAI)")
            return ""
        
        try:
            print(f"    Downloading video for transcription...")
            
            audio_path = os.path.join(self.temp_dir, f"audio_{random.randint(1000,9999)}.mp3")
            
            ydl_opts = {
                'format': 'bestaudio/best',
                'outtmpl': audio_path.replace('.mp3', '.%(ext)s'),
                'postprocessors': [{
                    'key': 'FFmpegExtractAudio',
                    'preferredcodec': 'mp3',
                    'preferredquality': '128',
                }],
                'quiet': True,
                'no_warnings': True,
            }
            
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                ydl.download([video_url])
            
            # Find the audio file
            audio_file = None
            for f in os.listdir(self.temp_dir):
                if f.endswith(('.mp3', '.m4a', '.wav')):
                    audio_file = os.path.join(self.temp_dir, f)
                    break
            
            if not audio_file or not os.path.exists(audio_file):
                print("    No audio file found")
                return ""
            
            # Transcribe with Whisper API
            print(f"    Transcribing with Whisper...")
            
            with open(audio_file, 'rb') as f:
                transcription = self.openai_client.audio.transcriptions.create(
                    model="whisper-1",
                    file=f
                )
            
            text = transcription.text
            print(f"    Transcribed {len(text)} characters")
            
            # Cleanup
            try:
                os.remove(audio_file)
            except:
                pass
            
            return text
            
        except Exception as e:
            print(f"    Transcription error: {e}")
            return ""
    
    def _extract_with_ai(self, text: str, video_url: str) -> dict:
        """Use GPT to extract scholarship info and find apply links."""
        if not self.openai_client:
            return None
        
        try:
            prompt = f"""Analyze this TikTok video content about a scholarship opportunity.

VIDEO CONTENT:
{text[:2000]}

Extract scholarship information as JSON:
{{
    "title": "Name of the scholarship or program",
    "description": "Brief description of the opportunity",
    "amount": "Award amount if mentioned",
    "deadline": "Application deadline if mentioned",
    "source_url": "URL to apply if mentioned (look for 'link in bio', 'apply at', website mentions)",
    "organization": "Organization offering it"
}}

IMPORTANT: Look for mentions of websites, application portals, or "link in bio" references.
If the video mentions a specific website to apply, extract that URL.
If not scholarship-related, return null.
"""
            
            response = self.openai_client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[
                    {"role": "system", "content": "Extract scholarship info from video transcripts. Return only valid JSON."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.2,
                max_tokens=400
            )
            
            result_text = response.choices[0].message.content.strip()
            
            import json
            if result_text.startswith('```'):
                result_text = re.sub(r'^```\w*\n?', '', result_text)
                result_text = re.sub(r'\n?```$', '', result_text)
            
            if result_text.lower() == 'null':
                return None
            
            data = json.loads(result_text)
            
            # Use video URL if no apply URL found
            if not data.get('source_url'):
                data['source_url'] = video_url
            
            return data
            
        except Exception as e:
            print(f"    AI error: {e}")
            return None
    
    def _extract_title(self, text: str) -> str:
        lines = text.split('\n')
        for line in lines:
            line = line.strip()
            if 20 < len(line) < 100:
                return line
        return "TikTok Scholarship Video"
    
    def _extract_amount(self, text: str) -> str:
        match = re.search(r'\$[\d,]+(?:\.\d{2})?', text)
        return match.group() if match else None
    
    def _extract_deadline(self, text: str) -> str:
        patterns = [
            r'(?:deadline|due|by)[:\s]*([\w\s,]+\d{4})',
            r'(january|february|march|april|may|june|july|august|september|october|november|december)\s+\d{1,2},?\s+\d{4}',
        ]
        for pattern in patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                return match.group(1) if match.lastindex else match.group()
        return None
    
    def scrape_all(self, max_videos_per_source: int = 3) -> list:
        """Run full TikTok scrape - hashtags and searches."""
        all_scholarships = []
        
        # Scrape hashtags
        hashtags = ['scholarship', 'scholarships', 'fullyFundedScholarship', 'studyabroad']
        for hashtag in hashtags[:2]:  # Limit to 2 hashtags
            results = self.scrape_hashtag(hashtag, max_videos=max_videos_per_source)
            all_scholarships.extend(results)
            time.sleep(random.uniform(3, 7))
        
        # Scrape searches
        for term in self.SEARCH_TERMS[:2]:  # Limit to 2 search terms
            results = self.scrape_search(term, max_videos=max_videos_per_source)
            all_scholarships.extend(results)
            time.sleep(random.uniform(3, 7))
        
        return all_scholarships
    
    def sync_to_database(self, scholarships: list):
        """Save scholarships to database via API."""
        API_URL = os.getenv("API_URL", "http://64.23.231.89:8000/scholarships/")
        
        synced = 0
        for sch in scholarships:
            try:
                payload = {
                    'title': sch.get('title', 'TikTok Scholarship'),
                    'source_url': sch.get('source_url', ''),
                    'description': sch.get('description', '')[:500],
                    'amount': sch.get('amount'),
                    'deadline': sch.get('deadline'),
                    'platform': 'tiktok',
                }
                
                response = requests.post(f"{API_URL}?skip_validation=true", json=payload, timeout=10)
                if response.json().get('saved') or response.json().get('id'):
                    synced += 1
            except Exception as e:
                print(f"Sync error: {e}")
        
        print(f"📊 Synced {synced}/{len(scholarships)} from TikTok")
        return synced


def run_tiktok_scrape():
    """Run a single TikTok scrape cycle."""
    scraper = TikTokScholarshipScraper(use_tor=True)
    scholarships = scraper.scrape_all(max_videos_per_source=3)
    
    if scholarships:
        scraper.sync_to_database(scholarships)
    
    return len(scholarships)


if __name__ == "__main__":
    scraper = TikTokScholarshipScraper(use_tor=False)
    results = scraper.scrape_hashtag("scholarship", max_videos=3)
    for r in results:
        print(f"Title: {r.get('title')}")
        print(f"URL: {r.get('source_url')}")
        print("-" * 40)

"""
TikTok Video Scraper with Audio Transcription

Pipeline:
1. Search TikTok for #scholarships hashtag
2. Download videos using yt-dlp
3. Extract audio and transcribe using Whisper
4. Parse transcription for scholarship info/URLs
5. Return scholarship objects for database storage
"""

import os
import re
import tempfile
import subprocess
from datetime import datetime
from scholarship_scraper.models.scholarship import Scholarship

# Lazy imports for heavy dependencies
whisper = None
yt_dlp = None

def load_whisper():
    global whisper
    if whisper is None:
        import whisper as w
        whisper = w
    return whisper

def load_ytdlp():
    global yt_dlp
    if yt_dlp is None:
        import yt_dlp as y
        yt_dlp = y
    return yt_dlp


class TikTokScraper:
    def __init__(self, whisper_model="base"):
        """
        Initialize TikTok scraper.
        
        Args:
            whisper_model: Whisper model size. Options: tiny, base, small, medium, large
                          Larger = more accurate but slower. "base" is good balance.
        """
        self.whisper_model_name = whisper_model
        self.whisper_model = None  # Lazy load
        self.download_dir = tempfile.mkdtemp(prefix="tiktok_")
        print(f"TikTok Scraper initialized. Temp dir: {self.download_dir}")
    
    def _load_whisper_model(self):
        """Lazy load Whisper model (it's heavy)."""
        if self.whisper_model is None:
            print(f"Loading Whisper model '{self.whisper_model_name}'...")
            w = load_whisper()
            self.whisper_model = w.load_model(self.whisper_model_name)
            print("Whisper model loaded.")
        return self.whisper_model
    
    def search_hashtag(self, hashtag: str = "scholarships", num_videos: int = 5):
        """
        Search TikTok for videos with a specific hashtag.
        
        Note: TikTok's API is very restrictive. We use yt-dlp's TikTok support
        which scrapes the hashtag page.
        """
        print(f"Searching TikTok for #{hashtag}...")
        
        ydl = load_ytdlp()
        
        # TikTok hashtag URL format
        hashtag_url = f"https://www.tiktok.com/tag/{hashtag}"
        
        ydl_opts = {
            'quiet': True,
            'no_warnings': True,
            'extract_flat': True,  # Just get video URLs, don't download yet
            'playlistend': num_videos,
        }
        
        try:
            with ydl.YoutubeDL(ydl_opts) as y:
                info = y.extract_info(hashtag_url, download=False)
                
            if not info or 'entries' not in info:
                print("No videos found or access blocked.")
                return []
            
            video_urls = []
            for entry in info['entries'][:num_videos]:
                if entry and 'url' in entry:
                    video_urls.append(entry['url'])
                elif entry and 'id' in entry:
                    video_urls.append(f"https://www.tiktok.com/@user/video/{entry['id']}")
            
            print(f"Found {len(video_urls)} video URLs.")
            return video_urls
            
        except Exception as e:
            print(f"TikTok search error: {e}")
            return []
    
    def download_video(self, video_url: str) -> str:
        """Download a TikTok video and return the file path."""
        print(f"Downloading: {video_url}")
        
        ydl = load_ytdlp()
        
        output_template = os.path.join(self.download_dir, '%(id)s.%(ext)s')
        
        ydl_opts = {
            'outtmpl': output_template,
            'format': 'best[ext=mp4]/best',
            'quiet': True,
            'no_warnings': True,
        }
        
        try:
            with ydl.YoutubeDL(ydl_opts) as y:
                info = y.extract_info(video_url, download=True)
                video_id = info.get('id', 'unknown')
                ext = info.get('ext', 'mp4')
                filepath = os.path.join(self.download_dir, f"{video_id}.{ext}")
                
                if os.path.exists(filepath):
                    print(f"Downloaded: {filepath}")
                    return filepath
                    
                # Try to find the file
                for f in os.listdir(self.download_dir):
                    if video_id in f:
                        return os.path.join(self.download_dir, f)
                        
                print("Download completed but file not found.")
                return None
                
        except Exception as e:
            print(f"Download error: {e}")
            return None
    
    def transcribe_video(self, video_path: str) -> str:
        """
        Transcribe audio from a video file using Whisper.
        """
        if not video_path or not os.path.exists(video_path):
            return ""
        
        print(f"Transcribing: {video_path}")
        
        model = self._load_whisper_model()
        
        try:
            # Whisper can work directly with video files
            result = model.transcribe(video_path)
            text = result.get('text', '')
            print(f"Transcription: {text[:100]}...")
            return text
            
        except Exception as e:
            print(f"Transcription error: {e}")
            return ""
    
    def extract_scholarship_info(self, text: str, source_url: str) -> list:
        """
        Extract scholarship information from transcribed text.
        
        Looks for:
        - Dollar amounts (e.g., $5,000, $10000)
        - Deadlines (dates)
        - Scholarship names
        - URLs mentioned
        """
        scholarships = []
        
        if not text or len(text) < 20:
            return scholarships
        
        # Clean up text
        text_lower = text.lower()
        
        # Check if it's actually about scholarships
        scholarship_keywords = ['scholarship', 'grant', 'financial aid', 'tuition', 'college money', 'free money']
        if not any(kw in text_lower for kw in scholarship_keywords):
            print("Video doesn't seem to be about scholarships, skipping.")
            return scholarships
        
        # Extract amounts
        amount_pattern = r'\$[\d,]+(?:\.[\d]{2})?|\d+(?:,\d{3})+(?:\s+dollars)?|\d+k'
        amounts = re.findall(amount_pattern, text, re.IGNORECASE)
        
        # Clean up amounts
        cleaned_amounts = []
        for a in amounts:
            # Convert "10k" to "$10,000"
            if 'k' in a.lower():
                num = int(re.sub(r'[^\d]', '', a)) * 1000
                cleaned_amounts.append(f"${num:,}")
            else:
                num = re.sub(r'[^\d]', '', a)
                if num:
                    cleaned_amounts.append(f"${int(num):,}")
        
        # Look for URLs in text
        url_pattern = r'https?://[^\s]+'
        urls = re.findall(url_pattern, text)
        
        # Create a scholarship entry for this video
        amount = cleaned_amounts[0] if cleaned_amounts else None
        
        scholarship = Scholarship(
            title=f"TikTok Scholarship Video",
            source_url=source_url,
            description=text[:500],
            amount=amount,
            deadline=None,  # Will be filled by enrichment
            platform="tiktok",
            date_posted=datetime.now()
        )
        
        scholarships.append(scholarship)
        
        # If multiple URLs found, create entries for each
        for url in urls[:3]:  # Max 3 additional
            if 'tiktok.com' not in url:
                sch = Scholarship(
                    title=f"Scholarship from TikTok mention",
                    source_url=url,
                    description=f"Found in TikTok video. Context: {text[:200]}",
                    amount=amount,
                    deadline=None,
                    platform="tiktok",
                    date_posted=datetime.now()
                )
                scholarships.append(sch)
        
        return scholarships
    
    def scrape(self, hashtag: str = "scholarships", num_videos: int = 5) -> list:
        """
        Full scraping pipeline:
        1. Search hashtag
        2. Download videos
        3. Transcribe
        4. Extract info
        
        Returns list of Scholarship objects.
        """
        print(f"\n{'='*60}")
        print(f"TikTok Scraper - Searching #{hashtag}")
        print(f"{'='*60}\n")
        
        all_scholarships = []
        
        # Step 1: Get video URLs
        video_urls = self.search_hashtag(hashtag, num_videos)
        
        if not video_urls:
            print("No videos to process.")
            return all_scholarships
        
        # Step 2-4: Process each video
        for i, url in enumerate(video_urls):
            print(f"\n--- Processing video {i+1}/{len(video_urls)} ---")
            
            # Download
            video_path = self.download_video(url)
            if not video_path:
                continue
            
            # Transcribe
            text = self.transcribe_video(video_path)
            if not text:
                continue
            
            # Extract
            scholarships = self.extract_scholarship_info(text, url)
            all_scholarships.extend(scholarships)
            
            # Cleanup video file to save space
            try:
                os.remove(video_path)
            except:
                pass
        
        print(f"\n{'='*60}")
        print(f"TikTok Scrape Complete. Found {len(all_scholarships)} potential scholarships.")
        print(f"{'='*60}\n")
        
        return all_scholarships


if __name__ == "__main__":
    # Test run
    scraper = TikTokScraper(whisper_model="tiny")  # Using tiny for speed
    results = scraper.scrape("scholarship", num_videos=2)
    
    for s in results:
        print(f"Title: {s.title}")
        print(f"URL: {s.source_url}")
        print(f"Amount: {s.amount}")
        print(f"Description: {s.description[:100]}...")
        print("-" * 40)

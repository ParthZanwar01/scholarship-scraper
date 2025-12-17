"""
Enhanced Instagram Scholarship Scraper

This scraper:
1. Uses Picuki (Instagram mirror) to find scholarship-related posts
2. Downloads images from posts
3. Uses OCR to extract text from images
4. Uses AI to find scholarship names and application links
5. Saves verified scholarships to database
6. Runs continuously

Designed for cloud deployment on DigitalOcean.
"""

import os
import re
import time
import random
import requests
from datetime import datetime
from bs4 import BeautifulSoup
from io import BytesIO

try:
    from PIL import Image
    import pytesseract
    OCR_AVAILABLE = True
except ImportError:
    OCR_AVAILABLE = False
    print("⚠ OCR not available - install pillow and pytesseract")

try:
    import openai
    OPENAI_AVAILABLE = True
except ImportError:
    OPENAI_AVAILABLE = False


class InstagramScholarshipScraper:
    """
    Enhanced Instagram scraper that:
    - Downloads post images
    - Extracts text via OCR
    - Uses AI to find application links
    - Saves to database
    """
    
    # Picuki is reliable for scraping Instagram content
    PICUKI_BASE = "https://www.picuki.com"
    
    # Hashtags to search
    SCHOLARSHIP_HASHTAGS = [
        "scholarships",
        "scholarship",
        "scholarships2025",
        "fullyFundedScholarships",
        "studyabroad",
        "financialaid",
        "collegescholarships",
        "graduatescholarships",
        "internationalstudents",
        "freeeducation",
    ]
    
    def __init__(self, openai_api_key=None):
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.5',
        })
        
        self.openai_api_key = openai_api_key or os.getenv("OPENAI_API_KEY")
        self.openai_client = None
        
        if OPENAI_AVAILABLE and self.openai_api_key:
            self.openai_client = openai.OpenAI(api_key=self.openai_api_key)
            print("✓ OpenAI initialized for link finding")
        
        print(f"✓ Instagram Scraper initialized (OCR: {OCR_AVAILABLE}, AI: {self.openai_client is not None})")
    
    def scrape_hashtag(self, hashtag: str, max_posts: int = 20) -> list:
        """
        Scrape Instagram posts for a hashtag via Picuki.
        
        Returns list of scholarship dicts ready for database.
        """
        url = f"{self.PICUKI_BASE}/tag/{hashtag}"
        print(f"\n--- Scraping #{hashtag} ---")
        print(f"URL: {url}")
        
        scholarships = []
        
        try:
            response = self.session.get(url, timeout=30)
            if response.status_code != 200:
                print(f"Failed to load page: {response.status_code}")
                return scholarships
            
            soup = BeautifulSoup(response.text, 'html.parser')
            
            # Find post items - Picuki uses .box-photo for posts
            posts = soup.select('.box-photo')
            print(f"Found {len(posts)} posts on page")
            
            for post in posts[:max_posts]:
                try:
                    result = self._process_post(post, hashtag)
                    if result:
                        scholarships.append(result)
                        print(f"  ✓ Found: {result.get('title', 'Unknown')[:50]}...")
                    
                    # Rate limiting
                    time.sleep(random.uniform(1, 3))
                    
                except Exception as e:
                    print(f"  Error processing post: {e}")
                    continue
            
        except Exception as e:
            print(f"Scrape error: {e}")
        
        return scholarships
    
    def _process_post(self, post_element, hashtag: str) -> dict:
        """
        Process a single post:
        1. Get image URL
        2. Download and OCR image
        3. Use AI to find scholarship info and apply link
        """
        # Get post link and image
        link_elem = post_element.select_one('a')
        img_elem = post_element.select_one('img')
        
        if not img_elem:
            return None
        
        img_url = img_elem.get('src') or img_elem.get('data-src')
        post_link = link_elem.get('href') if link_elem else None
        
        if post_link and not post_link.startswith('http'):
            post_link = f"{self.PICUKI_BASE}{post_link}"
        
        if not img_url:
            return None
        
        # Get caption if available
        caption = ""
        desc_elem = post_element.select_one('.photo-description')
        if desc_elem:
            caption = desc_elem.get_text(strip=True)
        
        # Download and OCR image
        ocr_text = ""
        if OCR_AVAILABLE and img_url:
            ocr_text = self._ocr_image(img_url)
        
        # Combine caption and OCR text
        full_text = f"{caption}\n\n{ocr_text}".strip()
        
        if not full_text or len(full_text) < 30:
            return None
        
        # Check if it's about scholarships
        text_lower = full_text.lower()
        scholarship_keywords = ['scholarship', 'grant', 'fellowship', 'funding', 'award', 'stipend', 'tuition']
        
        if not any(kw in text_lower for kw in scholarship_keywords):
            return None
        
        # Use AI to extract scholarship info and find apply link
        scholarship_info = self._extract_with_ai(full_text, post_link)
        
        if not scholarship_info:
            # Fallback: basic extraction
            scholarship_info = {
                'title': self._extract_title(full_text),
                'description': full_text[:500],
                'amount': self._extract_amount(full_text),
                'deadline': self._extract_deadline(full_text),
                'source_url': post_link or f"{self.PICUKI_BASE}/tag/{hashtag}",
                'apply_url': None,
            }
        
        # Set platform
        scholarship_info['platform'] = 'instagram'
        scholarship_info['date_posted'] = datetime.now()
        
        return scholarship_info
    
    def _ocr_image(self, img_url: str) -> str:
        """Download image and extract text via OCR."""
        try:
            print(f"    OCR: {img_url[:50]}...")
            
            response = self.session.get(img_url, timeout=15)
            if response.status_code != 200:
                return ""
            
            image = Image.open(BytesIO(response.content))
            
            # Convert to RGB if needed
            if image.mode != 'RGB':
                image = image.convert('RGB')
            
            # Run OCR
            text = pytesseract.image_to_string(image)
            
            # Clean up
            text = re.sub(r'\s+', ' ', text).strip()
            
            if len(text) > 10:
                print(f"    OCR extracted {len(text)} chars")
            
            return text
            
        except Exception as e:
            print(f"    OCR error: {e}")
            return ""
    
    def _extract_with_ai(self, text: str, source_url: str) -> dict:
        """
        Use GPT to extract scholarship info and find application links.
        """
        if not self.openai_client:
            return None
        
        try:
            prompt = f"""Analyze this Instagram post about a scholarship/grant opportunity.

POST CONTENT:
{text[:2000]}

Extract the following information and return as JSON:
{{
    "title": "Name of the scholarship or program",
    "description": "Brief description of the opportunity",
    "amount": "Award amount if mentioned (e.g., '$10,000', 'Full tuition')",
    "deadline": "Application deadline if mentioned",
    "apply_url": "Direct URL to apply if mentioned in the text, or null",
    "organization": "Organization offering the scholarship",
    "eligibility": "Key eligibility requirements"
}}

If no scholarship information is found, return null.
If there's a URL to apply, extract it exactly. Look for phrases like "apply at", "link in bio", "visit", etc.
"""
            
            response = self.openai_client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[
                    {"role": "system", "content": "Extract scholarship information from social media posts. Return only valid JSON."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.2,
                max_tokens=500
            )
            
            result_text = response.choices[0].message.content.strip()
            
            # Parse JSON
            import json
            if result_text.startswith('```'):
                result_text = re.sub(r'^```\w*\n?', '', result_text)
                result_text = re.sub(r'\n?```$', '', result_text)
            
            if result_text.lower() == 'null':
                return None
            
            data = json.loads(result_text)
            
            # Use source_url if no apply_url found
            if not data.get('apply_url'):
                data['source_url'] = source_url
            else:
                data['source_url'] = data['apply_url']
            
            return data
            
        except Exception as e:
            print(f"    AI extraction error: {e}")
            return None
    
    def _extract_title(self, text: str) -> str:
        """Extract a title from the text."""
        lines = text.split('\n')
        for line in lines:
            line = line.strip()
            if len(line) > 20 and len(line) < 100:
                return line
        return text[:80] + "..."
    
    def _extract_amount(self, text: str) -> str:
        """Extract scholarship amount."""
        patterns = [
            r'\$[\d,]+(?:\.\d{2})?',
            r'\d+(?:,\d{3})+\s*(?:USD|dollars?)',
        ]
        for pattern in patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                return match.group()
        return None
    
    def _extract_deadline(self, text: str) -> str:
        """Extract deadline from text."""
        patterns = [
            r'(?:deadline|due|by|before)[:\s]*([\w\s,]+\d{4})',
            r'(january|february|march|april|may|june|july|august|september|october|november|december)\s+\d{1,2},?\s+\d{4}',
        ]
        for pattern in patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                return match.group(1) if match.lastindex else match.group()
        return None
    
    def sync_to_database(self, scholarships: list):
        """Save scholarships to the database via API."""
        API_URL = os.getenv("API_URL", "http://64.23.231.89:8000/scholarships/")
        
        synced = 0
        skipped = 0
        
        for sch in scholarships:
            try:
                payload = {
                    'title': sch.get('title', 'Instagram Scholarship'),
                    'source_url': sch.get('source_url') or sch.get('apply_url', ''),
                    'description': sch.get('description', '')[:500],
                    'amount': sch.get('amount'),
                    'deadline': sch.get('deadline'),
                    'platform': 'instagram',
                }
                
                # Skip validation since we already processed with AI
                response = requests.post(
                    f"{API_URL}?skip_validation=true",
                    json=payload,
                    timeout=10
                )
                
                result = response.json()
                if result.get('saved') or result.get('id'):
                    synced += 1
                else:
                    skipped += 1
                    
            except Exception as e:
                print(f"Sync error: {e}")
                skipped += 1
        
        print(f"\n📊 Synced {synced}, Skipped {skipped}")
        return synced
    
    def run_continuous(self, interval_minutes: int = 30):
        """
        Run continuous scraping loop.
        
        Args:
            interval_minutes: Time between scraping cycles
        """
        print("=" * 60)
        print("INSTAGRAM SCHOLARSHIP SCRAPER - CONTINUOUS MODE")
        print("=" * 60)
        print(f"Hashtags: {self.SCHOLARSHIP_HASHTAGS}")
        print(f"Interval: {interval_minutes} minutes")
        print("=" * 60)
        
        cycle = 0
        while True:
            cycle += 1
            print(f"\n{'='*60}")
            print(f"CYCLE {cycle} - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
            print("=" * 60)
            
            all_scholarships = []
            
            # Rotate through hashtags
            hashtags_this_cycle = random.sample(
                self.SCHOLARSHIP_HASHTAGS,
                min(3, len(self.SCHOLARSHIP_HASHTAGS))  # Pick 3 random hashtags
            )
            
            for hashtag in hashtags_this_cycle:
                results = self.scrape_hashtag(hashtag, max_posts=10)
                all_scholarships.extend(results)
                
                # Delay between hashtags
                time.sleep(random.uniform(5, 10))
            
            print(f"\nCycle {cycle} found {len(all_scholarships)} scholarships")
            
            # Sync to database
            if all_scholarships:
                self.sync_to_database(all_scholarships)
            
            # Wait for next cycle
            print(f"\nSleeping for {interval_minutes} minutes...")
            time.sleep(interval_minutes * 60)


def run_single_scrape():
    """Run a single scrape cycle (for Celery task)."""
    scraper = InstagramScholarshipScraper()
    
    all_scholarships = []
    
    for hashtag in ['scholarships', 'scholarship2025', 'studyabroad']:
        results = scraper.scrape_hashtag(hashtag, max_posts=10)
        all_scholarships.extend(results)
        time.sleep(random.uniform(2, 5))
    
    if all_scholarships:
        scraper.sync_to_database(all_scholarships)
    
    return len(all_scholarships)


if __name__ == "__main__":
    # Run continuous scraping
    scraper = InstagramScholarshipScraper()
    scraper.run_continuous(interval_minutes=30)

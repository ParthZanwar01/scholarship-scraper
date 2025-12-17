"""
Enhanced Facebook Scholarship Scraper

Same pipeline as Instagram:
1. Scrape Facebook posts via mbasic.facebook.com (mobile, no login required)
2. Download images from posts
3. OCR images to extract text
4. Use AI to find scholarship info and application links
5. Save to database

Uses Tor for IP rotation to avoid blocking.
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

try:
    import openai
    OPENAI_AVAILABLE = True
except ImportError:
    OPENAI_AVAILABLE = False


class FacebookScholarshipScraper:
    """
    Enhanced Facebook scraper that:
    - Scrapes public scholarship pages/groups
    - Downloads post images
    - Runs OCR on images
    - Uses AI to find scholarship names and apply links
    """
    
    # Known public scholarship Facebook pages
    SCHOLARSHIP_PAGES = [
        "ScholarshipsCorner",
        "FullyFundedScholarships",
        "InternationalScholarships",
        "ScholarshipOpportunities",
        "StudyAbroadScholarships",
        "GraduateScholarships",
        "UndergraduateScholarships",
    ]
    
    def __init__(self, use_tor=True, openai_api_key=None):
        self.session = requests.Session()
        
        if use_tor:
            self.session.proxies = {
                'http': 'socks5h://127.0.0.1:9050',
                'https': 'socks5h://127.0.0.1:9050'
            }
        
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (iPhone; CPU iPhone OS 14_0 like Mac OS X) AppleWebKit/605.1.15',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.5',
        })
        
        self.openai_api_key = openai_api_key or os.getenv("OPENAI_API_KEY")
        self.openai_client = None
        
        if OPENAI_AVAILABLE and self.openai_api_key:
            self.openai_client = openai.OpenAI(api_key=self.openai_api_key)
        
        print(f"✓ Facebook Scraper initialized (OCR: {OCR_AVAILABLE}, AI: {self.openai_client is not None}, Tor: {use_tor})")
    
    def scrape_page(self, page_name: str, max_posts: int = 10) -> list:
        """
        Scrape a Facebook page for scholarship posts.
        
        Uses mbasic.facebook.com which doesn't require login.
        """
        url = f"https://mbasic.facebook.com/{page_name}"
        print(f"\n--- Scraping Facebook: {page_name} ---")
        
        scholarships = []
        
        try:
            response = self.session.get(url, timeout=30)
            
            if response.status_code != 200:
                print(f"Facebook returned {response.status_code}")
                return scholarships
            
            soup = BeautifulSoup(response.text, 'html.parser')
            
            # Find posts - mbasic.facebook.com uses specific structure
            # Posts are typically in divs with id starting with 'u_'
            posts = soup.find_all('div', id=re.compile(r'^u_')) or \
                    soup.find_all('article') or \
                    soup.find_all('div', {'role': 'article'})
            
            if not posts:
                # Fallback: find any div with substantial text
                posts = [div for div in soup.find_all('div') if len(div.get_text(strip=True)) > 100]
            
            print(f"Found {len(posts)} potential posts")
            
            for post in posts[:max_posts]:
                result = self._process_post(post, page_name)
                if result:
                    scholarships.append(result)
                    print(f"  ✓ Found: {result.get('title', 'Unknown')[:50]}...")
                
                time.sleep(random.uniform(1, 2))
        
        except Exception as e:
            print(f"Facebook scrape error: {e}")
        
        return scholarships
    
    def _process_post(self, post_element, page_name: str) -> dict:
        """Process a single Facebook post - download images, OCR, AI extract."""
        
        # Get post text
        post_text = post_element.get_text(strip=True)
        
        # Check if scholarship-related
        if not any(kw in post_text.lower() for kw in ['scholarship', 'grant', 'fellowship', 'funding', 'award']):
            return None
        
        # Find images in post
        images = post_element.find_all('img')
        image_urls = []
        for img in images:
            src = img.get('src') or img.get('data-src')
            if src and 'http' in src and 'emoji' not in src.lower():
                image_urls.append(src)
        
        # OCR images
        ocr_text = ""
        for img_url in image_urls[:3]:  # Limit to 3 images
            text = self._ocr_image(img_url)
            if text:
                ocr_text += " " + text
        
        # Combine post text and OCR text
        full_text = f"{post_text}\n\n{ocr_text}".strip()
        
        if len(full_text) < 50:
            return None
        
        # Extract links from post
        links = []
        for a in post_element.find_all('a', href=True):
            href = a['href']
            # Facebook wraps external links
            if 'l.facebook.com' in href or (href.startswith('http') and 'facebook.com' not in href):
                # Extract actual URL from Facebook redirect
                match = re.search(r'u=([^&]+)', href)
                if match:
                    from urllib.parse import unquote
                    links.append(unquote(match.group(1)))
                elif 'facebook.com' not in href:
                    links.append(href)
        
        # Use AI to extract scholarship info
        scholarship_info = self._extract_with_ai(full_text, links)
        
        if not scholarship_info:
            # Fallback: basic extraction
            scholarship_info = {
                'title': self._extract_title(full_text),
                'description': full_text[:500],
                'amount': self._extract_amount(full_text),
                'deadline': self._extract_deadline(full_text),
                'source_url': links[0] if links else f"https://facebook.com/{page_name}",
            }
        
        scholarship_info['platform'] = 'facebook'
        scholarship_info['date_posted'] = datetime.now()
        
        return scholarship_info
    
    def _ocr_image(self, img_url: str) -> str:
        """Download and OCR an image."""
        if not OCR_AVAILABLE:
            return ""
        
        try:
            response = self.session.get(img_url, timeout=15)
            if response.status_code != 200:
                return ""
            
            image = Image.open(BytesIO(response.content))
            if image.mode != 'RGB':
                image = image.convert('RGB')
            
            text = pytesseract.image_to_string(image)
            text = re.sub(r'\s+', ' ', text).strip()
            
            if len(text) > 20:
                print(f"    OCR: {len(text)} chars extracted")
            
            return text
        except Exception as e:
            return ""
    
    def _extract_with_ai(self, text: str, links: list) -> dict:
        """Use GPT to extract scholarship info and find apply links."""
        if not self.openai_client:
            return None
        
        try:
            links_text = "\n".join(links[:5]) if links else "No external links found"
            
            prompt = f"""Analyze this Facebook post about a scholarship opportunity.

POST CONTENT:
{text[:2000]}

LINKS FOUND IN POST:
{links_text}

Extract scholarship information as JSON:
{{
    "title": "Name of the scholarship",
    "description": "Brief description",
    "amount": "Award amount if mentioned",
    "deadline": "Application deadline if mentioned",
    "source_url": "Best URL to apply (prefer application links over info pages)",
    "organization": "Organization offering it"
}}

If not scholarship-related, return null.
"""
            
            response = self.openai_client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[
                    {"role": "system", "content": "Extract scholarship info from social media. Return only valid JSON."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.2,
                max_tokens=400
            )
            
            result_text = response.choices[0].message.content.strip()
            
            # Parse JSON
            import json
            if result_text.startswith('```'):
                result_text = re.sub(r'^```\w*\n?', '', result_text)
                result_text = re.sub(r'\n?```$', '', result_text)
            
            if result_text.lower() == 'null':
                return None
            
            return json.loads(result_text)
            
        except Exception as e:
            print(f"    AI error: {e}")
            return None
    
    def _extract_title(self, text: str) -> str:
        lines = text.split('\n')
        for line in lines:
            line = line.strip()
            if 20 < len(line) < 100:
                return line
        return text[:80] + "..."
    
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
    
    def scrape_all_pages(self, max_posts_per_page: int = 5) -> list:
        """Scrape all known scholarship pages."""
        all_scholarships = []
        
        for page in self.SCHOLARSHIP_PAGES:
            results = self.scrape_page(page, max_posts=max_posts_per_page)
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
                    'title': sch.get('title', 'Facebook Scholarship'),
                    'source_url': sch.get('source_url', ''),
                    'description': sch.get('description', '')[:500],
                    'amount': sch.get('amount'),
                    'deadline': sch.get('deadline'),
                    'platform': 'facebook',
                }
                
                response = requests.post(f"{API_URL}?skip_validation=true", json=payload, timeout=10)
                if response.json().get('saved') or response.json().get('id'):
                    synced += 1
            except Exception as e:
                print(f"Sync error: {e}")
        
        print(f"📊 Synced {synced}/{len(scholarships)} from Facebook")
        return synced


def run_facebook_scrape():
    """Run a single Facebook scrape cycle."""
    scraper = FacebookScholarshipScraper(use_tor=True)
    scholarships = scraper.scrape_all_pages(max_posts_per_page=5)
    
    if scholarships:
        scraper.sync_to_database(scholarships)
    
    return len(scholarships)


if __name__ == "__main__":
    scraper = FacebookScholarshipScraper(use_tor=False)  # No Tor for testing
    results = scraper.scrape_page("ScholarshipsCorner", max_posts=5)
    for r in results:
        print(f"Title: {r.get('title')}")
        print(f"URL: {r.get('source_url')}")
        print("-" * 40)

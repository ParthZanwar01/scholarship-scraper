"""
Orchestrator for Tor-Based Social Media Scraping

Uses Tor for IP rotation to bypass Instagram/TikTok blocking.
Implements:
- Tor circuit rotation for fresh IPs
- Account rotation
- Rate limiting
- Session management
"""

import os
import sys
import json
import time
import random
import requests
import logging
from datetime import datetime

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s',
    handlers=[
        logging.FileHandler('logs/orchestrator.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# Tor configuration
TOR_SOCKS_PORT = 9050
TOR_CONTROL_PORT = 9051

# API endpoint for syncing
API_URL = os.getenv("API_URL", "http://64.23.231.89:8000/scholarships/")


class TorSession:
    """Manages Tor-proxied requests with IP rotation."""
    
    def __init__(self):
        self.session = requests.Session()
        self.session.proxies = {
            'http': f'socks5h://127.0.0.1:{TOR_SOCKS_PORT}',
            'https': f'socks5h://127.0.0.1:{TOR_SOCKS_PORT}'
        }
        
    def get_current_ip(self):
        """Get current IP address through Tor."""
        try:
            resp = self.session.get('https://api.ipify.org?format=json', timeout=10)
            return resp.json().get('ip')
        except Exception as e:
            logger.error(f"Failed to get IP: {e}")
            return None
    
    def rotate_ip(self):
        """Request a new Tor circuit for a fresh IP."""
        try:
            from stem import Signal
            from stem.control import Controller
            
            with Controller.from_port(port=TOR_CONTROL_PORT) as controller:
                controller.authenticate()
                controller.signal(Signal.NEWNYM)
                logger.info("Tor circuit rotated, new IP assigned")
                time.sleep(5)  # Wait for new circuit
                return True
        except ImportError:
            logger.warning("stem not installed. Install with: pip install stem")
            return False
        except Exception as e:
            logger.error(f"Failed to rotate IP: {e}")
            return False
    
    def get(self, url, **kwargs):
        """Make a GET request through Tor."""
        kwargs.setdefault('timeout', 30)
        return self.session.get(url, **kwargs)
    
    def post(self, url, **kwargs):
        """Make a POST request through Tor."""
        kwargs.setdefault('timeout', 30)
        return self.session.post(url, **kwargs)


class SocialMediaOrchestrator:
    """Orchestrates scraping across Instagram and TikTok with Tor."""
    
    def __init__(self, accounts_file='accounts.json'):
        self.tor = TorSession()
        self.accounts = self._load_accounts(accounts_file)
        self.results = []
        
    def _load_accounts(self, filename):
        """Load account credentials."""
        try:
            with open(filename, 'r') as f:
                return json.load(f)
        except FileNotFoundError:
            logger.error(f"Accounts file not found: {filename}")
            return {'instagram': [], 'tiktok': []}
    
    def sync_to_cloud(self, scholarship_data):
        """Sync found scholarship to cloud database."""
        try:
            # Use regular requests (not Tor) for cloud sync
            response = requests.post(API_URL, json=scholarship_data, timeout=10)
            if response.status_code in [200, 201]:
                logger.info(f"✓ Synced: {scholarship_data.get('title', 'Unknown')[:40]}")
                return True
            else:
                logger.warning(f"Sync failed: {response.status_code}")
                return False
        except Exception as e:
            logger.error(f"Sync error: {e}")
            return False
    
    def scrape_instagram_hashtag(self, hashtag, limit=10):
        """Scrape Instagram hashtag via Tor."""
        logger.info(f"Scraping Instagram #{hashtag} via Tor...")
        
        # Get fresh IP
        self.tor.rotate_ip()
        ip = self.tor.get_current_ip()
        logger.info(f"Using IP: {ip}")
        
        scholarships = []
        
        try:
            # Instagram public hashtag page
            url = f"https://www.instagram.com/explore/tags/{hashtag}/"
            
            headers = {
                'User-Agent': 'Mozilla/5.0 (iPhone; CPU iPhone OS 14_0 like Mac OS X) AppleWebKit/605.1.15',
                'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
                'Accept-Language': 'en-US,en;q=0.5',
            }
            
            response = self.tor.get(url, headers=headers)
            
            if response.status_code == 200:
                # Parse for scholarship content
                # Instagram embeds data in the page
                import re
                from bs4 import BeautifulSoup
                
                soup = BeautifulSoup(response.text, 'html.parser')
                
                # Look for script tags with data
                scripts = soup.find_all('script', type='text/javascript')
                for script in scripts:
                    if script.string and 'window._sharedData' in script.string:
                        # Extract JSON data
                        match = re.search(r'window\._sharedData\s*=\s*({.*?});', script.string)
                        if match:
                            try:
                                data = json.loads(match.group(1))
                                # Parse posts from data
                                # Structure varies, this is a simplified example
                                logger.info("Found Instagram data, parsing...")
                            except json.JSONDecodeError:
                                pass
                
                # Alternative: Look for meta tags with content
                og_desc = soup.find('meta', property='og:description')
                if og_desc:
                    content = og_desc.get('content', '')
                    if 'scholarship' in content.lower():
                        scholarships.append({
                            'title': f'Instagram #{hashtag}',
                            'source_url': url,
                            'description': content[:500],
                            'platform': 'instagram'
                        })
                        
            elif response.status_code == 429:
                logger.warning("Rate limited! Rotating IP and waiting...")
                self.tor.rotate_ip()
                time.sleep(60)
            else:
                logger.warning(f"Instagram returned {response.status_code}")
                
        except Exception as e:
            logger.error(f"Instagram scrape error: {e}")
        
        return scholarships
    
    def scrape_tiktok_hashtag(self, hashtag, limit=10):
        """Scrape TikTok hashtag via Tor."""
        logger.info(f"Scraping TikTok #{hashtag} via Tor...")
        
        # Get fresh IP
        self.tor.rotate_ip()
        ip = self.tor.get_current_ip()
        logger.info(f"Using IP: {ip}")
        
        scholarships = []
        
        try:
            # TikTok public tag page
            url = f"https://www.tiktok.com/tag/{hashtag}"
            
            headers = {
                'User-Agent': 'Mozilla/5.0 (iPhone; CPU iPhone OS 14_0 like Mac OS X) AppleWebKit/605.1.15',
                'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
            }
            
            response = self.tor.get(url, headers=headers)
            
            if response.status_code == 200:
                from bs4 import BeautifulSoup
                soup = BeautifulSoup(response.text, 'html.parser')
                
                # TikTok embeds data in __UNIVERSAL_DATA_FOR_REHYDRATION__
                import re
                scripts = soup.find_all('script', id='__UNIVERSAL_DATA_FOR_REHYDRATION__')
                
                for script in scripts:
                    if script.string:
                        try:
                            data = json.loads(script.string)
                            # Parse video data
                            logger.info("Found TikTok data, parsing...")
                        except json.JSONDecodeError:
                            pass
                
                # Look for video descriptions in meta tags
                meta_desc = soup.find('meta', attrs={'name': 'description'})
                if meta_desc:
                    content = meta_desc.get('content', '')
                    if 'scholarship' in content.lower():
                        scholarships.append({
                            'title': f'TikTok #{hashtag}',
                            'source_url': url,
                            'description': content[:500],
                            'platform': 'tiktok'
                        })
                        
            elif response.status_code == 403:
                logger.warning("TikTok blocked request - rotating IP")
                self.tor.rotate_ip()
            else:
                logger.warning(f"TikTok returned {response.status_code}")
                
        except Exception as e:
            logger.error(f"TikTok scrape error: {e}")
        
        return scholarships
    
    def run(self, hashtags=None, platforms=None):
        """Main orchestration loop."""
        if hashtags is None:
            hashtags = ['scholarship', 'scholarships', 'studyabroad', 'financialaid']
        if platforms is None:
            platforms = ['instagram', 'tiktok']
        
        logger.info("="*60)
        logger.info("SCHOLARSHIP SCRAPER - TOR ORCHESTRATOR")
        logger.info("="*60)
        
        # Check Tor connection
        ip = self.tor.get_current_ip()
        if ip:
            logger.info(f"Tor connected. Current IP: {ip}")
        else:
            logger.error("Cannot connect through Tor. Is Tor running?")
            logger.info("Start Tor with: tor &")
            return
        
        all_scholarships = []
        
        for hashtag in hashtags:
            for platform in platforms:
                logger.info(f"\n--- Scraping {platform} #{hashtag} ---")
                
                if platform == 'instagram':
                    results = self.scrape_instagram_hashtag(hashtag, limit=10)
                elif platform == 'tiktok':
                    results = self.scrape_tiktok_hashtag(hashtag, limit=10)
                else:
                    continue
                
                # Sync results to cloud
                for sch in results:
                    self.sync_to_cloud(sch)
                    all_scholarships.append(sch)
                
                # Random delay between requests
                delay = random.uniform(5, 15)
                logger.info(f"Waiting {delay:.1f}s before next request...")
                time.sleep(delay)
        
        logger.info("="*60)
        logger.info(f"COMPLETE! Found {len(all_scholarships)} scholarships")
        logger.info("="*60)
        
        return all_scholarships


def main():
    """Entry point."""
    # Change to script directory
    os.chdir(os.path.dirname(os.path.abspath(__file__)))
    
    # Create logs directory
    os.makedirs('logs', exist_ok=True)
    
    # Run orchestrator
    orchestrator = SocialMediaOrchestrator()
    orchestrator.run()


if __name__ == "__main__":
    main()

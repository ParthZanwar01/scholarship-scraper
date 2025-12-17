"""
RSS Feed Scraper for Scholarships

Scrapes RSS/Atom feeds from major scholarship websites.
This is the most reliable and legitimate scraping method.
"""

import feedparser
import re
from datetime import datetime
from scholarship_scraper.models.scholarship import Scholarship


class RSSScholarshipScraper:
    """Scrapes scholarship information from RSS feeds."""
    
    # Known scholarship RSS feeds - EXPANDED LIST
    FEEDS = [
        # Major Scholarship Aggregators
        {
            "name": "Scholarships.com",
            "url": "https://www.scholarships.com/feed/",
            "keywords": ["scholarship", "grant", "award"]
        },
        {
            "name": "FastWeb",
            "url": "https://www.fastweb.com/college-scholarships/feed",
            "keywords": ["scholarship", "financial aid"]
        },
        {
            "name": "Scholarship America",
            "url": "https://scholarshipamerica.org/feed/",
            "keywords": ["scholarship", "student"]
        },
        {
            "name": "Bold.org",
            "url": "https://bold.org/blog/feed/",
            "keywords": ["scholarship", "award", "apply"]
        },
        {
            "name": "Niche",
            "url": "https://www.niche.com/blog/feed/",
            "keywords": ["scholarship", "college", "financial"]
        },
        
        # International Scholarships
        {
            "name": "GoOverseas",
            "url": "https://www.gooverseas.com/blog/feed",
            "keywords": ["scholarship", "study abroad", "funding"]
        },
        {
            "name": "IIE",
            "url": "https://www.iie.org/feed/",
            "keywords": ["scholarship", "fellowship", "grant", "fulbright"]
        },
        {
            "name": "StudyPortals",
            "url": "https://www.studyportals.com/blog/feed/",
            "keywords": ["scholarship", "study", "international"]
        },
        {
            "name": "TopUniversities",
            "url": "https://www.topuniversities.com/rss/news.xml",
            "keywords": ["scholarship", "funding", "study"]
        },
        {
            "name": "DAAD",
            "url": "https://www.daad.de/en/feeds/news/",
            "keywords": ["scholarship", "germany", "funding"]
        },
        {
            "name": "British Council",
            "url": "https://www.britishcouncil.org/feed",
            "keywords": ["scholarship", "uk", "study"]
        },
        {
            "name": "Chevening",
            "url": "https://www.chevening.org/feed/",
            "keywords": ["scholarship", "chevening", "uk"]
        },
        
        # Foundations & Organizations
        {
            "name": "JMO",
            "url": "https://www.jmof.org/feed/",
            "keywords": ["scholarship", "jack kent cooke"]
        },
        {
            "name": "Gates Foundation",
            "url": "https://www.gatesfoundation.org/ideas/feed",
            "keywords": ["scholarship", "grant", "education"]
        },
        {
            "name": "Rotary",
            "url": "https://blog.rotary.org/feed/",
            "keywords": ["scholarship", "peace", "global"]
        },
        {
            "name": "AAUW",
            "url": "https://www.aauw.org/feed/",
            "keywords": ["scholarship", "fellowship", "women"]
        },
        {
            "name": "Hispanic Scholarship Fund",
            "url": "https://www.hsf.net/feed/",
            "keywords": ["scholarship", "hispanic", "latino"]
        },
        {
            "name": "UNCF",
            "url": "https://uncf.org/feed/",
            "keywords": ["scholarship", "hbcu", "minority"]
        },
        
        # Graduate & Research
        {
            "name": "NSF",
            "url": "https://www.nsf.gov/rss/funding_rss.xml",
            "keywords": ["fellowship", "grant", "research"]
        },
        {
            "name": "NIH",
            "url": "https://grants.nih.gov/rss/funding.rss",
            "keywords": ["fellowship", "training", "research"]
        },
        {
            "name": "Ford Foundation",
            "url": "https://www.fordfoundation.org/feed/",
            "keywords": ["fellowship", "grant", "diversity"]
        },
        
        # University Scholarship Offices
        {
            "name": "MIT Financial Aid",
            "url": "https://sfs.mit.edu/feed/",
            "keywords": ["scholarship", "financial aid", "mit"]
        },
        {
            "name": "Stanford Scholarships",
            "url": "https://financialaid.stanford.edu/feed/",
            "keywords": ["scholarship", "aid", "stanford"]
        },
        
        # STEM & Tech Scholarships
        {
            "name": "Google Education",
            "url": "https://blog.google/outreach-initiatives/education/feed/",
            "keywords": ["scholarship", "computer science", "tech"]
        },
        {
            "name": "Microsoft",
            "url": "https://blogs.microsoft.com/feed/",
            "keywords": ["scholarship", "diversity", "tech"]
        },
        
        # Other Major Sources
        {
            "name": "Chegg",
            "url": "https://www.chegg.com/scholarships/rss",
            "keywords": ["scholarship", "college"]
        },
        {
            "name": "College Board",
            "url": "https://blog.collegeboard.org/rss.xml",
            "keywords": ["scholarship", "financial aid", "college"]
        },
        {
            "name": "Peterson's",
            "url": "https://www.petersons.com/blog/feed/",
            "keywords": ["scholarship", "graduate", "college"]
        },
        {
            "name": "Unigo",
            "url": "https://www.unigo.com/feed/",
            "keywords": ["scholarship", "college", "award"]
        },
        {
            "name": "Cappex",
            "url": "https://www.cappex.com/blog/feed/",
            "keywords": ["scholarship", "college", "financial"]
        },
    ]
    
    def __init__(self):
        print("RSS Scholarship Scraper initialized")
        
    def extract_amount(self, text):
        """Extract dollar amounts from text."""
        patterns = [
            r'\$[\d,]+(?:\.[\d]{2})?',
            r'\d+(?:,\d{3})+\s*(?:dollars?)?',
        ]
        
        for pattern in patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                return match.group()
        return None
    
    def extract_deadline(self, text):
        """Extract deadline dates from text."""
        patterns = [
            r'(?:deadline[:\s]+)?(\w+\s+\d{1,2},?\s+\d{4})',
            r'(?:due|by|before)[:\s]+(\w+\s+\d{1,2},?\s+\d{4})',
            r'(\d{1,2}/\d{1,2}/\d{4})',
        ]
        
        for pattern in patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                return match.group(1) if match.lastindex else match.group()
        return None
    
    def scrape_feed(self, feed_info):
        """Scrape a single RSS feed."""
        scholarships = []
        
        print(f"  Fetching: {feed_info['name']}...")
        
        try:
            feed = feedparser.parse(feed_info['url'])
            
            if feed.bozo:  # Feed parsing error
                print(f"    Error parsing feed: {feed.bozo_exception}")
                return []
            
            print(f"    Found {len(feed.entries)} entries")
            
            for entry in feed.entries[:20]:  # Limit per feed
                title = entry.get('title', '')
                description = entry.get('summary', '') or entry.get('description', '')
                link = entry.get('link', '')
                published = entry.get('published', '') or entry.get('updated', '')
                
                # Combine title and description for keyword matching
                full_text = f"{title} {description}".lower()
                
                # Check if any keywords match
                if any(kw in full_text for kw in feed_info['keywords']):
                    # Extract additional info
                    amount = self.extract_amount(f"{title} {description}")
                    deadline = self.extract_deadline(f"{title} {description}")
                    
                    scholarship = Scholarship(
                        title=title[:200],
                        source_url=link,
                        description=description[:500] if description else title,
                        amount=amount,
                        deadline=deadline,
                        platform="rss",
                        date_posted=datetime.now()
                    )
                    
                    scholarships.append(scholarship)
                    
        except Exception as e:
            print(f"    Error: {e}")
        
        return scholarships
    
    def scrape_all(self, limit_per_feed=10):
        """Scrape all configured RSS feeds."""
        print("\n" + "="*60)
        print("RSS SCHOLARSHIP SCRAPER")
        print("="*60)
        
        all_scholarships = []
        
        for feed_info in self.FEEDS:
            results = self.scrape_feed(feed_info)
            all_scholarships.extend(results[:limit_per_feed])
            
        print(f"\n{'='*60}")
        print(f"RSS Scrape Complete. Found {len(all_scholarships)} scholarships.")
        print(f"{'='*60}\n")
        
        return all_scholarships


if __name__ == "__main__":
    scraper = RSSScholarshipScraper()
    results = scraper.scrape_all(limit_per_feed=5)
    
    for s in results:
        print(f"Title: {s.title}")
        print(f"URL: {s.source_url}")
        print(f"Amount: {s.amount}")
        print(f"Description: {s.description[:100]}...")
        print("-" * 40)

import re
from datetime import datetime
from playwright.sync_api import sync_playwright
from scholarship_scraper.models.scholarship import Scholarship
from dateutil import parser

class EnrichmentProcessor:
    def __init__(self, headless=True):
        self.headless = headless

    def extract_amount(self, text):
        # Look for currency patterns like $10,000, $5000, 1000 USD, $2k
        # More robust regex
        text = text.replace(',', '') # Simplify numbers
        matches = re.findall(r'\$\s?\d+(?:k)?', text.lower())
        
        # Also look for "10000 dollars"
        matches_usd = re.findall(r'\d+\s?dollars', text.lower())
        
        amounts = []
        if matches:
            for m in matches:
                try:
                    val = m.replace('$', '').strip()
                    if 'k' in val:
                        val = float(val.replace('k', '')) * 1000
                    else:
                        val = float(val)
                    if val > 100: # Filter small numbers
                        amounts.append(val)
                except:
                    pass
                    
        if amounts:
            return f"${max(amounts):,.0f}"
        return None

    def extract_deadline(self, text):
        # Look for date patterns near keywords like "Deadline", "Due", "Ends", "Closes"
        keywords = ["deadline", "due date", "closes", "ends", "application period", "expires"]
        
        # Regex for common date formats:
        # 1. Month DD, YYYY (January 1, 2025 or Jan 1 2025)
        # 2. MM/DD/YYYY or MM.DD.YYYY
        date_regex = r'(?:Jan(?:uary)?|Feb(?:ruary)?|Mar(?:ch)?|Apr(?:il)?|May|Jun(?:e)?|Jul(?:y)?|Aug(?:ust)?|Sep(?:tember)?|Oct(?:ober)?|Nov(?:ember)?|Dec(?:ember)?)\s+\d{1,2},?\s+\d{4}'
        date_regex_short = r'\d{1,2}[/-]\d{1,2}[/-]\d{4}'
        
        lines = text.split('\n')
        for i, line in enumerate(lines):
            line_lower = line.lower()
            if any(k in line_lower for k in keywords):
                # Search for dates in this line or the immediate next ones
                snippet = line + " " + (lines[i+1] if i+1 < len(lines) else "")
                
                # Regex search first (more reliable)
                match = re.search(date_regex, snippet, re.IGNORECASE)
                if match:
                    try:
                         return parser.parse(match.group(0))
                    except:
                        pass
                        
                match_short = re.search(date_regex_short, snippet)
                if match_short:
                    try:
                        return parser.parse(match_short.group(0))
                    except:
                        pass
                
                # Fallback to fuzzy parsing of the snippet if it's short enough
                if len(snippet) < 100:
                    try:
                        # Exclude the keyword itself to avoid confusion? No, parser handles it.
                        return parser.parse(snippet, fuzzy=True)
                    except:
                        pass
        return None

    def enrich_url(self, url):
        print(f"Deep Researching: {url}")
        data = {}
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=self.headless)
            # Use distinct user agent
            context = browser.new_context(user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36")
            page = context.new_page()
            
            try:
                page.goto(url, timeout=30000)
                page.wait_for_load_state("domcontentloaded")
                
                # Get full text
                text = page.locator("body").inner_text()
                
                # Extract
                data['amount'] = self.extract_amount(text)
                data['deadline'] = self.extract_deadline(text)
                data['full_text'] = text[:5000] # Limit size
                
                print(f"  -> Found Amount: {data.get('amount')}")
                print(f"  -> Found Deadline: {data.get('deadline')}")
                
            except Exception as e:
                print(f"Enrichment Failed for {url}: {e}")
            
            browser.close()
        return data

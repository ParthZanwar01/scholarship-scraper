import re
from datetime import datetime
from playwright.sync_api import sync_playwright
from scholarship_scraper.models.scholarship import Scholarship
from dateutil import parser

class EnrichmentProcessor:
    def __init__(self, headless=True):
        self.headless = headless

    def extract_amount(self, text):
        # Look for currency patterns like $10,000, $5000, 1000 USD
        matches = re.findall(r'\$\s?[\d,]+(?:\.\d{2})?', text)
        if matches:
            # Return the largest amount found, assuming it's the max award
            try:
                values = [float(m.replace('$', '').replace(',', '')) for m in matches]
                return f"${max(values):,.0f}"
            except:
                return matches[0]
        return None

    def extract_deadline(self, text):
        # Look for date patterns near keywords like "Deadline", "Due"
        # This is a heuristic.
        lines = text.split('\n')
        for i, line in enumerate(lines):
            if "deadline" in line.lower() or "due date" in line.lower():
                # Try to fuzzy parse the whole line or next line
                try:
                    # simplistic extraction: look for date strings in this line
                    # Using dateutil to fuzzy parse
                    # We pick a substring to avoid parsing garbage
                    snippet = line + " " + (lines[i+1] if i+1 < len(lines) else "")
                    dt = parser.parse(snippet, fuzzy=True)
                    return dt
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

from playwright.sync_api import sync_playwright

def inspect_site(url):
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page(user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36")
        print(f"Visiting {url}...")
        page.goto(url)
        
        # Try to find links that look like scholarships
        links = page.locator("a").all()
        print(f"Total links: {len(links)}")
        
        candidates = []
        for link in links:
            href = link.get_attribute("href")
            text = link.inner_text().strip()
            if href and len(text) > 10 and ("scholarship" in href.lower() or "scholarship" in text.lower()):
                candidates.append((text, href))
        
        print("Potential Scholarship Links (First 5):")
        for text, href in candidates[:5]:
            print(f"Text: {text} | Href: {href}")
            
        browser.close()

if __name__ == "__main__":
    inspect_site("https://www.unigo.com/scholarships/our-scholarships")
    print("-" * 20)
    inspect_site("https://www.scholarships.com/financial-aid/college-scholarships/scholarship-directory")

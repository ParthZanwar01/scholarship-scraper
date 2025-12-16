from playwright.sync_api import sync_playwright

def test_mirrors():
    mirrors = [
        "https://www.picuki.com/tag/scholarship",
        "https://imginn.com/tag/scholarships/",
        "https://dumpor.com/v/scholarships"
    ]
    
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        # Randomize UA
        ua = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        
        for url in mirrors:
            print(f"Testing {url}...")
            context = browser.new_context(user_agent=ua)
            page = context.new_page()
            try:
                page.goto(url, timeout=15000)
                page.wait_for_load_state("domcontentloaded")
                title = page.title()
                print(f"  Title: {title}")
                
                # Check for common post selectors
                # Picuki: .box-photo
                # Imginn: .img-item
                # Dumpor: .content-grid
                if "picuki" in url:
                    count = page.locator(".box-photo").count()
                elif "imginn" in url:
                    count = page.locator(".item").count()
                else: 
                    count = 0
                    
                print(f"  Found {count} items.")
                
                if count > 0:
                    print("  SUCCESS!")
                    break
            except Exception as e:
                print(f"  Failed: {e}")
            finally:
                context.close()
                
        browser.close()

if __name__ == "__main__":
    test_mirrors()

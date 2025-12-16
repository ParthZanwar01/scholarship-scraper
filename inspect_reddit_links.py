from playwright.sync_api import sync_playwright

def test_urls():
    mirrors = [
        "https://redlib.catsarch.com",
        "https://libreddit.offer.space.tr",
        "https://libreddit.northboot.xyz",
        "https://snoo.habedieeh.re",
    ]
    
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        for base in mirrors:
            url = f"{base}/r/scholarships/new/"
            print(f"Checking {url}...")
            try:
                page = browser.new_page()
                page.goto(url, timeout=15000)
                posts = page.locator(".post_title").all()
                if not posts:
                    posts = page.locator("a[href*='/comments/']").all()

                print(f"Found {len(posts)} posts.")
                for post in posts[:5]:
                    title = post.inner_text()
                    href = post.get_attribute("href")
                    print(f"Title: {title}")
                    print(f"HREF: {href}")
                    if href and href.startswith("http") and "reddit" not in href and "redlib" not in href and "libreddit" not in href:
                        print("-> EXTERNAL LINK (Keeper)")
                    else:
                        print("-> INTERNAL THREAD")
                page.close()
            except Exception as e:
                print(f"Error: {e}")
        browser.close()

if __name__ == "__main__":
    test_urls()

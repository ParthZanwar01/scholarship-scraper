from playwright.sync_api import sync_playwright

def dump_html():
    url = "https://redlib.catsarch.com/r/scholarships/new/"
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()
        try:
            page.goto(url, timeout=30000)
            with open("redlib.html", "w") as f:
                f.write(page.content())
            print("Dumped redlib.html")
        except Exception as e:
            print(e)
        browser.close()

if __name__ == "__main__":
    dump_html()

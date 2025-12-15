import asyncpraw
import os
from datetime import datetime
from scholarship_scraper.models.scholarship import Scholarship
import asyncio

class RedditScraper:
    def __init__(self, client_id=None, client_secret=None, user_agent="scholarship_scraper:v1.0"):
        self.client_id = client_id or os.getenv("REDDIT_CLIENT_ID")
        self.client_secret = client_secret or os.getenv("REDDIT_CLIENT_SECRET")
        self.user_agent = user_agent

    async def scrape_subreddit(self, subreddit_name="scholarships", limit=10):
        if not self.client_id or not self.client_secret:
            print("Reddit API credentials missing.")
            return []

        results = []
        try:
            reddit = asyncpraw.Reddit(
                client_id=self.client_id,
                client_secret=self.client_secret,
                user_agent=self.user_agent
            )
            
            subreddit = await reddit.subreddit(subreddit_name)
            async for submission in subreddit.hot(limit=limit):
                title = submission.title
                text = submission.selftext
                url = submission.url
                
                # Check if it's likely a scholarship 
                if "scholarship" in title.lower() or "grant" in title.lower() or "fund" in title.lower():
                     scholarship = Scholarship(
                        title=f"[Reddit] {title}",
                        source_url=f"https://www.reddit.com{submission.permalink}",
                        description=text[:500] + "...",
                        platform="reddit",
                        date_posted=datetime.fromtimestamp(submission.created_utc)
                    )
                     results.append(scholarship)
            
            await reddit.close()
        except Exception as e:
            print(f"Reddit Scraping Error: {e}")
            
        return results

if __name__ == "__main__":
    # Test
    async def main():
        scraper = RedditScraper()
        res = await scraper.scrape_subreddit()
        print(res)
    asyncio.run(main())

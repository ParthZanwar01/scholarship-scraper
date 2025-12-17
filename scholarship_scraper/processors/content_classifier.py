"""
AI-Powered Content Classifier for Scholarship Pages

Uses OpenAI GPT to analyze page content and determine:
- Is this a direct scholarship application page?
- Or is it an article/blog post ABOUT scholarships?

This provides intelligent filtering beyond URL pattern matching.
"""

import os
import re
import requests
from bs4 import BeautifulSoup

try:
    import openai
    OPENAI_AVAILABLE = True
except ImportError:
    OPENAI_AVAILABLE = False


class ContentClassifier:
    """Classifies web pages as scholarship applications vs articles."""
    
    CLASSIFICATION_PROMPT = """Analyze this web page content and classify it.

PAGE CONTENT:
{content}

CLASSIFY AS ONE OF:
1. "APPLICATION" - This is a direct scholarship application page where students can apply, submit forms, or access the application portal
2. "INFO" - This is an informational page about a specific scholarship with eligibility requirements and how to apply (but not the application itself)
3. "ARTICLE" - This is a blog post, news article, or general content ABOUT scholarships (not a specific scholarship)
4. "OTHER" - Not scholarship related

Return ONLY a JSON object with these fields:
- "classification": one of APPLICATION, INFO, ARTICLE, OTHER
- "confidence": 0.0-1.0 how confident you are
- "scholarship_name": the name of the specific scholarship if found, else null
- "direct_apply_url": URL to apply if mentioned, else null
- "reason": one sentence explaining your classification

Example response:
{{"classification": "INFO", "confidence": 0.9, "scholarship_name": "Gates Scholarship", "direct_apply_url": "https://apply.gates.org", "reason": "Page describes eligibility and benefits but links to separate application portal."}}
"""

    def __init__(self, openai_api_key=None):
        self.api_key = openai_api_key or os.getenv("OPENAI_API_KEY")
        self.client = None
        
        if OPENAI_AVAILABLE and self.api_key:
            self.client = openai.OpenAI(api_key=self.api_key)
            print("✓ ContentClassifier: OpenAI initialized")
        else:
            print("⚠ ContentClassifier: OpenAI not available (will use fallback)")
    
    def fetch_page_content(self, url: str, max_chars: int = 4000) -> str:
        """
        Fetch and extract main text content from a URL.
        
        Args:
            url: The URL to fetch
            max_chars: Maximum characters to return (for API limits)
            
        Returns:
            Cleaned text content from the page
        """
        try:
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
            }
            response = requests.get(url, headers=headers, timeout=15)
            
            if response.status_code != 200:
                return ""
            
            soup = BeautifulSoup(response.text, 'html.parser')
            
            # Remove script, style, nav, footer elements
            for tag in soup(['script', 'style', 'nav', 'footer', 'header', 'aside']):
                tag.decompose()
            
            # Get text
            text = soup.get_text(separator=' ', strip=True)
            
            # Clean up whitespace
            text = re.sub(r'\s+', ' ', text)
            
            # Truncate to max_chars
            return text[:max_chars]
            
        except Exception as e:
            print(f"Error fetching {url}: {e}")
            return ""
    
    def classify_url(self, url: str) -> dict:
        """
        Fetch a URL and classify its content using AI.
        
        Args:
            url: The URL to analyze
            
        Returns:
            Classification result dict with:
            - classification: APPLICATION, INFO, ARTICLE, or OTHER
            - confidence: 0.0-1.0
            - scholarship_name: if found
            - direct_apply_url: if found
            - reason: explanation
            - is_worth_saving: bool - True for APPLICATION or INFO
        """
        # Default result for errors
        default_result = {
            "classification": "UNKNOWN",
            "confidence": 0.0,
            "scholarship_name": None,
            "direct_apply_url": None,
            "reason": "Could not analyze",
            "is_worth_saving": False
        }
        
        # Fetch page content
        content = self.fetch_page_content(url)
        if not content or len(content) < 100:
            default_result["reason"] = "Could not fetch page content"
            return default_result
        
        # Use AI if available
        if self.client:
            return self._classify_with_ai(url, content)
        else:
            return self._classify_with_heuristics(url, content)
    
    def _classify_with_ai(self, url: str, content: str) -> dict:
        """Use OpenAI GPT to classify the content."""
        try:
            prompt = self.CLASSIFICATION_PROMPT.format(content=content[:3000])
            
            response = self.client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[
                    {"role": "system", "content": "You are a scholarship classification assistant. Return only valid JSON."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.2,
                max_tokens=300
            )
            
            result_text = response.choices[0].message.content.strip()
            
            # Parse JSON response
            import json
            # Clean up potential markdown code blocks
            if result_text.startswith('```'):
                result_text = re.sub(r'^```\w*\n?', '', result_text)
                result_text = re.sub(r'\n?```$', '', result_text)
            
            result = json.loads(result_text)
            
            # Add is_worth_saving flag
            result["is_worth_saving"] = result.get("classification") in ["APPLICATION", "INFO"]
            
            return result
            
        except Exception as e:
            print(f"AI classification error: {e}")
            return self._classify_with_heuristics(url, content)
    
    def _classify_with_heuristics(self, url: str, content: str) -> dict:
        """Fallback classification using keyword heuristics."""
        content_lower = content.lower()
        url_lower = url.lower()
        
        # Application indicators
        application_keywords = [
            'apply now', 'submit application', 'application form',
            'application deadline', 'start application', 'create account',
            'sign up to apply', 'begin application'
        ]
        
        # Article indicators
        article_keywords = [
            'share this', 'related articles', 'read more',
            'by author', 'published on', 'comments section',
            'subscribe to', 'newsletter', 'blog post'
        ]
        
        # Count matches
        app_score = sum(1 for kw in application_keywords if kw in content_lower)
        article_score = sum(1 for kw in article_keywords if kw in content_lower)
        
        # URL-based hints
        if '/blog/' in url_lower or '/news/' in url_lower or '/article/' in url_lower:
            article_score += 3
        if '/apply' in url_lower or '/application' in url_lower:
            app_score += 3
        
        # Determine classification
        if app_score > article_score and app_score >= 2:
            classification = "APPLICATION"
            confidence = min(0.7, 0.4 + app_score * 0.1)
        elif article_score > app_score and article_score >= 2:
            classification = "ARTICLE"
            confidence = min(0.7, 0.4 + article_score * 0.1)
        elif 'scholarship' in content_lower or 'financial aid' in content_lower:
            classification = "INFO"
            confidence = 0.5
        else:
            classification = "OTHER"
            confidence = 0.3
        
        return {
            "classification": classification,
            "confidence": confidence,
            "scholarship_name": None,
            "direct_apply_url": None,
            "reason": f"Heuristic classification (app_score={app_score}, article_score={article_score})",
            "is_worth_saving": classification in ["APPLICATION", "INFO"]
        }
    
    def should_save_scholarship(self, url: str) -> tuple:
        """
        Quick check if a URL is worth saving to the database.
        
        Returns:
            tuple: (should_save: bool, reason: str, better_url: str or None)
        """
        result = self.classify_url(url)
        
        should_save = result.get("is_worth_saving", False)
        reason = result.get("reason", "Unknown")
        better_url = result.get("direct_apply_url")  # If found a direct link
        
        return (should_save, reason, better_url)


# Quick CLI test
if __name__ == "__main__":
    classifier = ContentClassifier()
    
    test_urls = [
        "https://www.iie.org/blog/truly-transformative/",
        "https://bold.org/scholarships/",
    ]
    
    for url in test_urls:
        print(f"\nAnalyzing: {url}")
        result = classifier.classify_url(url)
        print(f"  Classification: {result['classification']}")
        print(f"  Confidence: {result['confidence']}")
        print(f"  Worth Saving: {result['is_worth_saving']}")
        print(f"  Reason: {result['reason']}")

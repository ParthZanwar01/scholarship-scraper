"""
URL Filter for Scholarship Scraping

Distinguishes between:
- Article/blog URLs (BLOCK) - news posts about scholarships
- Direct scholarship URLs (ALLOW) - actual application pages

Usage:
    from processors.url_filter import filter_url, get_best_scholarship_url
    
    is_valid, reason = filter_url("https://example.com/blog/scholarship-tips")
    # (False, "blocked: contains /blog/ pattern")
    
    best_url = get_best_scholarship_url(["https://site.com/blog/...", "https://apply.org/scholarship"])
    # "https://apply.org/scholarship"
"""

import re
from urllib.parse import urlparse

# ============================================================================
# BLOCK PATTERNS - URLs matching these are likely articles/news, NOT applications
# ============================================================================

ARTICLE_PATH_PATTERNS = [
    r'/blog/',
    r'/blogs/',
    r'/news/',
    r'/article/',
    r'/articles/',
    r'/story/',
    r'/stories/',
    r'/press[-_]?release/',
    r'/press/',
    r'/featured/',
    r'/insights/',
    r'/about[-_]?us/',
    r'/about/',
    r'/learn/',
    r'/resources/article',
    r'/post/',
    r'/posts/',
    r'/updates/',
    r'/announcements/',
    r'/media/',
    r'/magazine/',
    r'/journal/',
]

# Domains that are primarily blog/news platforms (not scholarship sources)
ARTICLE_DOMAINS = [
    'medium.com',
    'wordpress.com',
    'blogger.com',
    'substack.com',
    'hubspot.com',
    'wix.com',
    'squarespace.com',
    'tumblr.com',
    'ghost.io',
    'telegraph.co.uk',
    'theguardian.com',
    'nytimes.com',
    'washingtonpost.com',
    'cnn.com',
    'bbc.com',
    'forbes.com',
    'huffpost.com',
    'buzzfeed.com',
]

# ============================================================================
# ALLOW PATTERNS - URLs matching these are likely direct scholarship pages
# ============================================================================

SCHOLARSHIP_PATH_PATTERNS = [
    r'/apply',
    r'/application',
    r'/scholarship',
    r'/scholarships',
    r'/financial[-_]?aid',
    r'/submit',
    r'/register',
    r'/eligibility',
    r'/award',
    r'/grants?/',
    r'/funding',
    r'/portal',
]

# Trusted scholarship database domains (always allow)
SCHOLARSHIP_DOMAINS = [
    'fastweb.com',
    'scholarships.com',
    'bold.org',
    'niche.com',
    'cappex.com',
    'chegg.com',
    'collegeboard.org',
    'petersons.com',
    'unigo.com',
    'scholarshipamerica.org',
    'thescholarshipsystem.com',
    'goingmerry.com',
    'raise.me',
    'scholly.com',
    'jlv.org',
    'questbridge.org',
    'coca-colascholarsfoundation.org',
    'goldwaterscholarship.gov',
    'nsf.gov',
    'ed.gov',
]

# .edu domains are generally trustworthy for scholarship info
EDU_DOMAIN_PATTERN = r'\.edu$'


def filter_url(url: str) -> tuple:
    """
    Determine if a URL should be kept or blocked.
    
    Args:
        url: The URL to check
        
    Returns:
        tuple: (is_valid: bool, reason: str)
               is_valid=True means this is likely a direct scholarship link
    """
    if not url or not isinstance(url, str):
        return (False, "invalid: empty or not a string")
    
    try:
        parsed = urlparse(url.lower())
        domain = parsed.netloc
        path = parsed.path
    except Exception:
        return (False, "invalid: could not parse URL")
    
    # Remove www. prefix for matching
    if domain.startswith('www.'):
        domain = domain[4:]
    
    # ---- ALWAYS ALLOW: Trusted scholarship domains ----
    for trusted in SCHOLARSHIP_DOMAINS:
        if domain == trusted or domain.endswith('.' + trusted):
            return (True, f"allowed: trusted scholarship domain ({trusted})")
    
    # ---- ALWAYS ALLOW: .edu domains ----
    if re.search(EDU_DOMAIN_PATTERN, domain):
        return (True, "allowed: .edu domain")
    
    # ---- BLOCK: Known article/blog domains ----
    for blocked in ARTICLE_DOMAINS:
        if domain == blocked or domain.endswith('.' + blocked):
            return (False, f"blocked: article/news domain ({blocked})")
    
    # ---- BLOCK: Article path patterns ----
    for pattern in ARTICLE_PATH_PATTERNS:
        if re.search(pattern, path, re.IGNORECASE):
            return (False, f"blocked: contains {pattern.replace(chr(92), '')} pattern")
    
    # ---- PRIORITIZE: Scholarship path patterns ----
    for pattern in SCHOLARSHIP_PATH_PATTERNS:
        if re.search(pattern, path, re.IGNORECASE):
            return (True, f"allowed: scholarship-related path ({pattern})")
    
    # ---- DEFAULT: Allow but with lower confidence ----
    return (True, "allowed: no blocking patterns found (neutral)")


def get_best_scholarship_url(urls: list) -> str:
    """
    Given a list of URLs, return the one most likely to be a direct scholarship link.
    
    Priority:
    1. Trusted scholarship domains
    2. .edu domains
    3. URLs with scholarship path patterns
    4. First valid URL
    
    Args:
        urls: List of URL strings
        
    Returns:
        The best URL, or empty string if none are valid
    """
    if not urls:
        return ""
    
    # Clean and dedupe
    urls = list(set([u.strip() for u in urls if u and isinstance(u, str)]))
    
    # Score each URL
    scored = []
    for url in urls:
        is_valid, reason = filter_url(url)
        if not is_valid:
            continue
        
        score = 0
        url_lower = url.lower()
        
        # Trusted domains get highest priority
        if "trusted scholarship domain" in reason:
            score += 100
        
        # .edu domains
        if ".edu" in reason:
            score += 80
        
        # Scholarship keywords in path
        if "scholarship-related path" in reason:
            score += 50
        
        # Bonus for apply/application in URL
        if '/apply' in url_lower or '/application' in url_lower:
            score += 30
        
        scored.append((score, url))
    
    if not scored:
        return ""
    
    # Sort by score descending, return best
    scored.sort(key=lambda x: x[0], reverse=True)
    return scored[0][1]


def filter_urls_batch(urls: list) -> list:
    """
    Filter a list of URLs, returning only valid ones.
    
    Args:
        urls: List of URL strings
        
    Returns:
        List of valid URLs (those that passed the filter)
    """
    return [u for u in urls if filter_url(u)[0]]


# ============================================================================
# CLI Testing
# ============================================================================

if __name__ == "__main__":
    # Test cases
    test_urls = [
        # Should be BLOCKED
        "https://www.iie.org/blog/truly-transformative-nextgen-service-fellows/",
        "https://medium.com/scholarships-for-students",
        "https://example.com/news/scholarship-announced",
        "https://university.edu/press-release/new-funding",
        
        # Should be ALLOWED
        "https://apply.iie.org/scholarship-portal",
        "https://www.fastweb.com/college-scholarships/scholarships/12345",
        "https://mit.edu/financial-aid/scholarships",
        "https://bold.org/scholarships/software-engineering",
        "https://example.org/submit-application",
    ]
    
    print("URL Filter Test Results:")
    print("=" * 60)
    
    for url in test_urls:
        is_valid, reason = filter_url(url)
        status = "✓ ALLOW" if is_valid else "✗ BLOCK"
        print(f"{status}: {url[:50]}...")
        print(f"         Reason: {reason}")
        print()
    
    print("=" * 60)
    print("Best URL from mixed list:")
    best = get_best_scholarship_url(test_urls)
    print(f"  -> {best}")

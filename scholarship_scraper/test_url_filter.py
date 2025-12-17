#!/usr/bin/env python3
"""Test the URL filter module."""

import sys
sys.path.insert(0, '/Users/parthzanwar/Desktop/Webscraper for Scholarships/scholarship_scraper')

from processors.url_filter import filter_url, get_best_scholarship_url

print('=== URL FILTER TEST ===')
print()

# Test article URLs (should be BLOCKED)
test_blocked = [
    'https://www.iie.org/blog/truly-transformative-nextgen/',
    'https://medium.com/scholarships-for-students',
    'https://example.com/news/scholarship-announced',
]

print('SHOULD BE BLOCKED:')
for url in test_blocked:
    is_valid, reason = filter_url(url)
    status = '✓ BLOCKED' if not is_valid else '✗ PASSED (bad!)'
    print(f'  {status}: {url[:50]}...')
    print(f'           {reason}')

print()

# Test scholarship URLs (should be ALLOWED)
test_allowed = [
    'https://apply.iie.org/scholarship-portal',
    'https://www.fastweb.com/scholarship/12345',
    'https://mit.edu/financial-aid/scholarships',
    'https://bold.org/scholarships/software-engineering',
]

print('SHOULD BE ALLOWED:')
for url in test_allowed:
    is_valid, reason = filter_url(url)
    status = '✓ ALLOWED' if is_valid else '✗ BLOCKED (bad!)'
    print(f'  {status}: {url[:50]}...')
    print(f'           {reason}')

print()

# Test get_best_scholarship_url
mixed = [
    'https://www.iie.org/blog/article/',
    'https://fastweb.com/scholarships/123',
    'https://random-site.com/page',
]
best = get_best_scholarship_url(mixed)
print(f'BEST URL from mixed list: {best}')

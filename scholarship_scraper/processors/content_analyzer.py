import re

class ContentAnalyzer:
    def __init__(self):
        self.keywords = ["scholarship", "grant", "fellowship", "aid", "tuition", "stipend"]
        self.negative_keywords = ["loan", "scam", "sweepstakes"]

    def calculate_relevance_score(self, text: str) -> int:
        score = 0
        text_lower = text.lower()
        
        for word in self.keywords:
            if word in text_lower:
                score += 10
        
        for word in self.negative_keywords:
            if word in text_lower:
                score -= 50
                
        return score

    def extract_amount(self, text: str):
        # Naive regex for $ amounts
        matches = re.findall(r'\$\d+(?:,\d+)?', text)
        if matches:
            # Return max amount found as a heuristic
            return max(matches, key=lambda x: int(x.replace("$", "").replace(",", "")))
        return None

    def is_scholarship(self, text: str) -> bool:
        return self.calculate_relevance_score(text) > 0

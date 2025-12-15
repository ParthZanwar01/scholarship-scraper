from dataclasses import dataclass
from typing import Optional, List
from datetime import datetime

@dataclass
class Scholarship:
    title: str
    source_url: str
    description: Optional[str] = None
    amount: Optional[str] = None
    deadline: Optional[str] = None # Keeping as string for flexibility, can parse to datetime later
    eligibility_criteria: Optional[List[str]] = None
    date_posted: Optional[datetime] = None
    platform: str = "general" # 'general', 'instagram', etc.

    def to_dict(self):
        return {
            "title": self.title,
            "source_url": self.source_url,
            "description": self.description,
            "amount": self.amount,
            "deadline": self.deadline,
            "eligibility_criteria": self.eligibility_criteria,
            "date_posted": self.date_posted.isoformat() if self.date_posted else None,
            "platform": self.platform
        }

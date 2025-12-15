from sqlalchemy import Column, Integer, String, Text, DateTime, Boolean
from sqlalchemy.sql import func
from .database import Base

class ScholarshipModel(Base):
    __tablename__ = "scholarships"

    id = Column(Integer, primary_key=True, index=True)
    title = Column(String, index=True)
    source_url = Column(String, unique=True, index=True)
    description = Column(Text, nullable=True)
    amount = Column(String, nullable=True)
    deadline = Column(String, nullable=True)
    platform = Column(String, default="general") # google, instagram, etc.
    raw_text = Column(Text, nullable=True) # Full scraped content/OCR text
    
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    def to_dict(self):
        return {
            "id": self.id,
            "title": self.title,
            "source_url": self.source_url,
            "description": self.description,
            "amount": self.amount,
            "deadline": self.deadline,
            "platform": self.platform,
            "created_at": self.created_at.isoformat() if self.created_at else None
        }

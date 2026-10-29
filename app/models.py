"""
Pydantic models for Revio Review Intelligence API.
"""

from enum import Enum
from typing import List, Optional

from pydantic import BaseModel, Field, field_validator


class Sentiment(str, Enum):
    POSITIVE = "Positive"
    NEGATIVE = "Negative"
    NEUTRAL = "Neutral"


class Urgency(str, Enum):
    LOW = "Low"
    MEDIUM = "Medium"
    HIGH = "High"


class ReviewAnalysis(BaseModel):
    sentiment: Sentiment = Field(..., description="Overall sentiment of the review.")
    topic: str = Field(..., description="Main topic or issue.")
    urgency: Urgency = Field(..., description="Urgency level.")
    explanation: str = Field(..., description="Brief explanation of the classification.")
    recommended_action: str = Field(..., description="Suggested business action.")
    draft_reply: str = Field(..., description="Draft customer reply — requires human approval before sending.")


class AnalyzeRequest(BaseModel):
    review_text: str = Field(..., min_length=1, max_length=2000, description="Customer review text.")

    @field_validator("review_text")
    @classmethod
    def not_blank(cls, v: str) -> str:
        if not v.strip():
            raise ValueError("review_text cannot be blank")
        return v


class AnalyzeResponse(BaseModel):
    analysis: ReviewAnalysis


class CSVAnalyzeResponse(BaseModel):
    analyses: List[ReviewAnalysis]
    summary: Optional[str] = None
    sentiment_distribution: Optional[dict] = None
    urgency_distribution: Optional[dict] = None
    frequent_issues: Optional[List[str]] = None
    important_negative_feedback: Optional[List[str]] = None
    recommended_actions: Optional[List[str]] = None
    draft_replies: Optional[List[str]] = None

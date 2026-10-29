"""
Service functions for analyzing reviews using the Groq/xAI LLM (OpenAI-compatible).
"""

import json
from typing import List

import openai
from openai import AsyncOpenAI
from pydantic import ValidationError

from app.models import ReviewAnalysis, CSVAnalyzeResponse, Sentiment

SYSTEM_PROMPT = """You are an AI assistant that analyses a single customer review.
Return ONLY a valid JSON object with these exact keys:
{
  "sentiment": "Positive" or "Negative" or "Neutral",
  "topic": "short description of the main issue",
  "urgency": "Low" or "Medium" or "High",
  "explanation": "brief explanation of your classification",
  "recommended_action": "suggested business action",
  "draft_reply": "draft customer reply (requires human approval before sending)"
}
Do not include any text outside the JSON object."""


def _get_client(settings):
    return AsyncOpenAI(
        api_key=settings.llm_api_key,
        base_url=settings.llm_base_url,
        timeout=30,
    )


async def analyze_review(review_text: str, settings) -> ReviewAnalysis:
    """Analyze a single review via LLM and return a validated ReviewAnalysis."""
    client = _get_client(settings)
    raw = ""
    try:
        response = await client.chat.completions.create(
            model=settings.llm_model,
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": review_text},
            ],
            temperature=0.0,
            response_format={"type": "json_object"},
        )
        raw = response.choices[0].message.content.strip()
        data = json.loads(raw)
        return ReviewAnalysis(**data)
    except openai.AuthenticationError as e:
        raise RuntimeError(f"Invalid API key: {e}")
    except openai.RateLimitError as e:
        raise RuntimeError(f"Rate limit exceeded: {e}")
    except openai.APITimeoutError as e:
        raise RuntimeError(f"Request timed out: {e}")
    except openai.APIError as e:
        raise RuntimeError(f"LLM API error: {e}")
    except json.JSONDecodeError as e:
        raise RuntimeError(f"Failed to parse LLM response as JSON: {e}. Raw: {raw}")
    except ValidationError as e:
        raise RuntimeError(f"Response schema validation failed: {e}. Raw: {raw}")


async def analyze_reviews_batch(reviews: List[str], settings) -> CSVAnalyzeResponse:
    """Analyze a list of reviews and compute aggregate insights."""
    analyses = []
    for text in reviews:
        analysis = await analyze_review(text, settings)
        analyses.append(analysis)

    sentiment_counts: dict = {}
    urgency_counts: dict = {}
    topics: dict = {}
    negative_feedback: List[str] = []
    actions: List[str] = []
    drafts: List[str] = []

    for a in analyses:
        sentiment_counts[a.sentiment.value] = sentiment_counts.get(a.sentiment.value, 0) + 1
        urgency_counts[a.urgency.value] = urgency_counts.get(a.urgency.value, 0) + 1
        topics[a.topic] = topics.get(a.topic, 0) + 1
        if a.sentiment == Sentiment.NEGATIVE:
            negative_feedback.append(a.explanation)
        actions.append(a.recommended_action)
        drafts.append(a.draft_reply)

    frequent_issues = [t for t, _ in sorted(topics.items(), key=lambda kv: kv[1], reverse=True)[:3]]

    summary = (
        f"Analyzed {len(analyses)} reviews. "
        f"Sentiment: {sentiment_counts}. "
        f"Urgency: {urgency_counts}."
    )

    return CSVAnalyzeResponse(
        analyses=analyses,
        summary=summary,
        sentiment_distribution=sentiment_counts,
        urgency_distribution=urgency_counts,
        frequent_issues=frequent_issues,
        important_negative_feedback=negative_feedback,
        recommended_actions=actions,
        draft_replies=drafts,
    )

"""
Tests for Revio Review Intelligence API.
"""

import io
import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from unittest import mock
from unittest.mock import AsyncMock, MagicMock
from fastapi.testclient import TestClient

from app.models import ReviewAnalysis, Sentiment, Urgency

# ---------------------------------------------------------------------------
# Shared mock analysis object
# ---------------------------------------------------------------------------
def _mock_analysis():
    return ReviewAnalysis(
        sentiment=Sentiment.POSITIVE,
        topic="Delivery speed",
        urgency=Urgency.LOW,
        explanation="Customer happy with fast delivery.",
        recommended_action="Thank the customer and encourage a repeat purchase.",
        draft_reply="[DRAFT - requires human approval] Thank you for your kind feedback!",
    )


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------
def get_client():
    from app.main import app
    return TestClient(app)


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------
def test_health():
    client = get_client()
    resp = client.get("/health")
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "ok"


@mock.patch("app.main.analyze_review", new_callable=AsyncMock)
def test_analyze_success(mock_fn):
    mock_fn.return_value = _mock_analysis()
    client = get_client()
    resp = client.post("/analyze", json={"review_text": "Great product, fast delivery!"})
    assert resp.status_code == 200
    data = resp.json()
    assert "analysis" in data
    assert data["analysis"]["sentiment"] == "Positive"
    assert data["analysis"]["urgency"] == "Low"
    assert "DRAFT" in data["analysis"]["draft_reply"]


def test_analyze_blank_review():
    client = get_client()
    resp = client.post("/analyze", json={"review_text": "   "})
    assert resp.status_code == 422


def test_analyze_empty_string():
    client = get_client()
    resp = client.post("/analyze", json={"review_text": ""})
    assert resp.status_code == 422


def test_analyze_missing_field():
    client = get_client()
    resp = client.post("/analyze", json={})
    assert resp.status_code == 422


@mock.patch("app.main.analyze_review", new_callable=AsyncMock)
def test_analyze_llm_error(mock_fn):
    mock_fn.side_effect = RuntimeError("LLM API error: connection refused")
    client = get_client()
    resp = client.post("/analyze", json={"review_text": "Some review."})
    assert resp.status_code == 502
    assert "LLM API error" in resp.json()["detail"]


@mock.patch("app.services.analyzer.analyze_review", new_callable=AsyncMock)
def test_analyze_csv_success(mock_fn):
    mock_fn.return_value = _mock_analysis()
    client = get_client()
    csv_content = "review_text\nGreat product!\nTerrible service.\nIt was okay.\n"
    resp = client.post(
        "/analyze-csv",
        files={"file": ("reviews.csv", io.BytesIO(csv_content.encode()), "text/csv")},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert "analyses" in data
    assert len(data["analyses"]) == 3
    assert "summary" in data
    assert "sentiment_distribution" in data


def test_analyze_csv_no_column():
    client = get_client()
    csv_content = "text\nHello\nWorld\n"
    resp = client.post(
        "/analyze-csv",
        files={"file": ("bad.csv", io.BytesIO(csv_content.encode()), "text/csv")},
    )
    assert resp.status_code == 400


def test_analyze_csv_empty_rows():
    client = get_client()
    csv_content = "review_text\n\n\n"
    resp = client.post(
        "/analyze-csv",
        files={"file": ("empty.csv", io.BytesIO(csv_content.encode()), "text/csv")},
    )
    assert resp.status_code == 400


def test_analyze_csv_malformed():
    client = get_client()
    resp = client.post(
        "/analyze-csv",
        files={"file": ("bad.csv", io.BytesIO(b"\x00\x01\x02"), "text/csv")},
    )
    assert resp.status_code in (400, 500)


def test_response_schema_fields():
    """Ensure ReviewAnalysis has all required fields."""
    a = _mock_analysis()
    assert hasattr(a, "sentiment")
    assert hasattr(a, "topic")
    assert hasattr(a, "urgency")
    assert hasattr(a, "explanation")
    assert hasattr(a, "recommended_action")
    assert hasattr(a, "draft_reply")

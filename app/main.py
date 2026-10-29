"""
FastAPI backend for Revio Review Intelligence.
"""

import io
import csv
import os
from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException, UploadFile, File

load_dotenv()

from pydantic_settings import BaseSettings

from app.models import AnalyzeRequest, AnalyzeResponse, CSVAnalyzeResponse
from app.services.analyzer import analyze_review, analyze_reviews_batch


class Settings(BaseSettings):
    llm_api_key: str = "unset"
    llm_base_url: str = "https://api.groq.com/openai/v1"
    llm_model: str = "openai/gpt-oss-20b"
    max_csv_size_mb: int = 5
    max_batch_size: int = 100

    model_config = {"env_file": ".env", "env_file_encoding": "utf-8", "extra": "ignore"}


settings = Settings()

app = FastAPI(
    title="Revio Review Intelligence API",
    description="AI-powered customer review analysis using Groq/xAI LLM.",
    version="1.0.0",
)


@app.get("/health", tags=["Health"])
def health_check():
    """Returns service health status. Does not expose credentials."""
    return {"status": "ok", "service": "Revio Review Intelligence API"}


@app.post("/analyze", response_model=AnalyzeResponse, tags=["Analysis"])
async def analyze_endpoint(request: AnalyzeRequest):
    """Analyze a single customer review."""
    try:
        analysis = await analyze_review(request.review_text, settings)
        return AnalyzeResponse(analysis=analysis)
    except RuntimeError as e:
        raise HTTPException(status_code=502, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Unexpected error: {e}")


@app.post("/analyze-csv", response_model=CSVAnalyzeResponse, tags=["Analysis"])
async def analyze_csv_endpoint(file: UploadFile = File(...)):
    """Upload a CSV with a 'review_text' column to analyze multiple reviews."""
    content = await file.read()
    if len(content) > settings.max_csv_size_mb * 1024 * 1024:
        raise HTTPException(status_code=413, detail="CSV file too large (max 5 MB).")
    try:
        csv_file = io.StringIO(content.decode("utf-8"))
        reader = csv.DictReader(csv_file)
        reviews = [row["review_text"].strip() for row in reader if row.get("review_text", "").strip()]
    except Exception:
        raise HTTPException(status_code=400, detail="Could not parse CSV. Ensure it has a 'review_text' column.")

    if not reviews:
        raise HTTPException(status_code=400, detail="No valid review_text rows found in CSV.")
    if len(reviews) > settings.max_batch_size:
        raise HTTPException(status_code=400, detail=f"Batch exceeds limit of {settings.max_batch_size} reviews.")

    try:
        result = await analyze_reviews_batch(reviews, settings)
        return result
    except RuntimeError as e:
        raise HTTPException(status_code=502, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Unexpected error: {e}")

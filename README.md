# Revio AI — Review Intelligence Copilot

> **Cynbit AI/ML Engineer Intern Phase 2 Assessment Project**
>
> An independent AI-powered customer review analysis platform built with FastAPI, Streamlit, and the Groq LLM API (OpenAI-compatible interface).

---

## What it does

For each customer review, Revio AI produces:

| Output | Description |
|---|---|
| **Sentiment** | Positive / Negative / Neutral |
| **Topic** | Main issue identified |
| **Urgency** | Low / Medium / High |
| **Explanation** | Why it was classified this way |
| **Recommended Action** | Suggested business response |
| **Draft Reply** | Customer-facing reply draft — **requires human approval before sending** |

Batch CSV mode also produces sentiment/urgency charts, most-frequent issues, and an overall summary.

---

## Tech stack

| Component | Technology |
|---|---|
| Backend API | FastAPI + Uvicorn |
| Frontend dashboard | Streamlit |
| LLM | Groq API (OpenAI-compatible, `llama3-8b-8192`) |
| LLM client | `openai` Python SDK (configured with Groq base URL) |
| Data validation | Pydantic v2 + pydantic-settings |
| Data processing | Pandas |
| Charts | Plotly |
| Tests | Pytest (LLM fully mocked) |
| Config | python-dotenv + Render environment variables |

---

## Project structure

```
revio-review-intelligence/
├── app/
│   ├── __init__.py
│   ├── main.py            # FastAPI routes
│   ├── models.py          # Pydantic request/response schemas
│   └── services/
│       ├── __init__.py
│       └── analyzer.py    # LLM analysis logic (isolated from routes)
├── frontend.py            # Streamlit dashboard
├── data/
│   └── sample_reviews.csv # 15 fictional reviews for demo
├── tests/
│   └── test_api.py        # 11 unit/integration tests (LLM mocked)
├── reports/
│   ├── ai_opportunity_report.md
│   └── technical_approach.md
├── requirements.txt
├── render.yaml            # Render deployment blueprint
├── .env.example           # Template — copy to .env, never commit .env
├── .gitignore
├── .streamlit/
│   └── secrets.toml.example
└── README.md
```

---

## Local Mac setup

### 1. Prerequisites

- Python 3.11+ (tested on 3.13)
- A [Groq API key](https://console.groq.com) — free tier available

### 2. Create and activate a virtual environment

```bash
cd revio-review-intelligence
python -m venv venv
source venv/bin/activate
```

### 3. Install dependencies

```bash
pip install -r requirements.txt
```

### 4. Configure environment variables

```bash
cp .env.example .env
```

Open `.env` and fill in your values:

```dotenv
LLM_API_KEY=gsk_your_real_groq_api_key
LLM_BASE_URL=https://api.groq.com/openai/v1
LLM_MODEL=llama3-8b-8192
API_BASE_URL=http://127.0.0.1:8000
```

> **Model IDs:** Check [console.groq.com/docs/models](https://console.groq.com/docs/models) for currently available models. Common choices: `llama3-8b-8192`, `llama3-70b-8192`, `mixtral-8x7b-32768`.

### 5. Start the FastAPI backend (Terminal 1)

```bash
uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```

- API docs: http://127.0.0.1:8000/docs
- Health check: http://127.0.0.1:8000/health

### 6. Start the Streamlit frontend (Terminal 2)

```bash
streamlit run frontend.py
```

- Dashboard: http://localhost:8501

### 7. Run tests

```bash
pytest tests/test_api.py -v
```

All 11 tests pass with the LLM fully mocked (no real API call made during tests).

---

## API endpoints

| Method | Path | Description |
|---|---|---|
| `GET` | `/health` | Service health status |
| `POST` | `/analyze` | Analyze a single review (JSON body) |
| `POST` | `/analyze-csv` | Upload CSV with `review_text` column for batch analysis |

### Example: single review

```bash
curl -X POST http://127.0.0.1:8000/analyze \
  -H "Content-Type: application/json" \
  -d '{"review_text": "The product arrived damaged and support ignored me."}'
```

---

## Sample dataset

`data/sample_reviews.csv` contains 15 fictional customer reviews covering positive, negative, neutral, and mixed scenarios. This is illustrative data — it does not contain any real customer information.

---

## GitHub upload

```bash
# Check what will be committed (verify .env is NOT listed)
git status

# Stage only the safe files
git add app/ frontend.py requirements.txt render.yaml .env.example .gitignore README.md data/ tests/ reports/ .streamlit/secrets.toml.example

git commit -m "Initial commit: Revio AI Review Intelligence Copilot"

# Create repo at github.com, then:
git remote add origin https://github.com/YOUR_USERNAME/revio-review-intelligence.git
git branch -M main
git push -u origin main
```

> **Never run `git add .`** — confirm `.env` is in `.gitignore` first.

---

## Render deployment (FastAPI backend)

1. Push code to GitHub.
2. Go to [render.com](https://render.com) → **New → Web Service** → connect your GitHub repo.
3. Render will auto-detect `render.yaml`. Confirm settings:
   - **Build command:** `pip install -r requirements.txt`
   - **Start command:** `uvicorn app.main:app --host 0.0.0.0 --port $PORT`
4. In Render **Environment** tab, add:
   - `LLM_API_KEY` = your Groq API key (**set as secret, not in render.yaml**)
   - `LLM_BASE_URL` = `https://api.groq.com/openai/v1`
   - `LLM_MODEL` = `llama3-8b-8192`
5. Deploy and verify: `https://your-service.onrender.com/health`

> Free Render services sleep after 15 min of inactivity. The first request may take ~30 s to wake up.

---

## Streamlit Community Cloud deployment (frontend)

1. Go to [share.streamlit.io](https://share.streamlit.io) → **New app**.
2. Select your GitHub repo, branch `main`, main file `frontend.py`.
3. Click **Advanced settings → Secrets** and add:

```toml
API_BASE_URL = "https://your-render-service.onrender.com"
```

4. Deploy. The frontend reads `API_BASE_URL` from Streamlit secrets.

> **Do NOT** put `LLM_API_KEY` in Streamlit secrets — all LLM calls happen on the backend only.

---

## Troubleshooting

| Error | Fix |
|---|---|
| `Cannot connect to backend` | Ensure `uvicorn` is running; check `API_BASE_URL` in `.env` |
| `Invalid API Key` | Verify `LLM_API_KEY` in `.env` matches your Groq console key |
| `Rate limit exceeded` | Groq free tier has rate limits; wait a moment and retry |
| `model not found` | Check `LLM_MODEL` — valid IDs at console.groq.com/docs/models |
| Render backend sleeping | First request takes ~30 s; refresh or wait |
| `pydantic ImportError BaseSettings` | Run `pip install pydantic-settings` |
| `ModuleNotFoundError: app` | Run pytest from the project root directory |

---

## Security notes

- API keys are **never** hardcoded, logged, or sent to the frontend.
- `.env` is in `.gitignore` — never commit it.
- Draft customer replies are clearly labeled and require human approval.
- Input length is validated (max 2 000 characters per review).
- CSV uploads are size-limited (max 5 MB, 100 rows per batch).

---

## Assessment checklist

- [x] FastAPI backend with `/health`, `/analyze`, `/analyze-csv`
- [x] Pydantic v2 request/response validation
- [x] Groq API via OpenAI-compatible client, fully configurable via env vars
- [x] Streamlit frontend with charts, draft replies, error messages
- [x] 11 automated tests, all passing, LLM fully mocked
- [x] `.env.example` template, `.gitignore`, no credentials in repo
- [x] `render.yaml` deployment blueprint
- [x] Streamlit secrets template
- [x] `data/sample_reviews.csv` — 15 fictional reviews
- [x] AI Opportunity Report (`reports/ai_opportunity_report.md`)
- [x] Technical Approach Report (`reports/technical_approach.md`)
- [x] README with full local setup, GitHub, Render, Streamlit Cloud instructions

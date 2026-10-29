"""
Revio AI — Review Intelligence Copilot
Streamlit frontend. Calls the FastAPI backend; contains NO LLM logic.
"""

import os
import streamlit as st
import httpx
import pandas as pd
import plotly.express as px

# ---------------------------------------------------------------------------
# Config — backend URL from Streamlit secrets (production) or env / default
# ---------------------------------------------------------------------------
try:
    API_BASE_URL = st.secrets["API_BASE_URL"]
except (FileNotFoundError, KeyError):
    API_BASE_URL = os.getenv("API_BASE_URL", "http://127.0.0.1:8000")

TIMEOUT = 60

# ---------------------------------------------------------------------------
# Page setup
# ---------------------------------------------------------------------------
st.set_page_config(
    page_title="Revio AI — Review Intelligence",
    page_icon="🔍",
    layout="wide",
    initial_sidebar_state="collapsed",
)

st.title("🔍 Revio AI — Review Intelligence Copilot")
st.markdown(
    "AI-powered analysis of customer reviews. "
    "Sentiment · Topic · Urgency · Recommended Actions · Draft Replies."
)
st.caption("⚠️ All suggested customer replies are **drafts only** and require human review before sending.")

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------
def backend_get(path: str):
    try:
        r = httpx.get(f"{API_BASE_URL}{path}", timeout=10)
        r.raise_for_status()
        return r.json(), None
    except httpx.ConnectError:
        return None, f"Cannot connect to backend at `{API_BASE_URL}`. Is the FastAPI server running?"
    except httpx.HTTPStatusError as e:
        return None, f"Backend returned HTTP {e.response.status_code}: {e.response.text}"
    except Exception as e:
        return None, str(e)


def backend_post_json(path: str, payload: dict):
    try:
        r = httpx.post(f"{API_BASE_URL}{path}", json=payload, timeout=TIMEOUT)
        r.raise_for_status()
        return r.json(), None
    except httpx.ConnectError:
        return None, f"Cannot connect to backend at `{API_BASE_URL}`. Is the FastAPI server running?"
    except httpx.HTTPStatusError as e:
        try:
            detail = e.response.json().get("detail", e.response.text)
        except Exception:
            detail = e.response.text
        return None, f"Error {e.response.status_code}: {detail}"
    except Exception as e:
        return None, str(e)


def backend_post_file(path: str, file_bytes: bytes, filename: str):
    try:
        r = httpx.post(
            f"{API_BASE_URL}{path}",
            files={"file": (filename, file_bytes, "text/csv")},
            timeout=TIMEOUT,
        )
        r.raise_for_status()
        return r.json(), None
    except httpx.ConnectError:
        return None, f"Cannot connect to backend at `{API_BASE_URL}`. Is the FastAPI server running?"
    except httpx.HTTPStatusError as e:
        try:
            detail = e.response.json().get("detail", e.response.text)
        except Exception:
            detail = e.response.text
        return None, f"Error {e.response.status_code}: {detail}"
    except Exception as e:
        return None, str(e)


def sentiment_color(s: str) -> str:
    return {"Positive": "🟢", "Negative": "🔴", "Neutral": "🟡"}.get(s, "⚪")


def urgency_color(u: str) -> str:
    return {"Low": "🟢", "Medium": "🟠", "High": "🔴"}.get(u, "⚪")



# ---------------------------------------------------------------------------
# Tab layout
# ---------------------------------------------------------------------------
tab_single, tab_batch = st.tabs(["📝 Single Review", "📊 Batch CSV Analysis"])

# ─── Single Review ──────────────────────────────────────────────────────────
with tab_single:
    st.subheader("Analyze a Single Review")
    review_text = st.text_area(
        "Paste a customer review here:",
        height=160,
        placeholder="e.g. The product arrived late and was damaged. Very disappointed.",
    )

    if st.button("🔍 Analyze Review", type="primary"):
        if not review_text.strip():
            st.warning("Please enter a review before clicking Analyze.")
        else:
            with st.spinner("Analyzing with Groq LLM…"):
                result, err = backend_post_json("/analyze", {"review_text": review_text})

            if err:
                st.error(f"Analysis failed: {err}")
                st.info(
                    "If the backend is sleeping (Render free tier), wait ~30 s and retry. "
                    "Verify your `LLM_API_KEY`, `LLM_BASE_URL`, and `LLM_MODEL` are set correctly."
                )
            else:
                a = result["analysis"]
                st.success("Analysis complete!")

                col1, col2, col3 = st.columns(3)
                col1.metric("Sentiment", f"{sentiment_color(a['sentiment'])} {a['sentiment']}")
                col2.metric("Urgency", f"{urgency_color(a['urgency'])} {a['urgency']}")
                col3.metric("Topic", a["topic"])

                st.markdown("**Explanation:**")
                st.info(a["explanation"])

                st.markdown("**Recommended Business Action:**")
                st.success(a["recommended_action"])

                st.markdown("**✏️ Draft Customer Reply** _(requires human approval before sending)_")
                st.warning(a["draft_reply"])

# ─── Batch CSV Analysis ─────────────────────────────────────────────────────
with tab_batch:
    st.subheader("Batch Review Analysis via CSV")
    st.markdown(
        "Upload a CSV with a column named **`review_text`**. "
        "Use `data/sample_reviews.csv` in the project for a quick demo."
    )

    uploaded = st.file_uploader("Choose a CSV file", type=["csv"])

    if uploaded:
        preview_df = pd.read_csv(uploaded)
        uploaded.seek(0)
        st.markdown(f"**Preview** ({len(preview_df)} rows):")
        st.dataframe(preview_df.head(5), use_container_width=True)

        if st.button("📊 Analyze All Reviews", type="primary"):
            with st.spinner(f"Analyzing {len(preview_df)} reviews… this may take a minute."):
                result, err = backend_post_file("/analyze-csv", uploaded.read(), uploaded.name)

            if err:
                st.error(f"Batch analysis failed: {err}")
            else:
                # ── Summary ──────────────────────────────────────────────
                st.success("Batch analysis complete!")
                st.markdown("### 📋 Overall Summary")
                st.info(result.get("summary", "No summary available."))

                col1, col2 = st.columns(2)

                # Sentiment chart
                with col1:
                    st.markdown("### Sentiment Distribution")
                    sd = result.get("sentiment_distribution", {})
                    if sd:
                        fig = px.pie(
                            names=list(sd.keys()),
                            values=list(sd.values()),
                            color=list(sd.keys()),
                            color_discrete_map={"Positive": "#22c55e", "Negative": "#ef4444", "Neutral": "#eab308"},
                        )
                        st.plotly_chart(fig, use_container_width=True)

                # Urgency chart
                with col2:
                    st.markdown("### Urgency Distribution")
                    ud = result.get("urgency_distribution", {})
                    if ud:
                        fig2 = px.bar(
                            x=list(ud.keys()),
                            y=list(ud.values()),
                            color=list(ud.keys()),
                            color_discrete_map={"Low": "#22c55e", "Medium": "#f97316", "High": "#ef4444"},
                            labels={"x": "Urgency", "y": "Count"},
                        )
                        st.plotly_chart(fig2, use_container_width=True)

                # Frequent issues
                fi = result.get("frequent_issues", [])
                if fi:
                    st.markdown("### 🔁 Most Frequent Issues")
                    for i, issue in enumerate(fi, 1):
                        st.markdown(f"**{i}.** {issue}")

                # Important negative feedback
                neg = result.get("important_negative_feedback", [])
                if neg:
                    st.markdown("### ⚠️ Key Negative Feedback")
                    for item in neg:
                        st.error(item)

                # Recommended actions
                actions = result.get("recommended_actions", [])
                if actions:
                    st.markdown("### ✅ Recommended Actions")
                    unique_actions = list(dict.fromkeys(actions))
                    for action in unique_actions[:5]:
                        st.success(action)

                # Results table
                st.markdown("### 📄 Individual Review Analyses")
                rows = []
                for i, a in enumerate(result["analyses"]):
                    rows.append({
                        "Review #": i + 1,
                        "Sentiment": a["sentiment"],
                        "Urgency": a["urgency"],
                        "Topic": a["topic"],
                        "Explanation": a["explanation"],
                        "Recommended Action": a["recommended_action"],
                    })
                df_results = pd.DataFrame(rows)
                st.dataframe(df_results, use_container_width=True)

                # Draft replies
                drafts = result.get("draft_replies", [])
                if drafts:
                    st.markdown("### ✏️ Draft Customer Replies _(all require human approval before sending)_")
                    for i, dr in enumerate(drafts, 1):
                        with st.expander(f"Draft reply for Review #{i}"):
                            st.warning(dr)

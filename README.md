<p align="center">
  <h1 align="center">InsightScrape</h1>
  <p align="center">
    AI-powered website audit tool that extracts real page metrics and delivers data-grounded SEO, content, and UX insights.
    <br />
    <strong>Single-request AI pipeline · Rich media detection · Full transparency</strong>
  </p>
</p>

---

## Table of Contents

- [Overview](#overview)
- [Features](#features)
- [Architecture](#architecture)
- [AI Design Decisions](#ai-design-decisions)
- [Trade-offs](#trade-offs)
- [What I'd Improve With More Time](#what-id-improve-with-more-time)
- [Getting Started](#getting-started)
  - [Prerequisites](#prerequisites)
  - [Backend Setup](#backend-setup)
  - [Frontend Setup](#frontend-setup)
- [Running Tests](#running-tests)
- [Deployment Guide](#deployment-guide)
  - [Backend on Render](#backend-on-render)
  - [Frontend on Vercel](#frontend-on-vercel)
  - [Securing the Gemini API Key](#securing-the-gemini-api-key)
- [Project Structure](#project-structure)
- [License](#license)

---

## Overview

InsightScrape is a lightweight, AI-native website audit tool. Enter any URL and get:

- **Deterministic metrics** — word count, headings, CTAs, images, links, rich media — scraped from live HTML  
- **AI-powered analysis** — 5-category scoring (Structure, Messaging, CTAs, Depth, UX) grounded in the extracted data  
- **Actionable recommendations** — 3–5 prioritized fixes with specific metrics, actions, and expected impact  
- **Full transparency** — every prompt and raw AI response is visible in an expandable trace panel  

The entire audit — analysis and recommendations — runs in **a single AI request**, minimizing API usage while maximizing context coherence.

## Features

| Feature | Description |
|---|---|
| **Single-Pass AI Audit** | Analysis + recommendations in one Gemini API call using a combined structured schema |
| **Dual Scraping** | Playwright (JS rendering) with HTTPX fallback for maximum site compatibility |
| **Rich Media Detection** | SVGs, `<video>`, YouTube/Vimeo embeds, `<canvas>`, CSS animations, Lottie, WebGL/3D |
| **Technical SEO Signals** | Viewport meta, canonical, Open Graph, Twitter Card, JSON-LD structured data |
| **Model Selection** | Choose between 4 Gemini models (Flash-Lite → Flash) via the UI |
| **Graceful Degradation** | If the AI fails, you still get all scraped metrics |
| **AI Transparency** | Expandable prompt logs show exact system/user prompts and raw responses |
| **Deterministic Scoring** | Overall score computed server-side as a weighted average, not by the AI |
| **SSRF Protection** | Backend rejects localhost, 127.0.0.1, and private-range URLs |
| **Dark Mode** | Toggle with `localStorage` persistence |

---

## Architecture

```
┌──────────────────────┐     POST /audit      ┌───────────────────────────────┐
│                      │ ──────────────────►   │         FastAPI Backend       │
│   React + Vite +     │                       │                               │
│   Tailwind CSS       │   ◄────────────────   │  ┌─────────┐  ┌───────────┐  │
│                      │     AuditResult JSON   │  │ Scraper │  │ AI Service│  │
│   (Vercel)           │                       │  │ Playwright│  │  Gemini   │  │
└──────────────────────┘                       │  │ + HTTPX  │  │  API (1x) │  │
                                               │  └─────────┘  └───────────┘  │
                                               │        (Render)               │
                                               └───────────────────────────────┘
```

**Request flow:**

1. **Fetch** — Playwright renders the page (full JS execution). Falls back to HTTPX if Playwright fails.
2. **Extract** — BeautifulSoup parses the HTML: headings, CTAs, images, alt text, links, meta tags, rich media (SVG/video/canvas/animations/3D), structured data, technical SEO signals.
3. **Analyze** — A single Gemini API call receives all metrics + up to 30K chars of visible text → returns structured analysis (5 categories × score + findings + evidence) AND 3–5 prioritized recommendations in one response.
4. **Score** — The overall score is recomputed server-side as a deterministic weighted average (`structure×0.25 + messaging×0.20 + cTA×0.20 + depth×0.20 + UX×0.15`).
5. **Respond** — Results, metrics, and full prompt traces are returned to the frontend.

### Why a Single AI Request?

Previously, the tool made 2 sequential API calls (analysis → recommendations). Since Gemini models support large context windows (1M+ tokens), both tasks fit comfortably in a single request using a combined `FullAuditResponse` Pydantic schema. This:

- **Halves the API request count** — critical when the free tier allows only 20 RPD
- **Improves recommendation coherence** — the model generates recommendations in the same context as its analysis, so they reference the *exact* findings it just produced
- **Reduces latency** — one round-trip instead of two

The prompt uses XML-style tags (`<role>`, `<constraints>`, `<context>`, `<task>`) following Gemini's prompting best practices, and all prompts/responses are captured by a `PromptTracer` for full auditability.

---

## AI Design Decisions

1. **Dual Scraping Strategy** — Playwright (headless Chromium) renders JavaScript-heavy pages and bypasses bot protection. HTTPX serves as a fast fallback. This ensures real-world agency sites are auditable.

2. **Content Quality Awareness** — When thin content is detected (low word count, no visual media), the system injects a `<data_quality_note>` into the prompt, instructing the AI to score conservatively rather than hallucinate quality. Rich-media-aware: pages using SVGs, video, canvas, Lottie, or WebGL/3D are not falsely flagged.

3. **Deterministic Grounding** — The AI is explicitly prompted to anchor every claim to a factual metric (e.g., *"4 out of 5 images (80%) lack alt text"*). We never ask it to guess counts.

4. **Structured Output via Pydantic** — We use `response_schema=FullAuditResponse` with `Field(description=...)` annotations. Gemini returns valid JSON matching the schema — zero regex parsing.

5. **AI Transparency Layer** — The frontend shows expandable prompt logs (system prompt, user prompt, raw JSON response, token usage) so users can verify exactly how the AI reached its conclusions.

6. **Deterministic Overall Score** — Computed as a weighted average server-side, never by the AI. This ensures auditability and cross-run consistency.

7. **Rich Visual Media Detection** — Sites increasingly use SVGs, CSS animations, Lottie, `<canvas>`, and WebGL/3D instead of traditional `<img>` tags. The scraper detects all of these *before* DOM cleanup, so nothing is missed.

8. **Technical SEO Extraction** — Viewport meta, canonical URLs, robots directives, Open Graph, Twitter Cards, and JSON-LD structured data are all extracted and fed into the AI prompt.

9. **Expert Prompt Engineering** — The prompt uses agency context (*"evaluating as a digital agency like EIGHT25MEDIA"*), a scored rubric (1-2 through 9-10), per-category evaluation instructions, E-E-A-T signals, and meta-length analysis against ideal character ranges.

10. **Graceful AI Failure** — If the AI returns an error (rate limit, timeout), the tool still returns all scraped metrics. Users get partial but useful results instead of a blank error page.

---

## Trade-offs

| Decision | Trade-off |
|---|---|
| **Playwright** | Adds ~50 MB to install size, but is essential for JS-rendered sites. HTTPX is kept as a fast fallback. |
| **Single AI Request** | One large structured response vs. two focused calls. Slightly larger output schema, but halves API usage and improves recommendation coherence. |
| **CTA Heuristics** | Keyword matching + CSS class detection (`.btn`, `.cta`) + nav-aware filtering. Subjective by nature — a production system would use an ML classifier. |
| **No Database** | Prompt logs and audit history are ephemeral (generated per request). Reduces deployment complexity but loses historical comparison. |
| **Free-Tier AI Models** | Limited to 20 RPD on most Gemini models. Single-request architecture mitigates this. |

---

## What I'd Improve With More Time

- **Multi-Page Crawling** — Crawl full sitemaps with Celery/Redis workers instead of single-page analysis.
- **Lighthouse Integration** — Blend AI insights with deterministic Core Web Vitals (LCP, CLS, INP) data.
- **Audit History & Diffing** — Store previous runs in Postgres and ask the AI to compare versions.
- **Response Caching** — Cache scrape+AI results by URL hash with a configurable TTL.
- **CTA ML Classifier** — Replace heuristics with a fine-tuned model for more accurate CTA detection.
- **Streaming AI Response** — Use Gemini's streaming API to show results progressively as they're generated.
- **Competitor Benchmarking** — Audit multiple URLs and generate a comparative scorecard.

---

## Getting Started

### Prerequisites

- **Python 3.11+**
- **Node.js 18+** and npm
- **Gemini API Key** — Free from [Google AI Studio](https://aistudio.google.com/apikey)

### Backend Setup

```bash
cd backend
python -m venv venv

# Activate virtual environment
source venv/bin/activate        # macOS/Linux
venv\Scripts\activate           # Windows

pip install -r requirements.txt
playwright install chromium     # Downloads headless Chromium (~50 MB)

# Configure API key
cp .env.example .env
# Edit .env and set: GEMINI_API_KEY=your_key_here

# Start the server
python main.py                  # Runs on http://localhost:8000
```

### Frontend Setup

```bash
cd frontend
npm install
npm run dev                     # Runs on http://localhost:5173
```

Open `http://localhost:5173` in your browser. Make sure the backend is running.

---

## Running Tests

### Backend (100+ tests)

```bash
cd backend
python -m pytest tests/ -v
```

Tests cover:
- **Scraper** — CTA detection, metrics extraction, edge cases, binary content detection
- **Rich Media** — SVG counting, video/canvas/Lottie/WebGL detection, CSS animations
- **Technical SEO** — Viewport, canonical, OG, Twitter Card, JSON-LD, meta lengths
- **Models** — Pydantic validation, score ranges, serialization roundtrips, `FullAuditResponse`
- **AI Service** — Weighted score computation, prompt construction, content truncation
- **API Routes** — Health endpoint, input validation, SSRF protection

### Frontend (15 tests)

```bash
cd frontend
npm test
```

Tests cover:
- **API Module** — Request construction, error handling, health check
- **AuditApp** — Rendering, dark mode toggle + persistence, form validation

---

## Deployment Guide

### Backend on Render

1. **Create a new Web Service** on [render.com](https://render.com) linked to this repo.

2. **Configure build settings:**
   - **Root Directory:** `backend`
   - **Build Command:**
     ```bash
     pip install -r requirements.txt && playwright install chromium && playwright install-deps
     ```
   - **Start Command:**
     ```bash
     uvicorn main:app --host 0.0.0.0 --port $PORT
     ```

3. **Set environment variables** in the Render dashboard (Settings → Environment):
   - `GEMINI_API_KEY` = your API key (set as **secret** — Render encrypts it at rest)

4. The `.env` file is `.gitignore`'d and never committed. Render injects the environment variable at runtime.

### Frontend on Vercel

1. **Import the repo** on [vercel.com](https://vercel.com).

2. **Configure:**
   - **Root Directory:** `frontend`
   - **Build Command:** `npm run build`
   - **Output Directory:** `dist`

3. **Set the API URL** — update the `API_BASE` in `frontend/src/api/audit.ts` to point to your Render backend URL (e.g., `https://insightscrape-api.onrender.com`).

4. For production, restrict CORS in `backend/main.py`:
   ```python
   allow_origins=["https://your-app.vercel.app"]
   ```

### Securing the Gemini API Key

> **The API key must NEVER be exposed to the frontend or committed to Git.**

The architecture ensures this by design:

1. **Backend-only access** — The Gemini API key is only used in `backend/services/ai_service.py`. The frontend never sees or sends it — it only talks to your backend API.

2. **Environment variables** — The key is loaded via `python-dotenv` from a `.env` file (local) or platform environment variables (production). The `.env` file is in `.gitignore`.

3. **Platform secrets** — On Render/Railway/Fly.io, set `GEMINI_API_KEY` as an encrypted environment variable in the dashboard. It is injected at runtime and never stored in the codebase.

4. **No client exposure** — The frontend calls `/audit` on your backend. The backend calls Gemini. The API key never travels to the browser.

```
Browser → Your Backend (has GEMINI_API_KEY) → Gemini API
                ↑ key stays here
```

**Checklist:**
- [ ] `.env` is in `.gitignore` (already configured)
- [ ] API key set via platform dashboard, not in code
- [ ] CORS restricted to your frontend domain in production
- [ ] No API key in frontend code or build artifacts

---

## Project Structure

```
InsightScrape/
├── backend/
│   ├── main.py                    # FastAPI app entry point
│   ├── requirements.txt           # Python dependencies
│   ├── .env.example               # Template for environment variables
│   ├── models.py                  # Pydantic schemas (PageMetrics, SEOAnalysis, FullAuditResponse, etc.)
│   ├── routes/
│   │   └── audit.py               # POST /audit endpoint with input validation
│   ├── services/
│   │   ├── ai_service.py          # Single-pass Gemini AI audit (analysis + recommendations)
│   │   ├── audit_orchestrator.py  # Orchestrates scrape → AI → response
│   │   ├── prompt_tracer.py       # Captures all prompts and responses for transparency
│   │   └── scraper.py             # Playwright/HTTPX scraping + metrics extraction
│   └── tests/
│       ├── test_ai_service.py     # AI prompt construction and score tests
│       ├── test_api.py            # API route and SSRF tests
│       ├── test_models.py         # Pydantic model validation tests
│       └── test_scraper.py        # Scraper, rich media, and technical SEO tests
├── frontend/
│   ├── src/
│   │   ├── api/audit.ts           # API client and TypeScript types
│   │   ├── components/
│   │   │   └── AuditApp.tsx       # Main React component
│   │   └── test/                  # Vitest test files
│   ├── package.json
│   └── vite.config.ts
├── .gitignore
└── README.md
```

---

## License

This project was built as a 24-hour engineering assignment for [EIGHT25MEDIA](https://eight25media.com).
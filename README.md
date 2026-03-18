# InsightScrape — AI-Powered Website Audit Tool

A lightweight, AI-native website audit tool that extracts factual metrics from a given URL and uses a multi-stage AI reasoning pipeline to provide actionable, data-grounded insights. Built for EIGHT25MEDIA's 24-hour engineering assignment.

## Architecture Overview

InsightScrape employs a decoupled, AI-native architecture:
- **Frontend**: React + Vite + Tailwind CSS (Deployable to Vercel)
- **Backend API**: Python + FastAPI (Deployable to Render)
- **AI Engine**: Google Gemini 2.0 Flash (via `google-genai` SDK)
- **Data Extractor**: HTTPX + BeautifulSoup4

### The Two-Stage AI Reasoning Pipeline
Instead of a monolithic single prompt, this tool uses pipeline orchestration:
1. **Stage 1 (Analysis)**: The AI receives strictly deterministic scraped metrics (word count, CTA count, link counts, proper Heading Hierarchy tuples `[(H1, Title)]`) + ~50k characters of cleaned page text. It evaluates the page across 5 categories (Structure, Messaging, CTAs, Depth, UX) returning a structured Pydantic Schema.
2. **Stage 2 (Recommendations)**: We pass the *raw metrics* and the *Stage 1 Analysis* back to the AI. This forces recommendations to be grounded in data ("H3 found before H2" rather than "Fix your headers") and ranked by priority.

Both stages are wrapped in a custom `PromptTracer` that captures every prompt (system and user) and raw JSON response.

## AI Design Decisions

1. **Leveraging the 1M Token Context Window**: Instead of aggressively truncating to 8K characters, we send up to 50K characters of cleaned body text to Gemini. This allows the AI to perform "Document-level reasoning".
2. **Deterministic Grounding**: The AI is explicitly prompted to anchor its insights to the factual numbers (e.g. `images_missing_alt_pct`). We don't ask it to guess counts.
3. **Structured Outputs**: We utilize strict Pydantic JSON schemas. There is zero unreliable text-parsing regex.
4. **Transparency Layer**: The frontend features a "Transparency Panel" (AI Reasoning Trace) that surfaces the internal state of the `PromptTracer`. We show exactly what was sent and received.

## Trade-offs Made
1. **Static vs Dynamic Scraping**: We used `HTTPX` over a headless browser like Playwright to maximize speed within a 24-hour build window. Consequently, heavily JS-rendered text might be missed, but we explicitly added modern component checks (`role="button"`) to compensate.
2. **CTA Heuristics**: The definition of a "CTA" is subjective. We rely on CSS class heuristics (`.btn`, `.cta`) and keywords ("Get Started"). A production system would fine-tune an ML classifier for this.
3. **No Database Integration**: To remove deployment complexity, prompt logs and history are not saved to Postgres. They are generated on the fly and visible in the UI.

## What I'd Improve With More Time
- **Async Site Crawling**: Moving from a single-page analysis to a full sitemap crawl using Celery/Redis workers.
- **Lighthouse API Integration**: Blending our AI insights with deterministic Google Core Web Vitals data.
- **Diff Tracking**: Saving previous audit runs and asking the AI to compare the current site version against the previous version.
- **Caching**: Currently each request triggers a full scrape and LLM cycle. I'd add a caching layer based on URL hashes.

## Setup Instructions

### Backend (Python)
1. `cd backend`
2. `python -m venv venv`
3. Activate: `source venv/bin/activate` or `venv\Scripts\activate` (Windows)
4. `pip install -r requirements.txt`
5. Get a free API key from Google AI Studio and copy `.env.example` to `.env`. Set `GEMINI_API_KEY=your_key_here`.
6. Run server: `python main.py` or `uvicorn main:app --reload` (Runs on port 8000)

### Frontend (React)
1. `cd frontend`
2. `npm install`
3. `npm run dev`
4. The React app is available on `http://localhost:5173`. Make sure the backend is running!
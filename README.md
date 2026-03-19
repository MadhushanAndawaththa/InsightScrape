# InsightScrape — AI-Powered Website Audit Tool

A lightweight, AI-native website audit tool that extracts factual metrics from a given URL and uses a multi-stage AI reasoning pipeline to provide actionable, data-grounded insights. Built for EIGHT25MEDIA's 24-hour engineering assignment.

## Architecture Overview

InsightScrape employs a decoupled, AI-native architecture:
- **Frontend**: React + Vite + Tailwind CSS (Deployable to Vercel)
- **Backend API**: Python + FastAPI (Deployable to Render)
- **AI Engine**: Google Gemini (4 selectable models: 2.5 Flash-Lite, 2.5 Flash, 3 Flash, 3.1 Flash-Lite) via `google-genai` SDK
- **Data Extractor**: Playwright (primary, JS rendering) + HTTPX (fallback) + BeautifulSoup4

### The Two-Stage AI Reasoning Pipeline
Instead of a monolithic single prompt, this tool uses pipeline orchestration:
1. **Stage 1 (Analysis)**: The AI receives strictly deterministic scraped metrics (word count, CTA count, link counts, heading hierarchy, **rich visual media signals**, **technical SEO signals**, **meta tag lengths**) + up to 30K characters of cleaned page text. It evaluates the page across 5 categories (Structure, Messaging, CTAs, Depth, UX) using a detailed scoring rubric, returning a structured Pydantic Schema. The overall score is computed server-side as a deterministic weighted average for consistency.
2. **Stage 2 (Recommendations)**: We pass the *raw metrics* and the *Stage 1 Analysis* back to the AI. This forces recommendations to be grounded in data ("H3 found before H2" rather than "Fix your headers") and ranked by priority. Recommendations include `grounded_metric`, `action`, and `expected_impact` fields for agency-ready output.

Both stages use XML-style prompt tags (`<role>`, `<constraints>`, `<context>`, `<task>`) following Gemini's official prompting best practices, and are wrapped in a custom `PromptTracer` that captures every prompt and raw JSON response.

## AI Design Decisions

1. **Dual Scraping Strategy**: Playwright (headless Chromium) renders JavaScript-heavy pages and bypasses bot protection (Cloudflare/WAF). HTTPX serves as a fast fallback for simple pages. This ensures we can audit real-world agency sites.
2. **Content Quality Awareness**: When the scraper detects thin content (low word count, zero images), the system injects a `<data_quality_note>` into the prompt, instructing the AI to score conservatively rather than hallucinate quality. The system is **rich-media-aware** — pages using SVGs, video, canvas, Lottie, or WebGL/3D instead of traditional `<img>` tags are not penalized.
3. **Deterministic Grounding**: The AI is explicitly prompted to anchor its insights to factual numbers (e.g., `images_missing_alt_pct`). We don't ask it to guess counts.
4. **Structured Outputs**: We utilize strict Pydantic JSON schemas with `Field(description=...)` annotations that guide the model's structured output generation. Zero unreliable text-parsing regex.
5. **Transparency Layer**: The frontend features a "Transparency Panel" (AI Reasoning Trace) with **expandable prompt logs** — prompts show a preview with a click-to-expand toggle, so users can inspect the full prompt text without UI clutter.
6. **Deterministic Overall Score**: The overall score is computed as a weighted average (`structure*0.25 + messaging*0.20 + cta*0.20 + depth*0.20 + ux*0.15`) rather than letting the AI pick arbitrarily, ensuring consistency and auditability.
7. **Rich Visual Media Detection**: The scraper detects modern visual techniques beyond `<img>` tags: inline SVGs (counted before DOM cleanup), `<video>` elements, YouTube/Vimeo/Wistia/Vidyard embeds, `<canvas>`, CSS animations (`@keyframes`, transitions), Lottie animations, and WebGL/3D frameworks (Three.js, Babylon.js, A-Frame, Spline, model-viewer).
8. **Technical SEO Signals**: The scraper extracts viewport meta, canonical URLs, robots directives, Open Graph tags, Twitter Cards, and JSON-LD structured data types — all fed into the AI prompt for comprehensive evaluation.
9. **Expert-Level Prompt Engineering**: Prompts use agency context ("evaluating as a digital agency like EIGHT25MEDIA"), a detailed scoring rubric (1-2 through 9-10 ranges), per-category evaluation instructions, E-E-A-T content depth signals, and meta tag length analysis against ideal character ranges.
10. **Graceful AI Failure**: If the AI service returns an error (rate limit, timeout), the tool still returns all scraped metrics with a clear error message rather than failing entirely. Users get partial but useful results.
11. **Model Selection**: Users can choose between 4 Gemini models via a dropdown, allowing flexibility between speed (Flash-Lite) and depth (Flash).

## Trade-offs Made
1. **Playwright over Pure HTTPX**: We added Playwright for JS rendering, which adds ~50MB to the install size but is essential for auditing modern websites. HTTPX is kept as a fast fallback.
2. **CTA Heuristics**: The definition of a "CTA" is subjective. We use keyword matching, CSS class heuristics (`.btn`, `.cta`), and navigation-aware filtering (links inside `<nav>` aren't counted as CTAs). A production system would fine-tune an ML classifier.
3. **No Database Integration**: To minimize deployment complexity, prompt logs and history are not saved to Postgres. They are generated on the fly and visible in the UI.

## What I'd Improve With More Time
- **Async Site Crawling**: Moving from a single-page analysis to a full sitemap crawl using Celery/Redis workers.
- **Lighthouse API Integration**: Blending our AI insights with deterministic Google Core Web Vitals data.
- **Diff Tracking**: Saving previous audit runs and asking the AI to compare the current site version against the previous version.
- **Caching**: Currently each request triggers a full scrape and LLM cycle. I'd add a caching layer based on URL hashes.
- **CTA ML Classifier**: Replacing keyword/class heuristics with a fine-tuned model for more accurate CTA detection.

## Setup Instructions

### Backend (Python)
1. `cd backend`
2. `python -m venv venv`
3. Activate: `source venv/bin/activate` or `venv\Scripts\activate` (Windows)
4. `pip install -r requirements.txt`
5. `playwright install chromium` (downloads the Chromium browser for JS rendering)
6. Get a free API key from Google AI Studio and copy `.env.example` to `.env`. Set `GEMINI_API_KEY=your_key_here`.
7. Run server: `python main.py` or `uvicorn main:app --reload` (Runs on port 8000)

### Frontend (React)
1. `cd frontend`
2. `npm install`
3. `npm run dev`
4. The React app is available on `http://localhost:5173`. Make sure the backend is running!

### Running Tests

#### Backend (100+ tests)
```bash
cd backend
./venv/Scripts/python.exe -m pytest tests/ -v   # Windows
# or: python -m pytest tests/ -v                # Mac/Linux
```

Tests cover:
- **Scraper**: CTA detection (keyword, class, role, nav filtering), metrics extraction (headings, images, links, meta), binary content detection, edge cases
- **Rich Media Detection**: SVG counting (before DOM cleanup), video tags, YouTube/Vimeo iframes, canvas elements, CSS animations (@keyframes, transitions), Lottie detection, Three.js/WebGL detection, plain page baseline
- **Technical SEO Detection**: Viewport meta, canonical URLs, Open Graph tags, Twitter Cards, JSON-LD structured data (single & multiple types), meta title/description length tracking, content quality warning suppression for rich-media pages
- **Models**: Pydantic validation (score ranges, required fields, serialization roundtrip), rich media field defaults and set values
- **AI Service**: Weighted score computation, prompt construction logic, content truncation
- **API Routes**: Health endpoint, input validation, SSRF protection (localhost/127.0.0.1 blocked)

#### Frontend (15 tests)
```bash
cd frontend
npm test
```

Tests cover:
- **API Module**: Request construction, error handling, health check
- **AuditApp Component**: Rendering, dark mode toggle + persistence, form validation
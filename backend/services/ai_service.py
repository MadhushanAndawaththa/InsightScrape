import os
import json
import time
import asyncio
from typing import List
from google import genai
from google.genai import types
from google.api_core.exceptions import ResourceExhausted, ServiceUnavailable
from models import PageMetrics, SEOAnalysis, Recommendation
from services.prompt_tracer import PromptTracer

# gemini-2.0-flash-lite: higher free-tier RPM (30 vs 15) and lower token cost
# Testing: gemini-2.5-flash-lite (highest free-tier RPD, ~1500/day)
# Production: gemini-2.5-flash (best price-performance, superior reasoning)
MODEL = "gemini-2.5-flash-lite"

# Maximum chars of visible page text sent to the model (~3 000 tokens)
_MAX_PAGE_CHARS = 12_000

_client = None

def get_client() -> genai.Client:
    global _client
    if _client is None:
        api_key = os.environ.get("GEMINI_API_KEY")
        if not api_key:
            raise ValueError("GEMINI_API_KEY environment variable is not set. Copy .env.example to .env and add your key.")
        _client = genai.Client(api_key=api_key)
    return _client


def _generate_with_retry(model: str, contents: str, config: types.GenerateContentConfig, max_retries: int = 3):
    """Call generate_content with exponential backoff on 429 / 503 errors."""
    delay = 15  # seconds — start conservative for free-tier quota windows
    for attempt in range(max_retries):
        try:
            return get_client().models.generate_content(
                model=model,
                contents=contents,
                config=config,
            )
        except (ResourceExhausted, ServiceUnavailable) as exc:
            if attempt == max_retries - 1:
                raise
            print(f"[ai_service] 429/503 on attempt {attempt + 1}, retrying in {delay}s… ({exc})")
            time.sleep(delay)
            delay *= 2  # exponential backoff
        except Exception:
            raise


async def analyze_page(metrics: PageMetrics, page_content: str, tracer: PromptTracer) -> SEOAnalysis:
    """Stage 1 — Structured analysis of the scraped page.
    
    Prompt engineering follows Gemini best practices:
    - XML-style tags to separate role, context, constraints, and task
    - Metrics-first layout: facts before content so the model anchors on data
    - Truncated page content to minimize token burn while preserving analysis quality
    - Low temperature (0.2) for deterministic, fact-grounded scoring
    """

    system_prompt = """<role>
You are a senior web strategist at a digital agency specializing in SEO, conversion optimization, and UX.
You are precise, analytical, and data-driven.
</role>

<constraints>
1. Analyze ONLY using the provided metrics and content — do not use external knowledge.
2. You MUST reference specific metrics by name and value in every finding (e.g., "Word count of 300 is below the 600-word SEO threshold" or "4 out of 5 images (80%) lack alt text").
3. Specifically check for Heading Hierarchy Violations: H3 before any H2, missing H1, level skips (H1 → H3).
4. Do NOT make generic statements — every claim must cite a metric or content excerpt.
5. Scores must be integers from 1 to 10.
</constraints>

<output_format>
Return a single JSON object matching the provided schema with scores, findings, and evidence for each category.
</output_format>"""

    # Truncate page content before building the prompt to cap token usage
    trimmed = page_content[:_MAX_PAGE_CHARS]
    if len(page_content) > _MAX_PAGE_CHARS:
        trimmed += "\n\n...[content truncated]"

    user_prompt = f"""<context>
## Extracted Page Metrics (Deterministic — scraped from HTML)
- Word Count: {metrics.word_count}
- CTA Count: {metrics.cta_count}
- Internal Links: {metrics.internal_links}
- External Links: {metrics.external_links}
- Total Images: {metrics.image_count}
- Images Missing Alt Text: {metrics.images_missing_alt_count} ({metrics.images_missing_alt_pct}%)
- Images with Decorative Alt (alt=""): {metrics.images_decorative_alt_count}
- Meta Title: {metrics.meta_title or 'MISSING'}
- Meta Description: {metrics.meta_description or 'MISSING'}
- Heading Counts: {json.dumps(metrics.headings_count)}

## Heading Hierarchy (order as found in HTML)
{json.dumps(metrics.heading_hierarchy)}

## Page Content (visible text excerpt)
{trimmed}
</context>

<task>
Analyze the page above across all five categories (structure, messaging, CTAs, content depth, UX).
For each category, provide a score (1-10), findings grounded in specific metrics, and direct evidence.
Return the result as structured JSON matching the schema.
</task>"""

    response = _generate_with_retry(
        model=MODEL,
        contents=user_prompt,
        config=types.GenerateContentConfig(
            system_instruction=system_prompt,
            response_mime_type="application/json",
            response_schema=SEOAnalysis,
            temperature=0.2,
        ),
    )

    raw_text = response.text
    try:
        parsed_out = json.loads(raw_text)
        analysis_result = SEOAnalysis(**parsed_out)
    except Exception as e:
        print(f"Error parsing JSON from raw LLM output: {e}\n{raw_text}")
        raise ValueError("Failed to parse stage 1 response")

    token_usage = {
        "prompt_token_count": response.usage_metadata.prompt_token_count,
        "candidates_token_count": response.usage_metadata.candidates_token_count,
        "total_token_count": response.usage_metadata.total_token_count,
    }

    tracer.add_stage("Stage 1 - Analysis", system_prompt, user_prompt, raw_text, parsed_out, token_usage)
    return analysis_result


async def recommend_actions(metrics: PageMetrics, analysis: SEOAnalysis, tracer: PromptTracer) -> List[Recommendation]:
    """Stage 2 — Generate prioritized recommendations from Stage 1 analysis.
    
    This is a chained prompt: Stage 1 output becomes Stage 2 input context.
    The prompt is concise because it only references structured data (no raw HTML).
    """

    system_prompt = """<role>
You are a senior web consultant who provides actionable, prioritized website improvement recommendations.
</role>

<constraints>
1. Generate exactly 3 to 5 recommendations, no more, no fewer.
2. Every recommendation MUST be directly grounded in a specific metric or analysis finding — never generic advice.
3. Prioritize by impact: priority 1 = highest impact, must-fix; priority 3 = nice-to-have improvement.
4. The "grounded_metric" field must cite the exact data point (e.g., "4 images missing alt text" or "Structure score: 3/10").
5. The "action" field must be a specific, implementable step (not vague like "improve SEO").
6. The "expected_impact" field must describe the concrete outcome of the action.
</constraints>

<output_format>
Return a JSON array of 3-5 recommendation objects matching the provided schema.
</output_format>"""

    user_prompt = f"""<context>
## Raw Metrics (factual)
- Word Count: {metrics.word_count}
- Images Missing Alt Text: {metrics.images_missing_alt_count} ({metrics.images_missing_alt_pct}%)
- Meta Title: {metrics.meta_title or 'MISSING'}
- Meta Description: {metrics.meta_description or 'MISSING'}
- Headings: {json.dumps(metrics.headings_count)}
- CTAs Found: {metrics.cta_count}
- Internal Links: {metrics.internal_links} | External Links: {metrics.external_links}

## AI Analysis Scores (from Stage 1)
- Overall: {analysis.overall_score}/10
- Structure & SEO: {analysis.structure_score}/10 — {analysis.structure_analysis.findings[:200]}
- Messaging: {analysis.messaging_score}/10 — {analysis.messaging_analysis.findings[:200]}
- CTAs: {analysis.cta_score}/10 — {analysis.cta_analysis.findings[:200]}
- Content Depth: {analysis.content_depth_score}/10 — {analysis.content_depth_analysis.findings[:200]}
- UX: {analysis.ux_score}/10 — {analysis.ux_analysis.findings[:200]}
</context>

<task>
Based on the metrics and analysis above, generate 3-5 prioritized recommendations.
Focus on the lowest-scoring categories first. Each recommendation must cite specific data.
</task>"""

    response = _generate_with_retry(
        model=MODEL,
        contents=user_prompt,
        config=types.GenerateContentConfig(
            system_instruction=system_prompt,
            response_mime_type="application/json",
            response_schema=list[Recommendation],
            temperature=0.2,
        ),
    )

    raw_text = response.text
    try:
        parsed_out = json.loads(raw_text)
        recommendations = [Recommendation(**rec) for rec in parsed_out]
    except Exception as e:
        print(f"Error parsing recommendations: {e}\n{raw_text}")
        raise ValueError("Failed to parse stage 2 response")

    token_usage = {
        "prompt_token_count": response.usage_metadata.prompt_token_count,
        "candidates_token_count": response.usage_metadata.candidates_token_count,
        "total_token_count": response.usage_metadata.total_token_count,
    }

    tracer.add_stage("Stage 2 - Recommendations", system_prompt, user_prompt, raw_text, parsed_out, token_usage)
    return recommendations

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

# Maximum chars of visible page text sent to the model (~7 500 tokens)
# Gemini 2.5 Flash-Lite supports 1M tokens in — 30K chars is comfortable
_MAX_PAGE_CHARS = 30_000

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


async def analyze_page(metrics: PageMetrics, page_content: str, tracer: PromptTracer, *, model: str = MODEL) -> SEOAnalysis:
    """Stage 1 — Structured analysis of the scraped page.
    
    Prompt engineering follows Gemini best practices:
    - XML-style tags to separate role, context, constraints, and task
    - Metrics-first layout: facts before content so the model anchors on data
    - Rich media awareness: sites can be visually rich via SVGs, video, animations, 3D
    - Technical SEO signals: viewport, canonical, Open Graph, structured data
    - Low temperature (0.2) for deterministic, fact-grounded scoring
    """

    system_prompt = """<role>
You are a senior web strategist at a digital agency (like EIGHT25MEDIA) specializing in SEO, conversion optimization, content strategy, and UX for marketing websites.
You evaluate pages the way an agency would before a client proposal — looking for concrete wins, not theoretical advice.
You are precise, analytical, and data-driven.
</role>

<constraints>
1. Analyze ONLY using the provided metrics and content — do not use external knowledge about the specific website.
2. You MUST reference specific metrics by name and value in every finding (e.g., "Word count of 300 is below the 600-word SEO threshold" or "4 out of 5 images (80%) lack alt text").
3. Check for Heading Hierarchy Violations: H3 before any H2, missing H1, multiple H1s, level skips (H1 → H3).
4. Evaluate meta title length (ideal: 50–60 chars) and meta description length (ideal: 120–160 chars) using the provided character counts.
5. Consider rich visual media holistically: a page may lack traditional <img> tags but use SVGs, CSS animations, video embeds, Lottie animations, canvas/WebGL, or 3D elements. Do NOT penalize visual quality if rich media alternatives are present.
6. Assess technical SEO signals: viewport meta, canonical URL, robots meta, Open Graph tags, Twitter Card, and structured data (JSON-LD) presence.
7. Evaluate CTA quality: are there enough CTAs for the page length? Are they above the fold? Is the language action-oriented?
8. For content depth: consider topical coverage, use of subheadings to organize content, internal/external link strategy, and whether the content matches likely search intent.
9. Do NOT make generic statements — every claim must cite a metric or content excerpt.
10. Scores must be integers from 1 to 10.
</constraints>

<scoring_rubric>
- 9-10: Exceptional — best practices exceeded, clear competitive advantage
- 7-8: Good — solid foundation with minor improvements possible
- 5-6: Average — functional but missing key optimizations that impact rankings/conversions
- 3-4: Below average — significant gaps that hurt performance
- 1-2: Critical — fundamental issues that need immediate attention
</scoring_rubric>

<output_format>
Return a single JSON object matching the provided schema with scores, findings, and evidence for each category.
</output_format>"""

    # Truncate page content before building the prompt to cap token usage
    trimmed = page_content[:_MAX_PAGE_CHARS]
    if len(page_content) > _MAX_PAGE_CHARS:
        trimmed += "\n\n...[content truncated]"

    # Data quality note for thin / JS-rendered pages — now considers rich media
    has_rich_media = metrics.has_video or metrics.has_canvas or metrics.svg_count > 0 or metrics.has_lottie or metrics.has_webgl_or_3d
    quality_note = ""
    if metrics.word_count < 300 and not has_rich_media:
        quality_note = """\n<data_quality_note>
WARNING: The extracted content appears thin (low word count and no rich visual media detected).
This often happens when the page relies heavily on JavaScript rendering.
Score CONSERVATIVELY — do not give high scores for categories that lack supporting evidence.
If content appears incomplete, note this limitation in your findings.
</data_quality_note>\n"""

    # Build rich media context string
    rich_media_parts = []
    if metrics.svg_count > 0:
        rich_media_parts.append(f"{metrics.svg_count} SVG elements")
    if metrics.has_video:
        rich_media_parts.append("Video embeds detected")
    if metrics.has_canvas:
        rich_media_parts.append("Canvas element detected")
    if metrics.has_css_animations:
        rich_media_parts.append("CSS animations/transitions detected")
    if metrics.has_lottie:
        rich_media_parts.append("Lottie animations detected")
    if metrics.has_webgl_or_3d:
        rich_media_parts.append("WebGL/3D elements detected")
    rich_media_summary = ", ".join(rich_media_parts) if rich_media_parts else "None detected"

    # Build structured data context
    structured_data_summary = ", ".join(metrics.structured_data_types) if metrics.structured_data_types else "None"

    user_prompt = f"""{quality_note}<context>
## Extracted Page Metrics (Deterministic — scraped from HTML)

### Content Metrics
- Word Count: {metrics.word_count}
- CTA Count: {metrics.cta_count}
- Internal Links: {metrics.internal_links}
- External Links: {metrics.external_links}

### Image & Visual Media
- Total Images (<img>): {metrics.image_count}
- Images Missing Alt Text: {metrics.images_missing_alt_count} ({metrics.images_missing_alt_pct}%)
- Images with Decorative Alt (alt=""): {metrics.images_decorative_alt_count}
- Rich Visual Media: {rich_media_summary}

### Technical SEO
- Meta Title: {metrics.meta_title or 'MISSING'} ({metrics.meta_title_length or 0} chars — ideal: 50-60)
- Meta Description: {metrics.meta_description or 'MISSING'} ({metrics.meta_description_length or 0} chars — ideal: 120-160)
- Viewport Meta: {'Present' if metrics.has_viewport_meta else 'MISSING'}
- Canonical URL: {'Present' if metrics.has_canonical else 'MISSING'}
- Robots Meta: {'Present' if metrics.has_robots_meta else 'Not set'}
- Open Graph Tags: {'Present' if metrics.has_open_graph else 'MISSING'}
- Twitter Card: {'Present' if metrics.has_twitter_card else 'MISSING'}
- Structured Data (JSON-LD): {structured_data_summary}

### Heading Structure
- Heading Counts: {json.dumps(metrics.headings_count)}

## Heading Hierarchy (order as found in HTML)
{json.dumps(metrics.heading_hierarchy)}

## Page Content (visible text excerpt)
{trimmed}
</context>

<task>
Analyze the page above across all five categories (structure, messaging, CTAs, content depth, UX).

For **Structure & SEO**: Evaluate heading hierarchy (H1 presence, proper nesting, no skips), meta tag quality (title/description length and relevance), technical SEO signals (viewport, canonical, OG tags, structured data), and overall HTML organization.

For **Messaging & Clarity**: Assess the value proposition clarity, brand voice consistency, whether the content answers the user's likely intent, and if key messages are prioritized above the fold.

For **CTAs**: Evaluate quantity relative to page length, action-oriented language quality, variety of CTAs (primary vs secondary), and strategic placement signals.

For **Content Depth**: Consider word count relative to topic complexity, use of subheadings for scannability, internal/external link strategy for topical authority, and whether the content demonstrates expertise (E-E-A-T signals).

For **UX**: Assess content readability structure (short paragraphs, logical flow), mobile-readiness signals (viewport meta), image optimization (alt text), rich media usage for engagement, and overall page organization.

For each category, provide a score (1-10), findings grounded in specific metrics, and direct evidence.
Return the result as structured JSON matching the schema.
</task>"""

    response = _generate_with_retry(
        model=model,
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

    # Override overall_score with a deterministic weighted average
    weighted = round(
        analysis_result.structure_score * 0.25
        + analysis_result.messaging_score * 0.20
        + analysis_result.cta_score * 0.20
        + analysis_result.content_depth_score * 0.20
        + analysis_result.ux_score * 0.15
    )
    analysis_result.overall_score = max(1, min(10, weighted))

    token_usage = {
        "prompt_token_count": response.usage_metadata.prompt_token_count,
        "candidates_token_count": response.usage_metadata.candidates_token_count,
        "total_token_count": response.usage_metadata.total_token_count,
    }

    tracer.add_stage("Stage 1 - Analysis", system_prompt, user_prompt, raw_text, parsed_out, token_usage, model=model)
    return analysis_result


async def recommend_actions(metrics: PageMetrics, analysis: SEOAnalysis, tracer: PromptTracer, *, model: str = MODEL) -> List[Recommendation]:
    """Stage 2 — Generate prioritized recommendations from Stage 1 analysis.
    
    This is a chained prompt: Stage 1 output becomes Stage 2 input context.
    The prompt is concise because it only references structured data (no raw HTML).
    """

    system_prompt = """<role>
You are a senior web consultant at a digital agency that builds high-performing marketing websites.
You provide actionable, prioritized website improvement recommendations that a development team can immediately implement.
Think like someone preparing a client proposal — every recommendation should justify its priority with data and have a clear ROI.
</role>

<constraints>
1. Generate exactly 3 to 5 recommendations, no more, no fewer.
2. Every recommendation MUST be directly grounded in a specific metric or analysis finding — never generic advice.
3. Prioritize by impact: priority 1 = highest impact, must-fix (e.g., missing H1, no meta description); priority 2 = significant improvement; priority 3 = nice-to-have optimization.
4. The "grounded_metric" field must cite the exact data point (e.g., "4 images missing alt text", "Meta title is 78 chars — exceeds 60-char ideal", "Structure score: 3/10").
5. The "action" field must be a specific, implementable step (not vague like "improve SEO"). Include concrete guidance (e.g., "Add H1 tag with primary keyword 'X' based on page content", "Add alt text to 4 images describing their visual content").
6. The "expected_impact" field must describe the concrete outcome (e.g., "Improves image search visibility and accessibility compliance", "Increases CTR in search results by 15-30%").
7. Consider the full picture: if images are missing but SVGs/video/animations are present, don't prioritize adding images — focus on what's actually broken.
</constraints>

<output_format>
Return a JSON array of 3-5 recommendation objects matching the provided schema.
</output_format>"""

    # Build rich media context
    rich_media_parts = []
    if metrics.svg_count > 0:
        rich_media_parts.append(f"{metrics.svg_count} SVGs")
    if metrics.has_video:
        rich_media_parts.append("Video")
    if metrics.has_canvas:
        rich_media_parts.append("Canvas")
    if metrics.has_css_animations:
        rich_media_parts.append("CSS animations")
    if metrics.has_lottie:
        rich_media_parts.append("Lottie")
    if metrics.has_webgl_or_3d:
        rich_media_parts.append("WebGL/3D")
    rich_media_str = ", ".join(rich_media_parts) if rich_media_parts else "None"

    user_prompt = f"""<context>
## Raw Metrics (factual)
- Word Count: {metrics.word_count}
- Images Missing Alt Text: {metrics.images_missing_alt_count} ({metrics.images_missing_alt_pct}%)
- Meta Title: {metrics.meta_title or 'MISSING'} ({metrics.meta_title_length or 0} chars)
- Meta Description: {metrics.meta_description or 'MISSING'} ({metrics.meta_description_length or 0} chars)
- Headings: {json.dumps(metrics.headings_count)}
- CTAs Found: {metrics.cta_count}
- Internal Links: {metrics.internal_links} | External Links: {metrics.external_links}
- Rich Visual Media: {rich_media_str}
- Viewport Meta: {'Yes' if metrics.has_viewport_meta else 'MISSING'}
- Canonical: {'Yes' if metrics.has_canonical else 'MISSING'}
- Open Graph: {'Yes' if metrics.has_open_graph else 'MISSING'}
- Structured Data: {', '.join(metrics.structured_data_types) if metrics.structured_data_types else 'None'}

## AI Analysis Scores (from Stage 1)
- Overall: {analysis.overall_score}/10
- Structure & SEO: {analysis.structure_score}/10 — {analysis.structure_analysis.findings[:300]}
- Messaging: {analysis.messaging_score}/10 — {analysis.messaging_analysis.findings[:300]}
- CTAs: {analysis.cta_score}/10 — {analysis.cta_analysis.findings[:300]}
- Content Depth: {analysis.content_depth_score}/10 — {analysis.content_depth_analysis.findings[:300]}
- UX: {analysis.ux_score}/10 — {analysis.ux_analysis.findings[:300]}
</context>

<task>
Based on the metrics and analysis above, generate 3-5 prioritized recommendations.
Focus on the lowest-scoring categories first. Each recommendation must cite specific data.
Recommendations should be the kind a web agency would include in a client audit report — actionable, specific, and tied to measurable outcomes.
</task>"""

    response = _generate_with_retry(
        model=model,
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

    tracer.add_stage("Stage 2 - Recommendations", system_prompt, user_prompt, raw_text, parsed_out, token_usage, model=model)
    return recommendations

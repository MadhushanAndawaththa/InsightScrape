import os
import json
import time
import asyncio
from typing import List, Tuple
from google import genai
from google.genai import types
from google.api_core.exceptions import ResourceExhausted, ServiceUnavailable
from models import PageMetrics, SEOAnalysis, Recommendation, FullAuditResponse
from services.prompt_tracer import PromptTracer

# Default model: gemini-2.5-flash-lite (20 RPD, 10 RPM on free tier)
# Available: gemini-2.5-flash (20 RPD), gemini-3.1-flash-lite-preview (500 RPD), gemini-3-flash-preview (20 RPD)
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


async def run_audit_analysis(metrics: PageMetrics, page_content: str, tracer: PromptTracer, *, model: str = MODEL) -> Tuple[SEOAnalysis, List[Recommendation]]:
    """Single-pass AI audit — analysis + recommendations in one Gemini call.

    Combines what was previously two sequential API calls into one, halving
    the request count while leveraging Gemini's large context window.
    The model performs the analysis first, then generates recommendations
    grounded in its own analysis — all within a single structured output.

    Prompt engineering follows Gemini best practices:
    - XML-style tags to separate role, context, constraints, and task
    - Metrics-first layout: facts before content so the model anchors on data
    - Rich media awareness: sites can be visually rich via SVGs, video, animations, 3D
    - Technical SEO signals: viewport, canonical, Open Graph, structured data
    - Combined scoring rubric + recommendation constraints in one system prompt
    - Low temperature (0.2) for deterministic, fact-grounded output
    """

    system_prompt = """<role>
You are a senior web strategist at a digital agency specializing in SEO, conversion optimization, content strategy, and UX for marketing websites.
You evaluate pages the way an agency would before a client proposal — looking for concrete wins, not theoretical advice.
You are precise, analytical, and data-driven.
</role>

<constraints>
## Analysis Constraints
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

## Recommendation Constraints
11. Generate 5 recommendations in the "recommendations" array. Only reduce to 4 if the page is near-perfect in one category, or 3 if the page excels in multiple areas. Default to 5.
12. Every recommendation MUST be directly grounded in your analysis findings — never generic advice.
13. Prioritize by impact: priority 1 = highest impact, must-fix; priority 2 = significant improvement; priority 3 = nice-to-have optimization.
14. The "grounded_metric" field must cite the exact data point (e.g., "4 images missing alt text", "Meta title is 78 chars — exceeds 60-char ideal").
15. The "action" field must be a specific, implementable step — not vague advice.
16. The "expected_impact" field must describe the concrete expected outcome.
17. Focus recommendations on the lowest-scoring categories first.

## Quality Guards
18. THINK BEFORE SCORING: For each category, first identify the relevant metrics, then compare against best practices, then assess real-world impact — only then assign a score. Never pick a score first and justify it after.
19. ANTI-HALLUCINATION: If the extracted metrics say a feature is MISSING (e.g., "Structured Data (JSON-LD): None" or "Canonical URL: MISSING"), treat it as definitively absent. Do not infer its presence from the page text.
20. NO DUPLICATE RECOMMENDATIONS: Each of the 5 recommendations must address a distinct issue. Do not suggest the same fix in different wording.
21. PROFESSIONAL TONE: Avoid vague marketing buzzwords ("leverage", "supercharge", "synergize"). Write like a senior consultant delivering a client audit report.
</constraints>

<scoring_rubric>
- 9-10: Exceptional — best practices exceeded, clear competitive advantage
- 7-8: Good — solid foundation with minor improvements possible
- 5-6: Average — functional but missing key optimizations that impact rankings/conversions
- 3-4: Below average — significant gaps that hurt performance
- 1-2: Critical — fundamental issues that need immediate attention
</scoring_rubric>

<output_format>
Return a single JSON object with:
1. Scores and detailed analysis for each of the 5 categories (structure, messaging, CTAs, content depth, UX)
2. A "recommendations" array with 5 prioritized, actionable recommendations grounded in your analysis (reduce to 4 or 3 only if the page truly excels)
All in one structured response matching the provided schema.
</output_format>

<examples>
## Good vs. Bad — calibrate your output quality

BAD finding (vague, no data):
"The content is too short and doesn't explain the product well."

GOOD finding (grounded, specific):
"Word count of 300 is below the 600-word threshold for competitive mid-funnel queries, and with no rich media alternatives (0 videos, 0 canvas elements), the page lacks depth to rank."

BAD recommendation (generic):
"Improve SEO by adding alt text to images."

GOOD recommendation (actionable, cited):
"Add descriptive alt text to the 4 images missing it (80% of total). Prioritize the hero banner and product thumbnails, as these appear in Google Image search results."
</examples>"""

    # Truncate page content before building the prompt to cap token usage
    trimmed = page_content[:_MAX_PAGE_CHARS]
    if len(page_content) > _MAX_PAGE_CHARS:
        trimmed += "\n\n...[content truncated]"

    # Data quality note for thin / JS-rendered pages — considers rich media
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
Perform a complete website audit in two parts:

**STEP 0 — Page Classification**: First, determine the primary purpose of this page from its content, CTAs, and structure (e.g., SaaS landing page, e-commerce product page, blog/article, documentation, portfolio, corporate homepage). Tailor your scoring expectations to that page type — a blog post needs fewer CTAs than a landing page, and a portfolio site may rely on visuals over word count.

**PART 1 — Analysis**: Evaluate the page across all five categories:

- **Structure & SEO**: Heading hierarchy (H1 presence, proper nesting, no skips), meta tag quality (title/description length and relevance), technical SEO signals (viewport, canonical, OG tags, structured data), and overall HTML organization.
- **Messaging & Clarity**: Value proposition clarity, brand voice consistency, whether the content answers the user's likely intent, and if key messages are prioritized above the fold.
- **CTAs**: Quantity relative to page length, action-oriented language quality, variety of CTAs (primary vs secondary), and strategic placement signals.
- **Content Depth**: Word count relative to topic complexity, use of subheadings for scannability, internal/external link strategy for topical authority, and whether the content demonstrates expertise (E-E-A-T signals).
- **UX**: Content readability structure (short paragraphs, logical flow), mobile-readiness signals (viewport meta), image optimization (alt text), rich media usage for engagement, and overall page organization.

For each category, provide a score (1-10), findings grounded in specific metrics, and direct evidence.

**PART 2 — Recommendations**: Based on your analysis above, generate 5 prioritized recommendations (reduce to 4 or 3 only if the page truly excels in most categories). Focus on the lowest-scoring categories first. Each recommendation must cite specific data and be the kind a web agency would include in a client audit report.

Return everything as a single structured JSON object matching the schema.
</task>"""

    response = _generate_with_retry(
        model=model,
        contents=user_prompt,
        config=types.GenerateContentConfig(
            system_instruction=system_prompt,
            response_mime_type="application/json",
            response_schema=FullAuditResponse,
            temperature=0.2,
        ),
    )

    raw_text = response.text
    try:
        parsed_out = json.loads(raw_text)
        full_response = FullAuditResponse(**parsed_out)
    except Exception as e:
        print(f"Error parsing JSON from raw LLM output: {e}\n{raw_text}")
        raise ValueError("Failed to parse audit response")

    # Override overall_score with a deterministic weighted average
    weighted = round(
        full_response.structure_score * 0.25
        + full_response.messaging_score * 0.20
        + full_response.cta_score * 0.20
        + full_response.content_depth_score * 0.20
        + full_response.ux_score * 0.15
    )
    full_response.overall_score = max(1, min(10, weighted))

    token_usage = {
        "prompt_token_count": response.usage_metadata.prompt_token_count,
        "candidates_token_count": response.usage_metadata.candidates_token_count,
        "total_token_count": response.usage_metadata.total_token_count,
    }

    tracer.add_stage("Full Audit — Analysis + Recommendations", system_prompt, user_prompt, raw_text, parsed_out, token_usage, model=model)

    # Split into SEOAnalysis + Recommendations for backward compatibility
    analysis = SEOAnalysis(
        structure_score=full_response.structure_score,
        messaging_score=full_response.messaging_score,
        cta_score=full_response.cta_score,
        content_depth_score=full_response.content_depth_score,
        ux_score=full_response.ux_score,
        overall_score=full_response.overall_score,
        structure_analysis=full_response.structure_analysis,
        messaging_analysis=full_response.messaging_analysis,
        cta_analysis=full_response.cta_analysis,
        content_depth_analysis=full_response.content_depth_analysis,
        ux_analysis=full_response.ux_analysis,
    )

    recommendations = sorted(full_response.recommendations, key=lambda x: x.priority)
    return analysis, recommendations

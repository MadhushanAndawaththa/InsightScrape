import os
import json
from typing import List
from google import genai
from google.genai import types
from models import PageMetrics, SEOAnalysis, Recommendation
from services.prompt_tracer import PromptTracer

MODEL = "gemini-2.0-flash"

_client = None

def get_client() -> genai.Client:
    global _client
    if _client is None:
        api_key = os.environ.get("GEMINI_API_KEY")
        if not api_key:
            raise ValueError("GEMINI_API_KEY environment variable is not set. Copy .env.example to .env and add your key.")
        _client = genai.Client(api_key=api_key)
    return _client

async def analyze_page(metrics: PageMetrics, page_content: str, tracer: PromptTracer) -> SEOAnalysis:
    system_prompt = """You are a senior web strategist at a digital agency specializing in SEO, conversion optimization, and UX. 
Analyze this webpage using ONLY the provided metrics and content. 
Specifically check for Heading Hierarchy Violations (e.g., H3 appearing before any H2, missing H1, level skips). 
You MUST reference specific metrics by name and value in your findings (e.g., 'Word count of 300' or '80% of images lack alt text').
Do not make generic statements. Provide scores from 1-10 for each category along with findings and evidence."""

    user_prompt = f"""
## Page Metrics Summary
- Word Count: {metrics.word_count}
- CTA Count: {metrics.cta_count}
- Internal/External Links: {metrics.internal_links} / {metrics.external_links}
- Images: {metrics.image_count} total ({metrics.images_missing_alt_count} totally missing alt, {metrics.images_decorative_alt_count} intentionally empty alt="")
- Title: {metrics.meta_title or 'Missing'}
- Description: {metrics.meta_description or 'Missing'}

## Heading Hierarchy
{json.dumps(metrics.heading_hierarchy, indent=2)}

## Page Content (Excerpts)
{page_content}

Perform your analysis and return it as a structured JSON matching the requested schema.
"""
    
    response = get_client().models.generate_content(
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
    system_prompt = """You are a senior web consultant. 
Based on the provided audit analysis and raw metrics, provide 3 to 5 highly prioritized, actionable recommendations.
Your recommendations MUST be directly grounded in the metrics or the structured analysis.
Specify the grounded metric (e.g. 'H1 hierarchy violation: H3 found before H2' or '5 missing alt tags')."""

    user_prompt = f"""
## Raw Metrics
Word Count: {metrics.word_count}
Missing Alt Tags: {metrics.images_missing_alt_count}
Title: {metrics.meta_title or 'Missing'}
Description: {metrics.meta_description or 'Missing'}
Headings: {metrics.headings_count}

## Structured Analysis
Overall Score: {analysis.overall_score}/10
Structure Score: {analysis.structure_score}
Messaging Score: {analysis.messaging_score}
CTA Score: {analysis.cta_score}
Content Depth Score: {analysis.content_depth_score}
UX Score: {analysis.ux_score}

Return a list of strictly 3 to 5 recommendations matching the JSON schema.
"""

    response = get_client().models.generate_content(
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

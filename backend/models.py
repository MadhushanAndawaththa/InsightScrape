from pydantic import BaseModel, Field
from typing import List, Dict, Tuple, Literal, Optional
from datetime import datetime

class PageMetrics(BaseModel):
    word_count: int
    headings_count: Dict[str, int]
    heading_hierarchy: List[Tuple[str, str]]
    cta_count: int
    internal_links: int
    external_links: int
    image_count: int
    images_missing_alt_count: int
    images_decorative_alt_count: int
    images_missing_alt_pct: float
    meta_title: Optional[str] = None
    meta_description: Optional[str] = None
    meta_title_length: Optional[int] = None
    meta_description_length: Optional[int] = None
    has_viewport_meta: bool = False
    has_canonical: bool = False
    has_robots_meta: bool = False
    has_open_graph: bool = False
    has_twitter_card: bool = False
    structured_data_types: List[str] = []
    svg_count: int = 0
    has_video: bool = False
    has_canvas: bool = False
    has_css_animations: bool = False
    has_lottie: bool = False
    has_webgl_or_3d: bool = False
    scrape_method: str = "httpx"
    content_quality_warning: Optional[str] = None

class SectionAnalysis(BaseModel):
    score: int = Field(ge=1, le=10, description="Score from 1 (worst) to 10 (best) for this category.")
    findings: str = Field(description="Detailed findings referencing specific metrics by name and value. Use markdown.")
    evidence: str = Field(description="Direct evidence from the page content or metrics supporting the findings.")

class SEOAnalysis(BaseModel):
    structure_score: int = Field(ge=1, le=10, description="Score for HTML structure, heading hierarchy, and technical SEO.")
    messaging_score: int = Field(ge=1, le=10, description="Score for clarity, value proposition, and brand messaging.")
    cta_score: int = Field(ge=1, le=10, description="Score for quality, placement, and persuasiveness of calls to action.")
    content_depth_score: int = Field(ge=1, le=10, description="Score for content depth, expertise, and topical coverage.")
    ux_score: int = Field(ge=1, le=10, description="Score for user experience signals inferred from page structure and content.")
    overall_score: int = Field(ge=1, le=10, description="Weighted overall score across all categories.")
    structure_analysis: SectionAnalysis
    messaging_analysis: SectionAnalysis
    cta_analysis: SectionAnalysis
    content_depth_analysis: SectionAnalysis
    ux_analysis: SectionAnalysis

class Recommendation(BaseModel):
    priority: int = Field(ge=1, le=5, description="1 = highest impact must-fix, 5 = nice-to-have improvement.")
    category: Literal["seo", "messaging", "cta", "content", "ux"]
    title: str = Field(description="Short, actionable title for the recommendation.")
    description: str = Field(description="Detailed explanation of the issue and why it matters.")
    grounded_metric: str = Field(description="The exact metric or data point this recommendation is based on, e.g. '4 images missing alt text'.")
    action: str = Field(description="Specific, implementable fix — not vague advice.")
    expected_impact: str = Field(description="Concrete expected outcome of implementing the action.")

class FullAuditResponse(BaseModel):
    """Combined schema for the single-pass AI audit — analysis + recommendations in one call."""
    structure_score: int = Field(ge=1, le=10, description="Score for HTML structure, heading hierarchy, and technical SEO.")
    messaging_score: int = Field(ge=1, le=10, description="Score for clarity, value proposition, and brand messaging.")
    cta_score: int = Field(ge=1, le=10, description="Score for quality, placement, and persuasiveness of calls to action.")
    content_depth_score: int = Field(ge=1, le=10, description="Score for content depth, expertise, and topical coverage.")
    ux_score: int = Field(ge=1, le=10, description="Score for user experience signals inferred from page structure and content.")
    overall_score: int = Field(ge=1, le=10, description="Weighted overall score across all categories.")
    structure_analysis: SectionAnalysis
    messaging_analysis: SectionAnalysis
    cta_analysis: SectionAnalysis
    content_depth_analysis: SectionAnalysis
    ux_analysis: SectionAnalysis
    recommendations: List[Recommendation] = Field(description="3 to 5 prioritized, actionable recommendations grounded in the analysis above.")

class PromptLog(BaseModel):
    stage: str
    system_prompt: str
    user_prompt: str
    raw_response: str
    parsed_response: str
    timestamp: str
    model: str = "gemini-2.5-flash-lite"
    token_usage: Optional[Dict[str, int]] = None


AVAILABLE_MODELS = [
    {"id": "gemini-2.5-flash-lite", "name": "Gemini 2.5 Flash Lite", "tier": "Free (20 RPD)"},
    {"id": "gemini-2.5-flash", "name": "Gemini 2.5 Flash", "tier": "Free (20 RPD)"},
    {"id": "gemini-3-flash", "name": "Gemini 3 Flash", "tier": "Free (20 RPD)"},
    {"id": "gemini-3.1-flash-lite", "name": "Gemini 3.1 Flash Lite", "tier": "Free (500 RPD)"},
]

class AuditResult(BaseModel):
    url: str
    metrics: PageMetrics
    analysis: Optional[SEOAnalysis] = None
    recommendations: List[Recommendation] = []
    prompt_logs: List[PromptLog] = []
    audit_duration_ms: int
    ai_error: Optional[str] = None

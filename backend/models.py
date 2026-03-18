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

class SectionAnalysis(BaseModel):
    score: int = Field(ge=1, le=10)
    findings: str
    evidence: str

class SEOAnalysis(BaseModel):
    structure_score: int = Field(ge=1, le=10)
    messaging_score: int = Field(ge=1, le=10)
    cta_score: int = Field(ge=1, le=10)
    content_depth_score: int = Field(ge=1, le=10)
    ux_score: int = Field(ge=1, le=10)
    overall_score: int = Field(ge=1, le=10)
    structure_analysis: SectionAnalysis
    messaging_analysis: SectionAnalysis
    cta_analysis: SectionAnalysis
    content_depth_analysis: SectionAnalysis
    ux_analysis: SectionAnalysis

class Recommendation(BaseModel):
    priority: int = Field(ge=1, le=5)
    category: Literal["seo", "messaging", "cta", "content", "ux"]
    title: str
    description: str
    grounded_metric: str
    action: str
    expected_impact: str

class PromptLog(BaseModel):
    stage: str
    system_prompt: str
    user_prompt: str
    raw_response: str
    parsed_response: str
    timestamp: str
    model: str = "gemini-2.0-flash"
    token_usage: Optional[Dict[str, int]] = None

class AuditResult(BaseModel):
    url: str
    metrics: PageMetrics
    analysis: SEOAnalysis
    recommendations: List[Recommendation]
    prompt_logs: List[PromptLog]
    audit_duration_ms: int

import time
from models import AuditResult
from services.scraper import fetch_page, extract_metrics
from services.ai_service import analyze_page, recommend_actions
from services.prompt_tracer import PromptTracer
from fastapi import HTTPException

async def run_audit(url: str) -> AuditResult:
    start_time = time.time()
    tracer = PromptTracer()

    try:
        html_content, scrape_method = await fetch_page(url)
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"Failed to fetch page: {str(e)}")

    metrics, visible_text = extract_metrics(html_content, url, scrape_method)

    try:
        analysis = await analyze_page(metrics, visible_text, tracer)
    except Exception as e:
        raise HTTPException(status_code=503, detail=f"AI Analysis failed: {str(e)}")

    try:
        recommendations = await recommend_actions(metrics, analysis, tracer)
    except Exception as e:
        raise HTTPException(status_code=503, detail=f"AI Recommendations failed: {str(e)}")

    duration_ms = int((time.time() - start_time) * 1000)

    # Sort recommendations by priority (1 is highest priority)
    recommendations = sorted(recommendations, key=lambda x: x.priority)

    return AuditResult(
        url=url,
        metrics=metrics,
        analysis=analysis,
        recommendations=recommendations,
        prompt_logs=tracer.stages,
        audit_duration_ms=duration_ms
    )

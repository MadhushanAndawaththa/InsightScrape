import time
from models import AuditResult
from services.scraper import fetch_page, extract_metrics
from services.ai_service import run_audit_analysis
from services.prompt_tracer import PromptTracer
from fastapi import HTTPException

async def run_audit(url: str, model: str = "gemini-2.5-flash-lite") -> AuditResult:
    start_time = time.time()
    tracer = PromptTracer()

    try:
        html_content, scrape_method = await fetch_page(url)
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"Failed to fetch page: {str(e)}")

    metrics, visible_text = extract_metrics(html_content, url, scrape_method)

    analysis = None
    recommendations = []
    ai_error = None

    try:
        analysis, recommendations = await run_audit_analysis(metrics, visible_text, tracer, model=model)
    except Exception as e:
        ai_error = f"AI analysis failed: {str(e)}"
        print(f"[orchestrator] {ai_error}")

    duration_ms = int((time.time() - start_time) * 1000)

    return AuditResult(
        url=url,
        metrics=metrics,
        analysis=analysis,
        recommendations=recommendations,
        prompt_logs=tracer.stages,
        audit_duration_ms=duration_ms,
        ai_error=ai_error,
    )

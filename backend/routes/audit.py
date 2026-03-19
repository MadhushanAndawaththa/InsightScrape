from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, HttpUrl
from typing import Optional
import urllib.parse
from services.audit_orchestrator import run_audit
from models import AuditResult, AVAILABLE_MODELS

router = APIRouter()

class AuditRequest(BaseModel):
    url: HttpUrl
    model: Optional[str] = "gemini-2.5-flash-lite"

@router.get("/api/models")
async def list_models():
    return {"models": AVAILABLE_MODELS}

@router.post("/api/audit", response_model=AuditResult)
async def create_audit(req: AuditRequest):
    parsed_url = urllib.parse.urlparse(str(req.url))
    
    # SSRF protection measures logic
    if parsed_url.hostname in ("localhost", "127.0.0.1", "0.0.0.0", "::1"):
        raise HTTPException(status_code=422, detail="Localhost or private IPs are not allowed")

    if parsed_url.scheme not in ("http", "https"):
        raise HTTPException(status_code=422, detail="Only HTTP/HTTPS schemes allowed")

    # Validate model selection
    valid_model_ids = {m["id"] for m in AVAILABLE_MODELS}
    model = req.model if req.model in valid_model_ids else "gemini-2.5-flash-lite"

    return await run_audit(str(req.url), model=model)

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, HttpUrl
import urllib.parse
from services.audit_orchestrator import run_audit
from models import AuditResult

router = APIRouter()

class AuditRequest(BaseModel):
    url: HttpUrl

@router.post("/api/audit", response_model=AuditResult)
async def create_audit(req: AuditRequest):
    parsed_url = urllib.parse.urlparse(str(req.url))
    
    # SSRF protection measures logic
    if parsed_url.hostname in ("localhost", "127.0.0.1", "0.0.0.0", "::1"):
        raise HTTPException(status_code=422, detail="Localhost or private IPs are not allowed")

    if parsed_url.scheme not in ("http", "https"):
        raise HTTPException(status_code=422, detail="Only HTTP/HTTPS schemes allowed")

    return await run_audit(str(req.url))

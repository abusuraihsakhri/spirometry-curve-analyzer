"""
FastAPI REST API Server for Spirometry Curve Analyzer.
"""
from typing import Dict, Any, List
import os
import hmac
from fastapi import FastAPI, HTTPException, Header, Depends
from pydantic import BaseModel
from .base import AuditLogger, PHIGuard, SecurityException
from .models import SystemTaskPayload, ConsensusDossier
from .supervisor import SystemSupervisor

supervisor = SystemSupervisor(model_provider="mock")

app = FastAPI(
    title="Spirometry Curve Analyzer API",
    description="Enterprise Distributed Component Platform (Clinical & Biomedical AI)",
    version="3.0.0-ENTERPRISE",
)


class ChatRequest(BaseModel):
    query: str


def require_api_token(authorization: str | None = Header(default=None)) -> None:
    """Sensitive API endpoints require a configured bearer token."""
    token = os.environ.get("API_ACCESS_TOKEN")
    if not token:
        raise HTTPException(status_code=503, detail="API_ACCESS_TOKEN is not configured")
    if not hmac.compare_digest(authorization or "", "Bearer " + token):
        raise HTTPException(
            status_code=401,
            detail="Authentication required",
            headers={"WWW-Authenticate": "Bearer"},
        )


@app.get("/health")
def health():
    return {"status": "HEALTHY", "service": "spirometry-curve-analyzer", "domain": "Clinical & Biomedical AI", "standard": "CAP / CLSI / ISO Standards", "version": "3.0.0-ENTERPRISE"}


@app.get("/metrics", dependencies=[Depends(require_api_token)])
def metrics():
    return {
        "dossiers_processed_total": len(supervisor.dossier_registry),
        "audit_blocks_total": len(AuditLogger.get_trail()),
        "system_status": "NOMINAL_OPTIMAL"
    }


@app.post("/api/audit", dependencies=[Depends(require_api_token)])
def api_audit(payload: SystemTaskPayload):
    try:
        dossier = supervisor.process_task(payload)
    except SecurityException:
        raise HTTPException(status_code=422, detail="Payload contains a prohibited identifier")
    return dossier.to_dict()


@app.post("/api/chat", dependencies=[Depends(require_api_token)])
def api_chat(req: ChatRequest):
    try:
        ans = supervisor.query_supervisory_chat(req.query)
        return {"response": ans}
    except SecurityException:
        raise HTTPException(status_code=422, detail="Query contains a prohibited identifier")


@app.get("/api/audit/logs", dependencies=[Depends(require_api_token)])
def api_audit_logs():
    return {"audit_trail": AuditLogger.get_trail(), "verified": AuditLogger.verify_integrity()}

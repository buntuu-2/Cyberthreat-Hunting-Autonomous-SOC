import asyncio
import json
import logging
from pathlib import Path
from typing import Optional, List, Any, Dict, Union
from fastapi import FastAPI, WebSocket, WebSocketDisconnect, HTTPException, Query, Response
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse, PlainTextResponse, FileResponse
from pydantic import BaseModel

from ai_soc.config.settings import get_settings
from ai_soc.pipeline import get_pipeline, SOCPipeline
from ai_soc.alerts.models import IncidentRecord
from simulator.attack_simulator import AttackSimulator

logger = logging.getLogger("ai_soc_api")
settings = get_settings()
pipeline = get_pipeline()
simulator = AttackSimulator(pipeline=pipeline)

app = FastAPI(
    title="AI Cyberthreat Hunting & Autonomous SOC",
    description="Semi-Autonomous Mini-SOC with SIEM, IDS, Threat Intel, AI Investigation, Risk Scoring, and Automated Response.",
    version="1.0.0"
)

# Active WebSocket connections
connected_websockets: List[WebSocket] = []


def on_new_incident(incident: IncidentRecord):
    """Callback triggered whenever an incident is processed in the pipeline."""
    payload = json.dumps({
        "type": "NEW_INCIDENT",
        "data": incident.model_dump(mode="json")
    })
    for ws in list(connected_websockets):
        asyncio.create_task(send_ws_safe(ws, payload))


pipeline.subscribe(on_new_incident)


async def send_ws_safe(ws: WebSocket, message: str):
    try:
        await ws.send_text(message)
    except Exception:
        if ws in connected_websockets:
            connected_websockets.remove(ws)


# Ingestion request schemas
class IngestRequest(BaseModel):
    raw_event: Any = None
    source: Optional[str] = None


class ManualBlockRequest(BaseModel):
    ip: str
    reason: Optional[str] = "Manual analyst intervention"
    ttl_seconds: Optional[int] = 300


class ManualUnblockRequest(BaseModel):
    ip: str


@app.get("/api/stats")
async def get_system_stats():
    pipeline.firewall.check_expirations()
    incidents = pipeline.store.get_all(limit=500)
    
    crit_count = sum(1 for i in incidents if i.risk_assessment.severity == "CRITICAL")
    high_count = sum(1 for i in incidents if i.risk_assessment.severity == "HIGH")
    med_count = sum(1 for i in incidents if i.risk_assessment.severity == "MEDIUM")
    low_count = sum(1 for i in incidents if i.risk_assessment.severity == "LOW")
    active_blocks = len(pipeline.firewall.get_active_blocks())

    return {
        "total_incidents": len(incidents),
        "critical_incidents": crit_count,
        "high_incidents": high_count,
        "medium_incidents": med_count,
        "low_incidents": low_count,
        "active_firewall_blocks": active_blocks,
        "firewall_mode": settings.FIREWALL_MODE,
        "auto_response_enabled": settings.AUTO_RESPONSE_ENABLED,
        "llm_provider": settings.LLM_PROVIDER,
        "mock_threat_intel": settings.MOCK_THREAT_INTEL
    }


@app.get("/api/incidents")
async def get_incidents(
    limit: int = Query(50, ge=1, le=200),
    severity: Optional[str] = None,
    query: Optional[str] = None
):
    incidents = pipeline.store.get_all(limit=limit)
    if severity:
        incidents = [i for i in incidents if i.risk_assessment.severity.upper() == severity.upper()]
    if query:
        q = query.lower()
        incidents = [
            i for i in incidents
            if q in (i.alert.title or "").lower()
            or q in (i.alert.source_ip or "").lower()
            or q in (i.alert.target_user or "").lower()
            or q in (i.alert.event_type or "").lower()
        ]
    return [i.model_dump(mode="json") for i in incidents]


@app.get("/api/incidents/{incident_id}")
async def get_incident_detail(incident_id: str):
    inc = pipeline.store.get_by_id(incident_id)
    if not inc:
        raise HTTPException(status_code=404, detail="Incident not found")
    return inc.model_dump(mode="json")


@app.get("/api/incidents/{incident_id}/report")
async def get_incident_report(incident_id: str, format: str = Query("markdown", pattern="^(markdown|json|html)$")):
    inc = pipeline.store.get_by_id(incident_id)
    if not inc:
        raise HTTPException(status_code=404, detail="Incident not found")
    
    if format == "json":
        return Response(content=inc.model_dump_json(indent=2), media_type="application/json")
    
    md_content = pipeline.report_generator.generate_markdown(inc)
    if format == "markdown":
        return Response(
            content=md_content,
            media_type="text/markdown",
            headers={"Content-Disposition": f"attachment; filename=incident_{incident_id[:8]}.md"}
        )
    
    # HTML format
    html_content = f"""<!DOCTYPE html>
<html>
<head>
  <meta charset="utf-8">
  <title>Incident Report - {incident_id}</title>
  <link rel="stylesheet" href="/static/css/style.css">
  <style>
    body {{ background: #0b0f19; color: #e2e8f0; font-family: 'Inter', sans-serif; padding: 40px; }}
    .report-box {{ max-width: 900px; margin: 0 auto; background: rgba(30, 41, 59, 0.7); border: 1px solid #334155; border-radius: 12px; padding: 32px; backdrop-filter: blur(10px); }}
    pre {{ background: #020617; padding: 16px; border-radius: 8px; overflow-x: auto; }}
    h1, h2, h3 {{ color: #38bdf8; }}
  </style>
</head>
<body>
  <div class="report-box">
    <pre>{md_content}</pre>
  </div>
</body>
</html>"""
    return HTMLResponse(content=html_content)


@app.post("/api/ingest")
async def ingest_event(req: IngestRequest):
    if not req.raw_event:
        raise HTTPException(status_code=400, detail="raw_event required")
    try:
        incident = pipeline.process_raw(req.raw_event)
        return {"status": "success", "incident": incident.model_dump(mode="json")}
    except Exception as e:
        logger.exception("Ingest failed")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/simulate/{workflow}")
async def trigger_simulation(workflow: str):
    wf = workflow.upper()
    if wf == "A":
        # Workflow A: SSH Brute Force
        incidents = simulator.run_workflow_a_ssh_bruteforce()
        return {"status": "success", "workflow": "A", "count": len(incidents), "incidents": [i.model_dump(mode="json") for i in incidents]}
    elif wf == "B":
        # Workflow B: Port Scan
        incident = simulator.run_workflow_b_portscan()
        return {"status": "success", "workflow": "B", "incident": incident.model_dump(mode="json")}
    elif wf == "C":
        # Workflow C: Threat Intel Enrichment
        incident = simulator.run_workflow_c_threat_intel()
        return {"status": "success", "workflow": "C", "incident": incident.model_dump(mode="json")}
    elif wf == "D":
        # Workflow D: Credential Compromise
        incident = simulator.run_workflow_d_credential_compromise()
        return {"status": "success", "workflow": "D", "incident": incident.model_dump(mode="json")}
    else:
        raise HTTPException(status_code=400, detail=f"Unknown workflow '{workflow}'. Use A, B, C, or D.")


@app.get("/api/firewall/blocks")
async def get_firewall_blocks():
    blocks = pipeline.firewall.get_active_blocks()
    return [b.model_dump(mode="json") for b in blocks]


@app.post("/api/firewall/block")
async def manual_firewall_block(req: ManualBlockRequest):
    action = pipeline.firewall.block_ip(
        ip=req.ip,
        reason=req.reason or "Analyst manual quarantine",
        risk_score=90,
        rule_applied="MANUAL_ANALYST_BLOCK",
        ttl_seconds=req.ttl_seconds or 300,
        executed_by="SOC Analyst (Web Console)"
    )
    return {"status": "success", "action": action.model_dump(mode="json")}


@app.post("/api/firewall/unblock")
async def manual_firewall_unblock(req: ManualUnblockRequest):
    action = pipeline.firewall.unblock_ip(
        ip=req.ip,
        executed_by="SOC Analyst (Web Console)"
    )
    return {"status": "success", "action": action.model_dump(mode="json")}


@app.get("/api/firewall/audit")
async def get_firewall_audit():
    audit = pipeline.firewall.get_audit_trail()
    return [a.model_dump(mode="json") for a in audit]


@app.get("/api/threat-intel/{ip}")
async def query_threat_intel(ip: str):
    res = pipeline.threat_intel.lookup_ip(ip)
    return res.model_dump(mode="json")


@app.get("/api/viva-qa")
async def get_viva_qa():
    """Returns curated Viva preparation questions directly from the project roadmap."""
    return [
        {
            "question": "What is a SOC?",
            "answer": "A Security Operations Center (SOC) is a centralized function or facility responsible for continuously monitoring, detecting, investigating, and responding to cyberthreats and security events across endpoints and networks."
        },
        {
            "question": "What is SIEM?",
            "answer": "Security Information and Event Management (SIEM) aggregates log and event data from across an infrastructure, normalizes it, correlates disparate events against detection rules, triggers alerts, and facilitates compliance and threat hunting."
        },
        {
            "question": "Why Wazuh?",
            "answer": "Wazuh is an open-source security monitoring platform providing unified endpoint security (Wazuh Agent), log collection, file integrity monitoring, vulnerability detection, and centralized SIEM correlation suitable for modern defense architectures."
        },
        {
            "question": "What is Suricata?",
            "answer": "Suricata is a high-performance open-source Network Threat Detection Engine capable of real-time Network Intrusion Detection (IDS), Network Intrusion Prevention (IPS), and Network Security Monitoring (NSM)."
        },
        {
            "question": "What is Threat Hunting?",
            "answer": "Threat hunting is the proactive, hypothesis-driven human- and automated-led search through networks and endpoints to detect malicious activity, stealthy attackers, or IOCs that evaded automated detection controls."
        },
        {
            "question": "Why use Threat Intelligence?",
            "answer": "Threat Intelligence enriches atomic observables (IP addresses, domain names, hashes) with global telemetry, known adversary campaigns, historical abuse records, and reputation scores, giving context to security events."
        },
        {
            "question": "Why AI in the SOC?",
            "answer": "AI assists analysts by distilling high-volume log streams into structured natural-language narratives, mapping alerts to the MITRE ATT&CK matrix, identifying correlated signals, explaining threat severity, and proposing remediation steps in seconds."
        },
        {
            "question": "Is the SOC fully autonomous?",
            "answer": "No. The system is designed as semi-autonomous. AI acts strictly in an advisory investigative capacity, while deterministic rules, strict allowlists, and policy thresholds govern automated containment (e.g. temporary UFW firewall blocks) to prevent hallucination-induced lockouts."
        },
        {
            "question": "Why use a deterministic risk engine if AI already gives a severity?",
            "answer": "A deterministic risk engine ensures auditability, reproducibility, and explainability. Every single point (+20 for repeated failures, +20 for root target, +30 for malicious IP) is backed by hard evidence, eliminating reliance on black-box probabilistic model outputs."
        },
        {
            "question": "What happens when an alert arrives?",
            "answer": "The alert is: 1) Ingested & Parsed -> 2) Normalized into standard schema -> 3) Enriched with Threat Intel -> 4) Evaluated by Deterministic Risk Engine -> 5) Investigated by AI Analyzer -> 6) Checked against Response Policy & Allowlists -> 7) Automatically Contained via UFW if critical -> 8) Recorded in Audit Trail & Dashboard."
        }
    ]


@app.websocket("/ws/events")
async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()
    connected_websockets.append(websocket)
    try:
        while True:
            # Keepalive ping/pong
            await websocket.receive_text()
    except WebSocketDisconnect:
        if websocket in connected_websockets:
            connected_websockets.remove(websocket)


# Mount static frontend
STATIC_DIR = Path(__file__).parent / "static"
STATIC_DIR.mkdir(parents=True, exist_ok=True)
app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")


@app.get("/")
async def root_index():
    index_file = STATIC_DIR / "index.html"
    if index_file.exists():
        return FileResponse(index_file)
    return HTMLResponse("<h1>AI Cyberthreat Hunting & Autonomous SOC Running</h1><p>Visit /docs for API</p>")

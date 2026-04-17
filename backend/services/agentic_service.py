from __future__ import annotations

import datetime as dt
from typing import Any

from services.impact_service import simulate_cascade
from utils.storage import read_json, write_json


def _now_iso() -> str:
    return dt.datetime.utcnow().replace(microsecond=0).isoformat() + "Z"


def _draft_supplier_email(supplier: str, duration_days: int, severity: float) -> str:
    return (
        f"Subject: Urgent continuity support for {supplier}\n\n"
        f"Hello Team {supplier},\n"
        f"We have detected a disruption risk window of {duration_days} days at severity {severity:.2f}. "
        "Please confirm immediate recovery ETA, available dispatch capacity, and alternate lane options.\n\n"
        "Required within 2 hours:\n"
        "1) Revised commitment dates\n"
        "2) Priority SKU allocation plan\n"
        "3) Escalation SPOC details\n\n"
        "Regards,\nSupply Resilience Control Tower"
    )


def _po_top_up_suggestion(total_revenue_at_risk_inr: float) -> dict[str, Any]:
    urgency = "P1" if total_revenue_at_risk_inr >= 1200000 else "P2"
    top_up_pct = 35 if urgency == "P1" else 20
    return {
        "urgency": urgency,
        "top_up_percentage": top_up_pct,
        "note": "Top-up from alternate approved suppliers with best on-time rate in same category",
    }


def run_agentic_workflow(
    risk_scores: list[dict[str, Any]],
    records: list[dict[str, Any]],
    alerts_path: str,
    logs_path: str,
    threshold: float,
) -> dict[str, Any]:
    alerts = read_json(alerts_path, default=[])
    logs = read_json(logs_path, default=[])

    breached = [item for item in risk_scores if float(item.get("risk_score", 0)) >= threshold]
    workflow_runs: list[dict[str, Any]] = []

    for item in breached:
        supplier = item.get("supplier", "unknown")

        # Agent 1: Detector
        detector_event = {
            "agent": "Detector",
            "action": "threshold_breach_detected",
            "supplier": supplier,
            "risk_score": item.get("risk_score", 0),
            "reason_codes": item.get("reason_codes", []),
            "timestamp": _now_iso(),
        }

        # Agent 2: Analyst
        impact_report = simulate_cascade(records, supplier=supplier, severity=0.85, duration_days=5)
        analyst_event = {
            "agent": "Analyst",
            "action": "impact_report_generated",
            "supplier": supplier,
            "report": impact_report,
            "reason_codes": ["CASCADE_ANALYSIS_COMPLETED"],
            "timestamp": _now_iso(),
        }

        # Agent 3: Responder
        email_draft = _draft_supplier_email(supplier, 5, 0.85)
        po_plan = _po_top_up_suggestion(float(impact_report.get("total_revenue_at_risk_inr", 0)))
        responder_event = {
            "agent": "Responder",
            "action": "mitigation_actions_prepared",
            "supplier": supplier,
            "email_draft": email_draft,
            "po_top_up": po_plan,
            "notifications": [
                {
                    "channel": "slack",
                    "message": f"Risk breach at {supplier}; mitigation draft ready.",
                },
                {
                    "channel": "email",
                    "message": f"Escalation: {supplier} disruption risk above threshold.",
                },
            ],
            "reason_codes": ["ALTERNATE_SUPPLIER_EMAIL_DRAFTED", "PO_TOPUP_SUGGESTED"],
            "timestamp": _now_iso(),
        }

        workflow = {
            "supplier": supplier,
            "detector": detector_event,
            "analyst": analyst_event,
            "responder": responder_event,
            "workflow_timestamp": _now_iso(),
        }
        workflow_runs.append(workflow)

        alerts.append(
            {
                "supplier": supplier,
                "severity": "high",
                "reason": f"Score {item.get('risk_score')} crossed threshold {threshold}",
                "reason_codes": item.get("reason_codes", []),
                "timestamp": _now_iso(),
            }
        )

    logs.extend(workflow_runs)
    write_json(alerts_path, alerts[-500:])
    write_json(logs_path, logs[-500:])

    return {
        "breaches": len(breached),
        "workflows": workflow_runs,
    }


def mitigation_plan_for_query(records: list[dict[str, Any]], supplier: str, duration_days: int) -> dict[str, Any]:
    report = simulate_cascade(records, supplier=supplier, severity=0.9, duration_days=duration_days)
    email = _draft_supplier_email(supplier, duration_days, 0.9)
    po_plan = _po_top_up_suggestion(float(report.get("total_revenue_at_risk_inr", 0)))

    return {
        "supplier": supplier,
        "duration_days": duration_days,
        "impact": report,
        "email_draft": email,
        "po_top_up": po_plan,
        "reason_codes": [
            "WHAT_IF_SIMULATION_REQUEST",
            "CASCADE_ANALYSIS_COMPLETED",
            "MITIGATION_PLAN_GENERATED",
        ],
    }

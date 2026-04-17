import os
import re
import time
from pathlib import Path

from dotenv import load_dotenv
from flask import Flask, jsonify, request
from flask_cors import CORS
from werkzeug.utils import secure_filename

from services.agentic_service import mitigation_plan_for_query, run_agentic_workflow
from services.data_ingestion_service import ingest_supplier_csv
from services.decision_service import evaluate_decision
from services.impact_service import batch_impact, simulate_cascade
from services.llm_service import GroqClient
from services.parser_service import detect_and_parse
from services.risk_service import batch_risk, batch_risk_ml, compute_supplier_risk_scores, should_refresh
from services.signal_service import indian_festival_calendar, poll_external_signals
from utils.storage import read_json, write_json

load_dotenv()

BASE_DIR = Path(__file__).resolve().parent
UPLOAD_DIR = BASE_DIR / "uploads"
DATA_DIR = BASE_DIR / "data"
ALLOWED_EXTENSIONS = {"xlsx", "csv", "pdf"}

RECORDS_PATH = DATA_DIR / "processed_records.json"
SUPPLIERS_PATH = DATA_DIR / "suppliers.json"
PRODUCTS_PATH = DATA_DIR / "products.json"
SIGNALS_PATH = DATA_DIR / "signals.json"
FESTIVALS_PATH = DATA_DIR / "festival_calendar.json"
SUPPLIER_GRAPH_PATH = DATA_DIR / "supplier_graph.json"
SUPPLIER_RISK_SNAPSHOT_PATH = DATA_DIR / "supplier_risk_snapshot.json"
ALERTS_PATH = DATA_DIR / "alerts.json"
AGENT_LOGS_PATH = DATA_DIR / "agent_logs.json"

UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
DATA_DIR.mkdir(parents=True, exist_ok=True)

app = Flask(__name__)
CORS(app)


def allowed_file(filename: str) -> bool:
    return "." in filename and filename.rsplit(".", 1)[1].lower() in ALLOWED_EXTENSIONS


@app.get("/health")
def health() -> tuple:
    return jsonify({"status": "ok"}), 200


@app.post("/upload")
def upload_file() -> tuple:
    file = request.files.get("file")
    if not file or not file.filename:
        return jsonify({"error": "No file provided"}), 400

    if not allowed_file(file.filename):
        return jsonify({"error": "Unsupported file type"}), 400

    safe_name = secure_filename(file.filename)
    stamped_name = f"{int(time.time())}_{safe_name}"
    target = UPLOAD_DIR / stamped_name
    file.save(target)

    extension = target.suffix.lower().replace(".", "")
    return jsonify(
        {
            "message": "File uploaded successfully",
            "filename": stamped_name,
            "type": extension,
            "path": str(target),
        }
    ), 201


@app.post("/parse")
def parse_file() -> tuple:
    payload = request.get_json(silent=True) or {}
    filename = payload.get("filename")
    if not filename:
        return jsonify({"error": "filename is required"}), 400

    file_path = UPLOAD_DIR / filename
    if not file_path.exists():
        return jsonify({"error": "File not found in uploads"}), 404

    try:
        source_type, records = detect_and_parse(str(file_path))
    except Exception as error:
        return jsonify({"error": str(error)}), 400

    existing = read_json(str(RECORDS_PATH), default=[])
    write_json(str(RECORDS_PATH), existing + records)

    return jsonify({"source_type": source_type, "records": records, "count": len(records)}), 200


@app.post("/ingest/supplier-csv")
def ingest_supplier_csv_file() -> tuple:
    payload = request.get_json(silent=True) or {}
    filename = payload.get("filename")
    if not filename:
        return jsonify({"error": "filename is required"}), 400

    file_path = UPLOAD_DIR / filename
    if not file_path.exists():
        return jsonify({"error": "File not found in uploads"}), 404

    if file_path.suffix.lower() != ".csv":
        return jsonify({"error": "Only .csv is supported for supplier graph ingestion"}), 400

    result = ingest_supplier_csv(
        str(file_path),
        str(SUPPLIERS_PATH),
        str(RECORDS_PATH),
        str(SUPPLIER_GRAPH_PATH),
        os.getenv("POSTGRES_DSN"),
    )
    return jsonify({"message": "Supplier CSV ingested", **result}), 200


@app.post("/signals/poll")
def poll_signals() -> tuple:
    suppliers = read_json(str(SUPPLIERS_PATH), default=[])
    signals = poll_external_signals(suppliers)
    festivals = indian_festival_calendar(window_days=45)

    existing = read_json(str(SIGNALS_PATH), default=[])
    write_json(str(SIGNALS_PATH), (existing + signals)[-1500:])
    write_json(str(FESTIVALS_PATH), festivals)

    return jsonify({"signals_added": len(signals), "festival_entries": festivals, "signals": signals}), 200


@app.post("/risk")
def risk() -> tuple:
    payload = request.get_json(silent=True) or {}
    records = payload.get("records") or read_json(str(RECORDS_PATH), default=[])
    mode = payload.get("mode", "rule")
    enriched = batch_risk_ml(records) if mode == "ml" else batch_risk(records)
    return jsonify({"records": enriched, "count": len(enriched)}), 200


@app.get("/risk/supplier-scores")
def supplier_risk_scores() -> tuple:
    threshold = float(request.args.get("threshold", 70))
    snapshot = read_json(str(SUPPLIER_RISK_SNAPSHOT_PATH), default={})

    if should_refresh(snapshot.get("updated_at"), refresh_seconds=900):
        records = read_json(str(RECORDS_PATH), default=[])
        suppliers = read_json(str(SUPPLIERS_PATH), default=[])
        signals = read_json(str(SIGNALS_PATH), default=[])

        calculated = compute_supplier_risk_scores(records, suppliers, signals, threshold=threshold)
        write_json(str(SUPPLIER_RISK_SNAPSHOT_PATH), calculated)
        write_json(str(ALERTS_PATH), (read_json(str(ALERTS_PATH), default=[]) + calculated["alerts"])[-1000:])
        snapshot = calculated

    return jsonify(snapshot), 200


@app.post("/risk/refresh")
def refresh_supplier_risk_scores() -> tuple:
    payload = request.get_json(silent=True) or {}
    threshold = float(payload.get("threshold", 70))

    records = read_json(str(RECORDS_PATH), default=[])
    suppliers = read_json(str(SUPPLIERS_PATH), default=[])
    signals = read_json(str(SIGNALS_PATH), default=[])
    calculated = compute_supplier_risk_scores(records, suppliers, signals, threshold=threshold)
    write_json(str(SUPPLIER_RISK_SNAPSHOT_PATH), calculated)
    write_json(str(ALERTS_PATH), (read_json(str(ALERTS_PATH), default=[]) + calculated["alerts"])[-1000:])

    return jsonify(calculated), 200


@app.post("/impact")
def impact() -> tuple:
    payload = request.get_json(silent=True) or {}
    records = payload.get("records") or read_json(str(RECORDS_PATH), default=[])
    impacted = batch_impact(records)
    total_loss = round(sum(item.get("revenue_loss", 0) for item in impacted), 2)
    return jsonify({"records": impacted, "total_revenue_loss": total_loss}), 200


@app.post("/simulate/what-if")
def what_if_simulation() -> tuple:
    payload = request.get_json(silent=True) or {}
    supplier = payload.get("supplier")
    severity = float(payload.get("severity", 0.75))
    duration_days = int(payload.get("duration_days", 5))

    if not supplier:
        return jsonify({"error": "supplier is required"}), 400

    records = read_json(str(RECORDS_PATH), default=[])
    result = simulate_cascade(records, supplier=supplier, severity=severity, duration_days=duration_days)
    return jsonify(result), 200


@app.post("/agent/run")
def run_agents() -> tuple:
    payload = request.get_json(silent=True) or {}
    threshold = float(payload.get("threshold", 70))

    snapshot = read_json(str(SUPPLIER_RISK_SNAPSHOT_PATH), default={})
    if not snapshot:
        records = read_json(str(RECORDS_PATH), default=[])
        suppliers = read_json(str(SUPPLIERS_PATH), default=[])
        signals = read_json(str(SIGNALS_PATH), default=[])
        snapshot = compute_supplier_risk_scores(records, suppliers, signals, threshold=threshold)
        write_json(str(SUPPLIER_RISK_SNAPSHOT_PATH), snapshot)

    records = read_json(str(RECORDS_PATH), default=[])
    result = run_agentic_workflow(
        snapshot.get("scores", []),
        records,
        str(ALERTS_PATH),
        str(AGENT_LOGS_PATH),
        threshold,
    )
    return jsonify(result), 200


@app.get("/agent/logs")
def agent_logs() -> tuple:
    logs = read_json(str(AGENT_LOGS_PATH), default=[])
    return jsonify({"count": len(logs), "logs": logs[-100:]}), 200


@app.get("/alerts")
def alerts() -> tuple:
    feed = read_json(str(ALERTS_PATH), default=[])
    return jsonify({"count": len(feed), "alerts": feed[-100:]}), 200


@app.post("/decision")
def decision() -> tuple:
    payload = request.get_json(silent=True) or {}
    result = evaluate_decision(payload)

    if payload.get("explain", False):
        llm = GroqClient()
        prompt = (
            "Explain why this is the best decision in simple business terms. "
            "Mention trade-offs, cost impact, and service level impact."
        )
        try:
            explanation = llm.chat(
                "You are a supply chain strategy advisor.",
                f"{prompt}\n\nDecision data: {result}",
            )
            result["explanation"] = explanation
        except Exception as error:
            result["explanation"] = f"LLM explanation unavailable: {error}"

    return jsonify(result), 200


@app.post("/chat")
def chat() -> tuple:
    payload = request.get_json(silent=True) or {}
    message = payload.get("message", "")
    if not message:
        return jsonify({"error": "message is required"}), 400

    context = {
        "suppliers": read_json(str(SUPPLIERS_PATH), default=[]),
        "products": read_json(str(PRODUCTS_PATH), default=[]),
        "records": read_json(str(RECORDS_PATH), default=[]),
    }

    lowered = message.lower()
    what_if_match = re.search(r"supplier\s+(.+?)\s+is\s+offline\s+for\s+(\d+)\s+days", lowered)
    if what_if_match:
        supplier_name = what_if_match.group(1).strip().title()
        duration_days = int(what_if_match.group(2))
        plan = mitigation_plan_for_query(context["records"], supplier_name, duration_days)
        return jsonify({"response": plan["impact"]["headline"], "mitigation_plan": plan}), 200

    llm = GroqClient()
    system_prompt = (
        "You are a supply chain resilience copilot. "
        "Provide practical, business-friendly, context-aware advice."
    )
    user_prompt = f"User question: {message}\n\nSystem context: {context}"

    try:
        response_text = llm.chat(system_prompt, user_prompt)
    except Exception as error:
        response_text = f"Unable to call LLM: {error}"

    return jsonify({"response": response_text}), 200


@app.get("/summary")
def summary() -> tuple:
    records = read_json(str(RECORDS_PATH), default=[])
    risked = batch_risk(records)
    impacted = batch_impact(risked)

    total_products = len({r.get("product", "") for r in impacted if r.get("product")})
    active_risks = len([r for r in impacted if r.get("risk_level") in {"Medium", "High"}])
    delayed_shipments = len([r for r in impacted if float(r.get("delay", r.get("delay_days", 0))) > 0])
    estimated_revenue_loss = round(sum(float(r.get("revenue_loss", 0)) for r in impacted), 2)

    risk_distribution = {"Low": 0, "Medium": 0, "High": 0}
    inv_vs_demand = []
    for rec in impacted:
        level = rec.get("risk_level", "Low")
        if level in risk_distribution:
            risk_distribution[level] += 1
        inv_vs_demand.append(
            {
                "product": rec.get("product", "unknown"),
                "inventory": float(rec.get("inventory", 0)),
                "demand": float(rec.get("demand", rec.get("demand_per_day", 0))),
            }
        )

    supplier_snapshot = read_json(str(SUPPLIER_RISK_SNAPSHOT_PATH), default={})
    supplier_scores = supplier_snapshot.get("scores", [])
    alerts_feed = read_json(str(ALERTS_PATH), default=[])[-12:]
    festivals = read_json(str(FESTIVALS_PATH), default=[])

    return jsonify(
        {
            "kpis": {
                "total_products": total_products,
                "active_risks": active_risks,
                "estimated_revenue_loss": estimated_revenue_loss,
                "delayed_shipments": delayed_shipments,
            },
            "risk_distribution": risk_distribution,
            "inventory_vs_demand": inv_vs_demand,
            "records": impacted,
            "supplier_heatmap": supplier_scores,
            "alerts": alerts_feed,
            "festival_calendar": festivals,
        }
    ), 200


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.getenv("PORT", "5001")), debug=True)

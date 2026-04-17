import random
from collections import Counter
from datetime import datetime, timedelta
from typing import Any

import numpy as np
from sklearn.ensemble import RandomForestRegressor


_MODEL = None


def _get_model() -> RandomForestRegressor:
    global _MODEL
    if _MODEL is not None:
        return _MODEL

    rng = np.random.default_rng(42)
    n = 200
    delay = rng.uniform(0, 20, size=n)
    reliability = rng.uniform(0.4, 0.98, size=n)
    external = rng.uniform(0.05, 0.95, size=n)

    y = 0.5 * np.minimum(delay / 20.0, 1.0) + 0.3 * (1 - reliability) + 0.2 * external
    X = np.column_stack([delay, reliability, external])

    model = RandomForestRegressor(n_estimators=80, random_state=42)
    model.fit(X, y)
    _MODEL = model
    return model


def _risk_level(score: float) -> str:
    if score >= 0.7:
        return "High"
    if score >= 0.4:
        return "Medium"
    return "Low"


def compute_risk(record: dict[str, Any], mode: str = "rule") -> dict[str, Any]:
    delay = float(record.get("delay") or record.get("delay_days") or 0)
    reliability = float(record.get("supplier_reliability", 0.8))
    external = float(record.get("external_factor", random.uniform(0.1, 0.5)))

    delay_component = min(delay / 20.0, 1.0)
    reliability_component = 1 - max(0.0, min(reliability, 1.0))
    external_component = max(0.0, min(external, 1.0))

    if mode == "ml":
        model = _get_model()
        score = float(model.predict([[delay, reliability, external_component]])[0])
    else:
        score = 0.5 * delay_component + 0.3 * reliability_component + 0.2 * external_component
    score = max(0.0, min(score, 1.0))

    enriched = dict(record)
    enriched["risk_score"] = round(score, 3)
    enriched["risk_level"] = _risk_level(score)
    enriched["external_factor"] = round(external_component, 3)
    return enriched


def batch_risk(records: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return [compute_risk(record) for record in records]


def batch_risk_ml(records: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return [compute_risk(record, mode="ml") for record in records]


def _to_float(value: Any, default: float = 0.0) -> float:
    try:
        return float(value)
    except Exception:
        return default


def _severity_weight(severity: str) -> float:
    lowered = (severity or "").lower()
    if lowered == "high":
        return 1.0
    if lowered == "medium":
        return 0.6
    return 0.25


def _score_band(score: float) -> str:
    if score >= 80:
        return "Critical"
    if score >= 60:
        return "High"
    if score >= 35:
        return "Medium"
    return "Low"


def compute_supplier_risk_scores(
    records: list[dict[str, Any]],
    suppliers: list[dict[str, Any]],
    signals: list[dict[str, Any]],
    threshold: float = 70,
) -> dict[str, Any]:
    supplier_names = {
        item.get("supplier")
        for item in suppliers + records
        if item.get("supplier")
    }

    supplier_scores: list[dict[str, Any]] = []
    alerts: list[dict[str, Any]] = []

    for supplier_name in sorted(supplier_names):
        supplier_records = [item for item in records if item.get("supplier") == supplier_name]
        supplier_signals = [item for item in signals if item.get("supplier") == supplier_name]
        supplier_meta = next((item for item in suppliers if item.get("supplier") == supplier_name), {})

        signal_frequency = sum(_severity_weight(item.get("severity", "low")) for item in supplier_signals)
        signal_component = min(100.0, signal_frequency * 14)

        financial_health = _to_float(supplier_meta.get("financial_health_proxy"), 0.72)
        if not supplier_meta and supplier_records:
            financial_health = float(np.clip(np.mean([_to_float(r.get("financial_health_proxy"), 0.72) for r in supplier_records]), 0.3, 0.98))
        financial_component = (1.0 - np.clip(financial_health, 0.0, 1.0)) * 100.0

        on_time_samples = []
        for rec in supplier_records:
            if "on_time_rate" in rec:
                on_time_samples.append(np.clip(_to_float(rec.get("on_time_rate"), 0.75), 0.0, 1.0))
            else:
                delay = _to_float(rec.get("delay") or rec.get("delay_days"), 0.0)
                on_time_samples.append(1.0 if delay <= 2 else 0.75 if delay <= 5 else 0.4)
        on_time_rate = float(np.mean(on_time_samples)) if on_time_samples else 0.78
        on_time_component = (1.0 - on_time_rate) * 100.0

        locations = [
            str(item.get("location") or item.get("cluster") or "India")
            for item in supplier_records
        ]
        if locations:
            concentration = Counter(locations).most_common(1)[0][1] / max(1, len(locations))
        else:
            concentration = 0.5
        geo_component = concentration * 100.0

        score = (
            0.34 * signal_component
            + 0.26 * financial_component
            + 0.24 * on_time_component
            + 0.16 * geo_component
        )
        score = float(np.clip(score, 0.0, 100.0))

        reason_codes = []
        if signal_component >= 50:
            reason_codes.append("SIGNAL_FREQUENCY_SPIKE")
        if financial_component >= 45:
            reason_codes.append("FINANCIAL_STRESS_PROXY")
        if on_time_component >= 35:
            reason_codes.append("ON_TIME_RATE_WEAK")
        if geo_component >= 70:
            reason_codes.append("GEO_CONCENTRATION_RISK")
        if any("surat" in str(sig.get("title", "")).lower() for sig in supplier_signals):
            reason_codes.append("SURAT_TEXTILE_CLUSTER_NEWS")
        if any(str(sig.get("reason_code")) == "IMD_WEATHER_ALERT" for sig in supplier_signals):
            reason_codes.append("IMD_WEATHER_ALERT")
        if not reason_codes:
            reason_codes.append("BASELINE_MONITORING")

        payload = {
            "supplier": supplier_name,
            "risk_score": round(score, 2),
            "risk_band": _score_band(score),
            "signal_frequency": round(signal_frequency, 2),
            "financial_health_proxy": round(financial_health, 2),
            "historical_on_time_rate": round(on_time_rate, 2),
            "geo_concentration_risk": round(geo_component, 2),
            "reason_codes": reason_codes,
            "updated_at": datetime.utcnow().replace(microsecond=0).isoformat() + "Z",
        }
        supplier_scores.append(payload)

        if score >= threshold:
            alerts.append(
                {
                    "supplier": supplier_name,
                    "severity": "high" if score >= 80 else "medium",
                    "risk_score": round(score, 2),
                    "reason": f"Threshold breached at {round(score, 2)}",
                    "reason_codes": reason_codes,
                    "updated_at": payload["updated_at"],
                }
            )

    return {
        "updated_at": datetime.utcnow().replace(microsecond=0).isoformat() + "Z",
        "scores": supplier_scores,
        "alerts": alerts,
        "threshold": threshold,
    }


def should_refresh(last_updated_iso: str | None, refresh_seconds: int = 900) -> bool:
    if not last_updated_iso:
        return True
    try:
        normalized = last_updated_iso.replace("Z", "+00:00")
        last_updated = datetime.fromisoformat(normalized)
        return datetime.now(last_updated.tzinfo) - last_updated >= timedelta(seconds=refresh_seconds)
    except Exception:
        return True

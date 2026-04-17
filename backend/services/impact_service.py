import datetime as dt
from typing import Any


def impact_analysis(record: dict[str, Any]) -> dict[str, Any]:
    demand = float(record.get("demand", record.get("demand_per_day", 0)))
    inventory = float(record.get("inventory", 0))
    delay = float(record.get("delay", record.get("delay_days", 0)))
    product_price = float(record.get("product_price", 10))

    stockout_days = max(0.0, delay - (inventory / demand if demand else 0.0))
    revenue_loss = stockout_days * demand * product_price

    enriched = dict(record)
    enriched["stockout_days"] = round(stockout_days, 2)
    enriched["revenue_loss"] = round(revenue_loss, 2)
    return enriched


def batch_impact(records: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return [impact_analysis(record) for record in records]


def _to_float(value: Any, default: float = 0.0) -> float:
    try:
        return float(value)
    except Exception:
        return default


def _inr_lakh(value: float) -> str:
    return f"{value / 100000:.1f}L"


def simulate_cascade(
    records: list[dict[str, Any]],
    supplier: str,
    severity: float = 0.7,
    duration_days: int = 5,
) -> dict[str, Any]:
    severity = max(0.1, min(1.0, float(severity)))
    duration_days = max(1, int(duration_days))
    affected = [item for item in records if str(item.get("supplier", "")).lower() == supplier.lower()]
    start_date = dt.date.today()

    sku_impact: list[dict[str, Any]] = []
    total_revenue_at_risk_inr = 0.0

    for row in affected:
        sku = row.get("product", "unknown")
        demand = _to_float(row.get("demand") or row.get("demand_per_day"), 0.0)
        inventory = _to_float(row.get("inventory"), 0.0)
        depletion_rate = max(0.01, demand * severity)
        cover_days = inventory / depletion_rate if depletion_rate > 0 else 999
        stockout_in_days = max(0.0, cover_days)
        stockout_date = start_date + dt.timedelta(days=int(stockout_in_days))
        disruption_shortfall_days = max(0.0, duration_days - cover_days)

        unit_price_inr = _to_float(row.get("product_price_inr"), 0.0)
        if unit_price_inr <= 0:
            unit_price_inr = _to_float(row.get("product_price"), 15.0) * 83.0

        revenue_at_risk = disruption_shortfall_days * demand * unit_price_inr
        total_revenue_at_risk_inr += revenue_at_risk

        sku_impact.append(
            {
                "sku": sku,
                "inventory": round(inventory, 2),
                "demand_per_day": round(demand, 2),
                "depletion_rate": round(depletion_rate, 2),
                "stockout_in_days": round(stockout_in_days, 2),
                "stockout_date": stockout_date.isoformat(),
                "revenue_at_risk_inr": round(revenue_at_risk, 2),
            }
        )

    sku_impact.sort(key=lambda item: item["revenue_at_risk_inr"], reverse=True)
    stockout_days = [item["stockout_in_days"] for item in sku_impact] or [0.0]
    earliest_stockout = min(stockout_days)

    headline = (
        f"Supplier {supplier} disruption = INR {round(total_revenue_at_risk_inr, 2):,.0f} "
        f"({_inr_lakh(total_revenue_at_risk_inr)}) stockout risk in {earliest_stockout:.1f} days"
    )

    return {
        "supplier": supplier,
        "severity": severity,
        "duration_days": duration_days,
        "affected_sku_count": len(sku_impact),
        "earliest_stockout_days": round(earliest_stockout, 2),
        "total_revenue_at_risk_inr": round(total_revenue_at_risk_inr, 2),
        "headline": headline,
        "sku_impact": sku_impact,
    }

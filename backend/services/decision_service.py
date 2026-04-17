import random
from typing import Any


WEIGHTS = {"revenue_loss": 0.6, "extra_cost": 0.3, "delay": 0.1}


def _score(option: dict[str, Any]) -> float:
    return (
        option["revenue_loss"] * WEIGHTS["revenue_loss"]
        + option["extra_cost"] * WEIGHTS["extra_cost"]
        + option["delay"] * WEIGHTS["delay"]
    )


def _impact_for(delay_days: float, demand: float, inventory: float, product_price: float, reliability: float) -> float:
    stockout_days = max(0.0, delay_days - (inventory / demand if demand else 0.0))
    revenue_loss = stockout_days * demand * product_price
    adjusted_loss = revenue_loss * (1 - reliability)
    return max(0.0, adjusted_loss)


def evaluate_decision(payload: dict[str, Any]) -> dict[str, Any]:
    demand = float(payload.get("demand_per_day", 100))
    inventory = float(payload.get("inventory", 250))
    delay = float(payload.get("delay_days", 5))
    product_price = float(payload.get("product_price", 12))
    reliability = float(payload.get("supplier_reliability", 0.8))

    alternatives = payload.get("alternative_suppliers", [])
    if not alternatives:
        alternatives = [
            {"name": "AltFast", "cost": 1.12, "delay": max(1.0, delay - 2), "reliability": 0.88, "capacity": 0.7},
            {"name": "AltBudget", "cost": 0.95, "delay": delay + 1, "reliability": 0.72, "capacity": 1.0},
        ]

    option_a_delay = max(0.0, delay + random.uniform(-1, 1))
    option_a_loss = _impact_for(option_a_delay, demand, inventory, product_price, reliability)

    options: list[dict[str, Any]] = [
        {
            "option": "Option A: Do nothing",
            "revenue_loss": round(option_a_loss, 2),
            "extra_cost": 0.0,
            "delay": round(option_a_delay, 2),
        }
    ]

    best_alt = max(alternatives, key=lambda alt: float(alt.get("reliability", 0.5)))
    alt_delay = max(0.0, float(best_alt.get("delay", delay)) + random.uniform(-1, 1))
    alt_rel = min(1.0, max(0.0, float(best_alt.get("reliability", reliability))))
    alt_capacity = min(1.0, max(0.1, float(best_alt.get("capacity", 1.0))))
    switch_inventory = inventory * alt_capacity
    switch_loss = _impact_for(alt_delay, demand, switch_inventory, product_price, alt_rel)
    options.append(
        {
            "option": f"Option B: Switch supplier ({best_alt.get('name', 'Alternative')})",
            "revenue_loss": round(switch_loss, 2),
            "extra_cost": round(max(0.0, float(best_alt.get("cost", 1.0)) - 1.0) * demand * product_price * 0.2, 2),
            "delay": round(alt_delay, 2),
        }
    )

    redistributed_inventory = inventory * 1.25
    red_delay = max(0.0, delay - 1 + random.uniform(-1, 1))
    red_loss = _impact_for(red_delay, demand, redistributed_inventory, product_price, reliability)
    options.append(
        {
            "option": "Option C: Redistribute inventory",
            "revenue_loss": round(red_loss, 2),
            "extra_cost": round(demand * 0.7, 2),
            "delay": round(red_delay, 2),
        }
    )

    hybrid_delay = max(0.0, (delay * 0.6 + alt_delay * 0.4) + random.uniform(-1, 1))
    hybrid_reliability = min(1.0, reliability * 0.6 + alt_rel * 0.4)
    hybrid_inventory = inventory * min(1.0, 0.5 + 0.5 * alt_capacity)
    hybrid_loss = _impact_for(hybrid_delay, demand, hybrid_inventory, product_price, hybrid_reliability)
    options.append(
        {
            "option": "Option D: Hybrid split suppliers",
            "revenue_loss": round(hybrid_loss, 2),
            "extra_cost": round(demand * product_price * 0.05, 2),
            "delay": round(hybrid_delay, 2),
        }
    )

    for option in options:
        option["score"] = round(_score(option), 2)

    best_option = min(options, key=lambda opt: opt["score"])
    baseline_loss = options[0]["revenue_loss"]
    savings = max(0.0, baseline_loss - best_option["revenue_loss"])

    confidence = 0.5 + (0.4 * min(1.0, reliability)) + (0.1 if best_option["option"].startswith("Option D") else 0)
    confidence = min(0.98, confidence)

    return {
        "best_option": best_option,
        "options": options,
        "savings": round(savings, 2),
        "confidence_score": round(confidence, 2),
    }

from __future__ import annotations

import datetime as dt
import random
from typing import Any

import requests

try:
    from langchain.tools import tool
except Exception:  # pragma: no cover
    def tool(func):
        return func

try:
    import feedparser
except Exception:  # pragma: no cover
    feedparser = None

try:
    import holidays
except Exception:  # pragma: no cover
    holidays = None


IMD_ALERT_URL = "https://mausam.imd.gov.in/imd_latest/contents/warnings.php"
STATE_RSS_FEEDS = [
    "https://timesofindia.indiatimes.com/rssfeeds/-2128936835.cms",
    "https://timesofindia.indiatimes.com/rssfeeds/-2128833038.cms",
]


def _now_iso() -> str:
    return dt.datetime.utcnow().replace(microsecond=0).isoformat() + "Z"


def _safe_get(url: str) -> str:
    try:
        response = requests.get(url, timeout=10)
        response.raise_for_status()
        return response.text
    except Exception:
        return ""


@tool
def fetch_imd_flood_alerts(_: str = "latest") -> list[dict[str, Any]]:
    """LangChain tool that checks IMD warning bulletin page and emits flood-like alerts."""
    body = _safe_get(IMD_ALERT_URL).lower()
    alerts: list[dict[str, Any]] = []
    keywords = ["flood", "heavy rain", "orange alert", "red alert", "cyclone"]
    for keyword in keywords:
        if keyword in body:
            alerts.append(
                {
                    "signal_type": "weather",
                    "source": "IMD",
                    "title": f"IMD alert keyword matched: {keyword}",
                    "severity": "high" if keyword in {"flood", "red alert", "cyclone"} else "medium",
                    "region": "India",
                    "reason_code": "IMD_WEATHER_ALERT",
                    "timestamp": _now_iso(),
                }
            )
    if not alerts:
        alerts.append(
            {
                "signal_type": "weather",
                "source": "IMD",
                "title": "No severe IMD bulletin keyword match; monitoring continues",
                "severity": "low",
                "region": "India",
                "reason_code": "IMD_MONITOR_ONLY",
                "timestamp": _now_iso(),
            }
        )
    return alerts


@tool
def fetch_state_news_signals(_: str = "latest") -> list[dict[str, Any]]:
    """LangChain tool that polls state news RSS feeds for disruption terms."""
    signals: list[dict[str, Any]] = []
    disruption_keywords = ["strike", "port", "flood", "logistics", "power cut", "surat textile"]

    if feedparser is None:
        return [
            {
                "signal_type": "news",
                "source": "RSS",
                "title": "feedparser dependency unavailable; using synthetic state news monitor",
                "severity": "low",
                "region": "India",
                "reason_code": "STATE_RSS_UNAVAILABLE",
                "timestamp": _now_iso(),
            }
        ]

    for feed_url in STATE_RSS_FEEDS:
        parsed = feedparser.parse(feed_url)
        for entry in parsed.entries[:25]:
            title = (getattr(entry, "title", "") or "").lower()
            for keyword in disruption_keywords:
                if keyword in title:
                    signals.append(
                        {
                            "signal_type": "news",
                            "source": "StateRSS",
                            "title": getattr(entry, "title", "State disruption signal"),
                            "severity": "high" if keyword in {"strike", "flood", "surat textile"} else "medium",
                            "region": "India",
                            "reason_code": "STATE_NEWS_DISRUPTION",
                            "timestamp": _now_iso(),
                        }
                    )
                    break

    if not signals:
        signals.append(
            {
                "signal_type": "news",
                "source": "StateRSS",
                "title": "No high-impact state disruption headlines in latest poll",
                "severity": "low",
                "region": "India",
                "reason_code": "STATE_NEWS_CLEAR",
                "timestamp": _now_iso(),
            }
        )
    return signals


def _gst_disruption_proxy(today: dt.date) -> dict[str, Any]:
    due_day = 20
    delta = abs(today.day - due_day)
    if delta <= 3:
        severity = "medium"
        title = "GST filing window may cause trucking and dispatch friction"
        reason = "GST_WINDOW_PRESSURE"
    else:
        severity = "low"
        title = "GST disruption proxy low"
        reason = "GST_PROXY_LOW"
    return {
        "signal_type": "gst_proxy",
        "source": "GSTProxy",
        "title": title,
        "severity": severity,
        "region": "India",
        "reason_code": reason,
        "timestamp": _now_iso(),
    }


def indian_festival_calendar(window_days: int = 45) -> list[dict[str, Any]]:
    today = dt.date.today()
    end = today + dt.timedelta(days=window_days)

    entries: list[dict[str, Any]] = []
    if holidays is not None:
        india_holidays = holidays.India(years=[today.year, end.year])
        for day, name in india_holidays.items():
            if today <= day <= end:
                entries.append(
                    {
                        "date": day.isoformat(),
                        "festival": name,
                        "risk_hint": "Potential labor/logistics capacity dip",
                        "reason_code": "FESTIVAL_CAPACITY_CONSTRAINT",
                    }
                )

    if not entries:
        entries = [
            {
                "date": (today + dt.timedelta(days=12)).isoformat(),
                "festival": "Regional Festival (synthetic fallback)",
                "risk_hint": "Potential labor/logistics capacity dip",
                "reason_code": "FESTIVAL_CAPACITY_CONSTRAINT",
            }
        ]
    return entries


def poll_external_signals(suppliers: list[dict[str, Any]]) -> list[dict[str, Any]]:
    weather = fetch_imd_flood_alerts.invoke("latest") if hasattr(fetch_imd_flood_alerts, "invoke") else fetch_imd_flood_alerts("latest")
    news = fetch_state_news_signals.invoke("latest") if hasattr(fetch_state_news_signals, "invoke") else fetch_state_news_signals("latest")
    gst = [_gst_disruption_proxy(dt.date.today())]

    all_signals = weather + news + gst
    supplier_names = [item.get("supplier", "") for item in suppliers if item.get("supplier")]

    assigned: list[dict[str, Any]] = []
    for signal in all_signals:
        if signal.get("severity") == "low":
            target_suppliers = supplier_names[:2] or ["unknown"]
        else:
            target_suppliers = supplier_names or ["unknown"]

        for name in target_suppliers:
            enriched = dict(signal)
            enriched["supplier"] = name
            if "surat" in str(enriched.get("title", "")).lower():
                enriched["cluster"] = "Surat Textile"
                enriched["reason_code"] = "SURAT_TEXTILE_CLUSTER_NEWS"
            assigned.append(enriched)

    # Add one synthetic weather pulse to keep demo lively when external feeds are calm.
    if not any(item.get("severity") in {"high", "medium"} for item in assigned):
        if supplier_names:
            assigned.append(
                {
                    "signal_type": "weather",
                    "source": "IMD",
                    "title": "Localized heavy rain advisory affecting west corridor",
                    "severity": random.choice(["medium", "high"]),
                    "region": "India",
                    "reason_code": "IMD_WEATHER_ALERT",
                    "timestamp": _now_iso(),
                    "supplier": supplier_names[0],
                    "cluster": "Surat Textile",
                }
            )
    return assigned

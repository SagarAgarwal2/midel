from __future__ import annotations

import csv
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from utils.storage import read_json, write_json

try:
    import psycopg2
except Exception:  # pragma: no cover
    psycopg2 = None


@dataclass
class GraphPayload:
    suppliers: list[dict[str, Any]]
    skus: list[dict[str, Any]]
    edges: list[dict[str, Any]]


def _to_float(value: Any, default: float = 0.0) -> float:
    try:
        return float(value)
    except Exception:
        return default


def ingest_supplier_csv(
    file_path: str,
    suppliers_path: str,
    records_path: str,
    graph_path: str,
    postgres_dsn: str | None = None,
) -> dict[str, Any]:
    suppliers = read_json(suppliers_path, default=[])
    records = read_json(records_path, default=[])

    supplier_index = {item.get("supplier", ""): item for item in suppliers if item.get("supplier")}
    sku_nodes: dict[str, dict[str, Any]] = {}
    edges: list[dict[str, Any]] = []
    new_records: list[dict[str, Any]] = []

    with open(file_path, "r", encoding="utf-8") as csv_file:
        reader = csv.DictReader(csv_file)
        for raw in reader:
            supplier_name = (raw.get("supplier") or raw.get("supplier_name") or "unknown").strip()
            sku_name = (raw.get("product") or raw.get("sku") or "unknown").strip()
            demand = _to_float(raw.get("demand") or raw.get("demand_per_day"), 0.0)
            inventory = _to_float(raw.get("inventory"), 0.0)
            delay = _to_float(raw.get("delay") or raw.get("delay_days"), 0.0)
            on_time_rate = _to_float(raw.get("on_time_rate"), 0.82)
            financial_health = _to_float(raw.get("financial_health_proxy"), 0.7)
            location = (raw.get("location") or raw.get("city") or "India").strip()
            cluster = (raw.get("cluster") or "General").strip()

            if supplier_name not in supplier_index:
                supplier_index[supplier_name] = {
                    "supplier": supplier_name,
                    "reliability": round(on_time_rate, 3),
                    "region": "India",
                    "location": location,
                    "cluster": cluster,
                    "financial_health_proxy": round(financial_health, 3),
                }

            if sku_name not in sku_nodes:
                sku_nodes[sku_name] = {
                    "sku": sku_name,
                    "category": raw.get("category") or "General",
                    "unit_price_inr": _to_float(raw.get("unit_price_inr"), _to_float(raw.get("product_price"), 1000.0)),
                }

            record = {
                "supplier": supplier_name,
                "product": sku_name,
                "demand": demand,
                "inventory": inventory,
                "delay": delay,
                "supplier_reliability": on_time_rate,
                "financial_health_proxy": financial_health,
                "location": location,
                "cluster": cluster,
                "on_time_rate": on_time_rate,
                "product_price_inr": _to_float(raw.get("unit_price_inr"), _to_float(raw.get("product_price"), 1000.0)),
            }
            new_records.append(record)
            edges.append(
                {
                    "from": supplier_name,
                    "to": sku_name,
                    "edge_type": "supplies",
                    "lead_time_days": delay,
                    "on_time_rate": on_time_rate,
                    "location": location,
                }
            )

    all_suppliers = sorted(supplier_index.values(), key=lambda item: item["supplier"])
    all_records = records + new_records

    graph_payload = GraphPayload(
        suppliers=all_suppliers,
        skus=sorted(sku_nodes.values(), key=lambda item: item["sku"]),
        edges=edges,
    )

    write_json(suppliers_path, all_suppliers)
    write_json(records_path, all_records)
    write_json(
        graph_path,
        {
            "nodes": {
                "suppliers": graph_payload.suppliers,
                "skus": graph_payload.skus,
            },
            "edges": graph_payload.edges,
        },
    )

    postgres_status = _sync_graph_to_postgres(graph_payload, postgres_dsn)

    return {
        "suppliers_count": len(graph_payload.suppliers),
        "sku_count": len(graph_payload.skus),
        "edges_count": len(graph_payload.edges),
        "records_added": len(new_records),
        "postgres": postgres_status,
    }


def _sync_graph_to_postgres(graph: GraphPayload, postgres_dsn: str | None) -> dict[str, Any]:
    if not postgres_dsn:
        return {"enabled": False, "message": "POSTGRES_DSN not configured"}
    if psycopg2 is None:
        return {"enabled": True, "synced": False, "message": "psycopg2 not installed"}

    try:
        with psycopg2.connect(postgres_dsn) as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    CREATE TABLE IF NOT EXISTS supplier_nodes (
                      supplier TEXT PRIMARY KEY,
                      reliability DOUBLE PRECISION,
                      region TEXT,
                      location TEXT,
                      cluster TEXT,
                      financial_health_proxy DOUBLE PRECISION
                    )
                    """
                )
                cur.execute(
                    """
                    CREATE TABLE IF NOT EXISTS sku_nodes (
                      sku TEXT PRIMARY KEY,
                      category TEXT,
                      unit_price_inr DOUBLE PRECISION
                    )
                    """
                )
                cur.execute(
                    """
                    CREATE TABLE IF NOT EXISTS supplier_sku_edges (
                      supplier TEXT,
                      sku TEXT,
                      edge_type TEXT,
                      lead_time_days DOUBLE PRECISION,
                      on_time_rate DOUBLE PRECISION,
                      location TEXT,
                      PRIMARY KEY (supplier, sku)
                    )
                    """
                )

                for supplier in graph.suppliers:
                    cur.execute(
                        """
                        INSERT INTO supplier_nodes (supplier, reliability, region, location, cluster, financial_health_proxy)
                        VALUES (%s, %s, %s, %s, %s, %s)
                        ON CONFLICT (supplier) DO UPDATE SET
                          reliability = EXCLUDED.reliability,
                          region = EXCLUDED.region,
                          location = EXCLUDED.location,
                          cluster = EXCLUDED.cluster,
                          financial_health_proxy = EXCLUDED.financial_health_proxy
                        """,
                        (
                            supplier.get("supplier"),
                            _to_float(supplier.get("reliability"), 0.8),
                            supplier.get("region", "India"),
                            supplier.get("location", "India"),
                            supplier.get("cluster", "General"),
                            _to_float(supplier.get("financial_health_proxy"), 0.7),
                        ),
                    )

                for sku in graph.skus:
                    cur.execute(
                        """
                        INSERT INTO sku_nodes (sku, category, unit_price_inr)
                        VALUES (%s, %s, %s)
                        ON CONFLICT (sku) DO UPDATE SET
                          category = EXCLUDED.category,
                          unit_price_inr = EXCLUDED.unit_price_inr
                        """,
                        (sku.get("sku"), sku.get("category", "General"), _to_float(sku.get("unit_price_inr"), 0.0)),
                    )

                for edge in graph.edges:
                    cur.execute(
                        """
                        INSERT INTO supplier_sku_edges (supplier, sku, edge_type, lead_time_days, on_time_rate, location)
                        VALUES (%s, %s, %s, %s, %s, %s)
                        ON CONFLICT (supplier, sku) DO UPDATE SET
                          edge_type = EXCLUDED.edge_type,
                          lead_time_days = EXCLUDED.lead_time_days,
                          on_time_rate = EXCLUDED.on_time_rate,
                          location = EXCLUDED.location
                        """,
                        (
                            edge.get("from"),
                            edge.get("to"),
                            edge.get("edge_type", "supplies"),
                            _to_float(edge.get("lead_time_days"), 0.0),
                            _to_float(edge.get("on_time_rate"), 0.8),
                            edge.get("location", "India"),
                        ),
                    )

        return {"enabled": True, "synced": True, "message": "Graph synced to PostgreSQL"}
    except Exception as error:  # pragma: no cover
        return {"enabled": True, "synced": False, "message": str(error)}

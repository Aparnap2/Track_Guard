"""Anomaly agent graph - stub for V3.0."""
from typing import Any


def anomaly_graph(tenant_id: str) -> dict:
    return {"tenant_id": tenant_id}


def build_anomaly_graph(tenant_id: str) -> Any:
    return anomaly_graph(tenant_id)
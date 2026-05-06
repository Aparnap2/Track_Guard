"""Memory service schemas - Pydantic contracts."""
from __future__ import annotations
from pydantic import BaseModel, Field
from typing import Literal


class MemoryReadRequest(BaseModel):
    """Request to read memories."""
    tenant_id: str = Field(..., description="Tenant ID for isolation")
    query: str = Field(..., description="Query text for semantic search")
    top_k: int = Field(default=5, ge=1, le=100, description="Maximum results")


class MemoryWriteRequest(BaseModel):
    """Request to write a memory."""
    tenant_id: str = Field(..., description="Tenant ID for isolation")
    content: str = Field(..., description="Memory content")
    memory_type: str = Field(..., description="Type: anomaly, revenue_event, etc.")
    metadata: dict = Field(default_factory=dict, description="Additional metadata")


class MemoryResult(BaseModel):
    """Single memory result."""
    content: str
    memory_type: str
    score: float = Field(default=0.0, description="Relevance score")
    source: Literal["vector", "graph", "episodic"] = Field(..., description="Memory layer")
    metadata: dict = Field(default_factory=dict)


class MemoryContextLoadRequest(BaseModel):
    """Request to load full context."""
    tenant_id: str = Field(..., description="Tenant ID for isolation")


__all__ = [
    "MemoryReadRequest",
    "MemoryWriteRequest",
    "MemoryResult",
    "MemoryContextLoadRequest",
]
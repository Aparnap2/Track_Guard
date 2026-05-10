"""
Decision Engine Service - Pydantic Contracts
"""
from pydantic import BaseModel, Field
from enum import Enum
from typing import Optional
import uuid
from datetime import datetime


class Severity(str, Enum):
    CRITICAL = "critical"
    WARNING = "warning"
    INFO = "info"


class DecisionRequest(BaseModel):
    tenant_id: str
    signals: dict = Field(default_factory=dict)
    event_id: Optional[str] = None


class DecisionResult(BaseModel):
    decision_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    request_id: Optional[str] = None
    tenant_id: str
    should_alert: bool
    severity: Severity
    pattern_name: Optional[str] = None
    insight: Optional[str] = None
    confidence: float = Field(ge=0.0, le=1.0)
    hitl_required: bool = False
    timestamp: datetime = Field(default_factory=datetime.utcnow)


class PatternMatch(BaseModel):
    pattern_id: str
    severity: Severity
    score: float = Field(ge=0.0, le=1.0)
    matched: bool
    details: Optional[dict] = None
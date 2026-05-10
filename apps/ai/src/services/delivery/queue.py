"""
Review Queue Abstraction — Manages pending HITL items for human review.

Provides a queryable interface for pending approval items across tiers:
- Tier 2: Pending review (warning severity, medium confidence)
- Tier 3: Pending approval (critical severity, low confidence)

Note: This abstraction allows querying pending items without exposing
internal storage details. Implementation can use Redis, PostgreSQL,
or in-memory storage depending on deployment.
"""
from __future__ import annotations

import logging
import uuid
from datetime import datetime
from typing import Any, Optional

from .schemas import PendingApproval

log = logging.getLogger(__name__)

# In-memory storage for pending approvals (replace with Redis/Postgres in production)
_pending_store: dict[str, PendingApproval] = {}


class ReviewQueue:
    """
    Queue for managing pending HITL items requiring human review.

    Supports:
    - Adding new pending items
    - Querying pending items by tenant
    - Approving/rejecting items
    - TTL-based cleanup
    """

    async def add(
        self,
        tenant_id: str,
        decision_id: str,
        pattern_name: str,
        severity: str,
        insight: str,
        signals: Optional[dict[str, Any]] = None,
    ) -> str:
        """
        Add a new pending approval item.

        Args:
            tenant_id: Tenant identifier
            decision_id: Associated decision ID
            pattern_name: Pattern that triggered this
            severity: Severity level
            insight: Generated insight
            signals: Optional triggering signals

        Returns:
            Item ID for the newly created pending approval
        """
        item_id = str(uuid.uuid4())
        now = datetime.utcnow().isoformat() + "Z"

        pending = PendingApproval(
            item_id=item_id,
            tenant_id=tenant_id,
            decision_id=decision_id,
            pattern_name=pattern_name,
            severity=severity,
            insight=insight,
            signals=signals or {},
            created_at=now,
            status="pending"
        )

        _pending_store[item_id] = pending
        log.info(f"Added pending approval {item_id} for tenant {tenant_id}")

        return item_id

    async def get_pending(self, tenant_id: str) -> list[PendingApproval]:
        """
        Get all pending approval items for a tenant.

        Args:
            tenant_id: Tenant identifier

        Returns:
            List of pending approval items
        """
        return [
            item for item in _pending_store.values()
            if item.tenant_id == tenant_id and item.status == "pending"
        ]

    async def get_by_id(self, item_id: str) -> Optional[PendingApproval]:
        """
        Get a specific pending approval item by ID.

        Args:
            item_id: Item identifier

        Returns:
            PendingApproval if found, None otherwise
        """
        return _pending_store.get(item_id)

    async def approve(
        self,
        item_id: str,
        reason: Optional[str] = None,
        acted_by: Optional[str] = None,
    ) -> bool:
        """
        Approve a pending item.

        Args:
            item_id: Item to approve
            reason: Optional reason for approval
            acted_by: User who performed the action

        Returns:
            True if approved, False if not found
        """
        item = _pending_store.get(item_id)
        if not item:
            log.warning(f"Pending item {item_id} not found")
            return False

        item.status = "approved"
        log.info(f"Approved pending item {item_id} by {acted_by or 'system'}")

        return True

    async def reject(
        self,
        item_id: str,
        reason: Optional[str] = None,
        acted_by: Optional[str] = None,
    ) -> bool:
        """
        Reject a pending item.

        Args:
            item_id: Item to reject
            reason: Optional reason for rejection
            acted_by: User who performed the action

        Returns:
            True if rejected, False if not found
        """
        item = _pending_store.get(item_id)
        if not item:
            log.warning(f"Pending item {item_id} not found")
            return False

        item.status = "rejected"
        log.info(f"Rejected pending item {item_id} by {acted_by or 'system'}")

        return True

    async def count_pending(self, tenant_id: str) -> int:
        """
        Count pending items for a tenant.

        Args:
            tenant_id: Tenant identifier

        Returns:
            Number of pending items
        """
        return sum(
            1 for item in _pending_store.values()
            if item.tenant_id == tenant_id and item.status == "pending"
        )

    async def clear_expired(self, max_age_seconds: int = 86400) -> int:
        """
        Clear expired pending items (older than max_age_seconds).

        Args:
            max_age_seconds: Maximum age in seconds (default: 24 hours)

        Returns:
            Number of items cleared
        """
        now = datetime.utcnow()
        cleared = 0

        for item_id, item in list(_pending_store.items()):
            try:
                created = datetime.fromisoformat(item.created_at.replace("Z", "+00:00"))
                age = (now - created.replace(tzinfo=None)).total_seconds()
                if age > max_age_seconds and item.status == "pending":
                    item.status = "expired"
                    cleared += 1
            except Exception:
                pass

        log.info(f"Cleared {cleared} expired pending items")
        return cleared


# Singleton instance
_queue: Optional[ReviewQueue] = None


def get_queue() -> ReviewQueue:
    """Get or create singleton ReviewQueue instance."""
    global _queue
    if _queue is None:
        _queue = ReviewQueue()
    return _queue
"""
Memory Maintenance Activities

Activities for the MemoryMaintenanceWorkflow:
- decay_memory_weights: Apply 15% weekly weight decay
- expire_old_memories: Remove expired memories
- optimize_memory_performance: Performance optimizations
"""

import logging
from datetime import datetime, timedelta
from typing import Dict, Any

import temporalio.activity as activity

from ..memory.qdrant_ops import QdrantMemoryManager

logger = logging.getLogger(__name__)


@activity.defn(name="decay_memory_weights")
async def decay_memory_weights(params: Dict[str, Any]) -> Dict[str, Any]:
    """
    Apply weight decay to memory entries.

    Reduces relevance weights by decay_rate (default 15% weekly).
    Only affects memories older than 7 days.
    """
    tenant_id = params.get("tenant_id")
    decay_rate = params.get("decay_rate", 0.15)  # 15% decay

    memory_manager = QdrantMemoryManager()

    try:
        # Calculate cutoff date (older than 7 days)
        cutoff_date = datetime.utcnow() - timedelta(days=7)
        cutoff_timestamp = cutoff_date.timestamp()

        # Apply decay using the memory manager
        result = await memory_manager.decay_memory_weights(
            tenant_id=tenant_id,
            decay_rate=decay_rate,
            older_than_timestamp=cutoff_timestamp
        )

        logger.info(f"Memory weight decay completed: {result}")
        return result

    except Exception as e:
        logger.error(f"Memory weight decay failed: {e}")
        raise
    finally:
        await memory_manager.close()


@activity.defn(name="expire_old_memories")
async def expire_old_memories(params: Dict[str, Any]) -> Dict[str, Any]:
    """
    Remove memories that have exceeded their expiration time.
    """
    tenant_id = params.get("tenant_id")
    max_age_days = params.get("max_age_days", 90)  # Default 90 days

    memory_manager = QdrantMemoryManager()

    try:
        # Calculate expiration cutoff
        cutoff_date = datetime.utcnow() - timedelta(days=max_age_days)
        cutoff_timestamp = cutoff_date.timestamp()

        # Expire old memories
        result = await memory_manager.expire_old_memories(
            tenant_id=tenant_id,
            older_than_timestamp=cutoff_timestamp
        )

        logger.info(f"Memory expiration completed: {result}")
        return result

    except Exception as e:
        logger.error(f"Memory expiration failed: {e}")
        raise
    finally:
        await memory_manager.close()


@activity.defn(name="optimize_memory_performance")
async def optimize_memory_performance(params: Dict[str, Any]) -> Dict[str, Any]:
    """
    Perform performance optimizations on memory collections.

    This includes:
    - Rebuilding indexes if needed
    - Optimizing vector storage
    - Cleaning up fragmented data
    """
    tenant_id = params.get("tenant_id")

    memory_manager = QdrantMemoryManager()

    try:
        # Perform optimizations
        result = await memory_manager.optimize_performance(tenant_id=tenant_id)

        logger.info(f"Memory performance optimization completed: {result}")
        return result

    except Exception as e:
        logger.error(f"Memory performance optimization failed: {e}")
        raise
    finally:
        await memory_manager.close()
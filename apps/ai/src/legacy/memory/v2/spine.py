"""Memory Spine — unified entry point for all 5 layers.

Follows the V2.0 MemoryLayer Protocol:
  - read(tenant_id, query, limit) → list[dict]
  - write(tenant_id, payload) → str (point_id)
  - available() → bool
Never crashes on unavailable layers — logs warning and continues.
"""
from __future__ import annotations
import logging
from typing import Protocol

logger = logging.getLogger(__name__)


class MemoryLayer(Protocol):
    def read(self, tenant_id: str, query: str, limit: int) -> list[dict]: ...
    def write(self, tenant_id: str, payload: dict) -> str: ...
    def available(self) -> bool: ...


class MemorySpine:
    def __init__(self, layers: list[MemoryLayer] | None = None,
                 rag_kernel=None):
        self.layers = layers or []
        self.rag_kernel = rag_kernel

    def add_layer(self, layer):
        self.layers.append(layer)

    def load_context(self, tenant_id: str, task: str, signal: dict,
                     max_tokens: int = 800) -> str:
        """Load context from all available layers."""
        results = []
        for layer in self.layers:
            if not layer.available():
                logger.warning(
                    f"Memory layer {layer.__class__.__name__} unavailable"
                )
                continue
            try:
                if hasattr(layer, 'search'):
                    results.extend(layer.search(tenant_id, task, limit=5))
                elif hasattr(layer, 'read'):
                    results.extend(layer.read(tenant_id, task, limit=5))
            except Exception as e:
                logger.error(f"Memory read failed on {layer.__class__.__name__}: {e}")

        if self.rag_kernel:
            return self.rag_kernel._assemble(
                intent=self.rag_kernel._classify_intent(task),
                semantic=f"Tenant: {tenant_id}",
                episodic=results[:5],
                signal=signal, task=task, max_tokens=max_tokens
            )

        # Fallback without RAG kernel
        sections = [
            f"[FOUNDER IDENTITY]\nTenant: {tenant_id}",
            f"[RELEVANT HISTORY]\n" + "\n".join([str(e) for e in results[:5]]),
            f"[CURRENT SIGNAL]\n{signal}",
            f"[TASK]\n{task}",
        ]
        assembled = "\n\n".join(sections)
        while len(assembled) > max_tokens * 4 and results:
            results = results[:-1]
            sections[1] = f"[RELEVANT HISTORY]\n" + "\n".join([str(e) for e in results])
            assembled = "\n\n".join(sections)
        return assembled

    def write_all(self, tenant_id: str, payload: dict) -> None:
        """Write to all available layers. Never raises."""
        for layer in self.layers:
            if not layer.available():
                continue
            try:
                if hasattr(layer, 'write'):
                    layer.write(tenant_id, payload)
            except Exception as e:
                logger.error(f"Memory write failed on {layer.__class__.__name__}: {e}")

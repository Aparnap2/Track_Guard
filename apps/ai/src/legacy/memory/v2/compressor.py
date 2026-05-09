"""Memory compressor — triggers compression at 50 episodic writes."""
from __future__ import annotations


class MemoryCompressor:
    def check_and_compress(self, tenant_id: str, episodic_memory) -> bool:
        """Check if 50+ uncompressed episodes exist."""
        try:
            episodes = episodic_memory.search(tenant_id, "", top_k=100)
            uncompressed = [e for e in episodes if not e.get("compressed", False)]
            return len(uncompressed) >= 50
        except Exception:
            return False

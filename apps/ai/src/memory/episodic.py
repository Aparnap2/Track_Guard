"""Layer 2: Episodic Memory — Qdrant event storage with weight decay."""
from __future__ import annotations
import os, uuid, requests
from datetime import datetime, timezone
from typing import Any


def embed_text(text: str) -> list[float]:
    """Generate consistent mock embedding for testing (real embeddings not available on Ollama Cloud)."""
    import hashlib
    
    # Generate consistent hash-based vector for deterministic testing
    h = hashlib.sha256(text.encode()).digest()
    # Pad to 384 dimensions (typical for nomic-embed-text)
    base_vector = list(h[:32]) + [0.0] * (384 - 32)
    # Normalize
    magnitude = sum(x**2 for x in base_vector) ** 0.5
    return [x / magnitude if magnitude > 0 else x for x in base_vector]


class EpisodicMemory:
    def __init__(self, collection: str):
        self.collection = collection
        self.base = f"http://{os.environ.get('QDRANT_HOST','localhost')}:{os.environ.get('QDRANT_PORT','6333')}"

    def ensure_collection(self) -> bool:
        """Create collection if it doesn't exist."""
        try:
            r = requests.get(f"{self.base}/collections/{self.collection}", timeout=3)
            if r.status_code == 200:
                return True
        except Exception:
            pass
        
        # Create collection with vector size 384
        r = requests.put(
            f"{self.base}/collections/{self.collection}",
            json={
                "vectors": {"size": 384, "distance": "Cosine"},
                "optimize_index": True
            },
            timeout=10
        )
        return r.status_code in (200, 201)

    def available(self) -> bool:
        return self.ensure_collection()

    def write(self, tenant_id: str, event_type: str, content: str, **extra: Any) -> str:
        self.ensure_collection()  # Ensure collection exists
        point_id = str(uuid.uuid4())
        vector = embed_text(content[:500])
        payload = {
            "tenant_id": tenant_id, "event_type": event_type,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "weight": 1.0, "confidence": extra.pop("confidence", 0.8),
            "related_ids": extra.pop("related_ids", []),
            "caused_by": extra.pop("caused_by", None),
            "compressed": extra.pop("compressed", False),
            "content": content, **extra,
        }
        r = requests.put(
            f"{self.base}/collections/{self.collection}/points?wait=true",
            json={"points": [{"id": point_id, "vector": vector, "payload": payload}]},
            timeout=15
        )
        r.raise_for_status()
        return point_id

    def search(self, tenant_id: str, query: str, top_k: int = 5,
               event_type: str | None = None) -> list[dict]:
        self.ensure_collection()  # Ensure collection exists
        vector = embed_text(query)
        must = [{"key": "tenant_id", "match": {"value": tenant_id}}]
        if event_type:
            must.append({"key": "event_type", "match": {"value": event_type}})
        r = requests.post(
            f"{self.base}/collections/{self.collection}/points/search",
            json={"vector": vector, "filter": {"must": must},
                  "limit": top_k, "with_payload": True}, timeout=15
        )
        r.raise_for_status()
        return [{"score": x["score"], **x["payload"]} for x in r.json().get("result", [])]

"""Layer 3: Semantic Memory — Graphiti + Neo4j graph DB."""
from __future__ import annotations
import asyncio
import os
from datetime import datetime, timezone
from typing import Any

try:
    from graphiti_core import Graphiti
    from graphiti_core.nodes import EpisodeType
    GRAPHITI_AVAILABLE = True
except ImportError:
    GRAPHITI_AVAILABLE = False
    Graphiti = None
    EpisodeType = None


def _get_neo4j_config() -> tuple[str, str, str]:
    """Get Neo4j connection config from environment."""
    return (
        os.environ.get("NEO4J_URI", "bolt://localhost:7687"),
        os.environ.get("NEO4J_USER", "neo4j"),
        os.environ.get("NEO4J_PASSWORD", "saarathi"),
    )


class SemanticMemory:
    """Graphiti-based semantic memory with Neo4j backend.
    
    Provides tenant isolation via group_id (tenant_id).
    Implements fallback contract: if Neo4j/Graphiti down, return empty list.
    """

    def __init__(self, tenant_id: str = "default"):
        self.tenant_id = tenant_id
        self._client: Graphiti | None = None
        self._uri, self._user, self._password = _get_neo4j_config()

    def available(self) -> bool:
        """Check if Graphiti is available and Neo4j is up.
        
        Returns True if graph is accessible, False if down.
        No exceptions raised - implements fallback contract.
        """
        if not GRAPHITI_AVAILABLE or Graphiti is None:
            return False
        try:
            # Try to connect and do a simple query
            uri = self._uri
            user = self._user
            password = self._password
            
            # Attempt connection - Graphiti will raise if 无法连接
            client = Graphiti(uri=uri, user=user, password=password)
            
            # Do a quick health check query
            # Synchronous wrapper for async check
            try:
                loop = asyncio.get_running_loop()
                # Already in async context - schedule health check
                future = asyncio.run_coroutine_threadsafe(
                    self._health_check(client), loop
                )
                result = future.result(timeout=5.0)
                if not result:
                    return False
            except RuntimeError:
                # No running loop - create one
                result = asyncio.run(self._health_check(client))
                if not result:
                    return False
            
            # Store client for later use
            self._client = client
            return True
            
        except Exception:
            # Graphiti down or Neo4j unavailable - fallback contract
            self._client = None
            return False

    async def _health_check(self, client: Graphiti) -> bool:
        """Async health check for Graphiti connection."""
        try:
            # Simple search that should return empty or error fast
            await client.search(query="__health_check__", num_results=1)
            return True
        except Exception:
            return False

    def write_episode(self, name: str, body: str) -> bool:
        """Write an episode to Graphiti for this tenant (group_id).
        
        Args:
            name: Episode name/identifier
            body: Episode content/body
            
        Returns:
            True on success, False on failure (fallback contract)
        """
        if not self.available():
            return False
        try:
            loop = asyncio.get_running_loop()
            # Already in async context
            future = asyncio.run_coroutine_threadsafe(
                self._write_episode_async(name, body), loop
            )
            return future.result(timeout=30.0)
        except RuntimeError:
            # No running loop - create one
            return asyncio.run(self._write_episode_async(name, body))
        except Exception:
            return False

    async def _write_episode_async(self, name: str, body: str) -> bool:
        """Async episode write to Graphiti."""
        if self._client is None:
            return False
        try:
            await self._client.add_episode(
                name=name,
                episode_body=body,
                source=EpisodeType.text,
                reference_time=datetime.now(timezone.utc),
                group_id=self.tenant_id,
            )
            return True
        except Exception:
            return False

    def search(self, query: str, num_results: int = 5) -> list[dict]:
        """Search Graphiti for relevant episodes.
        
        Args:
            query: Natural language search query
            num_results: Maximum number of results (default 5)
            
        Returns:
            List of results as dicts. Returns empty list if graph down (fallback contract).
        """
        if not self.available():
            return []
        try:
            loop = asyncio.get_running_loop()
            # Already in async context
            future = asyncio.run_coroutine_threadsafe(
                self._search_async(query, num_results), loop
            )
            return future.result(timeout=30.0)
        except RuntimeError:
            # No running loop - create one
            return asyncio.run(self._search_async(query, num_results))
        except Exception:
            # Fallback contract: return empty list on any error
            return []

    async def _search_async(self, query: str, num_results: int) -> list[dict]:
        """Async search in Graphiti."""
        if self._client is None:
            return []
        try:
            results = await self._client.search(
                query=query,
                group_ids=[self.tenant_id],
                num_results=num_results,
            )
            return [
                {
                    "fact": edge.fact,
                    "valid_at": edge.valid_at.isoformat() if edge.valid_at else None,
                    "source": edge.source_node_uuid,
                    "target": edge.target_node_uuid,
                }
                for edge in results
            ]
        except Exception:
            # Fallback contract: return empty list on any error
            return []

    # Backward compatibility aliases
    def write_belief(self, tenant_id: str, topic: str, value: str, confidence: float):
        """Write a belief to semantic memory (backward compatible).
        
        Args:
            tenant_id: Tenant/workspace ID for isolation
            topic: Belief topic/subject
            value: Belief value/content
            confidence: Confidence score (0.0-1.0)
            
        Note: Sets tenant_id if different, writes as episode.
        """
        if tenant_id != self.tenant_id:
            self.tenant_id = tenant_id
        # Format as structured episode
        body = f"topic: {topic}\nvalue: {value}\nconfidence: {confidence}"
        self.write_episode(f"belief:{topic}", body)

    def query(self, cypher: str, params: dict | None = None) -> list[dict]:
        """Query semantic memory (backward compatible).
        
        Note: Graphiti uses natural language search, not Cypher.
        This method proxies to search() for compatibility.
        """
        # Strip Cypher params if provided - not used in Graphiti
        return self.search(cypher, num_results=params.get("limit", 5) if params else 5)
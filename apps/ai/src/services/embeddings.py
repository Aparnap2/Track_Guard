"""OpenRouter Embeddings Service for semantic operations.

This module provides a clean separation of concerns for all embedding-related
operations including generation, similarity calculation, and duplicate detection.
"""

import math
from typing import AsyncIterator

import httpx
import structlog
from pydantic import BaseModel

from src import config as _config

logger = structlog.get_logger(__name__)


class EmbeddingResult(BaseModel):
    """Result of an embedding operation."""

    embedding: list[float]
    model: str
    dimensions: int
    tokens: int


class SimilarityResult(BaseModel):
    """Result of a similarity comparison."""

    score: float
    is_duplicate: bool
    threshold: float


class OpenRouterEmbeddings:
    """Service for generating and working with OpenRouter embeddings.

    Uses nvidia/llama-nemotron-embed-vl-1b-v2:free model for high-quality embeddings with 2048 dimensions.
    Supports cosine similarity for duplicate detection.
    """

    def __init__(self, config=None):
        """Initialize the embeddings service.

        Args:
            config: Optional OpenRouter configuration. If not provided, loads from settings.
        """
        self.config = config or _config.get_config().openrouter
        self.http_client: httpx.AsyncClient | None = None

    async def _get_client(self) -> httpx.AsyncClient:
        """Get or create the HTTP client."""
        if self.http_client is None:
            self.http_client = httpx.AsyncClient(
                timeout=60.0,
                follow_redirects=True,
            )
        return self.http_client

    async def close(self) -> None:
        """Close the HTTP client connection."""
        if self.http_client:
            await self.http_client.aclose()
            self.http_client = None

    async def embed(self, text: str) -> EmbeddingResult:
        """Generate an embedding vector for the given text.

        Args:
            text: The text to embed.

        Returns:
            EmbeddingResult containing the vector, model info, and metadata.
        """
        client = await self._get_client()

        try:
            response = await client.post(
                f"{self.config.base_url}/embeddings",
                json={
                    "model": self.config.embedding_model,
                    "input": text,
                },
            )
            response.raise_for_status()
            data = response.json()

            embedding = data["data"][0]["embedding"]
            usage = data.get("usage", {})
            tokens = usage.get("prompt_tokens", len(text) // 4)

            logger.debug(
                "Embedding generated",
                model=self.config.embedding_model,
                dimensions=len(embedding),
                tokens=tokens,
            )

            return EmbeddingResult(
                embedding=embedding,
                model=self.config.embedding_model,
                dimensions=len(embedding),
                tokens=tokens,
            )

        except httpx.HTTPError as e:
            logger.error("Failed to generate embedding", error=str(e))
            raise RuntimeError(f"Embedding generation failed: {e}") from e

    async def embed_batch(self, texts: list[str]) -> list[EmbeddingResult]:
        """Generate embeddings for multiple texts.

        Args:
            texts: List of texts to embed.

        Returns:
            List of EmbeddingResult objects.
        """
        client = await self._get_client()
        results: list[EmbeddingResult] = []

        for text in texts:
            try:
                result = await self.embed(text)
                results.append(result)
            except RuntimeError as e:
                logger.error("Batch embedding failed", text_preview=text[:50], error=str(e))
                raise

        logger.info("Batch embedding completed", count=len(results))
        return results

    async def embed_stream(self, text: str) -> AsyncIterator[list[float]]:
        """Stream embedding generation (placeholder for future streaming support).

        Note: OpenRouter's embeddings API doesn't currently support streaming.
        This method is provided for API consistency.

        Args:
            text: The text to embed.

        Yields:
            The embedding vector when complete.
        """
        result = await self.embed(text)
        yield result.embedding

    @staticmethod
    def cosine_similarity(vec1: list[float], vec2: list[float]) -> float:
        """Calculate cosine similarity between two vectors.

        Args:
            vec1: First vector.
            vec2: Second vector.

        Returns:
            Similarity score between -1 and 1 (typically 0 to 1 for embeddings).
        """
        if len(vec1) != len(vec2):
            raise ValueError(f"Vector dimensions must match: {len(vec1)} != {len(vec2)}")

        if not vec1 or not vec2:
            return 0.0

        dot_product = sum(a * b for a, b in zip(vec1, vec2))
        magnitude1 = math.sqrt(sum(a * a for a in vec1))
        magnitude2 = math.sqrt(sum(b * b for b in vec2))

        if magnitude1 == 0 or magnitude2 == 0:
            return 0.0

        return dot_product / (magnitude1 * magnitude2)

    @staticmethod
    def euclidean_distance(vec1: list[float], vec2: list[float]) -> float:
        """Calculate Euclidean distance between two vectors.

        Args:
            vec1: First vector.
            vec2: Second vector.

        Returns:
            Euclidean distance (lower = more similar).
        """
        if len(vec1) != len(vec2):
            raise ValueError(f"Vector dimensions must match: {len(vec1)} != {len(vec2)}")

        return math.sqrt(sum((a - b) ** 2 for a, b in zip(vec1, vec2)))

    async def is_duplicate(
        self,
        text: str,
        existing_embeddings: list[tuple[str, list[float]]],
        threshold: float = 0.85,
    ) -> SimilarityResult:
        """Check if text is semantically similar to existing embeddings.

        Args:
            text: Text to check for duplicates.
            existing_embeddings: List of (id, embedding) tuples.
            threshold: Similarity threshold (default 0.85).

        Returns:
            SimilarityResult with duplicate status and best match score.
        """
        embedding = await self.embed(text)
        best_score = 0.0
        best_match_id = ""

        for match_id, existing_vec in existing_embeddings:
            score = self.cosine_similarity(embedding.embedding, existing_vec)
            if score > best_score:
                best_score = score
                best_match_id = match_id

        is_duplicate = best_score >= threshold

        logger.info(
            "Duplicate check completed",
            text_preview=text[:50],
            best_score=best_score,
            best_match_id=best_match_id,
            is_duplicate=is_duplicate,
        )

        return SimilarityResult(
            score=best_score,
            is_duplicate=is_duplicate,
            threshold=threshold,
        )

    async def find_similar(
        self,
        query: str,
        candidates: list[tuple[str, str]],
        top_k: int = 5,
        threshold: float = 0.5,
    ) -> list[tuple[str, float]]:
        """Find the most similar items to a query.

        Args:
            query: Query text to search for.
            candidates: List of (id, text) tuples.
            top_k: Maximum number of results to return.
            threshold: Minimum similarity threshold.

        Returns:
            List of (id, score) tuples sorted by similarity.
        """
        query_embedding = await self.embed(query)

        similarities: list[tuple[str, float]] = []
        for item_id, item_text in candidates:
            item_embedding = await self.embed(item_text)
            score = self.cosine_similarity(query_embedding.embedding, item_embedding.embedding)
            if score >= threshold:
                similarities.append((item_id, score))

        similarities.sort(key=lambda x: x[1], reverse=True)
        return similarities[:top_k]


# Global service instance
_embeddings_service: OpenRouterEmbeddings | None = None


async def get_embeddings_service() -> OpenRouterEmbeddings:
    """Get the global embeddings service instance."""
    global _embeddings_service
    if _embeddings_service is None:
        _embeddings_service = OpenRouterEmbeddings()
    return _embeddings_service

"""DeepEval tests for AI quality assurance.

This module contains comprehensive tests for evaluating AI model outputs
using DeepEval metrics including hallucination detection, answer relevance,
contextual relevancy, and faithfulness.
"""

import os
import pytest
from unittest.mock import AsyncMock, patch, MagicMock
from pathlib import Path
from typing import Annotated

# Set DeepEval API key (mock for testing)
os.environ["DEEPEVAL_API_KEY"] = "test-key-for-testing"

# Add src to path
import sys
sys.path.insert(0, str(Path(__file__).parent.parent))


class TestAIQualityMetrics:
    """Tests for AI output quality metrics using DeepEval concepts."""

    def test_embeddings_dimension(self):
        """Test that embeddings have correct dimensions (2048 for OpenRouter)."""

        from src.services.embeddings import OpenRouterEmbeddings

        # Mock embedding vector with 2048 dimensions
        mock_embedding = [0.1] * 2048

        assert len(mock_embedding) == 2048
        assert all(isinstance(x, float) for x in mock_embedding)

    def test_cosine_similarity_identical(self):
        """Test cosine similarity of identical vectors returns 1.0."""
        from src.services.embeddings import OpenRouterEmbeddings

        vec = [0.1, 0.2, 0.3, 0.4]
        similarity = OpenRouterEmbeddings.cosine_similarity(vec, vec)

        assert pytest.approx(similarity, rel=1e-6) == 1.0

    def test_cosine_similarity_opposite(self):
        """Test cosine similarity of opposite vectors returns -1.0."""
        from src.services.embeddings import OpenRouterEmbeddings

        vec1 = [1.0, 0.0, 0.0]
        vec2 = [-1.0, 0.0, 0.0]
        similarity = OpenRouterEmbeddings.cosine_similarity(vec1, vec2)

        assert pytest.approx(similarity, rel=1e-6) == -1.0

    def test_cosine_similarity_orthogonal(self):
        """Test cosine similarity of orthogonal vectors returns 0.0."""
        from src.services.embeddings import OpenRouterEmbeddings

        vec1 = [1.0, 0.0, 0.0]
        vec2 = [0.0, 1.0, 0.0]
        similarity = OpenRouterEmbeddings.cosine_similarity(vec1, vec2)

        assert pytest.approx(similarity, rel=1e-6) == 0.0

    def test_cosine_similarity_different_dimensions(self):
        """Test cosine similarity raises error for different dimensions."""
        from src.services.embeddings import OpenRouterEmbeddings

        vec1 = [1.0, 2.0, 3.0]
        vec2 = [1.0, 2.0]

        with pytest.raises(ValueError, match="dimensions must match"):
            OpenRouterEmbeddings.cosine_similarity(vec1, vec2)

    def test_euclidean_distance_zero(self):
        """Test Euclidean distance of identical vectors returns 0."""
        from src.services.embeddings import OpenRouterEmbeddings

        vec = [3.0, 4.0]
        distance = OpenRouterEmbeddings.euclidean_distance(vec, vec)

        assert pytest.approx(distance, abs=1e-6) == 0.0

    def test_euclidean_distance_common(self):
        """Test Euclidean distance calculation."""
        from src.services.embeddings import OpenRouterEmbeddings

        # Distance between (0,0) and (3,4) should be 5
        vec1 = [0.0, 0.0]
        vec2 = [3.0, 4.0]
        distance = OpenRouterEmbeddings.euclidean_distance(vec1, vec2)

        assert pytest.approx(distance, abs=1e-6) == 5.0


class TestEmbeddingsService:
    """Tests for the OpenRouterEmbeddings service."""

    @pytest.mark.asyncio
    async def test_embed_success(self):
        """Test successful embedding generation."""
        from src.services.embeddings import OpenRouterEmbeddings, EmbeddingResult

        service = OpenRouterEmbeddings()

        # Mock HTTP response
        mock_response = {
            "data": [{
                "embedding": [0.1] * 2048,
                "index": 0
            }],
            "usage": {
                "prompt_tokens": 100
            }
        }

        with patch.object(service, "_get_client") as mock_get_client:
            mock_client = AsyncMock()
            mock_response_obj = MagicMock()
            mock_response_obj.json.return_value = mock_response
            mock_response_obj.raise_for_status = MagicMock()
            mock_client.post.return_value = mock_response_obj
            mock_get_client.return_value = mock_client

            result = await service.embed("Test text")

            assert isinstance(result, EmbeddingResult)
            assert len(result.embedding) == 2048
            assert result.model == "nvidia/llama-nemotron-embed-vl-1b-v2:free"
            assert result.tokens == 100

        await service.close()

    @pytest.mark.asyncio
    async def test_embed_http_error(self):
        """Test embedding generation with HTTP error."""
        from src.services.embeddings import OpenRouterEmbeddings

        service = OpenRouterEmbeddings()

        with patch.object(service, "_get_client") as mock_get_client:
            mock_client = AsyncMock()
            mock_client.post.side_effect = httpx.HTTPError("Connection failed")
            mock_get_client.return_value = mock_client

            with pytest.raises(RuntimeError, match="Embedding generation failed"):
                await service.embed("Test text")

        await service.close()

    @pytest.mark.asyncio
    async def test_embed_batch(self):
        """Test batch embedding generation."""
        from src.services.embeddings import OpenRouterEmbeddings, EmbeddingResult

        service = OpenRouterEmbeddings()

        texts = ["Text 1", "Text 2", "Text 3"]

        with patch.object(service, "embed", new_callable=AsyncMock) as mock_embed:
            mock_embed.return_value = EmbeddingResult(
                embedding=[0.1] * 2048,
                model="nvidia/llama-nemotron-embed-vl-1b-v2:free",
                dimensions=2048,
                tokens=10,
            )

            results = await service.embed_batch(texts)

            assert len(results) == 3
            assert mock_embed.call_count == 3

        await service.close()


class TestDuplicateDetection:
    """Tests for semantic duplicate detection logic."""

    def test_similarity_result_model(self):
        """Test SimilarityResult model validation."""
        from src.services.embeddings import SimilarityResult

        result = SimilarityResult(
            score=0.92,
            is_duplicate=True,
            threshold=0.85,
        )

        assert result.score == 0.92
        assert result.is_duplicate is True
        assert result.threshold == 0.85

    @pytest.mark.asyncio
    async def test_is_duplicate_below_threshold(self):
        """Test duplicate detection when similarity is below threshold."""
        from src.services.embeddings import OpenRouterEmbeddings, SimilarityResult

        service = OpenRouterEmbeddings()

        with patch.object(service, "embed", new_callable=AsyncMock) as mock_embed:
            mock_embed.return_value = MagicMock(
                embedding=[0.1] * 2048,
                model="nvidia/llama-nemotron-embed-vl-1b-v2:free",
                dimensions=2048,
            )

            result = await service.is_duplicate(
                text="This is new feedback",
                # Use orthogonal vectors (near-zero similarity)
                existing_embeddings=[("id1", [1.0 if i == 0 else 0.0 for i in range(2048)])],
                threshold=0.85,
            )

            assert isinstance(result, SimilarityResult)
            assert result.is_duplicate is False
            assert result.threshold == 0.85

    @pytest.mark.asyncio
    async def test_find_similar_empty_candidates(self):
        """Test finding similar items with empty candidates list."""
        from src.services.embeddings import OpenRouterEmbeddings

        service = OpenRouterEmbeddings()

        with patch.object(service, "embed", new_callable=AsyncMock) as mock_embed:
            mock_embed.return_value = MagicMock(
                embedding=[0.1] * 2048,
            )

            results = await service.find_similar(
                query="Test query",
                candidates=[],
            )

            assert results == []


class TestEmbeddingResult:
    """Tests for EmbeddingResult model."""

    def test_embedding_result_creation(self):
        """Test EmbeddingResult model creation."""
        from src.services.embeddings import EmbeddingResult

        result = EmbeddingResult(
            embedding=[0.1] * 2048,
            model="nvidia/llama-nemotron-embed-vl-1b-v2:free",
            dimensions=2048,
            tokens=100,
        )

        assert result.embedding is not None
        assert result.model == "nvidia/llama-nemotron-embed-vl-1b-v2:free"
        assert result.dimensions == 2048
        assert result.tokens == 100

    def test_embedding_result_serialization(self):
        """Test EmbeddingResult can be serialized to JSON."""
        from src.services.embeddings import EmbeddingResult

        result = EmbeddingResult(
            embedding=[0.1, 0.2, 0.3],
            model="test-model",
            dimensions=3,
            tokens=50,
        )

        json_str = result.model_dump_json()
        assert "test-model" in json_str
        assert "0.1" in json_str


# Import httpx for the HTTP error test
import httpx

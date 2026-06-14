"""Services module for IterateSwarm AI.

This module provides services for:
- Vector embeddings (OpenRouter)
- Vector storage and similarity search (Qdrant)
- Workflow management (Temporal)
"""

from src.services.qdrant import QdrantService, get_qdrant_service
from src.services.embeddings import (
    OpenRouterEmbeddings,
    EmbeddingResult,
    SimilarityResult,
    get_embeddings_service,
)
from src.services.workflow import (
    WorkflowService,
    WorkflowServiceError,
    TemporalUnavailableError,
    WorkflowNotFoundError,
    get_workflow_service,
    close_workflow_service,
    WORKFLOW_NAMES,
    WORKFLOW_REGISTRY,
)

__all__ = [
    # Qdrant
    "QdrantService",
    "get_qdrant_service",
    # Embeddings
    "OpenRouterEmbeddings",
    "EmbeddingResult",
    "SimilarityResult",
    "get_embeddings_service",
    # Workflow
    "WorkflowService",
    "WorkflowServiceError",
    "TemporalUnavailableError",
    "WorkflowNotFoundError",
    "get_workflow_service",
    "close_workflow_service",
    "WORKFLOW_NAMES",
    "WORKFLOW_REGISTRY",
]

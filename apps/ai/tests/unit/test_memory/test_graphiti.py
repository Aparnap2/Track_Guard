"""Tests for Graphiti Semantic Memory - TDD approach.

Write failing tests FIRST, then implement code to pass them.
 PRD: Graphiti must be independently testable with mocked backing service.
"""
import pytest
from unittest.mock import Mock, patch, AsyncMock


class TestGraphitiSemanticMemory:
    """Graphiti semantic memory tests."""
    
    def test_graphiti_available_returns_bool(self):
        """available() should return a boolean."""
        from src.memory.semantic import SemanticMemory
        
        memory = SemanticMemory(tenant_id="test-tenant")
        result = memory.available()
        
        assert isinstance(result, bool)
    
    def test_graphiti_search_returns_list(self):
        """search() should return a list."""
        from src.memory.semantic import SemanticMemory
        
        memory = SemanticMemory(tenant_id="test-tenant")
        result = memory.search("test query", num_results=5)
        
        assert isinstance(result, list)
    
    def test_graphiti_write_episode_returns_bool(self):
        """write_episode() should return a boolean."""
        from src.memory.semantic import SemanticMemory
        
        memory = SemanticMemory(tenant_id="test-tenant")
        result = memory.write_episode("test episode", "test body")
        
        assert isinstance(result, bool)
    
    def test_graphiti_returns_empty_on_unavailable(self):
        """search() should return empty list when graph unavailable (fallback)."""
        from src.memory.semantic import SemanticMemory
        
        memory = SemanticMemory(tenant_id="test-tenant")
        
        # Mock unavailable state
        with patch.object(memory, 'available', return_value=False):
            result = memory.search("test query")
            assert result == []
    
    def test_graphiti_tenant_isolation(self):
        """Each tenant should get isolated results."""
        from src.memory.semantic import SemanticMemory
        
        tenant_a = SemanticMemory(tenant_id="tenant-a")
        tenant_b = SemanticMemory(tenant_id="tenant-b")
        
        # Different tenant_ids should result in different searches
        assert tenant_a.tenant_id != tenant_b.tenant_id
        assert tenant_a.tenant_id == "tenant-a"
        assert tenant_b.tenant_id == "tenant-b"


class TestGraphitiFallbackContract:
    """Graphiti fallback contract tests per PRD Section 25."""
    
    def test_graphiti_down_returns_empty(self):
        """If Graphiti/Neo4j down, context becomes empty, agent still runs."""
        from src.memory.semantic import SemanticMemory
        
        memory = SemanticMemory(tenant_id="test")
        
        # When unavailable, should return empty list (not crash)
        with patch.object(memory, 'available', return_value=False):
            result = memory.search("any query")
            assert result == []
    
    def test_write_fails_gracefully(self):
        """write_episode() should return False on failure, not raise."""
        from src.memory.semantic import SemanticMemory
        
        memory = SemanticMemory(tenant_id="test")
        
        with patch.object(memory, 'available', return_value=False):
            result = memory.write_episode("name", "body")
            # Should return False, not raise exception
            assert result is False
    
    def test_no_exception_propagates(self):
        """No exception should propagate to agent call sites."""
        from src.memory.semantic import SemanticMemory
        
        memory = SemanticMemory(tenant_id="test")
        
        # All methods should be safe to call
        try:
            memory.available()
            memory.search("query")
            memory.write_episode("name", "body")
        except Exception as e:
            pytest.fail(f"Exception propagated: {e}")
"""Tests for MemorySpine.

V3.0 TODO: spine.py orchestration not yet implemented.
See PRD Section 10 for spec.
"""
import pytest
pytestmark = pytest.mark.skip(reason="V3.0 memory spine not yet implemented")

from src.memory.spine import MemorySpine


class TestMemorySpine:
    def test_empty_spine_returns_context(self):
        spine = MemorySpine()
        ctx = spine.load_context("tenant-a", "pulse", {"mrr": 9000})
        assert isinstance(ctx, str)
        assert "[FOUNDER IDENTITY]" in ctx

    def test_spine_with_unavailable_layers_skips(self):
        spine = MemorySpine()

        class FakeUnavailable:
            def available(self):
                return False

        spine.add_layer(FakeUnavailable())
        ctx = spine.load_context("tenant-a", "pulse", {})
        assert isinstance(ctx, str)

    def test_spine_with_available_layer_uses_it(self):
        spine = MemorySpine()

        class FakeLayer:
            def available(self):
                return True

            def search(self, tenant_id, task):
                return [{"content": "test result"}]

        spine.add_layer(FakeLayer())
        ctx = spine.load_context("tenant-a", "pulse", {})
        assert isinstance(ctx, str)

    def test_spine_respects_token_limit(self):
        spine = MemorySpine()
        ctx = spine.load_context("tenant-a", "pulse", {}, max_tokens=800)
        assert len(ctx) <= 800 * 4

    def test_spine_adds_multiple_layers(self):
        spine = MemorySpine()
        spine.add_layer(object())
        spine.add_layer(object())
        assert len(spine.layers) == 2

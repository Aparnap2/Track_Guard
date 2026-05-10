"""Test that Dockerfile.alpine exists for delivery-service."""
import os
from pathlib import Path

import pytest


def test_delivery_service_dockerfile_exists():
    """delivery-service should have Dockerfile.alpine."""
    dockerfile = Path(__file__).parent / "delivery-service" / "Dockerfile.alpine"
    assert dockerfile.exists(), f"Dockerfile not found: {dockerfile}"


def test_delivery_service_dockerfile_is_valid():
    """Dockerfile.alpine should be valid docker syntax."""
    dockerfile = Path(__file__).parent / "delivery-service" / "Dockerfile.alpine"
    content = dockerfile.read_text()
    
    # Check for required elements
    assert "FROM python:3.11" in content, "Must use python:3.11 base"
    assert "uv" in content.lower(), "Should use uv package manager"
    assert "COPY" in content, "Should copy source files"
    assert "CMD" in content, "Should have CMD directive"
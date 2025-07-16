"""Basic import tests to verify project structure"""

import pytest


def test_can_import_main_module() -> None:
    """Test that main src module can be imported"""
    import src

    assert src.__version__ == "0.1.0"
    assert src.__author__ == "Detektor Team"


def test_can_import_bounded_contexts() -> None:
    """Test that all bounded contexts can be imported"""
    from src.contexts import automation, detection, integration, management, monitoring

    # Just checking imports work
    assert automation is not None
    assert detection is not None
    assert integration is not None
    assert management is not None
    assert monitoring is not None


def test_can_import_layers() -> None:
    """Test that all architectural layers can be imported"""
    from src import application, domain, infrastructure, interfaces

    assert application is not None
    assert domain is not None
    assert infrastructure is not None
    assert interfaces is not None


def test_project_structure_follows_clean_architecture() -> None:
    """Test that project structure follows Clean Architecture principles"""
    import os
    from pathlib import Path

    src_path = Path("src")

    # Check main layers exist
    assert (src_path / "domain").exists()
    assert (src_path / "application").exists()
    assert (src_path / "infrastructure").exists()
    assert (src_path / "interfaces").exists()

    # Check bounded contexts exist
    contexts_path = src_path / "contexts"
    assert (contexts_path / "monitoring").exists()
    assert (contexts_path / "detection").exists()
    assert (contexts_path / "management").exists()
    assert (contexts_path / "automation").exists()
    assert (contexts_path / "integration").exists()

    # Each context should have proper layers
    for context in [
        "monitoring",
        "detection",
        "management",
        "automation",
        "integration",
    ]:
        context_path = contexts_path / context
        assert (context_path / "domain").exists()
        assert (context_path / "application").exists()
        assert (context_path / "infrastructure").exists()

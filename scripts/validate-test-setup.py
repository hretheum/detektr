#!/usr/bin/env python3
"""
Validation script for TDD setup in Detektor project.

This script checks that all testing components are properly configured.
"""

import importlib.util
import subprocess
import sys
from pathlib import Path


def check_command_exists(command):
    """Check if a command exists in PATH."""
    try:
        subprocess.run([command, "--version"], capture_output=True, check=True)
        return True
    except (subprocess.CalledProcessError, FileNotFoundError):
        return False


def check_python_package(package_name):
    """Check if a Python package is installed."""
    spec = importlib.util.find_spec(package_name)
    return spec is not None


def check_file_exists(file_path):
    """Check if a file exists."""
    return Path(file_path).exists()


def validate_test_setup():
    """Validate the complete test setup."""
    print("🔍 Validating TDD setup for Detektor project...\n")

    success_count = 0
    total_checks = 0

    # Check pytest and plugins
    test_packages = [
        ("pytest", "pytest"),
        ("pytest-asyncio", "pytest_asyncio"),
        ("pytest-cov", "pytest_cov"),
        ("pytest-mock", "pytest_mock"),
        ("pytest-benchmark", "pytest_benchmark"),
        ("testcontainers", "testcontainers"),
    ]

    print("📦 Testing Framework:")
    for display_name, import_name in test_packages:
        total_checks += 1
        if check_python_package(import_name):
            print(f"  ✅ {display_name}")
            success_count += 1
        else:
            print(f"  ❌ {display_name} - Missing")

    print()

    # Check configuration files
    config_files = [
        ("pytest.ini", "Pytest configuration"),
        (".coveragerc", "Coverage configuration"),
        ("tests/conftest.py", "Test fixtures"),
        (".vscode/python.code-snippets", "VS Code test snippets"),
        ("docker-compose.test.yml", "Test containers"),
        ("Dockerfile.test", "Test Dockerfile"),
    ]

    print("📋 Configuration Files:")
    for file_path, description in config_files:
        total_checks += 1
        if check_file_exists(file_path):
            print(f"  ✅ {description}")
            success_count += 1
        else:
            print(f"  ❌ {description} - Missing: {file_path}")

    print()

    # Check BaseService implementation
    base_service_files = [
        ("src/shared/base_service.py", "BaseService implementation"),
        ("src/shared/telemetry/__init__.py", "Telemetry configuration"),
        ("src/shared/metrics/__init__.py", "Metrics implementation"),
    ]

    print("🏗️  BaseService Components:")
    for file_path, description in base_service_files:
        total_checks += 1
        if check_file_exists(file_path):
            print(f"  ✅ {description}")
            success_count += 1
        else:
            print(f"  ❌ {description} - Missing: {file_path}")

    print()

    # Check example implementation
    example_files = [
        ("src/examples/frame_processor.py", "Example FrameProcessor"),
        ("tests/unit/test_frame_processor.py", "Unit tests"),
        ("tests/integration/test_frame_pipeline.py", "Integration tests"),
        ("tests/e2e/test_frame_flow.py", "E2E tests"),
        ("tests/performance/test_frame_processor_perf.py", "Performance tests"),
    ]

    print("📋 TDD Example Implementation:")
    for file_path, description in example_files:
        total_checks += 1
        if check_file_exists(file_path):
            print(f"  ✅ {description}")
            success_count += 1
        else:
            print(f"  ❌ {description} - Missing: {file_path}")

    print()

    # Check documentation
    doc_files = [
        ("docs/testing/tdd-guide.md", "TDD Guide"),
        ("docs/testing/base-service-guide.md", "BaseService Guide"),
    ]

    print("📚 Documentation:")
    for file_path, description in doc_files:
        total_checks += 1
        if check_file_exists(file_path):
            print(f"  ✅ {description}")
            success_count += 1
        else:
            print(f"  ❌ {description} - Missing: {file_path}")

    print()

    # Run basic tests to validate setup
    print("🧪 Test Execution Validation:")

    # Check if pytest can collect tests
    total_checks += 1
    try:
        result = subprocess.run(
            ["pytest", "--collect-only", "-q"],
            capture_output=True,
            text=True,
            check=True,
        )
        if "collected" in result.stdout:
            print("  ✅ Test discovery working")
            success_count += 1
        else:
            print("  ❌ Test discovery - No tests found")
    except (subprocess.CalledProcessError, FileNotFoundError) as e:
        print(f"  ❌ Test discovery failed: {e}")

    # Check if unit tests can run
    if check_file_exists("tests/unit"):
        total_checks += 1
        try:
            result = subprocess.run(
                ["pytest", "tests/unit", "--tb=no", "-q"],
                capture_output=True,
                text=True,
                timeout=30,
            )
            if result.returncode == 0:
                print("  ✅ Unit tests execution")
                success_count += 1
            else:
                print("  ❌ Unit tests failed")
        except (subprocess.CalledProcessError, subprocess.TimeoutExpired) as e:
            print(f"  ❌ Unit tests error: {e}")

    print()

    # Summary
    success_rate = (success_count / total_checks) * 100 if total_checks > 0 else 0
    print("📊 Summary:")
    print(f"  Total checks: {total_checks}")
    print(f"  Passed: {success_count}")
    print(f"  Failed: {total_checks - success_count}")
    print(f"  Success rate: {success_rate:.1f}%")

    if success_rate >= 90:
        print("\n🎉 TDD setup is excellent! Ready for development.")
        return 0
    elif success_rate >= 75:
        print("\n⚠️  TDD setup is mostly working, but some components need attention.")
        return 1
    else:
        print("\n❌ TDD setup needs significant work before development can begin.")
        return 2


def main():
    """Run main validation function."""
    if not Path("pytest.ini").exists():
        print("❌ This script must be run from the project root directory.")
        return 1

    return validate_test_setup()


if __name__ == "__main__":
    sys.exit(main())

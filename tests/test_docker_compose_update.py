"""Test docker-compose configuration for sample-processor migration."""
from pathlib import Path

import pytest
import yaml


def load_docker_compose(file_path: str) -> dict:
    """Load docker-compose.yml file."""
    with open(file_path, "r") as f:
        return yaml.safe_load(f)


def test_sample_processor_configuration():
    """Test docker-compose configuration for sample-processor."""
    # Load docker-compose
    config = load_docker_compose("docker/base/docker-compose.yml")

    # Check sample-processor config exists
    assert "sample-processor" in config["services"]
    sp_config = config["services"]["sample-processor"]

    # Verify image
    assert (
        sp_config["image"]
        == "ghcr.io/hretheum/detektr/sample-processor:${IMAGE_TAG:-latest}"
    )

    # Extract environment variables
    env_config = sp_config.get("environment", {})

    # Handle both list and dict formats
    env_vars = {}
    if isinstance(env_config, list):
        for env in env_config:
            if "=" in env:
                key, value = env.split("=", 1)
                env_vars[key] = value
    elif isinstance(env_config, dict):
        env_vars = env_config

    # Verify new ProcessorClient configuration
    assert "ORCHESTRATOR_URL" in env_vars
    assert (
        env_vars["ORCHESTRATOR_URL"]
        == "${ORCHESTRATOR_URL:-http://frame-buffer-v2:8002}"
    )

    assert "PROCESSOR_ID" in env_vars
    assert env_vars["PROCESSOR_ID"] == "${PROCESSOR_ID:-sample-processor-1}"

    # Verify old polling config removed
    assert "FRAME_BUFFER_URL" not in env_vars
    assert "ENABLE_FRAME_CONSUMER" not in env_vars
    assert "POLL_INTERVAL_MS" not in env_vars

    # Verify Redis configuration present for result publishing
    assert "REDIS_HOST" in env_vars
    assert "REDIS_PORT" in env_vars

    # Verify service dependencies
    depends_on = sp_config.get("depends_on", {})
    assert "frame-buffer-v2" in depends_on
    if isinstance(depends_on["frame-buffer-v2"], dict):
        assert depends_on["frame-buffer-v2"]["condition"] == "service_healthy"


def test_production_override_configuration():
    """Test production docker-compose override for sample-processor."""
    # Check if production override exists
    prod_compose_path = "docker/environments/production/docker-compose.yml"
    if not Path(prod_compose_path).exists():
        pytest.skip("Production override not yet created")

    config = load_docker_compose(prod_compose_path)

    if "sample-processor" in config.get("services", {}):
        sp_config = config["services"]["sample-processor"]

        # Should use production defaults
        assert "<<" in str(sp_config) or "x-production-defaults" in str(config)

        # Verify production-specific environment
        env_config = sp_config.get("environment", {})

        # Handle both list and dict formats
        env_vars = {}
        if isinstance(env_config, list):
            for env in env_config:
                if "=" in env:
                    key, value = env.split("=", 1)
                    env_vars[key] = value
        elif isinstance(env_config, dict):
            env_vars = env_config

        # Production should have proper logging and metrics
        assert env_vars.get("LOG_LEVEL") == "INFO"
        assert env_vars.get("METRICS_ENABLED") == "true"


def test_no_polling_configuration():
    """Verify sample-processor no longer has polling configuration."""
    config = load_docker_compose("docker/base/docker-compose.yml")

    sp_config = config["services"]["sample-processor"]
    env_config = sp_config.get("environment", {})

    # Convert to string to search for any polling-related config
    if isinstance(env_config, list):
        env_string = " ".join(env_config)
    elif isinstance(env_config, dict):
        env_string = " ".join(f"{k}={v}" for k, v in env_config.items())

    # These should NOT be present
    polling_configs = [
        "ENABLE_FRAME_CONSUMER",
        "FRAME_BUFFER_URL",
        "POLL_INTERVAL_MS",
        "CONSUMER_BATCH_SIZE",
        "MAX_RETRIES",
        "BACKOFF_MS",
    ]

    for config_key in polling_configs:
        assert config_key not in env_string, f"Found old polling config: {config_key}"


if __name__ == "__main__":
    # Run tests
    test_sample_processor_configuration()
    test_production_override_configuration()
    test_no_polling_configuration()
    print("All tests passed!")

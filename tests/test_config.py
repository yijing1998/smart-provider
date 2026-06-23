"""Tests for the Smart-Provider configuration module."""

import os
import sys
from pathlib import Path

import pytest
from pydantic import ValidationError

from src.config import Config, load_config


class TestConfigDefaults:
    """Verify default configuration values."""

    def test_default_values(self):
        cfg = Config()

        assert cfg.upstream_url == "https://api.openai.com/v1"
        assert cfg.upstream_litellm_provider == "openai"
        assert cfg.server_port == 8080
        assert cfg.client_id_header == "X-Client-Id"
        assert cfg.queue_max_size == 1000
        assert cfg.queue_max_wait_ms == 30000
        assert cfg.rate_limit_rpm == 60
        assert cfg.rate_limit_tpm is None
        assert cfg.rate_limit_window_seconds == 60
        assert cfg.forwarder_timeout_ms == 30000
        assert cfg.forwarder_max_retries == 0
        assert cfg.forwarder_retry_backoff_ms == 1000
        assert cfg.circuit_breaker_enabled is False
        assert cfg.circuit_breaker_failure_threshold == 5
        assert cfg.circuit_breaker_recovery_timeout_ms == 30000
        assert cfg.observability_log_level == "INFO"
        assert cfg.observability_metrics_enabled is False
        assert cfg.distributed_rate_limiter_enabled is False
        assert cfg.distributed_rate_limiter_url is None

    def test_load_config_returns_config_instance(self):
        cfg = load_config()
        assert isinstance(cfg, Config)
        assert cfg.server_port == 8080


class TestConfigEnvironmentVariables:
    """Verify configuration loading from environment variables."""

    def test_upstream_url_from_env(self, monkeypatch):
        monkeypatch.setenv("SMART_PROVIDER_UPSTREAM_URL", "https://custom.example.com/v1")
        cfg = load_config()
        assert cfg.upstream_url == "https://custom.example.com/v1"

    def test_upstream_litellm_provider_from_env(self, monkeypatch):
        monkeypatch.setenv("SMART_PROVIDER_UPSTREAM_LITELLM_PROVIDER", "azure")
        cfg = load_config()
        assert cfg.upstream_litellm_provider == "azure"

    def test_queue_max_size_from_env(self, monkeypatch):
        monkeypatch.setenv("SMART_PROVIDER_QUEUE_MAX_SIZE", "500")
        cfg = load_config()
        assert cfg.queue_max_size == 500

    def test_rate_limit_rpm_from_env(self, monkeypatch):
        monkeypatch.setenv("SMART_PROVIDER_RATE_LIMIT_RPM", "120")
        cfg = load_config()
        assert cfg.rate_limit_rpm == 120

    def test_log_level_from_env_is_normalized(self, monkeypatch):
        monkeypatch.setenv("SMART_PROVIDER_OBSERVABILITY_LOG_LEVEL", "debug")
        cfg = load_config()
        assert cfg.observability_log_level == "DEBUG"

    def test_overrides_take_precedence_over_env(self, monkeypatch):
        monkeypatch.setenv("SMART_PROVIDER_SERVER_PORT", "9000")
        cfg = load_config(server_port=7777)
        assert cfg.server_port == 7777


class TestConfigDotEnvFile:
    """Verify configuration loading from .env files."""

    def test_env_file_is_loaded(self, tmp_path, monkeypatch):
        env_file = tmp_path / ".env"
        env_file.write_text(
            "SMART_PROVIDER_UPSTREAM_URL=https://env-file.example.com/v1\n"
            "SMART_PROVIDER_QUEUE_MAX_SIZE=2000\n"
        )
        monkeypatch.chdir(tmp_path)

        cfg = load_config()
        assert cfg.upstream_url == "https://env-file.example.com/v1"
        assert cfg.queue_max_size == 2000

    def test_env_vars_take_precedence_over_env_file(self, tmp_path, monkeypatch):
        env_file = tmp_path / ".env"
        env_file.write_text("SMART_PROVIDER_RATE_LIMIT_RPM=30\n")
        monkeypatch.chdir(tmp_path)
        monkeypatch.setenv("SMART_PROVIDER_RATE_LIMIT_RPM", "90")

        cfg = load_config()
        assert cfg.rate_limit_rpm == 90


class TestCustomEnvFile:
    """Verify loading from custom env file names and CLI arguments."""

    def test_env_var_specifies_custom_env_file(self, tmp_path, monkeypatch):
        custom_env = tmp_path / "prod.env"
        custom_env.write_text("SMART_PROVIDER_UPSTREAM_URL=https://prod.example.com/v1\n")
        monkeypatch.chdir(tmp_path)
        monkeypatch.setenv("SMART_PROVIDER_ENV_FILE", str(custom_env))
        monkeypatch.setattr(sys, "argv", ["uvicorn"])

        cfg = load_config()
        assert cfg.upstream_url == "https://prod.example.com/v1"

    def test_env_var_replaces_default_env_file(self, tmp_path, monkeypatch):
        default_env = tmp_path / ".env"
        default_env.write_text("SMART_PROVIDER_UPSTREAM_URL=https://default.example.com/v1\n")
        custom_env = tmp_path / "prod.env"
        custom_env.write_text("SMART_PROVIDER_UPSTREAM_URL=https://prod.example.com/v1\n")
        monkeypatch.chdir(tmp_path)
        monkeypatch.setenv("SMART_PROVIDER_ENV_FILE", str(custom_env))
        monkeypatch.setattr(sys, "argv", ["uvicorn"])

        cfg = load_config()
        assert cfg.upstream_url == "https://prod.example.com/v1"

    def test_cli_env_file_argument(self, tmp_path, monkeypatch):
        custom_env = tmp_path / "prod.env"
        custom_env.write_text("SMART_PROVIDER_RATE_LIMIT_RPM=120\n")
        monkeypatch.chdir(tmp_path)
        monkeypatch.setattr(
            sys, "argv", ["uvicorn", "src.ingress.app:create_app", "--env-file", str(custom_env)]
        )

        cfg = load_config()
        assert cfg.rate_limit_rpm == 120

    def test_cli_env_file_argument_with_equals(self, tmp_path, monkeypatch):
        custom_env = tmp_path / "prod.env"
        custom_env.write_text("SMART_PROVIDER_RATE_LIMIT_RPM=150\n")
        monkeypatch.chdir(tmp_path)
        monkeypatch.setattr(
            sys,
            "argv",
            ["uvicorn", "src.ingress.app:create_app", f"--env-file={custom_env}"],
        )

        cfg = load_config()
        assert cfg.rate_limit_rpm == 150

    def test_cli_env_file_takes_precedence_over_env_var(self, tmp_path, monkeypatch):
        cli_env = tmp_path / "cli.env"
        cli_env.write_text("SMART_PROVIDER_RATE_LIMIT_RPM=200\n")
        var_env = tmp_path / "var.env"
        var_env.write_text("SMART_PROVIDER_RATE_LIMIT_RPM=100\n")
        monkeypatch.chdir(tmp_path)
        monkeypatch.setenv("SMART_PROVIDER_ENV_FILE", str(var_env))
        monkeypatch.setattr(
            sys, "argv", ["uvicorn", "--env-file", str(cli_env)]
        )

        cfg = load_config()
        assert cfg.rate_limit_rpm == 200

    def test_missing_env_file_from_env_var_raises(self, tmp_path, monkeypatch):
        missing = tmp_path / "missing.env"
        monkeypatch.chdir(tmp_path)
        monkeypatch.setenv("SMART_PROVIDER_ENV_FILE", str(missing))
        monkeypatch.setattr(sys, "argv", ["uvicorn"])

        with pytest.raises(FileNotFoundError):
            load_config()

    def test_missing_env_file_from_cli_raises(self, tmp_path, monkeypatch):
        missing = tmp_path / "missing.env"
        monkeypatch.chdir(tmp_path)
        monkeypatch.setattr(
            sys, "argv", ["uvicorn", "--env-file", str(missing)]
        )

        with pytest.raises(FileNotFoundError):
            load_config()

    def test_default_env_file_missing_is_allowed(self, tmp_path, monkeypatch):
        monkeypatch.chdir(tmp_path)
        monkeypatch.setattr(sys, "argv", ["uvicorn"])

        cfg = load_config()
        assert cfg.upstream_url == "https://api.openai.com/v1"


class TestConfigValidation:
    """Verify configuration validation rejects invalid values."""

    def test_rate_limit_rpm_must_be_positive(self):
        with pytest.raises(ValidationError):
            Config(rate_limit_rpm=0)

    def test_server_port_must_be_within_valid_range(self):
        with pytest.raises(ValidationError):
            Config(server_port=70000)

    def test_server_port_cannot_be_zero(self):
        with pytest.raises(ValidationError):
            Config(server_port=0)

    def test_queue_max_size_cannot_be_negative(self):
        with pytest.raises(ValidationError):
            Config(queue_max_size=-1)

    def test_forwarder_timeout_must_be_positive(self):
        with pytest.raises(ValidationError):
            Config(forwarder_timeout_ms=0)

    def test_invalid_log_level_is_rejected(self):
        with pytest.raises(ValidationError):
            Config(observability_log_level="VERBOSE")

    def test_empty_client_id_header_is_rejected(self):
        with pytest.raises(ValidationError):
            Config(client_id_header="")

    def test_empty_upstream_url_is_rejected(self):
        with pytest.raises(ValidationError):
            Config(upstream_url="")

    def test_invalid_upstream_litellm_provider_is_rejected(self):
        with pytest.raises(ValidationError):
            Config(upstream_litellm_provider="not-a-provider")


class TestConfigComponentViews:
    """Verify component configuration views."""

    def test_queue_view(self):
        cfg = Config(queue_max_size=42, queue_max_wait_ms=5000)
        assert cfg.queue.max_size == 42
        assert cfg.queue.max_wait_ms == 5000

    def test_limiter_view(self):
        cfg = Config(rate_limit_rpm=120, rate_limit_tpm=4000000, rate_limit_window_seconds=30)
        assert cfg.limiter.rpm == 120
        assert cfg.limiter.tpm == 4000000
        assert cfg.limiter.window_seconds == 30

    def test_forwarder_view(self):
        cfg = Config(forwarder_timeout_ms=10000, forwarder_max_retries=3, forwarder_retry_backoff_ms=500)
        assert cfg.forwarder.timeout_ms == 10000
        assert cfg.forwarder.max_retries == 3
        assert cfg.forwarder.retry_backoff_ms == 500

    def test_circuit_breaker_view_defaults(self):
        cfg = Config()
        assert cfg.circuit_breaker.enabled is False
        assert cfg.circuit_breaker.failure_threshold == 5
        assert cfg.circuit_breaker.recovery_timeout_ms == 30000

    def test_observability_view_defaults(self):
        cfg = Config()
        assert cfg.observability.log_level == "INFO"
        assert cfg.observability.metrics_enabled is False

    def test_distributed_rate_limiter_view_defaults(self):
        cfg = Config()
        assert cfg.distributed_rate_limiter.enabled is False
        assert cfg.distributed_rate_limiter.url is None

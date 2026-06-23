"""Configuration loader for Smart-Provider."""

import os
import sys
from pathlib import Path
from typing import Optional

from src.config.schema import Config


_ENV_FILE_CLI_FLAG = "--env-file"
_ENV_FILE_ENV_VAR = "SMART_PROVIDER_ENV_FILE"
_DEFAULT_ENV_FILE = Path(".env")


def _parse_env_file_from_argv(argv: list[str]) -> Optional[Path]:
    """Parse the first ``--env-file`` argument from the command line.

    Supports both ``--env-file path`` and ``--env-file=path`` forms.
    Multiple occurrences are not supported: only the first value is returned.

    Args:
        argv: The argument list, typically ``sys.argv``.

    Returns:
        A ``Path`` to the requested env file, or ``None`` if the flag is absent.
    """
    i = 0
    while i < len(argv):
        arg = argv[i]
        if arg == _ENV_FILE_CLI_FLAG:
            if i + 1 < len(argv):
                value = argv[i + 1].strip()
                return Path(value) if value else None
            return None
        if arg.startswith(f"{_ENV_FILE_CLI_FLAG}="):
            _, _, value = arg.partition("=")
            value = value.strip()
            return Path(value) if value else None
        i += 1
    return None


def _resolve_env_file(argv: list[str]) -> Optional[Path]:
    """Determine which env file to load.

    Resolution order (first match wins):

    1. ``--env-file <path>`` CLI argument.
    2. ``SMART_PROVIDER_ENV_FILE`` environment variable.
    3. Default ``.env`` file in the working directory.

    When an explicit file is requested via CLI or environment variable and
    the file does not exist, a ``FileNotFoundError`` is raised immediately so
    that misconfiguration is caught at startup.

    The default ``.env`` file is allowed to be missing; pydantic-settings will
    silently skip it, preserving backward compatibility.

    Args:
        argv: The argument list, typically ``sys.argv``.

    Returns:
        A ``Path`` to the env file to load, or ``None`` to let pydantic-settings
        fall back to the class-level default.
    """
    cli_file = _parse_env_file_from_argv(argv)
    if cli_file is not None:
        if not cli_file.is_file():
            raise FileNotFoundError(
                f"Env file specified by {_ENV_FILE_CLI_FLAG} does not exist: {cli_file}"
            )
        return cli_file

    env_var = os.getenv(_ENV_FILE_ENV_VAR)
    if env_var and env_var.strip():
        env_file = Path(env_var.strip())
        if not env_file.is_file():
            raise FileNotFoundError(
                f"Env file specified by {_ENV_FILE_ENV_VAR} does not exist: {env_file}"
            )
        return env_file

    return _DEFAULT_ENV_FILE


def load_config(**overrides) -> Config:
    """Load and validate the Smart-Provider runtime configuration.

    Configuration values are read from environment variables prefixed with
    ``SMART_PROVIDER_`` and from an optional env file. The env file can be
    customized via the ``SMART_PROVIDER_ENV_FILE`` environment variable or the
    ``--env-file`` CLI argument. Keyword arguments can be used to override
    values, which is convenient for tests.

    Args:
        **overrides: Explicit values that take precedence over environment
            variables and env files.

    Returns:
        A validated ``Config`` instance.
    """
    env_file = _resolve_env_file(sys.argv)
    return Config(_env_file=env_file, **overrides)

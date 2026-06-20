"""Configuration loader for Smart-Provider."""

from src.config.schema import Config


def load_config(**overrides) -> Config:
    """Load and validate the Smart-Provider runtime configuration.

    Configuration values are read from environment variables prefixed with
    ``SMART_PROVIDER_`` and from an optional ``.env`` file. Keyword arguments
    can be used to override values, which is convenient for tests.

    Args:
        **overrides: Explicit values that take precedence over environment
            variables and ``.env`` files.

    Returns:
        A validated ``Config`` instance.
    """
    return Config(**overrides)

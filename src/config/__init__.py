"""Configuration management for Smart-Provider."""

from .loader import load_config
from .schema import Config

__all__ = ["Config", "load_config"]

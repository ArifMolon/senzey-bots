"""Configuration loader — loads TOML config files from the config/ directory."""

import tomllib
from pathlib import Path


def load_config(path: str) -> dict[str, object]:
    """Load a TOML configuration file and return its contents as a dict.

    Args:
        path: Path to the TOML config file (relative to project root or absolute).

    Returns:
        Parsed configuration dictionary.

    """
    config_path = Path(path)
    with config_path.open("rb") as f:
        return tomllib.load(f)

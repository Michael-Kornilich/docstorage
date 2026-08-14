from datetime import date
from dataclasses import dataclass
from pathlib import Path
from typing import Literal


@dataclass(frozen=True)
class DateInterval:
    include_upper: bool = True
    include_lower: bool = True
    # Includes both to simplify handling of an open bound
    upper: date = date(9999, 12, 31)
    lower: date = date(1, 1, 1)

    def __post_init__(self):
        """
        Check types and if the given interval is valid
        """
        if not isinstance(self.lower, date):
            raise TypeError(f"The lower date must be a date. Got {type(self.lower).__name__}")
        if not isinstance(self.include_lower, bool):
            raise TypeError(f"The lower date inclusion must be boolean. Got {type(self.include_lower).__name__}")

        if not isinstance(self.upper, date):
            raise TypeError(f"The upper date must be a date. Got {type(self.upper).__name__}")
        if not isinstance(self.include_upper, bool):
            raise TypeError(f"The upper date inclusion must be boolean. Got {type(self.include_upper).__name__}")

        if self.lower == self.upper and not all([self.include_lower, self.include_upper]):
            raise ValueError("Invalid date interval: no dates exist with given restriction")

        if self.lower > self.upper:
            raise ValueError("Invalid date interval: no dates exist with given restriction")

        if self.upper == date(9999, 12, 31) and self.lower == date(1, 1, 1):
            from warnings import warn
            warn("Degenerate date interval")

    def __contains__(self, date_: date) -> bool:
        if not isinstance(date_, date):
            raise TypeError(f"The date must be a date. Got {type(date_).__name__}")

        if self.lower < date_ < self.upper:
            return True
        if (self.include_lower and date_ == self.lower) or (not self.include_upper and date_ == self.upper):
            return True

        return False


def get_config(tp: Literal["user", "local"]) -> dict[str, str]:
    """Load and validate either the user or local configuration.
    Checks for valid config keys"""
    import os
    CONFIG_DIR = Path(os.environ["PROJECT_ROOT"]) / "config"
    CONFIG_KEYS = {
        "user": {"landing-directory"},
        "local": {"db-path", "storage-path"},
    }
    if tp not in ("user", "local"):
        raise ValueError(f"Unknown config type: {tp}")

    config_path = CONFIG_DIR / f"{tp}.json"
    try:
        import json
        with open(config_path, mode="r") as f:
            config = json.load(f)
    except Exception as err:
        raise ImportError(f"Failed to load {tp} config: {err}") from err

    if CONFIG_KEYS[tp] != set(config.keys()) or not all(isinstance(value, str) for value in config.values()):
        raise KeyError(f"The {tp} config keys do not match the expected keys.")
    return config


def set_config(tp: Literal["user", "local"], key: str, value: str) -> None:
    """Validate input and set either the user or local configuration."""
    config = get_config(tp)
    if key not in config:
        raise KeyError(f"The {key} is invalid.")

    config[key] = value

    import os
    import json

    config_path = Path(os.environ["PROJECT_ROOT"]) / "config" / f"{tp}.json"
    with open(config_path, "w") as f:
        json.dump(config, f)
    return

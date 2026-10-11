"""Validated, opt-in settings for Telegram's local media archive."""

from dataclasses import dataclass
import math
from pathlib import Path
import re
from typing import FrozenSet

try:
    import tomllib
except ModuleNotFoundError:
    import tomli as tomllib

from kisara.config.settings import ConfigurationError


@dataclass(frozen=True)
class TgSetuConfig:
    """Keep archive policy separate from Telegram SDK connection settings."""

    enabled: bool = False
    allowed_users: FrozenSet[str] = frozenset()
    save_root: Path = Path("data/kisara/tgsetu")
    cache_root: Path = Path("/var/lib/telegram-bot-api")
    max_file_bytes: int = 2147483648
    max_unit_bytes: int = 8589934592
    max_unit_files: int = 30
    max_pending_files: int = 200
    workers: int = 2
    album_quiet_seconds: float = 1.0
    album_max_wait_seconds: float = 5.0

    @classmethod
    def load(cls, path: Path) -> "TgSetuConfig":
        """Load one optional TOML; reject unknown keys and unsafe limits."""
        if not path.exists():
            return cls.disabled()
        try:
            with path.open("rb") as stream:
                values = tomllib.load(stream)
        except (OSError, tomllib.TOMLDecodeError) as error:
            raise ConfigurationError("Cannot read tgsetu config.") from error
        if set(values) - set(cls.__dataclass_fields__):
            raise ConfigurationError("Unknown tgsetu config keys.")
        defaults = cls.disabled()
        enabled = values.get("enabled", defaults.enabled)
        users = values.get("allowed_users", [])
        if type(enabled) is not bool:
            raise ConfigurationError("Tgsetu enabled must be a boolean.")
        if not isinstance(users, list) or any(
                not isinstance(user, str) or not re.fullmatch(r"[1-9][0-9]*", user.strip())
                for user in users):
            raise ConfigurationError("Tgsetu allowed_users must contain positive Telegram user IDs.")
        fields = {"enabled": enabled, "allowed_users": frozenset(user.strip() for user in users)}
        for key in ("save_root", "cache_root"):
            value = values.get(key, str(getattr(defaults, key)))
            if not isinstance(value, str) or not value.strip() or "\x00" in value:
                raise ConfigurationError("Tgsetu {} must be a nonempty path.".format(key))
            fields[key] = Path(value).expanduser()
        for key in ("max_file_bytes", "max_unit_bytes"):
            value = values.get(key)
            fields[key] = getattr(defaults, key) if value is None else _size(value, key)
        for key in ("max_unit_files", "max_pending_files", "workers"):
            value = values.get(key, getattr(defaults, key))
            if type(value) is not int or value <= 0:
                raise ConfigurationError("Tgsetu {} must be a positive integer.".format(key))
            fields[key] = value
        for key in ("album_quiet_seconds", "album_max_wait_seconds"):
            value = values.get(key, getattr(defaults, key))
            if type(value) not in {int, float} or not math.isfinite(value) or value <= 0:
                raise ConfigurationError("Tgsetu {} must be a positive duration.".format(key))
            fields[key] = float(value)
        config = cls(**fields)
        if config.max_unit_bytes < config.max_file_bytes or config.workers > 16:
            raise ConfigurationError("Tgsetu unit bytes must cover one file; workers must be at most 16.")
        if config.album_quiet_seconds > config.album_max_wait_seconds:
            raise ConfigurationError("Tgsetu quiet window must not exceed maximum wait.")
        save, cache = config.save_root.resolve(), config.cache_root.resolve()
        if save == cache or save in cache.parents or cache in save.parents:
            raise ConfigurationError("Tgsetu cache and archive must be separate directories.")
        return config

    @classmethod
    def disabled(cls) -> "TgSetuConfig":
        """Return inert defaults without creating any paths."""
        return cls()


def _size(value: object, name: str) -> int:
    """Parse the same binary K/M/G limits used by Setu."""
    match = re.fullmatch(r"([1-9][0-9]*)([KMGkmg])", value) if isinstance(value, str) else None
    if match is None:
        raise ConfigurationError("Tgsetu {} must be a size such as 100M or 2G.".format(name))
    try:
        return int(match.group(1)) * 1024 ** {"K": 1, "M": 2, "G": 3}[match.group(2).upper()]
    except ValueError as error:
        raise ConfigurationError("Tgsetu {} is too large.".format(name)) from error

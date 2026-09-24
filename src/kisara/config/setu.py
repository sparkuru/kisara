"""Validated settings for the private setu feature."""

from dataclasses import dataclass
from pathlib import Path
from typing import FrozenSet, Tuple

try:
    import tomllib
except ModuleNotFoundError:
    import tomli as tomllib

from kisara.config.settings import ConfigurationError


@dataclass(frozen=True)
class SetuConfig:
    """Keep setu policy separate from engine and other feature settings."""

    enabled: bool
    allowed_users: FrozenSet[str]
    confirm_timeout_seconds: int
    confirm_words: Tuple[str, ...]
    cancel_words: Tuple[str, ...]
    save_root: Path
    save_mode: str
    max_file_bytes: int
    max_batch_bytes: int
    max_depth: int
    max_nodes: int
    local_media_root: Path

    @classmethod
    def load(cls, path: Path) -> "SetuConfig":
        """Load an optional feature file; absence leaves the feature disabled."""
        if not path.exists():
            return cls.disabled()
        try:
            with path.open("rb") as stream:
                values = tomllib.load(stream)
        except (OSError, tomllib.TOMLDecodeError) as error:
            raise ConfigurationError("Cannot read setu config: {}.".format(error)) from error
        if not isinstance(values, dict):
            raise ConfigurationError("Setu config must be a TOML table.")
        expected = {
            "enabled", "allowed_users",
            "confirm_timeout_seconds", "confirm_words", "cancel_words", "save_root",
            "save_mode", "max_file_bytes", "max_batch_bytes", "max_depth", "max_nodes",
            "local_media_root",
        }
        if set(values) - expected:
            raise ConfigurationError("Unknown setu config keys: {}.".format(
                ", ".join(sorted(set(values) - expected))))
        enabled = values.get("enabled", False)
        if not isinstance(enabled, bool):
            raise ConfigurationError("Setu enabled must be a boolean.")
        allowed_users = _words(values.get("allowed_users", []), "allowed_users")
        confirm_words = _ordered_words(values.get("confirm_words", ["确认"]), "confirm_words")
        cancel_words = _ordered_words(values.get("cancel_words", ["取消"]), "cancel_words")
        if set(confirm_words) & set(cancel_words) or not confirm_words or not cancel_words:
            raise ConfigurationError("Setu confirmation and cancellation words must be distinct.")
        if "/setu" in cancel_words:
            raise ConfigurationError("Setu /setu cannot be a cancellation word.")
        save_mode = values.get("save_mode", "date_original")
        if not isinstance(save_mode, str) or save_mode not in {"date_original", "timestamp_hash"}:
            raise ConfigurationError("Setu save_mode must be date_original or timestamp_hash.")
        save_root = _path(values.get("save_root", "data/kisara/setu"), "save_root")
        local_root = _path(values.get("local_media_root", "/app/.config/QQ"), "local_media_root")
        config = cls(
            enabled, allowed_users,
            _positive_int(values.get("confirm_timeout_seconds", 1800), "confirm_timeout_seconds"),
            confirm_words, cancel_words, save_root, save_mode,
            _positive_int(values.get("max_file_bytes", 104857600), "max_file_bytes"),
            _positive_int(values.get("max_batch_bytes", 1073741824), "max_batch_bytes"),
            _positive_int(values.get("max_depth", 5), "max_depth"),
            _positive_int(values.get("max_nodes", 500), "max_nodes"),
            local_root,
        )
        if config.max_batch_bytes < config.max_file_bytes:
            raise ConfigurationError("Setu max_batch_bytes must cover max_file_bytes.")
        return config

    @classmethod
    def disabled(cls) -> "SetuConfig":
        """Build inert defaults for installations without a feature config."""
        return cls(False, frozenset(), 1800,
                   ("确认",), ("取消",),
                   Path("data/kisara/setu"), "date_original",
                   104857600, 1073741824, 5, 500, Path("/app/.config/QQ"))


def _words(value: object, name: str) -> FrozenSet[str]:
    """Validate a list of nonempty words or identifiers."""
    if not isinstance(value, list) or any(not isinstance(item, str) or not item.strip()
                                           for item in value):
        raise ConfigurationError("Setu {} must be a string list.".format(name))
    return frozenset(item.strip().casefold() for item in value)


def _ordered_words(value: object, name: str) -> Tuple[str, ...]:
    """Validate words while retaining their configured display order."""
    if not isinstance(value, list) or any(not isinstance(item, str) or not item.strip()
                                           for item in value):
        raise ConfigurationError("Setu {} must be a string list.".format(name))
    return tuple(dict.fromkeys(item.strip().casefold() for item in value))


def _positive_int(value: object, name: str) -> int:
    """Reject booleans and nonpositive limits."""
    if type(value) is not int or value <= 0:
        raise ConfigurationError("Setu {} must be a positive integer.".format(name))
    return value


def _path(value: object, name: str) -> Path:
    """Validate a configured directory path."""
    if not isinstance(value, str) or not value.strip():
        raise ConfigurationError("Setu {} must be a nonempty path.".format(name))
    return Path(value).expanduser()

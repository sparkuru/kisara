"""Independent TOML files for configurable bot features."""

from pathlib import Path
from typing import Any, Callable, FrozenSet, Mapping

try:
    import tomllib
except ModuleNotFoundError:
    import tomli as tomllib


FEATURE_KEYS = {
    "chat": frozenset({
        "enabled", "bot_name", "sender_name", "library", "trigger_rate",
        "similarity_rate", "ignored_phrases", "banned_users",
        "always_reply_users", "reply_to_mentions", "groups",
    }),
    "tarot": frozenset({"enabled", "spread_rate", "image_dir", "groups"}),
    "news": frozenset({"push_groups", "push_time", "cache_days", "cache_dir", "font_paths"}),
    "source": frozenset({"api_key"}),
    "music": frozenset({"api_url"}),
    "love": frozenset({"api_key"}),
}


class ConfigurationError(ValueError):
    """A selected engine or feature configuration is invalid."""


class FeatureFileError(ConfigurationError):
    """A feature TOML file is malformed or contains unsupported options."""


def load_feature(name: str) -> Mapping[str, Any]:
    """Load one optional, explicitly named feature configuration file."""
    allowed = FEATURE_KEYS[name]
    path = Path("config/features") / name / "config.toml"
    if not path.exists():
        return {}
    try:
        with path.open("rb") as stream:
            document = tomllib.load(stream)
    except (OSError, tomllib.TOMLDecodeError) as error:
        raise FeatureFileError("Cannot read {} feature config: {}.".format(name, error)) from error
    if not isinstance(document, dict):
        raise FeatureFileError("{} feature config must be a TOML table.".format(name))
    unknown = set(document) - allowed
    if unknown:
        raise FeatureFileError("Unknown {} feature keys: {}.".format(
            name, ", ".join(sorted(unknown))))
    return document


def boolean(config: Mapping[str, Any], key: str, fallback: Callable[[], bool],
            feature: str) -> bool:
    """Select a validated boolean from TOML or an existing fallback."""
    if key not in config:
        return fallback()
    value = config[key]
    if not isinstance(value, bool):
        raise FeatureFileError("{}.{} must be a boolean.".format(feature, key))
    return value


def string(config: Mapping[str, Any], key: str, fallback: Callable[[], str],
           feature: str, allow_empty: bool = False) -> str:
    """Select a trimmed string from one feature file."""
    if key not in config:
        return fallback()
    value = config[key]
    if not isinstance(value, str) or (not allow_empty and not value.strip()):
        raise FeatureFileError("{}.{} must be a string.".format(feature, key))
    return value.strip()


def percent(config: Mapping[str, Any], key: str, fallback: Callable[[], int],
            feature: str) -> int:
    """Select a strict integer percentage."""
    if key not in config:
        return fallback()
    value = config[key]
    if type(value) is not int or value < 0 or value > 100:
        raise FeatureFileError("{}.{} must be an integer from 0 to 100.".format(feature, key))
    return value


def words(config: Mapping[str, Any], key: str, fallback: Callable[[], FrozenSet[str]],
          feature: str) -> FrozenSet[str]:
    """Select a list of nonempty user IDs or phrases."""
    if key not in config:
        return fallback()
    value = config[key]
    if not isinstance(value, list) or any(
        not isinstance(item, str) or not item.strip() for item in value
    ):
        raise FeatureFileError("{}.{} must be a string list.".format(feature, key))
    return frozenset(item.strip() for item in value)


def groups(config: Mapping[str, Any], feature: str) -> Mapping[str, Any]:
    """Return an optional group table for feature-specific validation."""
    value = config.get("groups", {})
    if not isinstance(value, dict):
        raise FeatureFileError("{}.groups must be a table.".format(feature))
    return value

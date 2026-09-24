"""Engine settings with independent feature TOML and legacy environment fallbacks."""

import os
import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, FrozenSet, Mapping, Optional, Tuple

from .feature_files import (
    ConfigurationError, boolean, groups, load_feature,
    percent, string, words,
)


DEFAULT_ENGINE = "onebot"
DEFAULT_ONEBOT_WS_URL = "ws://napcat:3001"
SUPPORTED_ENGINES = ("onebot", "official")


@dataclass(frozen=True)
class GroupOverride:
    """Validated overrides for one allowed group."""

    chat: Mapping[str, object] = field(default_factory=dict)
    tarot_spread_rate: Optional[int] = None


@dataclass(frozen=True)
class Settings:
    """Runtime settings shared by the selected protocol adapter."""

    engine: str
    instance_id: str
    allowed_users: FrozenSet[str]
    groups_enabled: bool
    allowed_groups: FrozenSet[str]
    onebot_ws_url: Optional[str] = None
    onebot_access_token: Optional[str] = None
    app_id: Optional[str] = None
    app_secret: Optional[str] = None
    chat_enabled: bool = True
    chat_bot_name: str = "Kisara"
    chat_sender_name: str = "you"
    chat_library: str = "cute"
    chat_trigger_rate: int = 30
    chat_similarity_rate: int = 60
    chat_ignored_phrases: FrozenSet[str] = frozenset()
    chat_banned_users: FrozenSet[str] = frozenset()
    chat_always_reply_users: FrozenSet[str] = frozenset()
    chat_reply_to_mentions: bool = True
    tarot_enabled: bool = True
    tarot_spread_rate: int = 5
    tarot_image_dir: str = "data/kisara/tarotCards"
    saucenao_key: str = ""
    music_api_url: str = ""
    tianapi_key: str = ""
    news_push_groups: FrozenSet[str] = frozenset()
    news_push_hour: int = 10
    news_push_minute: int = 30
    state_dir: str = "data/kisara"
    admin_users: FrozenSet[str] = frozenset()
    group_overrides: Mapping[str, GroupOverride] = field(default_factory=dict)

    @classmethod
    def from_environment(cls) -> "Settings":
        """Read common settings and validate only the selected engine."""

        engine = os.environ.get("KISARA_ENGINE", DEFAULT_ENGINE).strip().lower()
        if engine not in SUPPORTED_ENGINES:
            supported = ", ".join(SUPPORTED_ENGINES)
            raise ConfigurationError(
                "Unknown KISARA_ENGINE {!r}. Choose one of: {}.".format(
                    engine, supported
                )
            )

        instance_id = os.environ.get("KISARA_INSTANCE_ID", "personal").strip()
        if not instance_id:
            raise ConfigurationError("KISARA_INSTANCE_ID must not be empty.")

        allowed_users = _read_csv("KISARA_ALLOWED_USERS")
        admin_users = _read_csv("KISARA_ADMIN_USERS")
        if not admin_users.issubset(allowed_users):
            raise ConfigurationError("KISARA_ADMIN_USERS must be allowed users.")
        groups_enabled = _read_bool("KISARA_GROUPS_ENABLED", default=False)
        allowed_groups = _read_csv("KISARA_ALLOWED_GROUPS")
        group_overrides = _read_group_overrides(allowed_groups)
        chat_file = load_feature("chat")
        tarot_file = load_feature("tarot")
        news_file = load_feature("news")
        source_file = load_feature("source")
        music_file = load_feature("music")
        love_file = load_feature("love")
        chat_options = {
            "chat_enabled": boolean(chat_file, "enabled",
                                    lambda: _read_bool("KISARA_CHAT_ENABLED", True), "chat"),
            "chat_bot_name": string(chat_file, "bot_name",
                                    lambda: os.environ.get("KISARA_CHAT_BOT_NAME", "Kisara").strip(), "chat"),
            "chat_sender_name": string(chat_file, "sender_name",
                                       lambda: os.environ.get("KISARA_CHAT_SENDER_NAME", "you").strip(), "chat"),
            "chat_library": string(chat_file, "library",
                                   lambda: os.environ.get("KISARA_CHAT_LIBRARY", "cute").strip(), "chat").lower(),
            "chat_trigger_rate": percent(chat_file, "trigger_rate",
                                         lambda: _read_percent("KISARA_CHAT_TRIGGER_RATE", 30), "chat"),
            "chat_similarity_rate": percent(chat_file, "similarity_rate",
                                            lambda: _read_percent("KISARA_CHAT_SIMILARITY_RATE", 60), "chat"),
            "chat_ignored_phrases": words(chat_file, "ignored_phrases",
                                          lambda: _read_csv("KISARA_CHAT_IGNORED_PHRASES"), "chat"),
            "chat_banned_users": words(chat_file, "banned_users",
                                       lambda: _read_csv("KISARA_CHAT_BANNED_USERS"), "chat"),
            "chat_always_reply_users": words(chat_file, "always_reply_users",
                                             lambda: _read_csv("KISARA_CHAT_ALWAYS_REPLY_USERS"), "chat"),
            "chat_reply_to_mentions": boolean(chat_file, "reply_to_mentions",
                                              lambda: _read_bool("KISARA_CHAT_REPLY_TO_MENTIONS", True), "chat"),
        }
        if not chat_options["chat_bot_name"] or not chat_options["chat_sender_name"]:
            raise ConfigurationError("Chat display names must not be empty.")
        if chat_options["chat_library"] not in {"cute", "tsundere", "mixed"}:
            raise ConfigurationError(
                "KISARA_CHAT_LIBRARY must be cute, tsundere, or mixed."
            )
        tarot_options = {
            "tarot_enabled": boolean(tarot_file, "enabled",
                                     lambda: _read_bool("KISARA_TAROT_ENABLED", True), "tarot"),
            "tarot_spread_rate": percent(tarot_file, "spread_rate",
                                        lambda: _read_percent("KISARA_TAROT_SPREAD_RATE", 5), "tarot"),
            "tarot_image_dir": string(tarot_file, "image_dir",
                                      lambda: os.environ.get(
                                          "KISARA_TAROT_IMAGE_DIR", "data/kisara/tarotCards"
                                      ).strip(), "tarot"),
        }
        public_options = {
            "saucenao_key": string(source_file, "api_key",
                                   lambda: os.environ.get("SAUCENAO_API_KEY", "").strip(),
                                   "source", allow_empty=True),
            "music_api_url": string(music_file, "api_url",
                                    lambda: os.environ.get("KISARA_MUSIC_API_URL", "").strip(),
                                    "music", allow_empty=True),
            "tianapi_key": string(love_file, "api_key",
                                  lambda: os.environ.get("TIANAPI_KEY", "").strip(),
                                  "love", allow_empty=True),
        }
        music_api_url = public_options["music_api_url"]
        if music_api_url and not music_api_url.startswith(("http://", "https://")):
            raise ConfigurationError("KISARA_MUSIC_API_URL must be an HTTP URL.")
        news_push_groups = words(news_file, "push_groups",
                                 lambda: _read_csv("KISARA_NEWS_PUSH_GROUPS"), "news")
        if news_push_groups and not groups_enabled:
            raise ConfigurationError("News push requires KISARA_GROUPS_ENABLED=true.")
        if news_push_groups and engine != "onebot":
            raise ConfigurationError("Scheduled news push requires the OneBot engine.")
        if not news_push_groups.issubset(allowed_groups):
            raise ConfigurationError("News push groups must be in KISARA_ALLOWED_GROUPS.")
        news_time = string(news_file, "push_time",
                           lambda: os.environ.get("KISARA_NEWS_PUSH_TIME", "10:30").strip(), "news")
        news_push_hour, news_push_minute = _parse_clock_time(news_time, "news.push_time")
        group_overrides = _merge_feature_group_overrides(
            group_overrides, chat_file, tarot_file, allowed_groups
        )
        state_dir = os.environ.get("KISARA_STATE_DIR", "data/kisara").strip()
        if not state_dir:
            raise ConfigurationError("KISARA_STATE_DIR must not be empty.")
        news_options = {
            "news_push_groups": news_push_groups,
            "news_push_hour": news_push_hour,
            "news_push_minute": news_push_minute,
            "state_dir": state_dir,
            "admin_users": admin_users,
            "group_overrides": group_overrides,
        }

        if engine == "onebot":
            onebot_ws_url = (
                os.environ.get("ONEBOT_WS_URL", DEFAULT_ONEBOT_WS_URL).strip()
            )
            if not onebot_ws_url.startswith(("ws://", "wss://")):
                raise ConfigurationError(
                    "ONEBOT_WS_URL must start with ws:// or wss://."
                )
            onebot_access_token = _read_required(
                ("ONEBOT_ACCESS_TOKEN",), "ONEBOT_ACCESS_TOKEN"
            )
            return cls(
                engine=engine,
                instance_id=instance_id,
                allowed_users=allowed_users,
                groups_enabled=groups_enabled,
                allowed_groups=allowed_groups,
                onebot_ws_url=onebot_ws_url,
                onebot_access_token=onebot_access_token,
                **chat_options,
                **tarot_options,
                **public_options,
                **news_options,
            )

        app_id = _read_required(("AppID", "APP_ID"), "AppID")
        app_secret = _read_required(("AppSecret", "APP_SECRET"), "AppSecret")
        return cls(
            engine=engine,
            instance_id=instance_id,
            allowed_users=allowed_users,
            groups_enabled=groups_enabled,
            allowed_groups=allowed_groups,
            app_id=app_id,
            app_secret=app_secret,
            **chat_options,
            **tarot_options,
            **public_options,
            **news_options,
        )


def _read_required(names: Tuple[str, ...], label: str) -> str:
    """Return the first non-empty environment variable in ``names``."""

    for name in names:
        value = os.environ.get(name, "").strip()
        if value:
            return value

    raise ConfigurationError("Missing required configuration: {}.".format(label))


def _read_csv(name: str) -> FrozenSet[str]:
    """Read a comma-separated environment variable as normalized identifiers."""

    values = os.environ.get(name, "").split(",")
    return frozenset(value.strip() for value in values if value.strip())


def _read_bool(name: str, default: bool) -> bool:
    """Read a strict boolean environment variable."""

    raw_value = os.environ.get(name)
    if raw_value is None or not raw_value.strip():
        return default

    normalized = raw_value.strip().lower()
    if normalized in {"1", "true", "yes", "on"}:
        return True
    if normalized in {"0", "false", "no", "off"}:
        return False
    raise ConfigurationError(
        "{} must be one of true, false, 1, or 0.".format(name)
    )


def _read_percent(name: str, default: int) -> int:
    """Read an integer percentage from zero through one hundred."""

    value = os.environ.get(name, str(default)).strip()
    try:
        percent = int(value)
    except ValueError:
        raise ConfigurationError("{} must be an integer from 0 to 100.".format(name))
    if percent < 0 or percent > 100:
        raise ConfigurationError("{} must be an integer from 0 to 100.".format(name))
    return percent


def _parse_clock_time(value: str, name: str) -> Tuple[int, int]:
    """Parse an HH:MM China Standard Time schedule."""
    parts = value.split(":")
    if len(parts) != 2 or any(len(part) != 2 or not part.isdigit() for part in parts):
        raise ConfigurationError("{} must use HH:MM format.".format(name))
    hour, minute = (int(part) for part in parts)
    if hour > 23 or minute > 59:
        raise ConfigurationError("{} must be a valid time of day.".format(name))
    return hour, minute


def _read_group_overrides(allowed_groups: FrozenSet[str]) -> Mapping[str, GroupOverride]:
    """Load optional group settings without accepting unknown or disallowed keys."""

    configured_path = os.environ.get("KISARA_GROUP_CONFIG_PATH", "").strip()
    path = Path(configured_path or "config/groups.json")
    if not path.exists():
        if configured_path:
            raise ConfigurationError("Group config file does not exist: {}.".format(path))
        return {}
    try:
        document = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as error:
        raise ConfigurationError("Cannot read group config: {}.".format(error)) from error
    if not isinstance(document, dict):
        raise ConfigurationError("Group config must be a JSON object.")
    result: Dict[str, GroupOverride] = {}
    for group_id, value in document.items():
        if group_id not in allowed_groups:
            raise ConfigurationError("Group override is not in KISARA_ALLOWED_GROUPS: {}.".format(group_id))
        if not isinstance(value, dict) or set(value) - {"chat", "tarot"}:
            raise ConfigurationError("Invalid group override for {}.".format(group_id))
        chat = value.get("chat", {})
        tarot = value.get("tarot", {})
        if not isinstance(tarot, dict) or set(tarot) - {"spread_rate"}:
            raise ConfigurationError("Invalid tarot override for {}.".format(group_id))
        parsed_chat = _parse_chat_override(chat, group_id)
        spread_rate = tarot.get("spread_rate")
        if spread_rate is not None:
            spread_rate = _validate_percent(spread_rate, "spread_rate", group_id)
        result[group_id] = GroupOverride(parsed_chat, spread_rate)
    return result


def _merge_feature_group_overrides(
    legacy: Mapping[str, GroupOverride], chat_file: Mapping[str, object],
    tarot_file: Mapping[str, object], allowed_groups: FrozenSet[str],
) -> Mapping[str, GroupOverride]:
    """Apply each feature's group table over legacy group overrides."""
    result = dict(legacy)
    for group_id, value in groups(chat_file, "chat").items():
        if group_id not in allowed_groups:
            raise ConfigurationError("Chat group override is not allowed: {}.".format(group_id))
        old = result.get(group_id, GroupOverride())
        merged = dict(old.chat)
        merged.update(_parse_chat_override(value, group_id))
        result[group_id] = GroupOverride(merged, old.tarot_spread_rate)
    for group_id, value in groups(tarot_file, "tarot").items():
        if group_id not in allowed_groups:
            raise ConfigurationError("Tarot group override is not allowed: {}.".format(group_id))
        if not isinstance(value, dict) or set(value) - {"spread_rate"}:
            raise ConfigurationError("Invalid tarot override for {}.".format(group_id))
        old = result.get(group_id, GroupOverride())
        rate = old.tarot_spread_rate
        if "spread_rate" in value:
            rate = _validate_percent(value["spread_rate"], "spread_rate", group_id)
        result[group_id] = GroupOverride(old.chat, rate)
    return result


def _parse_chat_override(value: object, group_id: str) -> Mapping[str, object]:
    """Validate one chat group's policy fields for JSON or TOML."""
    string_fields = {"bot_name", "sender_name"}
    percent_fields = {"trigger_rate", "similarity_rate"}
    list_fields = {"ignored_phrases", "banned_users", "always_reply_users"}
    bool_fields = {"enabled", "reply_to_mentions"}
    if not isinstance(value, dict) or set(value) - (
        string_fields | percent_fields | list_fields | bool_fields
    ):
        raise ConfigurationError("Invalid chat override for {}.".format(group_id))
    parsed: Dict[str, object] = {}
    for name, item in value.items():
        if name in string_fields:
            if not isinstance(item, str) or not item.strip():
                raise ConfigurationError("Invalid {} for group {}.".format(name, group_id))
            parsed[name] = item.strip()
        elif name in percent_fields:
            parsed[name] = _validate_percent(item, name, group_id)
        elif name in bool_fields:
            if not isinstance(item, bool):
                raise ConfigurationError("Invalid {} for group {}.".format(name, group_id))
            parsed[name] = item
        else:
            if not isinstance(item, list) or any(
                not isinstance(entry, str) or not entry.strip() for entry in item
            ):
                raise ConfigurationError("Invalid {} for group {}.".format(name, group_id))
            parsed[name] = frozenset(entry.strip() for entry in item)
    return parsed


def _validate_percent(value: object, name: str, group_id: str) -> int:
    """Check a JSON percentage without treating booleans as integers."""

    if type(value) is not int or value < 0 or value > 100:
        raise ConfigurationError("Invalid {} for group {}: expected 0-100.".format(name, group_id))
    return value

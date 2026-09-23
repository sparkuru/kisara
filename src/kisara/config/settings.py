"""Environment-backed settings for the Kisara bot."""

import os
import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, FrozenSet, Mapping, Optional, Tuple


DEFAULT_ENGINE = "onebot"
DEFAULT_ONEBOT_WS_URL = "ws://napcat:3001"
SUPPORTED_ENGINES = ("onebot", "official")


class ConfigurationError(ValueError):
    """Raised when the selected engine is not correctly configured."""


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
        chat_options = {
            "chat_enabled": _read_bool("KISARA_CHAT_ENABLED", default=True),
            "chat_bot_name": os.environ.get("KISARA_CHAT_BOT_NAME", "Kisara").strip(),
            "chat_sender_name": os.environ.get("KISARA_CHAT_SENDER_NAME", "you").strip(),
            "chat_library": os.environ.get("KISARA_CHAT_LIBRARY", "cute").strip().lower(),
            "chat_trigger_rate": _read_percent("KISARA_CHAT_TRIGGER_RATE", 30),
            "chat_similarity_rate": _read_percent("KISARA_CHAT_SIMILARITY_RATE", 60),
            "chat_ignored_phrases": _read_csv("KISARA_CHAT_IGNORED_PHRASES"),
            "chat_banned_users": _read_csv("KISARA_CHAT_BANNED_USERS"),
            "chat_always_reply_users": _read_csv("KISARA_CHAT_ALWAYS_REPLY_USERS"),
            "chat_reply_to_mentions": _read_bool("KISARA_CHAT_REPLY_TO_MENTIONS", True),
        }
        if not chat_options["chat_bot_name"] or not chat_options["chat_sender_name"]:
            raise ConfigurationError("Chat display names must not be empty.")
        if chat_options["chat_library"] not in {"cute", "tsundere", "mixed"}:
            raise ConfigurationError(
                "KISARA_CHAT_LIBRARY must be cute, tsundere, or mixed."
            )
        tarot_options = {
            "tarot_enabled": _read_bool("KISARA_TAROT_ENABLED", default=True),
            "tarot_spread_rate": _read_percent("KISARA_TAROT_SPREAD_RATE", 5),
            "tarot_image_dir": os.environ.get(
                "KISARA_TAROT_IMAGE_DIR", "data/kisara/tarotCards"
            ).strip(),
        }
        public_options = {
            "saucenao_key": os.environ.get("SAUCENAO_API_KEY", "").strip(),
            "music_api_url": os.environ.get("KISARA_MUSIC_API_URL", "").strip(),
            "tianapi_key": os.environ.get("TIANAPI_KEY", "").strip(),
        }
        music_api_url = public_options["music_api_url"]
        if music_api_url and not music_api_url.startswith(("http://", "https://")):
            raise ConfigurationError("KISARA_MUSIC_API_URL must be an HTTP URL.")
        news_push_groups = _read_csv("KISARA_NEWS_PUSH_GROUPS")
        if news_push_groups and not groups_enabled:
            raise ConfigurationError("News push requires KISARA_GROUPS_ENABLED=true.")
        if news_push_groups and engine != "onebot":
            raise ConfigurationError("Scheduled news push requires the OneBot engine.")
        if not news_push_groups.issubset(allowed_groups):
            raise ConfigurationError("News push groups must be in KISARA_ALLOWED_GROUPS.")
        news_push_hour, news_push_minute = _read_clock_time("KISARA_NEWS_PUSH_TIME", "10:30")
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


def _read_clock_time(name: str, default: str) -> Tuple[int, int]:
    """Parse an HH:MM China Standard Time schedule."""

    value = os.environ.get(name, default).strip()
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
    chat_string_fields = {"bot_name", "sender_name"}
    chat_percent_fields = {"trigger_rate", "similarity_rate"}
    chat_list_fields = {"ignored_phrases", "banned_users", "always_reply_users"}
    chat_bool_fields = {"enabled", "reply_to_mentions"}
    chat_fields = chat_string_fields | chat_percent_fields | chat_list_fields | chat_bool_fields
    for group_id, value in document.items():
        if group_id not in allowed_groups:
            raise ConfigurationError("Group override is not in KISARA_ALLOWED_GROUPS: {}.".format(group_id))
        if not isinstance(value, dict) or set(value) - {"chat", "tarot"}:
            raise ConfigurationError("Invalid group override for {}.".format(group_id))
        chat = value.get("chat", {})
        tarot = value.get("tarot", {})
        if not isinstance(chat, dict) or set(chat) - chat_fields:
            raise ConfigurationError("Invalid chat override for {}.".format(group_id))
        if not isinstance(tarot, dict) or set(tarot) - {"spread_rate"}:
            raise ConfigurationError("Invalid tarot override for {}.".format(group_id))
        parsed_chat: Dict[str, object] = {}
        for name, item in chat.items():
            if name in chat_string_fields:
                if not isinstance(item, str) or not item.strip():
                    raise ConfigurationError("Invalid {} for group {}.".format(name, group_id))
                parsed_chat[name] = item.strip()
            elif name in chat_percent_fields:
                parsed_chat[name] = _validate_percent(item, name, group_id)
            elif name in chat_bool_fields:
                if not isinstance(item, bool):
                    raise ConfigurationError("Invalid {} for group {}.".format(name, group_id))
                parsed_chat[name] = item
            else:
                if not isinstance(item, list) or any(
                    not isinstance(entry, str) or not entry.strip() for entry in item
                ):
                    raise ConfigurationError("Invalid {} for group {}.".format(name, group_id))
                parsed_chat[name] = frozenset(entry.strip() for entry in item)
        spread_rate = tarot.get("spread_rate")
        if spread_rate is not None:
            spread_rate = _validate_percent(spread_rate, "spread_rate", group_id)
        result[group_id] = GroupOverride(parsed_chat, spread_rate)
    return result


def _validate_percent(value: object, name: str, group_id: str) -> int:
    """Check a JSON percentage without treating booleans as integers."""

    if type(value) is not int or value < 0 or value > 100:
        raise ConfigurationError("Invalid {} for group {}: expected 0-100.".format(name, group_id))
    return value

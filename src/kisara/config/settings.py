"""Environment-backed settings for the Kisara bot."""

import os
from dataclasses import dataclass
from typing import FrozenSet, Optional, Tuple


DEFAULT_ENGINE = "onebot"
DEFAULT_ONEBOT_WS_URL = "ws://napcat:3001"
SUPPORTED_ENGINES = ("onebot", "official")


class ConfigurationError(ValueError):
    """Raised when the selected engine is not correctly configured."""


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
        groups_enabled = _read_bool("KISARA_GROUPS_ENABLED", default=False)
        allowed_groups = _read_csv("KISARA_ALLOWED_GROUPS")

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

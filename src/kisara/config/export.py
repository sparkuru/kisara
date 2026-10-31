"""OneBot linked-video limits and an optional deployment-owned Bilibili session."""

from dataclasses import dataclass, field
from pathlib import Path
from typing import Mapping

from kisara.config.feature_files import ConfigurationError, boolean, load_feature, size_bytes


@dataclass(frozen=True)
class ExportConfig:
    """Keep video work bounded independently of original-image export."""

    video_enabled: bool = True
    max_file_bytes: int = 512 * 1024 * 1024
    timeout_seconds: int = 600
    max_urls: int = 3
    sessdata: str = field(default="", repr=False)

    @classmethod
    def load(cls, root: Path, environment: Mapping[str, str]) -> "ExportConfig":
        """Load operational TOML overrides and the selected engine's session."""
        values = load_feature("export", root)
        enabled = boolean(values, "video_enabled", lambda: _environment_bool(
            environment.get("KISARA_EXPORT_VIDEO_ENABLED", "true")), "export")
        size = values.get("max_file_bytes", environment.get("KISARA_EXPORT_MAX_FILE_BYTES", "512M"))
        max_bytes = size_bytes(size, "max_file_bytes", "export")
        if max_bytes > 1024 ** 3:
            raise ConfigurationError("export.max_file_bytes must not exceed 1G (2G workspace budget).")
        timeout = _positive(values, environment, "timeout_seconds", "600")
        max_urls = _positive(values, environment, "max_urls", "3")
        if max_urls > 20:
            raise ConfigurationError("export.max_urls must not exceed 20.")
        session = environment.get("KISARA_BILIBILI_SESSDATA", "").strip()
        if len(session) > 4096 or any(ord(char) < 33 or ord(char) > 126 or char == ";" for char in session):
            raise ConfigurationError("ONEBOT_BILIBILI_SESSDATA contains invalid cookie characters.")
        return cls(enabled, max_bytes, timeout, max_urls, session)


def _environment_bool(value: str) -> bool:
    """Use the same explicit boolean forms as other runtime switches."""
    lowered = value.strip().lower()
    if lowered not in {"true", "1", "yes", "on", "false", "0", "no", "off"}:
        raise ConfigurationError("KISARA_EXPORT_VIDEO_ENABLED must be a boolean.")
    return lowered in {"true", "1", "yes", "on"}


def _positive(values: Mapping[str, object], environment: Mapping[str, str], key: str, default: str) -> int:
    """Reject booleans, fractions and empty inputs without echoing their values."""
    value = values.get(key, environment.get("KISARA_EXPORT_" + key.upper(), default))
    if key not in values and isinstance(value, str) and value.isascii() and value.isdecimal():
        try:
            value = int(value)
        except ValueError:
            raise ConfigurationError("export.{} must be a positive integer.".format(key)) from None
    if type(value) is not int or value < 1:
        raise ConfigurationError("export.{} must be a positive integer.".format(key))
    return value

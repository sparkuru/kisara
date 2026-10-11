"""Startup validation for the opt-in Telegram archive policy."""

from pathlib import Path

import pytest

from kisara.config.settings import ConfigurationError
from kisara.config.tgsetu import TgSetuConfig


def test_missing_config_is_inert(tmp_path: Path) -> None:
    """Absence never enables or creates the feature."""
    assert TgSetuConfig.load(tmp_path / "missing.toml") == TgSetuConfig.disabled()
    assert not list(tmp_path.iterdir())


def test_valid_config_loads_binary_limits_and_user_ids(tmp_path: Path) -> None:
    """Dedicated settings normalize allowlists and timer/copy budgets."""
    path = tmp_path / "config.toml"
    path.write_text('enabled=true\nallowed_users=[" 123 ", "123"]\nmax_file_bytes="1M"\n'
                    'max_unit_bytes="2G"\nworkers=3\nalbum_quiet_seconds=0.5\n', encoding="utf-8")
    config = TgSetuConfig.load(path)
    assert config.enabled and config.allowed_users == frozenset({"123"})
    assert config.max_file_bytes == 1024 ** 2 and config.max_unit_bytes == 2 * 1024 ** 3
    assert config.workers == 3 and config.album_quiet_seconds == 0.5


@pytest.mark.parametrize("line", [
    "unknown=true", 'enabled="true"', 'allowed_users="123"', 'allowed_users=[123]',
    'allowed_users=["0123"]', 'allowed_users=["-123"]', 'allowed_users=[""]',
    "workers=true", "workers=0", "workers=17", "max_pending_files=-1", 'save_root=""',
    'max_file_bytes="0M"', 'max_file_bytes="1MB"', "max_unit_bytes=100", 'max_file_bytes="3G"',
    'max_file_bytes="{}M"'.format("9" * 4301),
    "album_quiet_seconds=0", "album_quiet_seconds=nan", "album_quiet_seconds=6",
    'save_root="/cache/archive"\ncache_root="/cache"',
])
def test_invalid_policy_fails_startup(tmp_path: Path, line: str) -> None:
    """Do not silently accept ambiguous types, unsafe roots or unbounded work."""
    path = tmp_path / "config.toml"
    path.write_text('max_unit_bytes="2G"\n' + line + "\n", encoding="utf-8")
    with pytest.raises(ConfigurationError):
        TgSetuConfig.load(path)

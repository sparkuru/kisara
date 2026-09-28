"""Tests for human-readable setu transfer limits."""

from pathlib import Path

import pytest

from kisara.config.setu import SetuConfig
from kisara.config.settings import ConfigurationError


@pytest.mark.parametrize(
    ("limit", "expected"),
    [("2K", 2 * 1024), ("3m", 3 * 1024 ** 2), ("1G", 1024 ** 3)],
)
def test_size_units_are_converted_to_bytes(
    tmp_path: Path, limit: str, expected: int,
) -> None:
    """The service receives byte counts from configured binary units."""
    path = tmp_path / "config.toml"
    path.write_text(
        'max_file_bytes = "1K"\nmax_batch_bytes = "{}"\n'.format(limit),
        encoding="utf-8",
    )

    config = SetuConfig.load(path)

    assert config.max_file_bytes == 1024
    assert config.max_batch_bytes == expected


@pytest.mark.parametrize(
    "value",
    ["1", "0", "-1", "true", '""', '"0M"', '"-1M"', '"1.5M"',
     '"1MB"', '"1T"', '"1 M"', '" 1M"', '"1M "', "1.5",
     pytest.param('"{}M"'.format("9" * 4301), id="oversized_decimal")],
)
@pytest.mark.parametrize("field", ["max_file_bytes", "max_batch_bytes"])
def test_size_limits_reject_unqualified_or_malformed_values(
    tmp_path: Path, field: str, value: str,
) -> None:
    """Only positive whole-number sizes with K, M, or G are accepted."""
    path = tmp_path / "config.toml"
    path.write_text("{} = {}\n".format(field, value), encoding="utf-8")

    with pytest.raises(ConfigurationError, match=field):
        SetuConfig.load(path)


def test_batch_limit_must_cover_file_limit(tmp_path: Path) -> None:
    """Compare converted byte values across different units."""
    path = tmp_path / "config.toml"
    path.write_text(
        'max_file_bytes = "2M"\nmax_batch_bytes = "1024K"\n', encoding="utf-8",
    )

    with pytest.raises(ConfigurationError, match="cover"):
        SetuConfig.load(path)


def test_example_and_omitted_limits_keep_original_byte_values(tmp_path: Path) -> None:
    """The published example and defaults retain the old effective caps."""
    example = Path(__file__).resolve().parents[2] / "config/features/setu/config.toml.example"
    missing_limits = tmp_path / "config.toml"
    missing_limits.write_text("enabled = false\n", encoding="utf-8")

    for config in (SetuConfig.load(example), SetuConfig.load(missing_limits)):
        assert config.max_file_bytes == 100 * 1024 ** 2
        assert config.max_batch_bytes == 1024 ** 3

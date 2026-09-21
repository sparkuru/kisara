"""Compatibility name for the moved official-platform adapter."""

from kisara.bot.adapters.official import OfficialAdapter

KisaraClient = OfficialAdapter

__all__ = ["KisaraClient"]

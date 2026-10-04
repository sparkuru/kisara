"""Explicit feature registration, platform support, switches and command help.

Definitions are static code. Native adapter workflows can call eligible() before
SDK effects; registration never loads executable paths from configuration.
"""

from dataclasses import dataclass
from typing import Callable, Mapping, Optional, Tuple

from kisara.bot.contracts import DispatchResult, MessageEvent


@dataclass(frozen=True)
class FeatureDefinition:
    """A feature's aliases, help and supported command/scheduled platforms."""

    name: str
    aliases: Tuple[str, ...]
    help_text: str
    engines: Tuple[str, ...] = ("onebot", "official", "telegram", "local")
    trigger: str = "command"
    telegram_aliases: Tuple[str, ...] = ()


QQ_ENGINES = ("onebot", "official", "local")
FEATURES = (
    FeatureDefinition("ping", ("ping",), "/ping — check whether Kisara is online"),
    FeatureDefinition("help", ("help", "ahelp"), "/help — show this command list", telegram_aliases=("start",)),
    FeatureDefinition("eat", ("eat", "what2eat"), "/eat — choose food suggestions", QQ_ENGINES),
    FeatureDefinition("roll", ("roll", "r", "dice"), "/roll [sides] or /roll <minimum> <maximum> [count]", QQ_ENGINES),
    FeatureDefinition("chat", ("chat",), "/chat <message> — ask the phrasebook directly", QQ_ENGINES),
    FeatureDefinition("tarot", ("tarot", "占卜"), "/tarot [single|spread] — draw a daily tarot reading", QQ_ENGINES),
    FeatureDefinition("wallpaper", ("wallpaper", "pixiv"), "/wallpaper — a Pixiv illustration", QQ_ENGINES),
    FeatureDefinition("source", ("source", "sauce"), "/source [similarity] + image — find an image source", QQ_ENGINES),
    FeatureDefinition("ba", ("ba", "guide"), "/ba <name> — find a Blue Archive guide", QQ_ENGINES),
    FeatureDefinition("music", ("music", "song"), "/music <song> — search a configured music API"),
    FeatureDefinition("love", ("love",), "/love — fetch a short love note", QQ_ENGINES),
    FeatureDefinition("recall", ("recall",), "/recall — recall a quoted bot message (OneBot)", QQ_ENGINES),
    FeatureDefinition("news", ("news", "brief", "news-clear"), "/news — today's daily news\n清除新闻缓存 — clear today's news PNG and HTML cache"),
    FeatureDefinition("news_push", (), "Scheduled daily news (configured recipients only)", ("onebot", "telegram"), "scheduled"),
)


@dataclass(frozen=True)
class RegisteredFeature:
    """Bind static metadata to an explicitly supplied application handler."""

    definition: FeatureDefinition
    handler: Callable[[MessageEvent, str, str], DispatchResult]


class FeatureRouter:
    """Resolve one alias once, then gate the handler by effective inventory."""

    def __init__(self, registrations: Tuple[RegisteredFeature, ...],
                 enabled: Mapping[str, bool]) -> None:
        self._registrations = registrations
        self._enabled = dict(enabled)
        self._aliases = {}
        for registration in registrations:
            for alias in registration.definition.aliases + registration.definition.telegram_aliases:
                if alias in self._aliases:
                    raise ValueError("Duplicate feature alias: {}".format(alias))
                self._aliases[alias] = registration

    def match(self, command: str, engine: str = "") -> Optional[RegisteredFeature]:
        """Return the sole registered owner of a normalized command."""
        registration = self._aliases.get(command)
        if registration and command in registration.definition.telegram_aliases and engine != "telegram":
            return None
        return registration

    def eligible(self, name: str, engine: str) -> bool:
        """Check registered platform support and effective startup switch."""
        return any(item.definition.name == name and engine in item.definition.engines
                   and self._enabled.get(name, True) for item in self._registrations)

    def help(self, engine: str) -> str:
        """Render only supported and enabled definitions in stable order."""
        return render_help(tuple(item.definition for item in self._registrations), self._enabled, engine)


def render_help(definitions: Tuple[FeatureDefinition, ...], enabled: Mapping[str, bool], engine: str) -> str:
    """Render command metadata without constructing executable dummy handlers."""
    lines = ["Available commands:"]
    for definition in definitions:
        if engine not in definition.engines or not enabled.get(definition.name, True):
            continue
        text = definition.help_text
        if engine == "telegram" and definition.name == "news":
            text = "/news — today's daily news\n/news_clear — clear today's news cache"
        if definition.trigger == "scheduled" and engine != "telegram":
            continue
        lines.append(text)
    return "\n".join(lines)

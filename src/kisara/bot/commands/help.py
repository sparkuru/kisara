"""Compatibility help entrypoint using the shared effective feature inventory."""

from kisara.bot.features import FEATURES, render_help


def execute(chat_enabled: bool = False, tarot_enabled: bool = False,
            public_enabled: bool = False, news_enabled: bool = False) -> str:
    """Return existing QQ/offline help from the same definitions as the router."""
    enabled = {
        "chat": chat_enabled, "tarot": tarot_enabled, "news": news_enabled,
        "news_push": False,
        **{name: public_enabled for name in ("wallpaper", "source", "ba", "music", "love", "recall")},
    }
    return render_help(FEATURES, enabled, "local")

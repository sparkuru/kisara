"""Shared help command for available text features."""


def execute(
    chat_enabled: bool = False,
    tarot_enabled: bool = False,
    public_enabled: bool = False,
) -> str:
    """Return a concise list of commands supported by Kisara."""

    commands = (
        "Available commands:\n"
        "/ping — check whether Kisara is online\n"
        "/help — show this command list\n"
        "/eat — choose food suggestions\n"
        "/roll [sides] or /roll <minimum> <maximum> [count]"
    )
    if chat_enabled:
        commands += "\n/chat <message> — ask the phrasebook directly"
    if tarot_enabled:
        commands += "\n/tarot [single|spread] — draw a daily tarot reading"
    if public_enabled:
        commands += (
            "\n/news — today's brief"
            "\n/wallpaper — a Pixiv illustration"
            "\n/source [similarity] + image — find an image source"
            "\n/ba <name> — find a Blue Archive guide"
            "\n/music <song> — search a configured music API"
            "\n/love — fetch a short love note"
            "\n/recall — recall a quoted bot message (OneBot)"
        )
    return commands

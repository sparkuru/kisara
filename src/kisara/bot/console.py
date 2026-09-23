"""Interactive offline console using the production message dispatcher."""

import os
import readline
import shutil
import sys
from datetime import datetime
from itertools import count
from time import perf_counter

from kisara.application.services.chat import ChatPolicy, ChatResponder
from kisara.application.services.tarot import TarotReader
from kisara.bot.contracts import DispatchResult, MessageEvent, MessageSegment
from kisara.bot.dispatcher import Dispatcher


class CLIStyle:
    """Color interactive output while keeping redirected output plain."""

    COLORS = {"TITLE": "36", "CONTENT": "32", "WARNING": "33", "META": "90", "ERROR": "31"}

    @classmethod
    def color(cls, text: str, role: str = "CONTENT", prompt: bool = False) -> str:
        """Apply a semantic terminal color when supported."""

        if not sys.stdout.isatty() or "NO_COLOR" in os.environ:
            return text
        start = "\033[1;{}m".format(cls.COLORS[role])
        end = "\033[0m"
        if prompt:
            # Readline excludes marked ANSI escapes from cursor width calculations.
            start, end = "\001" + start + "\002", "\001" + end + "\002"
        return start + text + end


def configure_line_editor() -> None:
    """Enable session history and familiar terminal editing bindings."""

    readline.parse_and_bind("set editing-mode emacs")
    for key, action in {
        r"\e[A": "previous-history",
        r"\e[B": "next-history",
        r"\e[C": "forward-char",
        r"\e[D": "backward-char",
        r"\e[1;5C": "forward-word",
        r"\e[1;5D": "backward-word",
        r"\e[H": "beginning-of-line",
        r"\e[F": "end-of-line",
        r"\e[3~": "delete-char",
    }.items():
        readline.parse_and_bind('"{}": {}'.format(key, action))
    readline.set_auto_history(True)


def print_turn_time() -> None:
    """Show a timezone-qualified timestamp for the current turn."""

    timestamp = datetime.now().astimezone().strftime("%Y-%m-%d %H:%M:%S %z")
    print(CLIStyle.color("[time] {}".format(timestamp), "META"))


def print_message(speaker: str, content: str, role: str = "CONTENT") -> None:
    """Align continuation lines beneath the message body."""

    prefix = "{} > ".format(speaker)
    lines = content.splitlines() or [""]
    body = ("\n" + " " * len(prefix)).join(lines)
    print(CLIStyle.color(prefix + body, role))


def process_turn(dispatcher: Dispatcher, event: MessageEvent) -> None:
    """Show an explicit outcome and keep the console usable after failures."""

    started = perf_counter()
    try:
        result = dispatcher.dispatch_result(event)
    except Exception as error:
        result = DispatchResult(
            "error", "{}: {}".format(type(error).__name__, error),
            "Command execution failed.",
        )
    elapsed_ms = (perf_counter() - started) * 1000
    role = {"handled": "CONTENT", "unhandled": "WARNING", "error": "ERROR"}[result.status]
    label = "[status] {}".format(result.status.upper())
    if result.reason:
        label += " - " + result.reason
    reply = result.reply if result.reply is not None else "(no reply)"
    if result.image_urls:
        reply += "\n" + "\n".join(result.image_urls)
    print_message("kisara", reply, role)
    print(CLIStyle.color("\n" + label, role))
    completed_at = datetime.now().astimezone().strftime("%Y-%m-%d %H:%M:%S %z")
    print(CLIStyle.color(
        "[last] Done in {}, elapsed: {:.2f} ms".format(completed_at, elapsed_ms),
        "META",
    ))
    width = max(1, shutil.get_terminal_size(fallback=(80, 24)).columns)
    print(CLIStyle.color("\n" + "-" * width + "\n", "META"))


def main() -> int:
    """Dispatch local private messages until EOF, interruption, or /quit."""

    if sys.stdin.isatty():
        configure_line_editor()
    dispatcher = Dispatcher(
        allowed_users=frozenset({"local-user"}),
        groups_enabled=False,
        allowed_groups=frozenset(),
        chat_responder=ChatResponder(ChatPolicy(trigger_rate=100)),
        tarot_reader=TarotReader(),
    )
    print(CLIStyle.color("Kisara offline console", "TITLE"))
    print(CLIStyle.color("Try /help, /chat hello, /tarot, or /roll 20. Exit: /quit or Ctrl-D."))
    if sys.stdin.isatty():
        print(CLIStyle.color(
            "Up/Down: history; Left/Right: move; Ctrl-Left/Right: move by word."
        ))
    try:
        for message_number in count(1):
            if sys.stdin.isatty():
                print_turn_time()
            prompt = CLIStyle.color("you > ", prompt=True) if sys.stdin.isatty() else ""
            text = input(prompt)
            if text.strip().lower() in {"/quit", "/exit"}:
                break
            if not text.strip():
                continue
            if not sys.stdin.isatty():
                print_turn_time()
                print_message("you", text)
            event = MessageEvent(
                engine="local",
                instance_id="offline-console",
                message_id=str(message_number),
                conversation_kind="private",
                conversation_id="local-conversation",
                sender_id="local-user",
                segments=(MessageSegment(kind="text", data={"text": text}),),
                reply_context={},
            )
            process_turn(dispatcher, event)
    except (EOFError, KeyboardInterrupt):
        print(CLIStyle.color("\nConsole closed.", "WARNING"))
    return 0


if __name__ == "__main__":
    sys.exit(main())

"""Exercise shared commands with synthetic events and no protocol adapter."""

from typing import Callable, Optional

import pytest

from kisara.bot.contracts import MessageEvent, MessageSegment
from kisara.bot.dispatcher import Dispatcher


@pytest.fixture
def dispatch_message() -> Callable[[str], Optional[str]]:
    """Build an allowed local user and dispatch text without engine setup."""

    dispatcher = Dispatcher(
        allowed_users=frozenset({"local-user"}),
        groups_enabled=False,
        allowed_groups=frozenset(),
    )
    message_number = 0

    def dispatch(text: str) -> Optional[str]:
        nonlocal message_number
        message_number += 1
        event = MessageEvent(
            engine="local",
            instance_id="offline-tester",
            message_id="local-{}".format(message_number),
            conversation_kind="private",
            conversation_id="local-conversation",
            sender_id="local-user",
            segments=(MessageSegment(kind="text", data={"text": text}),),
            reply_context={},
        )
        return dispatcher.dispatch(event)

    return dispatch


def test_roll_command_uses_inclusive_bounds_and_repeats(
    dispatch_message: Callable[[str], Optional[str]],
) -> None:
    """The offline route should allow repeated results from independent rolls."""

    assert dispatch_message("/roll 9 9 4") == (
        "Rolled 4 values (range: 9 to 9): 9, 9, 9, 9."
    )


def test_roll_command_caps_output(
    dispatch_message: Callable[[str], Optional[str]],
) -> None:
    """Large roll counts should be capped before formatting the response."""

    response = dispatch_message("/roll 1 1 40")

    assert response is not None
    assert response.startswith("Maximum 30 rolls; reduced to 30.\n")
    values = response.rsplit(": ", 1)[1].rstrip(".").split(", ")
    assert values == ["1"] * 30


def test_eat_command_returns_five_distinct_packaged_suggestions(
    dispatch_message: Callable[[str], Optional[str]],
) -> None:
    """Food suggestions should be loaded without external services."""

    response = dispatch_message("/eat")

    assert response is not None
    assert response.startswith("Try one of these: ")
    suggestions_text = response[len("Try one of these: ") :]
    suggestions = suggestions_text.rstrip(".").split(" | ")
    assert len(suggestions) == 5
    assert len(set(suggestions)) == 5


def test_help_command_lists_local_features(
    dispatch_message: Callable[[str], Optional[str]],
) -> None:
    """The offline command list should include the implemented features."""

    response = dispatch_message("/help")

    assert response is not None
    assert "/ping" in response
    assert "/eat" in response
    assert "/roll" in response

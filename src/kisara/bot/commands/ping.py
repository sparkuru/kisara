"""Answer /ping with pong for an allowed sender.

The dispatcher applies user and group allowlists before this command runs.
There is no feature configuration or persistent state.
"""


def execute() -> str:
    """Return the response for the ``/ping`` command."""

    return "pong"

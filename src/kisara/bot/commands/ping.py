"""Small shared health-check command."""


def execute() -> str:
    """Return the response for the ``/ping`` command."""

    return "pong"

"""Text command for rolling one or more dice."""

from kisara.application.services.dice import roll as roll_dice
from kisara.bot.contracts import CommandInputError


def execute(arguments: str = "") -> str:
    """Return a roll result or a user-facing validation message."""

    try:
        return execute_validated(arguments)
    except CommandInputError as error:
        return str(error)


def execute_validated(arguments: str = "") -> str:
    """Parse the legacy dice ranges and return their roll results."""

    tokens = arguments.split()
    if len(tokens) > 3:
        raise CommandInputError("Usage: /roll [sides] or /roll <minimum> <maximum> [count].")

    try:
        values = tuple(int(token) for token in tokens)
    except ValueError:
        raise CommandInputError("Usage: /roll [sides] or /roll <minimum> <maximum> [count].")

    if not values:
        start, end, count = 1, 100, 1
    elif len(values) == 1:
        if values[0] < 1:
            raise CommandInputError("The number of sides must be at least 1.")
        start, end, count = 1, values[0], 1
    elif len(values) == 2:
        start, end = values
        count = 1
    else:
        start, end, count = values

    if count < 1:
        raise CommandInputError("Roll count must be at least 1.")

    capped = count > 30
    count = min(count, 30)
    low, high = min(start, end), max(start, end)
    results = roll_dice(start, end, count)

    if count == 1:
        result = "Rolled {} (range: {} to {}).".format(results[0], low, high)
    else:
        result = "Rolled {} values (range: {} to {}): {}.".format(
            count, low, high, ", ".join(str(value) for value in results)
        )
    if capped:
        return "Maximum 30 rolls; reduced to 30.\n" + result
    return result

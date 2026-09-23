"""Text command for choosing food suggestions."""

from kisara.application.services.food import recommend_foods


def execute() -> str:
    """Return five suggestions from the packaged legacy food list."""

    foods = recommend_foods()
    return "Try one of these: {}.".format(" | ".join(foods))

"""Application entry point and dependency assembly for Kisara."""

import importlib
import logging

from kisara.bot.contracts import MessageAdapter, MessageHandler
from kisara.bot.dispatcher import Dispatcher
from kisara.config import ConfigurationError, Settings


_log = logging.getLogger("kisara")


def create_adapter(settings: Settings, handler: MessageHandler) -> MessageAdapter:
    """Load only the selected adapter and assemble it with the shared handler."""

    if settings.engine == "onebot":
        module = importlib.import_module("kisara.bot.adapters.onebot_v11")
        adapter_class = getattr(module, "OneBotV11Adapter")
    elif settings.engine == "official":
        module = importlib.import_module("kisara.bot.adapters.official")
        adapter_class = getattr(module, "OfficialAdapter")
    else:
        raise ConfigurationError("Unsupported engine: {}.".format(settings.engine))
    return adapter_class(settings, handler)


def main() -> int:
    """Validate settings, create the selected adapter, and run it."""

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    )

    try:
        settings = Settings.from_environment()
    except ConfigurationError as error:
        _log.error("%s", error)
        return 2

    dispatcher = Dispatcher(
        allowed_users=settings.allowed_users,
        groups_enabled=settings.groups_enabled,
        allowed_groups=settings.allowed_groups,
    )
    try:
        adapter = create_adapter(settings, dispatcher.dispatch)
    except ImportError as error:
        if settings.engine == "official":
            _log.error(
                "Official engine dependencies are missing; install .[official]: %s",
                error,
            )
        else:
            _log.error("OneBot engine dependencies are missing: %s", error)
        return 2

    _log.info("Starting Kisara with %s engine", settings.engine)
    try:
        adapter.start()
    except KeyboardInterrupt:
        _log.info("Stopping Kisara")
        return 130
    except Exception:
        _log.exception("Kisara stopped unexpectedly")
        return 1
    finally:
        adapter.close()
    return 0

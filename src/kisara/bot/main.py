"""Application entry point and dependency assembly for Kisara."""

import importlib
import logging
import sqlite3
from dataclasses import replace
from typing import Callable, Optional

from kisara.application.services.chat import ChatPolicy, ChatResponder
from kisara.application.services.public import PublicServices
from kisara.application.services.tarot import TarotReader
from kisara.bot.contracts import MessageAdapter, MessageHandler, OutgoingMessage
from kisara.bot.dispatcher import Dispatcher
from kisara.config import ConfigurationError, Settings
from kisara.infrastructure.persistence.news_delivery import NewsDeliveryStore


_log = logging.getLogger("kisara")


def create_adapter(
    settings: Settings,
    handler: MessageHandler,
    daily_news_factory: Optional[Callable[[], OutgoingMessage]] = None,
) -> MessageAdapter:
    """Load only the selected adapter and assemble it with the shared handler."""

    if settings.engine == "onebot":
        module = importlib.import_module("kisara.bot.adapters.onebot_v11")
        adapter_class = getattr(module, "OneBotV11Adapter")
        store = NewsDeliveryStore(settings.state_dir) if daily_news_factory else None
        return adapter_class(
            settings, handler, daily_news_factory=daily_news_factory,
            delivery_store=store,
        )
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

    chat_responder = None
    if settings.chat_enabled:
        chat_policy = ChatPolicy(
            bot_name=settings.chat_bot_name,
            sender_name=settings.chat_sender_name,
            library=settings.chat_library,
            trigger_rate=settings.chat_trigger_rate,
            similarity_rate=settings.chat_similarity_rate,
            ignored_phrases=settings.chat_ignored_phrases,
            banned_users=settings.chat_banned_users,
            always_reply_users=settings.chat_always_reply_users,
            reply_to_mentions=settings.chat_reply_to_mentions,
        )
        chat_responder = ChatResponder(
            chat_policy,
            {
                group_id: replace(chat_policy, **override.chat)
                for group_id, override in settings.group_overrides.items()
                if override.chat
            },
        )
    public_services = PublicServices(
        saucenao_key=settings.saucenao_key,
        music_api_url=settings.music_api_url,
        tianapi_key=settings.tianapi_key,
    )
    tarot_reader = None
    if settings.tarot_enabled:
        try:
            tarot_reader = TarotReader(
                settings.tarot_spread_rate,
                image_dir=settings.tarot_image_dir if settings.engine == "onebot" else None,
            )
        except ValueError as error:
            _log.error("Cannot load tarot images: %s", error)
            return 2
    dispatcher = Dispatcher(
        allowed_users=settings.allowed_users,
        groups_enabled=settings.groups_enabled,
        allowed_groups=settings.allowed_groups,
        chat_responder=chat_responder,
        tarot_reader=tarot_reader,
        tarot_group_rates={
            group_id: override.tarot_spread_rate
            for group_id, override in settings.group_overrides.items()
            if override.tarot_spread_rate is not None
        },
        public_services=public_services,
        admin_users=settings.admin_users,
    )

    def daily_news_factory() -> OutgoingMessage:
        """Build a fresh brief only when the scheduled send is due."""

        result = public_services.daily_news(require_today=True)
        return OutgoingMessage(result.text, result.image_urls)

    try:
        adapter = create_adapter(
            settings, dispatcher.dispatch_payload,
            daily_news_factory if settings.news_push_groups else None,
        )
    except ImportError as error:
        if settings.engine == "official":
            _log.error(
                "Official engine dependencies are missing; install .[official]: %s",
                error,
            )
        else:
            _log.error("OneBot engine dependencies are missing: %s", error)
        return 2
    except (OSError, sqlite3.Error) as error:
        _log.error("Cannot initialize bot state: %s", error)
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

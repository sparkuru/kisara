"""Telegram scheduled news through a narrow send gateway and durable claims.

Today's UTC+8 brief is generated off the loop once per pending pass. Generation
failures and known transient rejections retry after 15 minutes (or longer server
retry-after). Permanent rejections stop for the day. Unknown sends, cancellation
and failed completion writes preserve claim evidence and never auto-resend.
"""

import asyncio
import logging
import sqlite3
import time
from datetime import datetime, timedelta, timezone
from typing import Awaitable, Callable, Tuple

from kisara.bot.contracts import OutgoingMessage
from kisara.infrastructure.persistence.telegram_news import TelegramNewsStore


_log = logging.getLogger("kisara.telegram.news")
CHINA_TIME = timezone(timedelta(hours=8))


class DeliveryRejected(Exception):
    """A safe known Bot API rejection, classified by the owning adapter."""

    def __init__(self, permanent: bool = False, retry_after: float = 0) -> None:
        super().__init__("Telegram rejected delivery")
        self.permanent = permanent
        self.retry_after = retry_after


class TelegramNewsPush:
    """One owned scheduler with durable private/group target isolation."""

    def __init__(self, targets: Tuple[Tuple[str, str], ...], hour: int, minute: int,
                 factory: Callable[[], OutgoingMessage],
                 send: Callable[[str, OutgoingMessage], Awaitable[str]],
                 store: TelegramNewsStore,
                 clock: Callable[[], datetime] = lambda: datetime.now(CHINA_TIME),
                 timestamp: Callable[[], float] = time.time) -> None:
        self._targets = targets
        self._hour = hour
        self._minute = minute
        self._factory = factory
        self._send = send
        self._store = store
        self._clock = clock
        self._timestamp = timestamp

    async def run(self) -> None:
        """Catch up today only, with cancellation owned by the adapter."""
        while True:
            await self.deliver_due()
            await asyncio.sleep(30)

    async def deliver_due(self) -> None:
        """Claim before any send and checkpoint each target independently."""
        now = self._clock().astimezone(CHINA_TIME)
        if (now.hour, now.minute) < (self._hour, self._minute):
            return
        day = now.date().isoformat()
        self._store.prune(day)
        content = None
        generation_failed = False
        for kind, target in self._targets:
            if self._clock().astimezone(CHINA_TIME).date() != now.date():
                return
            stamp = self._timestamp()
            if not self._store.claim(day, kind, target, stamp):
                continue
            if generation_failed:
                self._store.reject(day, kind, target, stamp + 900)
                continue
            if content is None:
                try:
                    content = await asyncio.get_running_loop().run_in_executor(None, self._factory)
                except asyncio.CancelledError:
                    raise
                except Exception:
                    generation_failed = True
                    self._store.reject(day, kind, target, stamp + 900)
                    _log.warning("News generation failed; retry scheduled")
                    continue
            if self._clock().astimezone(CHINA_TIME).date() != now.date():
                self._store.reject(day, kind, target, 0, permanent=True)
                return
            try:
                message_id = await self._send(target, content)
            except asyncio.CancelledError:
                raise
            except DeliveryRejected as error:
                self._store.reject(day, kind, target, stamp + max(900, error.retry_after), error.permanent)
                _log.warning("Telegram news delivery rejected (%s)", "permanent" if error.permanent else "retryable")
            except Exception:
                self._store.uncertain(day, kind, target)
                _log.warning("Telegram news delivery outcome uncertain; automatic retry suppressed")
            else:
                try:
                    self._store.complete(day, kind, target, message_id)
                except (OSError, sqlite3.Error):
                    _log.warning("Telegram news checkpoint failed; claim retained without automatic retry")

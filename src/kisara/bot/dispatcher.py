"""Access control, de-duplication, and shared message routing."""

import time
from collections import OrderedDict
from typing import Callable, FrozenSet, Optional

from kisara.bot.commands.ping import execute as execute_ping
from kisara.bot.contracts import MessageEvent


class Dispatcher:
    """Route normalized events without depending on a platform SDK."""

    def __init__(
        self,
        allowed_users: FrozenSet[str],
        groups_enabled: bool,
        allowed_groups: FrozenSet[str],
        seen_limit: int = 1024,
        seen_ttl_seconds: float = 3600.0,
        clock: Callable[[], float] = time.monotonic,
    ) -> None:
        """Create a dispatcher with bounded in-memory duplicate tracking."""

        self._allowed_users = allowed_users
        self._groups_enabled = groups_enabled
        self._allowed_groups = allowed_groups
        self._seen_limit = seen_limit
        self._seen_ttl_seconds = seen_ttl_seconds
        self._clock = clock
        self._seen_messages = OrderedDict()

    def dispatch(self, event: MessageEvent) -> Optional[str]:
        """Return a shared response for an allowed event, if one is due."""

        if not self._is_allowed(event) or self._is_duplicate(event):
            return None

        content = event.text.strip()
        if content.lower() in {"/ping", "ping"}:
            return execute_ping()
        if not content:
            return "Kisara is online."
        return "Kisara received: {}".format(content[:500])

    def _is_allowed(self, event: MessageEvent) -> bool:
        """Check the sender, conversation kind, and group trigger policy."""

        if event.sender_id not in self._allowed_users:
            return False
        if event.conversation_kind == "group":
            return self._groups_enabled and self._group_is_allowed(event)
        return event.conversation_kind in {"private", "channel"}

    def _group_is_allowed(self, event: MessageEvent) -> bool:
        """Check the group allowlist and require a mention or command."""

        if event.conversation_id not in self._allowed_groups:
            return False
        if event.text.strip().startswith("/"):
            return True

        self_id = str(event.reply_context.get("self_id", ""))
        for segment in event.segments:
            if segment.kind != "at":
                continue
            mentioned_id = str(segment.data.get("qq", ""))
            if not mentioned_id or not self_id or mentioned_id == self_id:
                return True
        return False

    def _is_duplicate(self, event: MessageEvent) -> bool:
        """Return whether an event was already accepted within the TTL."""

        if not event.message_id:
            return False

        now = self._clock()
        expiry = now - self._seen_ttl_seconds
        while self._seen_messages:
            _, seen_at = next(iter(self._seen_messages.items()))
            if seen_at > expiry:
                break
            self._seen_messages.popitem(last=False)

        key = "\0".join(
            (
                event.engine,
                event.instance_id,
                event.message_id,
            )
        )
        if key in self._seen_messages:
            return True

        self._seen_messages[key] = now
        while len(self._seen_messages) > self._seen_limit:
            self._seen_messages.popitem(last=False)
        return False

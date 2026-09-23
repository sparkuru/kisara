"""Packaged phrasebook replies for allowed conversations."""

import csv
import io
import json
import pkgutil
import random
from collections import Counter, defaultdict
from dataclasses import dataclass
from typing import Dict, FrozenSet, Mapping, Optional, Set, Tuple

@dataclass(frozen=True)
class ChatPolicy:
    """Control phrasebook matching and who may trigger a reply."""

    bot_name: str = "Kisara"
    sender_name: str = "you"
    library: str = "cute"
    trigger_rate: int = 30
    similarity_rate: int = 60
    ignored_phrases: FrozenSet[str] = frozenset()
    banned_users: FrozenSet[str] = frozenset()
    always_reply_users: FrozenSet[str] = frozenset()
    reply_to_mentions: bool = True
    enabled: bool = True


class ChatResponder:
    """Match exact or similar phrases from the packaged conversation library."""

    def __init__(
        self, policy: ChatPolicy,
        group_policies: Optional[Mapping[str, ChatPolicy]] = None,
    ) -> None:
        """Load and index the phrasebook once per dispatcher."""

        if policy.library not in {"cute", "tsundere", "mixed"}:
            raise ValueError("Unknown chat library: {}.".format(policy.library))
        extension = "json" if policy.library == "mixed" else "csv"
        resource_name = "chat_{}.{}".format(policy.library, extension)
        content = pkgutil.get_data("kisara.resources", resource_name)
        if content is None:
            raise FileNotFoundError("Packaged chat data is unavailable.")
        data: Dict[str, list] = defaultdict(list)
        if policy.library == "mixed":
            data.update(json.loads(content.decode("utf-8")))
        else:
            reader = csv.DictReader(io.StringIO(content.decode("utf-8-sig")))
            if reader.fieldnames != ["reg", "reply"]:
                raise ValueError("Packaged chat data has invalid columns.")
            for row in reader:
                phrase = (row.get("reg") or "").strip()
                response = (row.get("reply") or "").strip()
                if phrase and response:
                    data[phrase].append(response)

        self._policy = policy
        self._group_policies = group_policies or {}
        self._responses: Dict[str, Tuple[str, ...]] = {}
        self._bigrams: Dict[str, Counter] = {}
        self._index: Dict[str, Set[str]] = defaultdict(set)
        self._rank: Dict[str, int] = {}
        for phrase, replies in data.items():
            if (
                not isinstance(phrase, str)
                or not phrase.strip()
                or not isinstance(replies, list)
                or not replies
                or any(not isinstance(reply, str) or not reply.strip() for reply in replies)
            ):
                raise ValueError("Packaged chat data contains an invalid entry.")
            self._responses[phrase] = tuple(replies)
            self._rank[phrase] = len(self._rank)
            grams = _bigrams(phrase)
            self._bigrams[phrase] = grams
            for gram in grams:
                self._index[gram].add(phrase)

    def reply(
        self, phrase: str, sender_id: str, mentioned: bool = False,
        force: bool = False, group_id: str = "",
    ) -> Optional[str]:
        """Return one phrasebook response when the message passes the policy."""

        policy = self._group_policies.get(group_id, self._policy)
        if not policy.enabled:
            return None
        phrase = phrase.strip().replace(policy.bot_name, "").strip()
        if not phrase or phrase in policy.ignored_phrases:
            return None
        if sender_id in policy.banned_users:
            return None

        forced = force or sender_id in policy.always_reply_users
        forced = forced or (policy.reply_to_mentions and mentioned)
        if not forced and random.randint(1, 100) > policy.trigger_rate:
            return None

        replies = self._responses.get(phrase)
        if replies is None:
            matched = self._closest_match(phrase, policy.similarity_rate)
            if matched is None:
                return None
            replies = self._responses[matched]

        response = random.choice(replies)
        return response.replace("{me}", policy.bot_name).replace(
            "{name}", policy.sender_name
        ).replace("{segment}", "\n")

    def _closest_match(self, phrase: str, similarity_rate: int) -> Optional[str]:
        """Find the best Dice bigram match above the configured threshold."""

        target = _bigrams(phrase)
        if not target:
            return None
        candidates: Set[str] = set()
        for gram in target:
            candidates.update(self._index.get(gram, ()))

        best_phrase: Optional[str] = None
        best_score = similarity_rate / 100.0
        for candidate in sorted(candidates, key=self._rank.__getitem__):
            source = self._bigrams[candidate]
            overlap = sum(min(count, source[gram]) for gram, count in target.items())
            score = 2 * overlap / (sum(target.values()) + sum(source.values()))
            if score > best_score or (score == best_score and best_phrase is None):
                best_phrase, best_score = candidate, score
        return best_phrase


def _bigrams(value: str) -> Counter:
    """Count adjacent characters using the old matcher whitespace rule."""

    normalized = "".join(value.split())
    return Counter(normalized[index : index + 2] for index in range(len(normalized) - 1))

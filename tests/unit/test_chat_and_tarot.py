"""Exercise migrated local features without a protocol connection."""

import json
import pkgutil
from datetime import date
from pathlib import Path
from urllib.parse import unquote, urlsplit

import pytest

from kisara.application.services.chat import ChatPolicy, ChatResponder
from kisara.application.services.tarot import TarotReader
from kisara.bot.contracts import MessageEvent, MessageSegment, OutgoingMessage
from kisara.bot.adapters.onebot_v11 import OneBotV11Adapter
from kisara.bot.dispatcher import Dispatcher


def test_phrasebook_sources_remain_separate_and_usable(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Both source styles and the old combined pool should load as shipped."""

    monkeypatch.setattr("kisara.application.services.chat.random.choice", lambda replies: replies[0])
    cute = ChatResponder(ChatPolicy(library="cute"))
    tsundere = ChatResponder(ChatPolicy(library="tsundere"))
    mixed = ChatResponder(ChatPolicy(library="mixed"))

    cute_reply = cute.reply("\u4f60", "user", force=True)
    tsundere_reply = tsundere.reply("\u4f60", "user", force=True)
    assert cute_reply and "Kisara" in cute_reply
    assert tsundere_reply and cute_reply != tsundere_reply
    assert mixed.reply("\u4f60", "user", force=True)


def test_phrasebook_respects_banned_users_and_disabled_probability() -> None:
    """A ban must take precedence over a forced reply and zero rate stays quiet."""

    responder = ChatResponder(ChatPolicy(trigger_rate=0, banned_users=frozenset({"blocked"})))

    assert responder.reply("\u4f60", "blocked", force=True) is None
    assert responder.reply("\u4f60", "allowed") is None
    assert responder.reply("\u4f60", "allowed", force=True)


def test_tarot_readings_are_stable_across_reader_instances() -> None:
    """The daily result must survive restarting the process."""

    today = lambda: date(2026, 9, 23)
    first = TarotReader(spread_rate=0, today=today)
    restarted = TarotReader(spread_rate=0, today=today)

    assert first.reading("user", "personal") == restarted.reading("user", "personal")
    assert first.reading("user", "personal") == first.reading("user", "personal", "single")
    spread = first.reading("user", "personal", "spread")
    assert len(spread.splitlines()) >= 4


def test_tarot_images_follow_the_stable_reading_and_reach_onebot(
    tmp_path: Path,
) -> None:
    """Installed art should accompany each drawn card without changing the text."""

    content = pkgutil.get_data("kisara.resources", "tarot_images.json")
    assert content is not None
    image_cards = json.loads(content.decode("utf-8"))
    for card in image_cards:
        folder = tmp_path / card["type"]
        folder.mkdir(exist_ok=True)
        (folder / "{}.png".format(card["pic"][0])).write_bytes(
            b"\x89PNG\r\n\x1a\n"
        )
    today = lambda: date(2026, 9, 23)
    illustrated = TarotReader(today=today, image_dir=str(tmp_path))
    plain = TarotReader(today=today)
    for mode in ("single", "spread"):
        text, images = illustrated.reading_with_images("user", "personal", mode)
        assert text == plain.reading("user", "personal", mode)
        assert images == illustrated.reading_with_images("user", "personal", mode)[1]
        assert len(images) == (1 if mode == "single" else len(text.splitlines()) - 1)
        assert all(
            Path(unquote(urlsplit(image).path)).is_file() for image in images
        )

    dispatcher = Dispatcher(
        allowed_users=frozenset({"user"}), groups_enabled=False,
        allowed_groups=frozenset(), tarot_reader=illustrated,
    )
    event = MessageEvent(
        engine="onebot", instance_id="personal", message_id="tarot-image-1",
        conversation_kind="private", conversation_id="user", sender_id="user",
        segments=(MessageSegment("text", {"text": "/tarot single"}),),
        reply_context={},
    )
    response = dispatcher.dispatch_payload(event)
    assert isinstance(response, OutgoingMessage)
    assert response.image_urls
    segments = OneBotV11Adapter._encode_message(response)
    assert segments[1] == {
        "type": "image", "data": {"file": response.image_urls[0]},
    }

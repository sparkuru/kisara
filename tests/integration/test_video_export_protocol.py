"""Native video export routing through correlated OneBot requests."""

import asyncio
import json
from dataclasses import replace
from pathlib import Path
from typing import Any

import pytest

from kisara.application.services.export_video import VideoExport
from kisara.bot.adapters import onebot_v11
from kisara.bot.adapters.onebot_v11 import OneBotV11Adapter
from kisara.bot.contracts import MessageEvent, MessageSegment
from kisara.config import Settings
from kisara.config.export import ExportConfig
from kisara.infrastructure.integrations.video_download import DownloadedVideo
from kisara.infrastructure.integrations.video_files import ExportSpool


class Peer:
    def __init__(self) -> None:
        self.sent = []

    async def send(self, raw: str) -> None:
        self.sent.append(json.loads(raw))


class Provider:
    def __init__(self, root: Path) -> None:
        self.spool = ExportSpool(root)
        self.calls = 0

    async def download(self, target: Any) -> DownloadedVideo:
        self.calls += 1
        job = self.spool.create()
        path = job / "video.mp4"
        path.write_bytes(b"complete")
        return DownloadedVideo(path, job, 1080, 30, path.stat().st_size)

    def release(self, video: DownloadedVideo, uncertain: bool = False) -> None:
        self.spool.retain(video.job) if uncertain else self.spool.remove(video.job)


def setup(root: Path) -> tuple:
    options = ExportConfig()
    provider = Provider(root)
    settings = Settings("onebot", "test", frozenset({"123"}), False, frozenset(),
                        onebot_ws_url="ws://unconnected", onebot_access_token="synthetic")
    adapter = OneBotV11Adapter(settings, lambda event: None, video_exporter=VideoExport(options, provider))
    peer = Peer()
    adapter._websocket = peer
    event = MessageEvent("onebot", "test", "command", "private", "123", "123",
                         (MessageSegment("text", {"text": "导出"}),),
                         {"quoted_message_id": "source", "self_id": "999"})
    return adapter, peer, provider, event


async def wait(peer: Peer, count: int) -> dict:
    for _ in range(200):
        if len(peer.sent) >= count:
            return peer.sent[count - 1]
        await asyncio.sleep(.005)
    raise AssertionError("missing OneBot request")


def ack(adapter: OneBotV11Adapter, request: dict, data: dict = None, failed: bool = False) -> None:
    adapter._resolve_pending({"echo": request["echo"], "status": "failed" if failed else "ok",
                              "retcode": 100 if failed else 0, "data": data or {"message_id": 456}})


@pytest.mark.parametrize("send_result", ["confirmed", "rejected", "unknown", "async"])
def test_video_return_uses_readable_local_path_and_receipt_lifetime(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, send_result: str,
) -> None:
    monkeypatch.setattr(onebot_v11, "_file_request_timeout", lambda size: .03)
    async def run() -> None:
        adapter, peer, provider, event = setup(tmp_path)
        task = asyncio.create_task(adapter._process_event(event))
        quote = await wait(peer, 1)
        assert quote["action"] == "get_msg"
        ack(adapter, quote, {"message_type": "private", "user_id": 123, "message": [
            {"type": "text", "data": {"text": "https://www.bilibili.com/video/av123"}},
        ]})
        ack(adapter, await wait(peer, 2))
        video_request = await wait(peer, 3)
        segment = video_request["params"]["message"][0]
        assert segment["type"] == "video" and segment["data"]["file"].startswith("file:///")
        assert video_request["params"]["user_id"] == 123
        path = Path(segment["data"]["file"][7:])
        assert path.read_bytes() == b"complete"
        if send_result == "async":
            adapter._resolve_pending({"echo": video_request["echo"], "status": "async",
                                      "retcode": 0, "data": {"message_id": 456}})
        elif send_result != "unknown":
            ack(adapter, video_request, failed=send_result == "rejected")
        completion = await wait(peer, 4)
        if send_result == "async":
            assert "结果未知" in completion["params"]["message"]
        ack(adapter, completion)
        await task
        assert path.exists() is (send_result in {"unknown", "async"})
        assert provider.calls == 1
    asyncio.run(run())


@pytest.mark.parametrize("case", ["sender", "group", "foreign_quote"])
def test_native_permission_and_quote_ownership_precede_provider(
    tmp_path: Path, case: str,
) -> None:
    async def run() -> None:
        adapter, peer, provider, event = setup(tmp_path)
        if case == "sender":
            event = replace(event, sender_id="456", conversation_id="456")
        elif case == "group":
            event = replace(event, conversation_kind="group", conversation_id="group1")
        task = asyncio.create_task(adapter._process_event(event))
        if case == "foreign_quote":
            ack(adapter, await wait(peer, 1), {"message_type": "private", "user_id": 456,
                "message": [{"type": "text", "data": {"text": "https://www.bilibili.com/video/av123"}}]})
            ack(adapter, await wait(peer, 2))
        await task
        assert provider.calls == 0
        if case != "foreign_quote":
            assert not peer.sent
    asyncio.run(run())

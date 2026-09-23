"""Check provider response contracts without network access."""

from typing import Any, Mapping, Optional

from kisara.application.services.public import PublicServices


class FakeReader:
    """Return provider-shaped payloads for each known URL."""

    def __init__(self, responses: Mapping[str, Any]) -> None:
        """Keep the response map for a single scenario."""

        self.responses = responses

    def get_json(
        self, url: str, params: Optional[Mapping[str, Any]] = None
    ) -> Any:
        """Return the requested provider response."""

        return self.responses[url]


def test_wallpaper_and_guide_return_native_image_urls() -> None:
    """Image features should keep metadata and media separate."""

    reader = FakeReader({
        "https://api.lolicon.app/setu/v2": {
            "data": [{"pid": 42, "title": "Art", "author": "Artist",
                      "r18": False, "urls": {"regular": "https://i.pixiv.re/42.jpg"}}],
        },
        "https://arona.diyigemt.com/api/v1/image": {
            "status": 200, "data": [{"name": "mika", "path": "/guide/mika.png"}],
        },
    })
    services = PublicServices(reader=reader)

    wallpaper = services.wallpaper()
    guide = services.blue_archive("mika")

    assert wallpaper.image_urls == ("https://i.pixiv.re/42.jpg",)
    assert "https://www.pixiv.net/artworks/42" in wallpaper.text
    assert guide.image_urls == ("https://arona.cdn.diyigemt.com/image/guide/mika.png",)


def test_news_and_music_parse_current_provider_shapes() -> None:
    """Briefing images and song cards should be structured for OneBot."""

    reader = FakeReader({
        "https://60s.viki.moe/v2/60s": {
            "code": 200,
            "data": {"date": "2026-09-23", "news": ["One headline"],
                     "image": "https://cdn.jsdmirror.com/brief.png"},
        },
        "http://music:3000/search": {
            "result": {"songs": [{"id": 123, "name": "Song",
                                  "artists": [{"name": "Artist"}]}]},
        },
    })
    services = PublicServices(reader=reader, music_api_url="http://music:3000")

    news = services.daily_news()
    music = services.music("Song")

    assert "One headline" in news.text
    assert news.image_urls == ("https://cdn.jsdmirror.com/brief.png",)
    assert music.music_id == "123"
    assert "https://music.163.com/#/song?id=123" in music.text


def test_source_search_filters_by_similarity() -> None:
    """Only links for matches above the requested threshold should be shown."""

    reader = FakeReader({
        "https://saucenao.com/search.php": {
            "results": [
                {"header": {"similarity": "82.0"},
                 "data": {"title": "Match", "ext_urls": ["https://example.com/match"]}},
                {"header": {"similarity": "40.0"},
                 "data": {"title": "Weak", "ext_urls": ["https://example.com/weak"]}},
            ],
        },
    })
    services = PublicServices(reader=reader, saucenao_key="test-key")

    result = services.source_search("https://example.com/query.jpg", 70)

    assert "Match" in result.text
    assert "https://example.com/match" in result.text
    assert "Weak" not in result.text

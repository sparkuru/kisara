"""Provider-backed /wallpaper, /ba, /source, /music, and /love commands.

/wallpaper fetches a non-adult Pixiv illustration. /ba <name> finds a Blue
Archive guide. /source [similarity] needs an image attachment, or on OneBot a
reply to an image, and config/features/source/config.toml api_key for SauceNAO.
/music <song> needs config/features/music/config.toml api_url for a compatible
search API; the optional Compose music profile serves http://music:3000 within
its network. /love needs config/features/love/config.toml api_key for TianAPI.

Responses carry text and optional image URLs or a music ID. OneBot sends native
image/music segments; the official adapter renders media links as text. HTTP
reads have a ten-second timeout and unavailable providers produce an error
reply. These queries do not create application database records. Daily /news
is implemented separately in application/services/daily_news.py.
"""

from dataclasses import dataclass
from typing import Any, Mapping, Optional, Sequence, Tuple
from urllib.parse import quote, urlsplit

from kisara.infrastructure.integrations.http import HttpReader, RemoteServiceError


@dataclass(frozen=True)
class RemoteResult:
    """A provider result ready for a protocol adapter to render."""

    text: str
    image_urls: Tuple[str, ...] = ()
    music_id: Optional[str] = None


class PublicServices:
    """Call bounded provider APIs and return normalized results."""

    def __init__(
        self,
        reader: Optional[HttpReader] = None,
        saucenao_key: str = "",
        music_api_url: str = "",
        tianapi_key: str = "",
    ) -> None:
        """Keep provider credentials and endpoints outside message routing."""

        self._reader = reader or HttpReader()
        self._saucenao_key = saucenao_key
        self._music_api_url = music_api_url.rstrip("/")
        self._tianapi_key = tianapi_key

    def wallpaper(self) -> RemoteResult:
        """Fetch one non-adult Pixiv illustration and its attribution."""

        payload = self._reader.get_json(
            "https://api.lolicon.app/setu/v2", {"r18": 0, "size": "regular"}
        )
        item = _first_item(payload, "data")
        if item.get("r18"):
            raise RemoteServiceError("Provider returned an excluded image.")
        urls = item.get("urls")
        if not isinstance(urls, dict):
            raise RemoteServiceError("Wallpaper provider omitted image URLs.")
        image_url = str(urls.get("regular") or urls.get("original") or "")
        image = _trusted_image(image_url, ("i.pixiv.re", "i.pximg.net"))
        if not image:
            raise RemoteServiceError("Wallpaper provider returned an invalid image URL.")
        title = str(item.get("title") or "Untitled")
        author = str(item.get("author") or "Unknown artist")
        pid = str(item.get("pid") or "")
        text = "Pixiv: {} — {}\nArtwork: https://www.pixiv.net/artworks/{}".format(
            title, author, pid
        )
        return RemoteResult(text, (image,))

    def blue_archive(self, query: str) -> RemoteResult:
        """Find one Blue Archive guide or offer disambiguation options."""

        payload = self._reader.get_json(
            "https://arona.diyigemt.com/api/v1/image", {"name": query}
        )
        if not isinstance(payload, dict):
            raise RemoteServiceError("Guide provider returned invalid data.")
        items = payload.get("data")
        if not isinstance(items, list) or not items:
            return RemoteResult("No Blue Archive guide found for {}.".format(query))
        if payload.get("status") != 200:
            choices = ", ".join(str(item.get("name", "")) for item in items[:8]
                                if isinstance(item, dict))
            return RemoteResult("Choose a more specific guide: {}".format(choices))
        item = items[0]
        if not isinstance(item, dict):
            raise RemoteServiceError("Guide provider returned an invalid item.")
        path = str(item.get("path") or "")
        if not path.startswith("/") or ".." in path.split("/"):
            raise RemoteServiceError("Guide provider returned an invalid image path.")
        image_url = "https://arona.cdn.diyigemt.com/image{}".format(
            quote(path, safe="/")
        )
        name = str(item.get("name") or query)
        return RemoteResult("Blue Archive guide: {}".format(name), (image_url,))

    def source_search(self, image_url: str, similarity: int = 70) -> RemoteResult:
        """Look up an incoming image URL using the SauceNAO JSON API."""

        if not self._saucenao_key:
            raise RemoteServiceError("SauceNAO API key is not configured.")
        parsed = urlsplit(image_url)
        if parsed.scheme not in {"http", "https"} or not parsed.hostname:
            raise RemoteServiceError("An HTTP image URL is required.")
        if similarity < 1 or similarity > 99:
            raise ValueError("similarity must be from 1 to 99")
        payload = self._reader.get_json(
            "https://saucenao.com/search.php",
            {
                "url": image_url,
                "db": 999,
                "api_key": self._saucenao_key,
                "output_type": 2,
                "numres": 3,
            },
        )
        if not isinstance(payload, dict):
            raise RemoteServiceError("Image search returned invalid data.")
        results = payload.get("results")
        if not isinstance(results, list):
            header = payload.get("header")
            message = header.get("message", "No results") if isinstance(header, dict) else "No results"
            raise RemoteServiceError("Image search: {}".format(str(message)[:200]))
        lines = ["Image search results (minimum {}%):".format(similarity)]
        for result in results:
            if not isinstance(result, dict):
                continue
            header, data = result.get("header"), result.get("data")
            if not isinstance(header, dict) or not isinstance(data, dict):
                continue
            try:
                score = float(header.get("similarity", 0))
            except (TypeError, ValueError):
                continue
            if score < similarity:
                continue
            title = str(data.get("title") or data.get("source") or "Untitled")
            lines.append("{:.1f}% — {}".format(score, title))
            urls = data.get("ext_urls")
            if isinstance(urls, list):
                lines.extend(str(url) for url in urls[:2] if _public_link(url))
        if len(lines) == 1:
            return RemoteResult("No image source met the {}% threshold.".format(similarity))
        return RemoteResult("\n".join(lines))

    def music(self, query: str) -> RemoteResult:
        """Search a configured local Netease API and return a native music card."""

        if not self._music_api_url:
            raise RemoteServiceError("Music search API is not configured.")
        payload = self._reader.get_json(
            self._music_api_url + "/search", {"keywords": query, "limit": 1}
        )
        if not isinstance(payload, dict):
            raise RemoteServiceError("Music provider returned invalid data.")
        result = payload.get("result")
        songs = result.get("songs") if isinstance(result, dict) else None
        if not isinstance(songs, list) or not songs:
            return RemoteResult("No song found for {}.".format(query))
        song = songs[0]
        if not isinstance(song, dict):
            raise RemoteServiceError("Music provider returned an invalid song.")
        song_id = str(song.get("id") or "")
        if not song_id.isdigit():
            raise RemoteServiceError("Music provider omitted a song ID.")
        artists = song.get("artists") or song.get("ar") or []
        artist = ", ".join(str(item.get("name", "")) for item in artists
                           if isinstance(item, dict))
        title = str(song.get("name") or query)
        text = "{} — {}\nhttps://music.163.com/#/song?id={}".format(
            title, artist or "Unknown artist", song_id
        )
        return RemoteResult(text, music_id=song_id)

    def love_note(self) -> RemoteResult:
        """Fetch one short note from the maintained TianAPI endpoint."""

        if not self._tianapi_key:
            raise RemoteServiceError("TianAPI key is not configured.")
        payload = self._reader.get_json(
            "https://apis.tianapi.com/tiangou/index", {"key": self._tianapi_key}
        )
        if not isinstance(payload, dict) or payload.get("code") != 200:
            raise RemoteServiceError("Short text provider returned an error.")
        result = payload.get("result")
        content = str(result.get("content") or "").strip() if isinstance(result, dict) else ""
        if not content or len(content) > 1000:
            raise RemoteServiceError("Short text provider returned invalid content.")
        return RemoteResult(content)


def _first_item(payload: Any, key: str) -> Mapping[str, Any]:
    """Extract the first object from a provider list."""

    values = payload.get(key) if isinstance(payload, dict) else None
    if not isinstance(values, list) or not values or not isinstance(values[0], dict):
        raise RemoteServiceError("Provider returned no usable item.")
    return values[0]


def _trusted_image(url: str, hosts: Sequence[str]) -> str:
    """Accept only HTTPS images from expected provider hosts."""

    try:
        parsed = urlsplit(url)
        if parsed.scheme != "https" or parsed.hostname not in hosts:
            return ""
        if parsed.username or parsed.password or parsed.port not in {None, 443}:
            return ""
    except ValueError:
        return ""
    return url


def _public_link(value: Any) -> bool:
    """Keep only public-looking HTTP links in search result text."""

    if not isinstance(value, str):
        return False
    parsed = urlsplit(value)
    return parsed.scheme in {"http", "https"} and bool(parsed.hostname)

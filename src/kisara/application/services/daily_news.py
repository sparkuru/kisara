"""Render, cache, and serve the daily LyToday brief for /news.

/news, /brief, and legacy news aliases return a PNG built from today's LyToday
HTML page. It includes the 15 headlines, visible trend lists, historical items,
almanac, and daily quote. The first request validates the page date and
headlines, keeps the source HTML temporarily in /tmp, and writes YYYYMMDD.png;
later requests reuse a valid image for the China Standard Time day. OneBot
sends the image, which credits https://60s.lylme.com/ at its top. The official
adapter replies with its date and source URL. config/features/news/config.toml
controls cache_days (default 7), optional cache_dir, and ordered font_paths
(the first CJK-capable file is selected, with bundled fonts as fallback).
The local default is data/daily-news;
Compose sets /app/state/daily-news in its persistent kisara_state volume.
Expired dated images are pruned.

The temporary HTML cache is scoped to the current operating-system user and
prunes older pages on the next HTML read. A failed or stale fetch is not cached,
so the next request can retry. No database is used for source content.

Optional OneBot daily push uses push_groups (allowed groups with groups enabled)
and push_users (canonical positive decimal QQ strings in KISARA_ALLOWED_USERS).
Private push works with groups disabled. Both share push_time (default 10:30
China Standard Time). Missing push_users falls back to comma-separated
KISARA_NEWS_PUSH_USERS; explicit TOML, including [], wins. Empty target lists
disable scheduled push. The connected-session adapter loop creates one payload
per pending iteration and records confirmed sends in separate deliveries and
private_deliveries tables in KISARA_STATE_DIR/news_delivery.sqlite3 (Compose
/app/state on kisara_state). Existing group records remain valid. Both tables
retain 30 days of completion history. Failed or unrecorded sends retry after
15 minutes; a late connection catches up today only, with no historical backfill.
Disconnect cancels the loop; reconnect checks durable state before sending.
Unknown remote outcomes or failed local writes can still cause duplicates.
Private delivery depends on the logged-in QQ account being able to contact the
recipient. Ordinary /news requests do not need a scheduled subscription.
"""

import base64
import io
import os
import re
import stat
import tempfile
from dataclasses import dataclass
from datetime import date, datetime, timedelta, timezone
from html.parser import HTMLParser
from pathlib import Path
from threading import Lock
from typing import Callable, List, Optional, Sequence, Tuple

from PIL import Image, ImageDraw, ImageFont, UnidentifiedImageError
from PIL.PngImagePlugin import PngInfo

from kisara.infrastructure.integrations.http import HttpReader, RemoteServiceError
from kisara.utils.files import atomic_write_bytes
from kisara.utils.pangu import pangu
from kisara.utils.text import wrap_text


SOURCE_URL = "https://60s.lylme.com/"
CHINA_TIME = timezone(timedelta(hours=8))
FONT_PATHS = (
    "/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc",
    "/usr/share/fonts/truetype/noto/NotoSansCJK-Regular.ttc",
    "/usr/share/fonts/truetype/wqy/wqy-microhei.ttc",
)
MAX_HOT_SECTIONS = 8
MAX_HOT_ITEMS = 10
MAX_HISTORY_ITEMS = 20
MAX_IMAGE_HEIGHT = 9_000
PNG_LAYOUT_VERSION = "lylme-centered-headings-v2"


@dataclass(frozen=True)
class DailyPage:
    """The dated page content selected for one readable news image."""

    headlines: Tuple[str, ...]
    hot_sections: Tuple[Tuple[str, Tuple[str, ...]], ...]
    history: Tuple[str, ...]
    calendar: Tuple[str, ...]
    quote: str
    news_title: str
    hot_title: str
    history_title: str
    calendar_title: str
    quote_title: str


@dataclass(frozen=True)
class DailyNewsResult:
    """Point to the cached image used for a dated brief."""

    day: date
    image_path: Path

    @property
    def text(self) -> str:
        """Identify the news date and original source."""

        return "Daily news for {}\nSource: {}".format(self.day.isoformat(), SOURCE_URL)

    def onebot_image(self) -> str:
        """Embed the cached file so the separate OneBot container can send it."""

        try:
            content = self.image_path.read_bytes()
        except OSError as error:
            raise RemoteServiceError("Cached daily news image is unavailable.") from error
        return "base64://" + base64.b64encode(content).decode("ascii")


class DailyNews:
    """Read today's LyToday data once and keep a dated local image cache."""

    def __init__(
        self,
        cache_dir: Path = Path("data/daily-news"),
        cache_days: int = 7,
        reader: Optional[HttpReader] = None,
        clock: Optional[Callable[[], datetime]] = None,
        renderer: Optional[Callable[[date, DailyPage], bytes]] = None,
        temp_dir: Optional[Path] = None,
        font_paths: Optional[Sequence[str]] = None,
    ) -> None:
        """Configure cache retention and replaceable provider/render boundaries."""

        if cache_days < 1:
            raise ValueError("cache_days must be positive")
        self._cache_dir = Path(cache_dir)
        self._cache_days = cache_days
        self._reader = reader or HttpReader()
        self._clock = clock or (lambda: datetime.now(CHINA_TIME))
        selected_fonts = (
            tuple(font_paths) + FONT_PATHS if font_paths is not None else FONT_PATHS
        )
        self._renderer = renderer or (
            lambda day, page: render_news_image(day, page, selected_fonts)
        )
        self._temp_dir = temp_dir or Path(tempfile.gettempdir()) / (
            "kisara-daily-news-{}".format(os.getuid())
        )
        self._lock = Lock()

    def get(self) -> DailyNewsResult:
        """Return today's cached PNG, fetching and rendering it only once."""

        today = self._clock().astimezone(CHINA_TIME).date()
        path = self._cache_dir / "{}.png".format(today.strftime("%Y%m%d"))
        with self._lock:
            try:
                self._cache_dir.mkdir(parents=True, exist_ok=True)
                self._prune(today)
                if _valid_png(path):
                    return DailyNewsResult(today, path)
                page = self._load_page(today)
                image = self._renderer(today, page)
                if not _valid_png_bytes(image):
                    raise RemoteServiceError("Daily news renderer returned an invalid PNG.")
                atomic_write_bytes(path, image)
            except OSError as error:
                raise RemoteServiceError("Daily news cache is unavailable.") from error
        return DailyNewsResult(today, path)

    def _load_page(self, today: date) -> DailyPage:
        """Reuse validated HTML on disk before fetching the source page."""

        self._temp_dir.mkdir(mode=0o700, parents=True, exist_ok=True)
        info = self._temp_dir.lstat()
        if (not stat.S_ISDIR(info.st_mode) or info.st_uid != os.getuid()
                or info.st_mode & 0o077):
            raise RemoteServiceError("Daily news temporary cache is unsafe.")
        for old in self._temp_dir.glob("*.html"):
            if re.fullmatch(r"\d{8}\.html", old.name) and old.stem != today.strftime("%Y%m%d"):
                old.unlink()
        path = self._temp_dir / "{}.html".format(today.strftime("%Y%m%d"))
        if path.is_file():
            try:
                if path.stat().st_size <= 2_000_000:
                    return _page_for_today(path.read_text(encoding="utf-8"), today)
            except (RemoteServiceError, UnicodeError):
                pass
            path.unlink()
        html = self._reader.get_text(SOURCE_URL)
        page = _page_for_today(html, today)
        atomic_write_bytes(path, html.encode("utf-8"))
        return page

    def _prune(self, today: date) -> None:
        """Delete only expired images with the cache's dated filename format."""

        first_kept = today - timedelta(days=self._cache_days - 1)
        for path in self._cache_dir.glob("*.png"):
            if not re.fullmatch(r"\d{8}\.png", path.name):
                continue
            try:
                day = datetime.strptime(path.stem, "%Y%m%d").date()
            except ValueError:
                continue
            if day < first_kept:
                path.unlink()


class _DailyPageParser(HTMLParser):
    """Extract visible text from the dated LyToday page sections."""

    def __init__(self) -> None:
        """Initialize the source fields in their display order."""

        super().__init__(convert_charrefs=True)
        self.year = ""
        self.month_day = ""
        self.headlines: List[str] = []
        self.hot_sections: List[Tuple[str, List[str]]] = []
        self.history: List[str] = []
        self.calendar: List[str] = []
        self.quote = ""
        self.titles = {}
        self._in_header = False
        self._section = ""
        self._in_list = ""
        self._capture = ""
        self._parts: List[str] = []

    def handle_starttag(self, tag: str, attrs: list) -> None:
        """Capture source headings, list items, calendar fields, and the quote."""

        if tag == "header":
            self._in_header = True
        elif self._in_header and tag == "p" and not self.year:
            self._start_capture("year")
        elif self._in_header and tag == "h2":
            self._start_capture("date")
        elif tag == "h1" and not self._in_header:
            self._start_capture("heading")
        elif tag == "h2" and self._section == "hot":
            self._start_capture("hot_heading")
        elif tag == "ul" and self._section in {"news", "history"}:
            self._in_list = self._section
        elif tag == "li" and self._in_list:
            self._start_capture("item")
        elif tag == "td" and self._section == "hot":
            classes = dict(attrs).get("class", "").split()
            if "hot" in classes and "h2" in classes and self.hot_sections:
                self._start_capture("hot_item")
        elif tag == "div" and self._section == "calendar":
            attributes = dict(attrs)
            if attributes.get("id") in {
                "md", "ymd", "yi", "ji", "jshen", "xshen",
            } or set(attributes.get("class", "").split()) & {
                "nayin", "chongsha", "pengzu", "xishen", "fushen", "caishen",
            }:
                self._start_capture("calendar_item")
        elif tag == "p" and self._section == "quote" and not self.quote:
            self._start_capture("quote")

    def handle_data(self, data: str) -> None:
        """Preserve text inside linked items and nested spans."""

        if self._capture:
            self._parts.append(data)

    def handle_endtag(self, tag: str) -> None:
        """Finalize the selected field when its outer element closes."""

        targets = {
            "year": "p", "date": "h2", "heading": "h1", "hot_heading": "h2",
            "item": "li", "hot_item": "td", "calendar_item": "div", "quote": "p",
        }
        if self._capture == "calendar_item" and tag in {"b", "i"}:
            self._parts.append(" ")
        if self._capture and tag == targets[self._capture]:
            value = " ".join("".join(self._parts).split())
            if self._capture == "year":
                self.year = value
            elif self._capture == "date":
                self.month_day = value
            elif self._capture == "heading":
                heading = re.search(r"「([^」]+)」", value)
                names = {
                    "60秒读懂世界": "news", "实时热搜": "hot",
                    "历史上的今天": "history", "今日黄历": "calendar",
                    "每日一语": "quote",
                }
                self._section = names.get(heading.group(1), "") if heading else ""
                if self._section:
                    self.titles[self._section] = heading.group(1)
            elif self._capture == "hot_heading":
                heading = re.search(r"「([^」]+)」", value)
                if heading and len(self.hot_sections) < MAX_HOT_SECTIONS:
                    self.hot_sections.append((heading.group(1), []))
            elif self._capture == "item":
                if self._in_list == "news":
                    self.headlines.append(value)
                elif self._in_list == "history" and len(self.history) < MAX_HISTORY_ITEMS:
                    self.history.append(value)
            elif self._capture == "hot_item":
                items = self.hot_sections[-1][1]
                if value and len(items) < MAX_HOT_ITEMS:
                    items.append(value)
            elif self._capture == "calendar_item" and value:
                self.calendar.append(value)
            elif self._capture == "quote":
                self.quote = value
            self._capture = ""
            self._parts = []
        if tag == "ul" and self._in_list:
            self._in_list = ""
        elif tag == "header":
            self._in_header = False

    def _start_capture(self, name: str) -> None:
        """Start collecting the text of one relevant element."""

        self._capture = name
        self._parts = []


def _page_for_today(html: str, today: date) -> DailyPage:
    """Reject stale or incomplete HTML before naming it as today's image."""

    parser = _DailyPageParser()
    parser.feed(html)
    match = re.fullmatch(r"(\d{1,2})月(\d{1,2})日", parser.month_day)
    if not re.fullmatch(r"\d{4}", parser.year) or match is None:
        raise RemoteServiceError("Daily news page omitted its date.")
    try:
        published = date(int(parser.year), int(match.group(1)), int(match.group(2)))
    except ValueError as error:
        raise RemoteServiceError("Daily news page returned an invalid date.") from error
    if published != today:
        raise RemoteServiceError("Today's daily news is not yet available.")
    if len(parser.headlines) != 15 or any(
        not item or len(item) > 300 for item in parser.headlines
    ):
        raise RemoteServiceError("Daily news page returned invalid headlines.")
    return DailyPage(
        headlines=tuple(parser.headlines),
        hot_sections=tuple(
            (name[:80], tuple(item[:300] for item in items))
            for name, items in parser.hot_sections if items
        ),
        history=tuple(item[:300] for item in parser.history if item),
        calendar=tuple(item[:300] for item in parser.calendar if item),
        quote=parser.quote[:500],
        news_title=parser.titles.get("news", "60秒读懂世界"),
        hot_title=parser.titles.get("hot", "实时热搜"),
        history_title=parser.titles.get("history", "历史上的今天"),
        calendar_title=parser.titles.get("calendar", "今日黄历"),
        quote_title=parser.titles.get("quote", "每日一语"),
    )


def _valid_png(path: Path) -> bool:
    """Reuse only a complete image generated with the current page layout."""

    try:
        with Image.open(path) as image:
            current_layout = image.info.get("kisara_layout") == PNG_LAYOUT_VERSION
            image.verify()
            return image.format == "PNG" and current_layout
    except (FileNotFoundError, OSError, UnidentifiedImageError):
        return False


def _valid_png_bytes(content: bytes) -> bool:
    """Check rendered output before replacing the cache entry."""

    try:
        with Image.open(io.BytesIO(content)) as image:
            current_layout = image.info.get("kisara_layout") == PNG_LAYOUT_VERSION
            image.verify()
            return image.format == "PNG" and current_layout
    except (OSError, UnidentifiedImageError):
        return False


def render_news_image(
    day: date, page: DailyPage, font_paths: Sequence[str] = FONT_PATHS,
) -> bytes:
    """Draw the source page's sections in one dated, attributed PNG."""

    font_path = None
    for path in font_paths:
        try:
            candidate = ImageFont.truetype(path, 20)
        except OSError:
            continue
        if not _font_has_cjk(candidate):
            continue
        font_path = path
        break
    if font_path is None:
        raise RemoteServiceError("No CJK-capable daily news font is available.")
    title_font = ImageFont.truetype(font_path, 44)
    metadata_font = ImageFont.truetype(font_path, 20)
    section_font = ImageFont.truetype(font_path, 34)
    group_font = ImageFont.truetype(font_path, 27)
    body_font = ImageFont.truetype(font_path, 23)
    compact_font = ImageFont.truetype(font_path, 21)
    width = 960
    measure = ImageDraw.Draw(Image.new("RGB", (1, 1)))
    rows: List[Tuple[str, ImageFont.FreeTypeFont, str, int, int, bool]] = []

    def add(text: str, font: ImageFont.FreeTypeFont, color: str,
            indent: int, line_height: int, gap: int,
            centered: bool = False) -> None:
        """Wrap one source entry and reserve its drawing height."""

        formatted = pangu(text)
        max_width = width - 104 if centered else width - indent - 52
        for line in wrap_text(
            formatted, max_width,
            lambda candidate: measure.textlength(candidate, font=font),
        ):
            rows.append((line, font, color, indent, line_height, centered))
        rows.append(("", font, color, indent, gap, centered))

    def section(title: str) -> None:
        """Add a visible break before a source section."""

        rows.append(("", section_font, "", 52, 15, True))
        add("「{}」".format(title), section_font, "#23456b", 52, 45, 12, True)

    section(page.news_title)
    for item in page.headlines:
        add(item, body_font, "#202938", 52, 35, 12)
    if page.hot_sections:
        section(page.hot_title)
        for name, items in page.hot_sections:
            add(name, group_font, "#315e89", 52, 39, 7, True)
            for index, item in enumerate(items, 1):
                add("{}. {}".format(index, item), compact_font, "#263746", 66, 31, 5)
            rows.append(("", compact_font, "", 52, 8, False))
    if page.history:
        section(page.history_title)
        for item in page.history:
            add(item, compact_font, "#263746", 52, 31, 5)
    if page.calendar:
        section(page.calendar_title)
        for item in page.calendar:
            add(item, compact_font, "#263746", 52, 31, 5)
    if page.quote:
        section(page.quote_title)
        add(page.quote, body_font, "#202938", 52, 36, 8)

    height = 216 + sum(row[4] for row in rows) + 52
    if height > MAX_IMAGE_HEIGHT:
        raise RemoteServiceError("Daily news page is too long to render safely.")
    image = Image.new("RGB", (width, height), "#f5f6f8")
    draw = ImageDraw.Draw(image)
    draw.rounded_rectangle((24, 24, width - 24, height - 24), radius=24, fill="white")
    draw.rounded_rectangle((24, 24, width - 24, 184), radius=24, fill="#23456b")
    draw.rectangle((24, 148, width - 24, 184), fill="#23456b")
    title = "60s Daily News"
    title_x = (width - draw.textlength(title, font=title_font)) / 2
    draw.text((title_x, 49), title, font=title_font, fill="white")
    source_label = "© Source: " + SOURCE_URL
    weekday_label = "{} / 星期{}".format(
        day.isoformat(), "一二三四五六日"[day.weekday()],
    )
    draw.text((52, 134), source_label, font=metadata_font, fill="#dce8f5")
    date_x = width - 52 - draw.textlength(weekday_label, font=metadata_font)
    draw.text((date_x, 134), weekday_label, font=metadata_font, fill="#dce8f5")
    y = 216
    for line, font, color, indent, step, centered in rows:
        if line:
            x = (width - draw.textlength(line, font=font)) / 2 if centered else indent
            draw.text((x, y), line, font=font, fill=color)
        y += step
    output = io.BytesIO()
    metadata = PngInfo()
    metadata.add_text("kisara_layout", PNG_LAYOUT_VERSION)
    image.save(output, format="PNG", optimize=True, pnginfo=metadata)
    return output.getvalue()


def _font_has_cjk(font: ImageFont.FreeTypeFont) -> bool:
    """Skip a font if common Han characters render as its missing-glyph box."""

    missing = font.getmask("\u0378")
    signature = (missing.size, bytes(missing))
    return all(
        (mask.size, bytes(mask)) != signature
        for mask in (font.getmask("中"), font.getmask("闻"))
    )

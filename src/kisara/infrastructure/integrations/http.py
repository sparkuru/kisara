"""Small bounded HTTP reader for remote command providers."""

import json
from typing import Any, Mapping, Optional
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import HTTPRedirectHandler, Request, build_opener


class RemoteServiceError(RuntimeError):
    """A remote provider returned an unusable response."""


class _NoRedirect(HTTPRedirectHandler):
    """Keep a provider response from redirecting requests to another host."""

    def redirect_request(self, request: Request, fp: Any, code: int,
                         msg: str, headers: Any, newurl: str) -> None:
        """Reject an unexpected redirect."""

        return None


class HttpReader:
    """Read bounded text or JSON from an explicit provider URL."""

    def __init__(self, timeout: float = 10.0, max_bytes: int = 2_000_000) -> None:
        """Set network and response size limits for each call."""

        self._timeout = timeout
        self._max_bytes = max_bytes
        self._opener = build_opener(_NoRedirect())

    def get_json(
        self, url: str, params: Optional[Mapping[str, Any]] = None
    ) -> Any:
        """Fetch and decode one JSON response."""

        payload = self.get_text(url, params)
        try:
            return json.loads(payload)
        except ValueError as error:
            raise RemoteServiceError("Provider returned invalid JSON.") from error

    def get_text(
        self, url: str, params: Optional[Mapping[str, Any]] = None
    ) -> str:
        """Fetch UTF-8 text with an explicit byte and time limit."""

        if params:
            separator = "&" if "?" in url else "?"
            url += separator + urlencode(params)
        request = Request(url, headers={"User-Agent": "Kisara/0.1"})
        try:
            with self._opener.open(request, timeout=self._timeout) as response:
                content = response.read(self._max_bytes + 1)
        except HTTPError as error:
            raise RemoteServiceError(
                "Provider returned HTTP {}.".format(error.code)
            ) from error
        except (OSError, URLError) as error:
            raise RemoteServiceError("Provider is unavailable.") from error
        if len(content) > self._max_bytes:
            raise RemoteServiceError("Provider response is too large.")
        try:
            return content.decode("utf-8")
        except UnicodeDecodeError as error:
            raise RemoteServiceError("Provider returned invalid UTF-8.") from error

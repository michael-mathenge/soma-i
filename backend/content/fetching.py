from dataclasses import dataclass
from urllib.error import HTTPError
from urllib.parse import urlsplit
from urllib.request import HTTPRedirectHandler, Request, build_opener

MAX_FEED_BYTES = 5 * 1024 * 1024
LIVE_TIMEOUT_SECONDS = 10
USER_AGENT = "SOMA.i feed ingester/1.0 (educational content app)"


@dataclass(frozen=True)
class FetchResponse:
    status: int
    headers: dict
    body: bytes


class LimitedHTTPSRedirectHandler(HTTPRedirectHandler):
    max_redirections = 5
    max_repeats = 5

    def redirect_request(self, request, response, code, message, headers, new_url):
        if urlsplit(new_url).scheme.lower() != "https":
            raise ValueError("Feed redirects must remain on HTTPS")
        return super().redirect_request(
            request, response, code, message, headers, new_url
        )


def _header(headers, name):
    for key, value in headers.items():
        if key.lower() == name.lower():
            return value
    return ""


def fetch_feed(url, headers=None, timeout=LIVE_TIMEOUT_SECONDS):
    parsed = urlsplit(url)
    if parsed.scheme.lower() != "https" or not parsed.hostname:
        raise ValueError("Feed URL must use HTTPS")

    request_headers = {"User-Agent": USER_AGENT}
    request_headers.update(headers or {})
    request = Request(url, headers=request_headers)
    opener = build_opener(LimitedHTTPSRedirectHandler())
    try:
        response = opener.open(request, timeout=timeout)
    except HTTPError as error:
        if error.code == 304:
            return FetchResponse(
                status=304,
                headers=dict(error.headers.items()) if error.headers else {},
                body=b"",
            )
        raise

    with response:
        response_headers = dict(response.headers.items())
        content_length = _header(response_headers, "Content-Length")
        if content_length and int(content_length) > MAX_FEED_BYTES:
            raise ValueError("Feed response exceeds the 5 MB limit")
        body = response.read(MAX_FEED_BYTES + 1)
        if len(body) > MAX_FEED_BYTES:
            raise ValueError("Feed response exceeds the 5 MB limit")
        status = getattr(response, "status", None)
        if status is None:
            status = response.getcode()
        return FetchResponse(status=status, headers=response_headers, body=body)

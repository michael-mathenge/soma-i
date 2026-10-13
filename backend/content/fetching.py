import socket
import ssl
import unicodedata
from dataclasses import dataclass
from datetime import UTC, datetime
from email.utils import parsedate_to_datetime
from http.client import HTTPConnection, HTTPSConnection
from ipaddress import ip_address, ip_network
from math import isfinite
from queue import Empty, Queue
from threading import Thread, Timer
from time import monotonic, sleep
from urllib.parse import urljoin, urlsplit
from urllib.request import HTTPRedirectHandler, Request

MAX_FEED_BYTES = 5 * 1024 * 1024
LIVE_TIMEOUT_SECONDS = 10
TOTAL_FETCH_SECONDS = 20
MAX_ATTEMPTS = 2
MAX_RETRY_DELAY_SECONDS = 2
USER_AGENT = "SOMA.i feed ingester/1.0 (educational content app)"
REDIRECT_STATUSES = {301, 302, 303, 307, 308}
RETRY_STATUSES = {429, 500, 502, 503, 504}
TRANSITION_NETWORKS = (
    ip_network("64:ff9b::/96"),
    ip_network("64:ff9b:1::/48"),
    ip_network("2002::/16"),
)


@dataclass(frozen=True)
class FetchResponse:
    status: int
    headers: dict
    body: bytes


class FeedFetchError(ValueError):
    """Safe fixed diagnostics: never include a URL or remote response text."""


class TransientFeedError(FeedFetchError):
    pass


def _public_address(value):
    address = ip_address(value)
    if (
        "%" in value
        or not address.is_global
        or address.is_multicast
        or address.is_reserved
        or getattr(address, "teredo", None)
        or any(address in network for network in TRANSITION_NETWORKS)
    ):
        raise FeedFetchError("Feed destination is not a public unicast address")
    return address


def validate_feed_url(url):
    if not isinstance(url, str) or not url or "\\" in url:
        raise FeedFetchError("Invalid feed URL")
    if any(char.isspace() or unicodedata.category(char) in {"Cc", "Cf"} for char in url):
        raise FeedFetchError("Invalid feed URL")
    try:
        parsed = urlsplit(url)
        host = parsed.hostname
        port = parsed.port
    except ValueError as exc:
        raise FeedFetchError("Invalid feed URL") from exc
    if parsed.scheme.lower() != "https" or not host:
        raise FeedFetchError("Feed URL must use HTTPS")
    if "@" in parsed.netloc or parsed.fragment or port not in (None, 443):
        raise FeedFetchError("Feed credentials, fragments and non-HTTPS ports are forbidden")
    if host.endswith(".") or host.endswith((".localhost", ".local", ".internal")):
        raise FeedFetchError("Local or ambiguous feed host is forbidden")
    try:
        ip_address(host)
    except ValueError:
        if (
            "." not in host
            or not host.isascii()
            or any(not (char.isalnum() or char in ".-") for char in host)
        ):
            raise FeedFetchError("Invalid feed hostname")
    else:
        _public_address(host)
    return parsed


class LimitedHTTPSRedirectHandler(HTTPRedirectHandler):
    max_redirections = 5
    max_repeats = 5

    def __init__(self, allowed_urls=None):
        super().__init__()
        self.allowed_urls = allowed_urls

    def redirect_request(self, request, response, code, message, headers, new_url):
        if urlsplit(new_url).scheme.lower() != "https":
            raise FeedFetchError("Feed redirects must remain on HTTPS")
        validate_feed_url(new_url)
        if self.allowed_urls is not None and new_url not in self.allowed_urls:
            raise FeedFetchError("Feed redirect endpoint is not approved")
        return super().redirect_request(
            request, response, code, message, headers, new_url
        )


def _header(headers, name):
    for key, value in headers.items():
        if key.lower() == name.lower():
            return value
    return ""


def _remaining(deadline):
    remaining = deadline - monotonic()
    if remaining <= 0:
        raise FeedFetchError("Feed fetch exceeded its total time budget")
    return remaining


def _public_addresses(host, deadline):
    """Bound DNS waiting and reject mixed public/private answer sets."""
    result = Queue(maxsize=1)

    def resolve():
        try:
            result.put(socket.getaddrinfo(host, 443, type=socket.SOCK_STREAM))
        except OSError:
            result.put(None)

    worker = Thread(target=resolve, name="soma-feed-dns", daemon=True)
    worker.start()
    try:
        addresses = result.get(timeout=_remaining(deadline))
    except Empty as exc:
        raise FeedFetchError("Feed DNS lookup exceeded its time budget") from exc
    if not addresses:
        raise TransientFeedError("Feed DNS lookup failed")
    for family, _kind, _protocol, _name, address in addresses:
        if family not in (socket.AF_INET, socket.AF_INET6):
            raise FeedFetchError("Unsupported feed address family")
        _public_address(address[0])
    return addresses[:2]


class _PinnedHTTPSConnection(HTTPSConnection):
    """Connect only to vetted numeric addresses; retain TLS SNI/certificate checks."""

    def __init__(self, host, addresses, timeout, deadline):
        super().__init__(host, port=443, timeout=timeout, context=ssl.create_default_context())
        self.addresses = addresses
        self.deadline = deadline
        self.active_socket = None
        self._create_connection = self._connect_vetted

    def _connect_vetted(self, _address, timeout, _source_address=None):
        for family, kind, protocol, _name, address in self.addresses:
            connection = socket.socket(family, kind, protocol)
            self.active_socket = connection
            try:
                connection.settimeout(min(timeout, _remaining(self.deadline)))
                connection.connect(address)
                return connection
            except FeedFetchError:
                connection.close()
                raise
            except OSError:
                connection.close()
        raise TransientFeedError("Feed connection failed")

    def connect(self):
        if self._tunnel_host:
            raise FeedFetchError("Feed proxies and tunnels are forbidden")
        HTTPConnection.connect(self)
        self.sock.settimeout(min(self.timeout, _remaining(self.deadline)))
        self.sock = self._context.wrap_socket(
            self.sock, server_hostname=self.host, do_handshake_on_connect=False
        )
        self.active_socket = self.sock
        self.sock.do_handshake()

    def abort(self):
        connection = self.active_socket or self.sock
        if connection is not None:
            try:
                connection.shutdown(socket.SHUT_RDWR)
            except OSError:
                pass
            connection.close()


def _request_once(url, headers, timeout, deadline):
    parsed = validate_feed_url(url)
    addresses = _public_addresses(parsed.hostname, deadline)
    connection = _PinnedHTTPSConnection(
        parsed.hostname, addresses, min(timeout, _remaining(deadline)), deadline
    )
    watchdog = Timer(_remaining(deadline), connection.abort)
    watchdog.daemon = True
    watchdog.start()
    response = None
    try:
        path = parsed.path or "/"
        if parsed.query:
            path += "?" + parsed.query
        connection.request("GET", path, headers=headers)
        response = connection.getresponse()
        response_headers = dict(response.getheaders())
        if response.status != 200:
            return FetchResponse(response.status, response_headers, b"")
        encoding = _header(response_headers, "Content-Encoding").lower()
        if encoding not in ("", "identity"):
            raise FeedFetchError("Compressed feed responses are not supported")
        expected_length = None
        content_length = _header(response_headers, "Content-Length")
        if content_length:
            try:
                length = int(content_length)
            except ValueError as exc:
                raise FeedFetchError("Invalid feed Content-Length") from exc
            expected_length = length
            if length < 0 or length > MAX_FEED_BYTES:
                raise FeedFetchError("Feed response exceeds the 5 MB limit")
        body = bytearray()
        while True:
            _remaining(deadline)
            connection.active_socket.settimeout(min(timeout, _remaining(deadline)))
            chunk = response.read1(min(65536, MAX_FEED_BYTES + 1 - len(body)))
            if not chunk:
                break
            body.extend(chunk)
            if len(body) > MAX_FEED_BYTES:
                raise FeedFetchError("Feed response exceeds the 5 MB limit")
        _remaining(deadline)
        if expected_length is not None and len(body) != expected_length:
            raise FeedFetchError("Incomplete feed response")
        return FetchResponse(response.status, response_headers, bytes(body))
    finally:
        watchdog.cancel()
        if response is not None:
            response.close()
        connection.close()


def _retry_delay(headers):
    value = _header(headers, "Retry-After")
    delay = 1.0
    if value:
        try:
            delay = float(value)
        except ValueError:
            try:
                retry_at = parsedate_to_datetime(value)
                if retry_at.tzinfo is None:
                    retry_at = retry_at.replace(tzinfo=UTC)
                delay = (retry_at - datetime.now(UTC)).total_seconds()
            except (ValueError, TypeError, OverflowError) as exc:
                raise FeedFetchError("Invalid Retry-After") from exc
    if not isfinite(delay) or delay > MAX_RETRY_DELAY_SECONDS:
        raise FeedFetchError("Retry-After exceeds the retry budget")
    return max(0, delay)


def fetch_feed(url, headers=None, timeout=LIVE_TIMEOUT_SECONDS, *, allowed_urls=None):
    validate_feed_url(url)
    if not allowed_urls or url not in allowed_urls:
        raise FeedFetchError("An exact approved feed endpoint allowlist is required")
    for allowed in allowed_urls:
        validate_feed_url(allowed)
    if not isinstance(timeout, (int, float)) or not isfinite(timeout) or timeout <= 0:
        raise FeedFetchError("Invalid feed timeout")
    timeout = min(timeout, LIVE_TIMEOUT_SECONDS)
    request_headers = {
        "User-Agent": USER_AGENT,
        "Accept": "application/rss+xml, application/atom+xml, application/xml, text/xml",
        "Accept-Encoding": "identity",
    }
    for name, value in (headers or {}).items():
        if (
            name.lower() not in {"if-none-match", "if-modified-since"}
            or not isinstance(value, str)
            or len(value) > 512
            or any(char in value for char in "\r\n")
        ):
            raise FeedFetchError("Invalid conditional feed headers")
        request_headers[name] = value
    deadline = monotonic() + TOTAL_FETCH_SECONDS
    redirector = LimitedHTTPSRedirectHandler(frozenset(allowed_urls))
    for attempt in range(MAX_ATTEMPTS):
        current_url = url
        current_headers = dict(request_headers)
        retry_headers = {}
        try:
            for redirect_count in range(redirector.max_redirections + 1):
                _remaining(deadline)
                response = _request_once(current_url, current_headers, timeout, deadline)
                _remaining(deadline)
                if response.status in REDIRECT_STATUSES:
                    if redirect_count == redirector.max_redirections:
                        raise FeedFetchError("Feed redirect limit exceeded")
                    destination = urljoin(current_url, _header(response.headers, "Location"))
                    if not _header(response.headers, "Location"):
                        raise FeedFetchError("Feed redirect lacks a destination")
                    redirector.redirect_request(
                        Request(current_url), None, response.status, "", {}, destination
                    )
                    if urlsplit(destination).netloc != urlsplit(current_url).netloc:
                        current_headers = {
                            key: value for key, value in current_headers.items()
                            if key.lower() not in {"if-none-match", "if-modified-since"}
                        }
                    current_url = destination
                    continue
                if response.status in RETRY_STATUSES:
                    retry_headers = response.headers
                    raise TransientFeedError(f"Temporary feed HTTP status {response.status}")
                if response.status not in (200, 304):
                    raise FeedFetchError(f"Unexpected feed HTTP status {response.status}")
                return response
        except ssl.SSLError as exc:
            raise FeedFetchError("Feed TLS validation failed") from exc
        except (TransientFeedError, OSError) as exc:
            if attempt + 1 == MAX_ATTEMPTS:
                raise FeedFetchError("Feed failed after bounded attempts") from exc
            delay = _retry_delay(retry_headers)
            if delay >= _remaining(deadline):
                raise FeedFetchError("Feed retry exceeds the total time budget") from exc
            sleep(delay)
    raise FeedFetchError("Feed fetch failed")

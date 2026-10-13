from datetime import date
from queue import Empty
from time import monotonic

import pytest

from content import fetching
from content.permissions import FeedPermissionError, approved_feed_urls

URL = "https://feeds.example.test/rss.xml"
OTHER_URL = "https://other.example.test/rss.xml"
PUBLIC = (fetching.socket.AF_INET, fetching.socket.SOCK_STREAM, 6, "", ("93.184.216.34", 443))


@pytest.fixture(autouse=True)
def no_real_network(monkeypatch):
    calls = []

    def blocked_dns(*_args, **_kwargs):
        calls.append("DNS")
        raise OSError("test network disabled")

    def blocked_socket(*_args, **_kwargs):
        pytest.fail("test attempted a real socket")

    monkeypatch.setattr(fetching.socket, "getaddrinfo", blocked_dns)
    monkeypatch.setattr(fetching.socket, "socket", blocked_socket)
    monkeypatch.setattr(fetching, "sleep", lambda _seconds: None)
    yield
    assert calls == [], "test attempted unmocked DNS"


def permission_feed():
    return {
        "url": URL,
        "permissions": {
            "feed_access": True,
            "metadata_reuse": True,
            "excerpt_reuse": True,
            "reviewed_by": "Offline test reviewer",
            "scope": "Fictional test feed metadata and excerpts only",
            "evidence_url": "https://publisher.example.test/permission",
            "reviewed_on": "2026-10-01",
            "expires_on": "2026-10-31",
            "allowed_urls": [URL],
        },
    }


@pytest.mark.parametrize(
    "change",
    [
        {"feed_access": False},
        {"metadata_reuse": "true"},
        {"excerpt_reuse": 1},
        {"reviewed_by": ""},
        {"scope": None},
        {"evidence_url": "https://user:secret@example.test/policy"},
        {"reviewed_on": "2026-10-15"},
        {"expires_on": "2026-10-13"},
        {"expires_on": "2027-10-01"},
        {"allowed_urls": [OTHER_URL]},
        {"allowed_urls": ["https://127.0.0.1/feed"]},
    ],
)
def test_permissions_reject_missing_approval_expiry_and_unsafe_endpoints(change):
    feed = permission_feed()
    feed["permissions"].update(change)
    with pytest.raises(FeedPermissionError):
        approved_feed_urls(feed, date(2026, 10, 14))


def test_permissions_require_evidence_not_a_licence_string():
    with pytest.raises(FeedPermissionError, match="missing"):
        approved_feed_urls({"url": URL, "rights": "CC BY 4.0"}, date(2026, 10, 14))
    assert approved_feed_urls(permission_feed(), date(2026, 10, 14)) == {URL}


@pytest.mark.parametrize(
    "url",
    [
        "http://feeds.example.test/rss.xml",
        "https://user:secret@feeds.example.test/rss.xml",
        "https://feeds.example.test:8443/rss.xml",
        "https://feeds.example.test/rss.xml#fragment",
        "https://feeds.example.test/rss.xml\r\nHeader: bad",
        "https://feeds.example.test\\@127.0.0.1/",
        "https://127.0.0.1/",
        "https://169.254.169.254/latest/meta-data/",
        "https://[::1]/",
        "https://[::ffff:127.0.0.1]/",
        "https://localhost/",
        "https://feeds.local/",
        "https://feeds.example.test./",
        "https://2130706433/",
    ],
)
def test_unsafe_urls_fail_before_any_dns_or_socket(url):
    with pytest.raises(fetching.FeedFetchError):
        fetching.fetch_feed(url, allowed_urls={url})


@pytest.mark.parametrize(
    "value",
    ["10.0.0.1", "100.64.0.1", "224.0.0.1", "0.0.0.0", "fc00::1", "64:ff9b::a00:1"],
)
def test_dns_rejects_mixed_public_and_unsafe_answers(monkeypatch, value):
    unsafe = (fetching.socket.AF_INET6 if ":" in value else fetching.socket.AF_INET,
              fetching.socket.SOCK_STREAM, 6, "", (value, 443))
    monkeypatch.setattr(fetching.socket, "getaddrinfo", lambda *_a, **_k: [PUBLIC, unsafe])
    with pytest.raises(fetching.FeedFetchError, match="public"):
        fetching._public_addresses("feeds.example.test", monotonic() + 5)


def test_dns_wait_is_bounded_without_waiting_for_a_stuck_resolver(monkeypatch):
    class NoWorker:
        def __init__(self, **_kwargs):
            pass

        def start(self):
            pass

    class NoResult:
        def __init__(self, **_kwargs):
            pass

        def get(self, timeout):
            assert 0 < timeout <= 5
            raise Empty

    monkeypatch.setattr(fetching, "Thread", NoWorker)
    monkeypatch.setattr(fetching, "Queue", NoResult)
    with pytest.raises(fetching.FeedFetchError, match="DNS lookup exceeded"):
        fetching._public_addresses("feeds.example.test", monotonic() + 5)


def test_pinned_connection_uses_numeric_address_and_original_tls_hostname(monkeypatch):
    connected = []
    tls_hosts = []

    class FakeSocket:
        def settimeout(self, _timeout):
            pass

        def connect(self, address):
            connected.append(address)

        def setsockopt(self, *_args):
            pass

        def do_handshake(self):
            pass

        def close(self):
            pass

        def shutdown(self, _how):
            pass

    class FakeContext:
        def wrap_socket(self, sock, server_hostname, do_handshake_on_connect):
            assert do_handshake_on_connect is False
            tls_hosts.append(server_hostname)
            return sock

    monkeypatch.setattr(fetching.socket, "socket", lambda *_args: FakeSocket())
    monkeypatch.setattr(fetching.ssl, "create_default_context", lambda: FakeContext())
    connection = fetching._PinnedHTTPSConnection(
        "feeds.example.test", [PUBLIC], 5, monotonic() + 5
    )
    connection.connect()
    connection.close()
    assert connected == [("93.184.216.34", 443)]
    assert tls_hosts == ["feeds.example.test"]


def test_tls_context_keeps_certificate_verification_enabled():
    connection = fetching._PinnedHTTPSConnection(
        "feeds.example.test", [PUBLIC], 5, monotonic() + 5
    )
    assert connection._context.check_hostname is True
    assert connection._context.verify_mode == fetching.ssl.CERT_REQUIRED
    connection.close()


def responses(monkeypatch, values):
    calls = []

    def request(url, headers, timeout, deadline):
        calls.append((url, headers))
        assert timeout <= fetching.LIVE_TIMEOUT_SECONDS
        assert deadline > monotonic()
        value = values.pop(0)
        if isinstance(value, Exception):
            raise value
        return value

    monkeypatch.setattr(fetching, "_request_once", request)
    return calls


def test_exact_allowlist_rejects_missing_and_unapproved_endpoints():
    with pytest.raises(fetching.FeedFetchError, match="allowlist"):
        fetching.fetch_feed(URL)
    with pytest.raises(fetching.FeedFetchError, match="allowlist"):
        fetching.fetch_feed(URL, allowed_urls={OTHER_URL})


def test_redirect_needs_exact_approval_and_drops_cross_host_validators(monkeypatch):
    redirect = fetching.FetchResponse(302, {"Location": OTHER_URL}, b"")
    calls = responses(monkeypatch, [redirect])
    with pytest.raises(fetching.FeedFetchError, match="not approved"):
        fetching.fetch_feed(URL, allowed_urls={URL})
    assert len(calls) == 1
    calls = responses(monkeypatch, [redirect, fetching.FetchResponse(200, {}, b"xml")])
    result = fetching.fetch_feed(
        URL, {"If-None-Match": '"private-validator"'}, allowed_urls={URL, OTHER_URL}
    )
    assert result.body == b"xml"
    assert calls[0][1]["If-None-Match"] == '"private-validator"'
    assert "If-None-Match" not in calls[1][1]


def test_redirect_loop_is_bounded(monkeypatch):
    calls = responses(
        monkeypatch,
        [fetching.FetchResponse(302, {"Location": URL}, b"")] * 6,
    )
    with pytest.raises(fetching.FeedFetchError, match="redirect limit"):
        fetching.fetch_feed(URL, allowed_urls={URL})
    assert len(calls) == 6


def test_transient_retry_can_recover_but_never_exceeds_two_attempts(monkeypatch):
    calls = responses(monkeypatch, [
        fetching.FetchResponse(503, {"Retry-After": "0"}, b""),
        fetching.FetchResponse(304, {}, b""),
    ])
    assert fetching.fetch_feed(URL, allowed_urls={URL}).status == 304
    assert len(calls) == 2
    calls = responses(monkeypatch, [TimeoutError("secret remote text")] * 2)
    with pytest.raises(fetching.FeedFetchError, match="bounded attempts") as error:
        fetching.fetch_feed(URL, allowed_urls={URL})
    assert len(calls) == 2
    assert "secret" not in str(error.value)


@pytest.mark.parametrize("retry_after", ["3600", "nan", "malformed"])
def test_retry_after_cannot_extend_or_bypass_the_retry_budget(monkeypatch, retry_after):
    calls = responses(monkeypatch, [
        fetching.FetchResponse(429, {"Retry-After": retry_after}, b""),
    ])
    with pytest.raises(fetching.FeedFetchError, match="Retry-After"):
        fetching.fetch_feed(URL, allowed_urls={URL})
    assert len(calls) == 1


def test_certificate_failure_is_not_retried(monkeypatch):
    calls = responses(monkeypatch, [fetching.ssl.SSLCertVerificationError("secret")])
    with pytest.raises(fetching.FeedFetchError, match="TLS validation"):
        fetching.fetch_feed(URL, allowed_urls={URL})
    assert len(calls) == 1


@pytest.mark.parametrize("headers", [
    {"Authorization": "secret"},
    {"Host": "127.0.0.1"},
    {"If-None-Match": "value\r\nHeader: secret"},
])
def test_only_safe_conditional_headers_are_allowed(headers):
    with pytest.raises(fetching.FeedFetchError, match="conditional"):
        fetching.fetch_feed(URL, headers, allowed_urls={URL})


class FakeSocket:
    def settimeout(self, _timeout):
        pass


class FakeResponse:
    status = 200

    def __init__(self, headers=None, chunks=None):
        self.headers = headers or {}
        self.chunks = list(chunks or [])
        self.closed = False

    def getheaders(self):
        return list(self.headers.items())

    def read1(self, maximum):
        chunk = self.chunks.pop(0) if self.chunks else b""
        assert len(chunk) <= maximum
        return chunk

    def close(self):
        self.closed = True


def transport(monkeypatch, response, resolver=None):
    connections = []
    if resolver is None:
        monkeypatch.setattr(fetching, "_public_addresses", lambda *_args: [PUBLIC])
    else:
        monkeypatch.setattr(fetching.socket, "getaddrinfo", resolver)

    class FakeConnection:
        def __init__(self, host, addresses, timeout, deadline):
            self.host = host
            self.active_socket = FakeSocket()
            self.closed = False
            connections.append(self)

        def request(self, *_args, **_kwargs):
            pass

        def getresponse(self):
            return response

        def abort(self):
            self.closed = True

        def close(self):
            self.closed = True

    monkeypatch.setattr(fetching, "_PinnedHTTPSConnection", FakeConnection)
    return connections


@pytest.mark.parametrize("headers", [
    {"Content-Length": str(fetching.MAX_FEED_BYTES + 1)},
    {"Content-Length": "-1"},
    {"Content-Length": "invalid"},
    {"Content-Encoding": "gzip"},
])
def test_transport_rejects_unsafe_lengths_and_compression_before_body_read(
    monkeypatch, headers
):
    response = FakeResponse(headers, [b"must not be read"])
    connections = transport(monkeypatch, response)
    with pytest.raises(fetching.FeedFetchError):
        fetching.fetch_feed(URL, allowed_urls={URL})
    assert response.chunks == [b"must not be read"]
    assert response.closed and connections[0].closed


def test_transport_limits_chunked_body_and_rejects_truncation(monkeypatch):
    monkeypatch.setattr(fetching, "MAX_FEED_BYTES", 4)
    response = FakeResponse(chunks=[b"1234", b"5"])
    transport(monkeypatch, response)
    with pytest.raises(fetching.FeedFetchError, match="5 MB"):
        fetching.fetch_feed(URL, allowed_urls={URL})
    response = FakeResponse({"Content-Length": "4"}, [b"123"])
    transport(monkeypatch, response)
    with pytest.raises(fetching.FeedFetchError, match="Incomplete"):
        fetching.fetch_feed(URL, allowed_urls={URL})


def test_approved_redirect_resolves_and_rejects_private_dns_before_connect(monkeypatch):
    response = FakeResponse({"Location": OTHER_URL})
    response.status = 302

    def resolve(host, *_args, **_kwargs):
        if host == "feeds.example.test":
            return [PUBLIC]
        return [(fetching.socket.AF_INET, fetching.socket.SOCK_STREAM, 6, "", ("10.0.0.1", 443))]

    connections = transport(monkeypatch, response, resolve)
    with pytest.raises(fetching.FeedFetchError, match="public"):
        fetching.fetch_feed(URL, allowed_urls={URL, OTHER_URL})
    assert [connection.host for connection in connections] == ["feeds.example.test"]


def test_total_deadline_stops_a_slow_body_and_closes_transport(monkeypatch):
    clock = [0.0]
    monkeypatch.setattr(fetching, "monotonic", lambda: clock[0])
    response = FakeResponse(chunks=[b"data"])
    original_read = response.read1

    def slow_read(maximum):
        result = original_read(maximum)
        clock[0] = fetching.TOTAL_FETCH_SECONDS + 1
        return result

    response.read1 = slow_read
    connections = transport(monkeypatch, response)
    with pytest.raises(fetching.FeedFetchError, match="total time budget"):
        fetching.fetch_feed(URL, allowed_urls={URL})
    assert response.closed and connections[0].closed


def test_watchdog_interrupts_a_blocked_header_read_without_network(monkeypatch):
    from threading import Event

    aborted = Event()
    response = FakeResponse()
    connections = transport(monkeypatch, response)
    connection_type = fetching._PinnedHTTPSConnection

    def abort(self):
        self.closed = True
        aborted.set()

    def getresponse(self):
        assert aborted.wait(1), "deadline watchdog did not interrupt header read"
        return response

    monkeypatch.setattr(connection_type, "abort", abort)
    monkeypatch.setattr(connection_type, "getresponse", getresponse)
    monkeypatch.setattr(fetching, "TOTAL_FETCH_SECONDS", 0.02)
    with pytest.raises(fetching.FeedFetchError, match="total time budget"):
        fetching.fetch_feed(URL, allowed_urls={URL})
    assert aborted.is_set() and connections[0].closed and response.closed

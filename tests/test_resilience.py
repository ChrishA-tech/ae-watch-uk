"""API Resilience and Retry Logic Tests.

Validates tenacity retries, exponential backoff with jitter, explicit timeouts,
and HTTP 429 Retry-After parsing.
Author: CHRISH PEP FELIX A
"""

from datetime import UTC, datetime, timedelta
from email.utils import format_datetime

import httpx
import pytest
import respx

from ae_watch.utils.resilience import (
    execute_with_resilience,
    parse_retry_after,
)


def test_parse_retry_after_integer_seconds():
    """Verify integer seconds parsing from Retry-After header."""
    resp = httpx.Response(429, headers={"Retry-After": "15"})
    delay = parse_retry_after(resp)
    assert delay == 15.0


def test_parse_retry_after_http_date():
    """Verify RFC 2822 HTTP date parsing from Retry-After header."""
    future = datetime.now(UTC) + timedelta(seconds=20)
    date_str = format_datetime(future)
    resp = httpx.Response(429, headers={"Retry-After": date_str})
    delay = parse_retry_after(resp)
    assert delay is not None
    assert 18.0 <= delay <= 22.0


def test_parse_retry_after_missing():
    """Verify missing Retry-After header returns None."""
    resp = httpx.Response(429)
    assert parse_retry_after(resp) is None


@pytest.mark.asyncio
async def test_resilience_recovers_from_429():
    """Simulate HTTP 429 followed by HTTP 200 OK, verifying tenacity recovery."""
    url = "https://test.api.gov.uk/data"

    with respx.mock(assert_all_called=True) as router:
        # First attempt returns 429 with small Retry-After
        route = router.get(url)
        route.side_effect = [
            httpx.Response(429, headers={"Retry-After": "0.1"}),
            httpx.Response(200, json={"status": "success", "data": [1, 2, 3]}),
        ]

        async with httpx.AsyncClient() as client:
            resp = await execute_with_resilience(client.get, url, max_attempts=3)
            assert resp.status_code == 200
            assert resp.json()["status"] == "success"
            assert route.call_count == 2


@pytest.mark.asyncio
async def test_resilience_bounds_retry_exhaustion():
    """Verify tenacity bounded retries exhaust at max_attempts without bare except."""
    url = "https://test.api.gov.uk/flake"

    with respx.mock(assert_all_called=True) as router:
        route = router.get(url).respond(503)

        async with httpx.AsyncClient() as client:
            with pytest.raises(httpx.HTTPStatusError) as exc_info:
                await execute_with_resilience(client.get, url, max_attempts=3)

            assert exc_info.value.response.status_code == 503
            assert route.call_count == 3


@pytest.mark.asyncio
async def test_resilience_recovers_from_network_timeout():
    """Verify automatic recovery from transient network timeouts."""
    url = "https://test.api.gov.uk/slow"

    with respx.mock(assert_all_called=True) as router:
        route = router.get(url)
        route.side_effect = [
            httpx.ReadTimeout("Connection timed out"),
            httpx.Response(200, json={"data": "recovered"}),
        ]

        async with httpx.AsyncClient() as client:
            resp = await execute_with_resilience(client.get, url, max_attempts=3)
            assert resp.status_code == 200
            assert resp.json()["data"] == "recovered"
            assert route.call_count == 2

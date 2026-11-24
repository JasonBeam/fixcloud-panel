from datetime import datetime
from zoneinfo import ZoneInfo

import httpx
import pytest

from app.services.subscription_usage import (
    SubscriptionUsageService,
    content_disposition_title,
    parse_subscription_userinfo,
    usage_payload,
)


def test_parse_subscription_userinfo() -> None:
    parsed = parse_subscription_userinfo(
        "upload=100; download=200; total=1000; expire=1814793183"
    )
    assert parsed == {
        "upload": 100,
        "download": 200,
        "total": 1000,
        "expire": 1814793183,
    }
    assert parse_subscription_userinfo("download=1") is None


def test_content_disposition_title() -> None:
    assert content_disposition_title('attachment; filename="oixCloud"') == "oixCloud"
    assert (
        content_disposition_title("attachment; filename*=UTF-8''My%20Cloud")
        == "My Cloud"
    )


def test_usage_payload() -> None:
    headers = httpx.Headers(
        {
            "subscription-userinfo": (
                "upload=100; download=200; total=1000; expire=1814793183"
            ),
            "content-disposition": 'attachment; filename="oixCloud"',
        }
    )
    payload = usage_payload(
        "Provider",
        headers,
        fetched_at=datetime(2026, 7, 26, tzinfo=ZoneInfo("Asia/Shanghai")),
    )
    assert payload["title"] == "oixCloud"
    assert payload["used"] == 300
    assert payload["remaining"] == 700
    assert payload["remainingPercent"] == 70.0
    assert payload["remainingDays"] > 300


@pytest.mark.asyncio
async def test_service_does_not_return_subscription_url() -> None:
    secret_url = "https://subscription.example/secret-token"

    def handler(request: httpx.Request) -> httpx.Response:
        assert str(request.url) == secret_url
        return httpx.Response(
            200,
            headers={
                "subscription-userinfo": (
                    "upload=10; download=20; total=100; expire=1814793183"
                ),
                "content-disposition": 'attachment; filename="Private Cloud"',
            },
        )

    service = SubscriptionUsageService(transport=httpx.MockTransport(handler))
    payload = await service.get_usage(
        {
            "proxy-providers": {
                "Provider": {
                    "type": "http",
                    "url": secret_url,
                }
            }
        },
        cache_key="test-no-url",
        force=True,
    )
    assert payload["subscriptions"][0]["available"] is True
    assert payload["subscriptions"][0]["title"] == "Private Cloud"
    assert secret_url not in str(payload)

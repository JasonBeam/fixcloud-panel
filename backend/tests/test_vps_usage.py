import json

import httpx
import pytest

from app.services.vps_usage import get_vps_usage


@pytest.mark.asyncio
async def test_vps_usage_keeps_provider_scopes_and_secrets_separate(monkeypatch):
    for key, value in {"EVOXT_USERNAME": "user", "EVOXT_API_PUBLIC": "pub", "EVOXT_API_PRIVATE": "secret", "EVOXT_SERVICE_ID": "42", "VULTR_API_KEY": "vultr-secret"}.items():
        monkeypatch.setenv(key, value)

    def respond(request):
        if request.url.host == "api.evoxt.com":
            return httpx.Response(200, json={"used_bandwidth": "12.3", "bandwidth": "500", "nextduedate": "2026-12-21", "password": "do-not-return"})
        return httpx.Response(200, json={"bandwidth": {"current_month_to_date": {"gb_in": 15, "gb_out": 20, "instance_bandwidth_credits": 100, "free_bandwidth_credits": 2000, "purchased_bandwidth_credits": 0}}})

    result = await get_vps_usage(httpx.MockTransport(respond))
    assert result[0]["used"] == 12.3 and result[0]["total"] == 500
    assert result[1]["used"] == 20 and result[1]["total"] == 2100
    assert result[1]["scope"] == "账号本月"
    assert result[0]["expiry"] == "2026-12-21" and result[0]["upload"] is None
    assert result[1]["upload"] == 20 and result[1]["download"] == 15 and result[1]["expiry"] is None
    assert "do-not-return" not in json.dumps(result) and "secret" not in json.dumps(result)


@pytest.mark.asyncio
async def test_unconfigured_providers_do_not_show_fake_zero(monkeypatch):
    for key in ("EVOXT_USERNAME", "EVOXT_API_PUBLIC", "EVOXT_API_PRIVATE", "EVOXT_SERVICE_ID", "VULTR_API_KEY"):
        monkeypatch.delenv(key, raising=False)
    result = await get_vps_usage(httpx.MockTransport(lambda request: httpx.Response(500)))
    assert all(not item["available"] and "used" not in item for item in result)

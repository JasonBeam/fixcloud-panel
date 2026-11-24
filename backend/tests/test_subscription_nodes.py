import base64

import httpx
import pytest

from app.services.subscription_nodes import SubscriptionNodesService, parse_subscription_nodes


def test_parse_yaml_nodes_returns_only_display_fields() -> None:
    nodes = parse_subscription_nodes(
        b"proxies:\n  - name: HK AI\n    type: vless\n    server: private.example\n    password: secret\n"
    )
    assert nodes == [{"name": "HK AI", "type": "vless"}]
    assert "private.example" not in str(nodes)
    assert "secret" not in str(nodes)


def test_parse_base64_uri_nodes() -> None:
    source = "ss://cipher:password@example.com:443#HK%20GPT\ntrojan://password@example.com:443#JP AI"
    nodes = parse_subscription_nodes(base64.b64encode(source.encode()))
    assert nodes == [{"name": "HK GPT", "type": "ss"}, {"name": "JP AI", "type": "trojan"}]


@pytest.mark.asyncio
async def test_service_does_not_return_subscription_url_or_node_secrets() -> None:
    secret_url = "https://subscription.example/secret-token"

    def handler(request: httpx.Request) -> httpx.Response:
        assert str(request.url) == secret_url
        return httpx.Response(200, text="proxies:\n- name: HK\n  type: ss\n  server: private.example\n  password: secret")

    service = SubscriptionNodesService(transport=httpx.MockTransport(handler))
    payload = await service.get_nodes(
        {"proxy-providers": {"Provider": {"type": "http", "url": secret_url}}},
        cache_key="nodes-no-secrets",
        force=True,
    )
    assert payload["totalNodes"] == 1
    assert payload["providers"][0]["nodes"] == [{"name": "HK", "type": "ss"}]
    assert secret_url not in str(payload)
    assert "private.example" not in str(payload)
    assert "secret" not in str(payload)

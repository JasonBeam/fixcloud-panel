from __future__ import annotations

import asyncio
import os
from typing import Any

import httpx


async def get_vps_usage(transport: httpx.AsyncBaseTransport | None = None) -> list[dict[str, Any]]:
    """Read provider billing data; never return credentials or raw provider responses."""
    async with httpx.AsyncClient(timeout=12, transport=transport) as client:
        return list(await asyncio.gather(_evoxt(client), _vultr(client)))


async def _evoxt(client: httpx.AsyncClient) -> dict[str, Any]:
    item: dict[str, Any] = {"name": "香港 VPS", "provider": "Evoxt", "available": False}
    username = os.getenv("EVOXT_USERNAME", "")
    public = os.getenv("EVOXT_API_PUBLIC", "")
    private = os.getenv("EVOXT_API_PRIVATE", "")
    service_id = os.getenv("EVOXT_SERVICE_ID", "")
    if not all((username, public, private, service_id)):
        return {**item, "message": "等待配置服务商 API"}
    try:
        response = await client.get("https://api.evoxt.com/listserver", params={"username": username, "serviceid": service_id}, auth=(public, private))
        response.raise_for_status()
        data = response.json()
        used, total = float(data["used_bandwidth"]), float(data["bandwidth"])
        if used < 0 or total <= 0:
            raise ValueError("invalid usage")
        return {**item, "available": True, "used": used, "total": total, "unit": "GiB", "scope": "服务器套餐", "note": "Evoxt 官方用量", "expiry": data.get("nextduedate"), "upload": None, "download": None}
    except (httpx.HTTPError, ValueError, TypeError, KeyError):
        return {**item, "message": "无法读取 Evoxt 用量，请检查连接或授权"}


async def _vultr(client: httpx.AsyncClient) -> dict[str, Any]:
    item: dict[str, Any] = {"name": "日本 VPS", "provider": "Vultr", "available": False}
    key = os.getenv("VULTR_API_KEY", "")
    if not key:
        return {**item, "message": "等待配置服务商 API"}
    try:
        response = await client.get("https://api.vultr.com/v2/account/bandwidth", headers={"Authorization": f"Bearer {key}"})
        response.raise_for_status()
        period = response.json()["bandwidth"]["current_month_to_date"]
        used = float(period["gb_out"])
        total = sum(float(period[key]) for key in ("instance_bandwidth_credits", "free_bandwidth_credits", "purchased_bandwidth_credits"))
        if used < 0 or total <= 0:
            raise ValueError("invalid usage")
        inbound = float(period["gb_in"]) if period.get("gb_in") is not None else None
        if inbound is not None and inbound < 0:
            raise ValueError("invalid inbound")
        return {**item, "available": True, "used": used, "total": total, "unit": "GB", "scope": "账号本月", "note": "Vultr 账号出站流量，含所有实例", "expiry": None, "upload": used, "download": inbound}
    except (httpx.HTTPError, ValueError, TypeError, KeyError):
        return {**item, "message": "无法读取 Vultr 用量，请检查连接或授权"}

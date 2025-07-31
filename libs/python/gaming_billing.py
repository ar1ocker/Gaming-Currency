import hashlib
import hmac
import json
from datetime import datetime, timezone
from typing import Any

import aiohttp
from yarl import URL


class GamingBillingAPI:
    def __init__(
        self,
        endpoint: str,
        service_name: str,
        secret_key: str,
        service_header: str = "X-SERVICE",
        signature_header: str = "X-SIGNATURE",
        timestamp_header: str = "X-SIGNATURE-TIMESTAMP",
    ) -> None:
        self.endpoint = URL(endpoint) / "api" / "currencies"
        self.service_name = service_name
        self.service_header = service_header
        self.signature_header = signature_header
        self.timestamp_header = timestamp_header
        self.secret_key = secret_key.encode("utf-8")
        self.session: aiohttp.ClientSession | None = None

    def _compute_signature(self, data: str) -> str:
        return hmac.digest(key=self.secret_key, msg=data.encode("utf-8"), digest=hashlib.sha256).hex()

    async def _get_headers(self, path: str, data: str | None = None) -> dict[str, str]:
        timestamp = datetime.now(timezone.utc).isoformat()

        signature_data = f"{timestamp}.{path}.{data or ''}"
        signature = self._compute_signature(signature_data)

        return {
            self.service_header: self.service_name,
            self.signature_header: signature,
            self.timestamp_header: timestamp,
            "Content-Type": "application/json",
        }

    async def _request(
        self,
        session: aiohttp.ClientSession,
        method: str,
        url: URL,
        headers: dict[str, str],
        data: str | None = None,
    ) -> dict:

        async with session.request(method, url, headers=headers, data=data) as response:
            return await response.json()

    async def holders_list(
        self,
        session: aiohttp.ClientSession,
        filters: dict | None = None,
    ) -> dict:

        filters = filters or {}
        url = (self.endpoint / "holders/").with_query(filters)
        headers = await self._get_headers(url.raw_path_qs)

        return await self._request(session, "GET", url, headers)

    async def holders_detail(
        self,
        session: aiohttp.ClientSession,
        holder_id: str,
    ) -> dict:

        url = (self.endpoint / "holders" / "detail/").with_query({"holder_id": holder_id})
        headers = await self._get_headers(url.raw_path_qs)

        return await self._request(session, "GET", url, headers)

    async def holders_create(
        self,
        session: aiohttp.ClientSession,
        holder_id: str,
        holder_type: str | None = None,
        info: dict | None = None,
    ) -> dict:

        info = info or {}
        url = self.endpoint / "holders" / "create/"
        payload: dict[str, Any] = {"holder_id": holder_id}

        if holder_type is not None:
            payload["holder_type"] = holder_type

        if info is not None:
            payload["info"] = info

        json_payload = json.dumps(payload)

        headers = await self._get_headers(url.raw_path_qs, json_payload)
        return await self._request(session, "POST", url, headers, json_payload)

    async def holders_update(
        self,
        session: aiohttp.ClientSession,
        holder_id: str,
        enabled: bool | None = None,
        info: dict | None = None,
    ) -> dict:

        if enabled is None and info is None:
            raise ValueError("At least one parameter must be provided")

        url = self.endpoint / "holders" / "update/"

        payload_data: dict[str, str | int | dict] = {"holder_id": holder_id}
        if enabled is not None:
            payload_data["enabled"] = enabled
        if info is not None:
            payload_data["info"] = info

        payload = json.dumps(payload_data)
        headers = await self._get_headers(url.raw_path_qs, payload)
        return await self._request(session, "POST", url, headers, payload)

    async def accounts_list(
        self,
        session: aiohttp.ClientSession,
        filters: dict | None = None,
    ) -> dict:

        filters = filters or {}
        url = (self.endpoint / "accounts/").with_query(filters)
        headers = await self._get_headers(url.raw_path_qs)

        return await self._request(session, "GET", url, headers)

    async def accounts_detail(
        self,
        session: aiohttp.ClientSession,
        holder_id: str,
        unit_symbol: str,
        holder_type: str | None = None,
    ) -> dict:

        url = (self.endpoint / "accounts" / "detail/").with_query({"holder_id": holder_id, "unit_symbol": unit_symbol})

        if holder_type is not None:
            url = url.update_query({"holder_type": holder_type})

        headers = await self._get_headers(url.raw_path_qs)

        return await self._request(session, "GET", url, headers)

    async def accounts_create(
        self,
        session: aiohttp.ClientSession,
        holder_id: str,
        unit_symbol: str,
        holder_type: str,
    ) -> dict:

        url = self.endpoint / "accounts" / "create/"
        payload = json.dumps({"holder_id": holder_id, "unit_symbol": unit_symbol, "holder_type": holder_type})
        headers = await self._get_headers(url.raw_path_qs, payload)

        return await self._request(session, "POST", url, headers, payload)

    async def units_list(
        self,
        session: aiohttp.ClientSession,
        filters: dict | None = None,
    ) -> dict:

        filters = filters or {}
        url = (self.endpoint / "units/").with_query(filters)
        headers = await self._get_headers(url.raw_path_qs)

        return await self._request(session, "GET", url, headers)

    async def adjustments_list(
        self,
        session: aiohttp.ClientSession,
        filters: dict | None = None,
    ) -> dict:

        filters = filters or {}
        url = (self.endpoint / "adjustments/").with_query(filters)
        headers = await self._get_headers(url.raw_path_qs)

        return await self._request(session, "GET", url, headers)

    async def adjustments_create(
        self,
        session: aiohttp.ClientSession,
        holder_id: str,
        unit_symbol: str,
        amount: float,
        description: str,
        auto_reject_timeout: int,
    ) -> dict:

        url = self.endpoint / "adjustments" / "create/"
        payload = json.dumps(
            {
                "holder_id": holder_id,
                "unit_symbol": unit_symbol,
                "amount": amount,
                "description": description,
                "auto_reject_timeout": auto_reject_timeout,
            }
        )
        headers = await self._get_headers(url.raw_path_qs, payload)

        return await self._request(session, "POST", url, headers, payload)

    async def adjustments_confirm(
        self,
        session: aiohttp.ClientSession,
        uuid: str,
        status_description: str,
    ) -> dict:

        url = self.endpoint / "adjustments" / "confirm/"
        payload = json.dumps({"uuid": uuid, "status_description": status_description})
        headers = await self._get_headers(url.raw_path_qs, payload)

        return await self._request(session, "POST", url, headers, payload)

    async def adjustments_reject(
        self,
        session: aiohttp.ClientSession,
        uuid: str,
        status_description: str,
    ) -> dict:

        url = self.endpoint / "adjustments" / "reject/"
        payload = json.dumps({"uuid": uuid, "status_description": status_description})
        headers = await self._get_headers(url.raw_path_qs, payload)

        return await self._request(session, "POST", url, headers, payload)

    async def transfers_list(
        self,
        session: aiohttp.ClientSession,
        filters: dict | None = None,
    ) -> dict:

        filters = filters or {}
        url = (self.endpoint / "transfers/").with_query(filters)
        headers = await self._get_headers(url.raw_path_qs)

        return await self._request(session, "GET", url, headers)

    async def transfers_create(
        self,
        session: aiohttp.ClientSession,
        from_holder_id: str,
        to_holder_id: str,
        transfer_rule: str,
        amount: float,
        description: str,
        auto_reject_timeout: int,
    ) -> dict:

        url = self.endpoint / "transfers" / "create/"
        payload = json.dumps(
            {
                "from_holder_id": from_holder_id,
                "to_holder_id": to_holder_id,
                "transfer_rule": transfer_rule,
                "amount": amount,
                "description": description,
                "auto_reject_timeout": auto_reject_timeout,
            }
        )
        headers = await self._get_headers(url.raw_path_qs, payload)

        return await self._request(session, "POST", url, headers, payload)

    async def transfers_confirm(
        self,
        session: aiohttp.ClientSession,
        uuid: str,
        status_description: str,
    ) -> dict:

        url = self.endpoint / "transfers" / "confirm/"
        payload = json.dumps({"uuid": uuid, "status_description": status_description})
        headers = await self._get_headers(url.raw_path_qs, payload)

        return await self._request(session, "POST", url, headers, payload)

    async def transfers_reject(
        self,
        session: aiohttp.ClientSession,
        uuid: str,
        status_description: str,
    ) -> dict:

        url = self.endpoint / "transfers" / "reject/"
        payload = json.dumps({"uuid": uuid, "status_description": status_description})
        headers = await self._get_headers(url.raw_path_qs, payload)

        return await self._request(session, "POST", url, headers, payload)

    async def exchanges_list(
        self,
        session: aiohttp.ClientSession,
        filters: dict | None = None,
    ) -> dict:

        filters = filters or {}
        url = (self.endpoint / "exchanges/").with_query(filters)
        headers = await self._get_headers(url.raw_path_qs)

        return await self._request(session, "GET", url, headers)

    async def exchanges_create(
        self,
        session: aiohttp.ClientSession,
        holder_id: str,
        exchange_rule: str,
        from_unit: str,
        to_unit: str,
        from_amount: float,
        description: str,
        auto_reject_timeout: int,
    ) -> dict:

        url = self.endpoint / "exchanges" / "create/"
        payload = json.dumps(
            {
                "holder_id": holder_id,
                "exchange_rule": exchange_rule,
                "from_unit": from_unit,
                "to_unit": to_unit,
                "from_amount": from_amount,
                "description": description,
                "auto_reject_timeout": auto_reject_timeout,
            }
        )
        headers = await self._get_headers(url.raw_path_qs, payload)

        return await self._request(session, "POST", url, headers, payload)

    async def exchanges_confirm(
        self,
        session: aiohttp.ClientSession,
        uuid: str,
        status_description: str,
    ) -> dict:

        url = self.endpoint / "exchanges" / "confirm/"
        payload = json.dumps({"uuid": uuid, "status_description": status_description})
        headers = await self._get_headers(url.raw_path_qs, payload)

        return await self._request(session, "POST", url, headers, payload)

    async def exchanges_reject(
        self,
        session: aiohttp.ClientSession,
        uuid: str,
        status_description: str,
    ) -> dict:

        url = self.endpoint / "exchanges" / "reject/"
        payload = json.dumps({"uuid": uuid, "status_description": status_description})
        headers = await self._get_headers(url.raw_path_qs, payload)

        return await self._request(session, "POST", url, headers, payload)

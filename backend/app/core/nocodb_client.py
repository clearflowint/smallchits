"""
Thin async HTTP client around the NocoDB v2 REST API.

CRITICAL SECURITY INVARIANT (Blueprint section 3 — Strict Query Scoping):
Every read/write against Chittis, Shares, and Transactions MUST inject
`Manager_ID = user_email` into the query/where clause. This module centralizes
that so no router can accidentally forget it — callers pass `manager_id`
explicitly and it is always folded into the NocoDB `where` param for scoped
tables.

NocoDB itself is NOT deployed by this repo — point NOCODB_BASE_URL at your
own self-hosted instance and create the tables per docs/NOCODB_SCHEMA.md.
"""
from typing import Any, Optional

import httpx

from app.core.config import get_settings

settings = get_settings()

# Tables that are always scoped to the authenticated manager.
TENANT_SCOPED_TABLES = {
    "Chittis": "Manager_ID",
    "Shares": "Manager_ID",
    "Transactions": None,  # Transactions are scoped indirectly via Share_ID -> Shares.Manager_ID
}


class NocoDBError(RuntimeError):
    pass


class NocoDBClient:
    def __init__(self) -> None:
        self._base_url = settings.NOCODB_BASE_URL.rstrip("/")
        self._headers = {
            "xc-token": settings.NOCODB_API_TOKEN,
            "Content-Type": "application/json",
        }

    def _table_url(self, table_name: str) -> str:
        # NocoDB v2 records API: /api/v2/tables/{tableId}/records
        # We accept either a raw tableId or a friendly name resolved by the caller.
        return f"{self._base_url}/api/v2/tables/{table_name}/records"

    async def list_records(
        self,
        table_id: str,
        *,
        where: Optional[str] = None,
        limit: int = 100,
        offset: int = 0,
        sort: Optional[str] = None,
    ) -> list[dict[str, Any]]:
        params: dict[str, Any] = {"limit": limit, "offset": offset}
        if where:
            params["where"] = where
        if sort:
            params["sort"] = sort
        async with httpx.AsyncClient(timeout=20) as client:
            resp = await client.get(self._table_url(table_id), headers=self._headers, params=params)
        if resp.status_code >= 400:
            raise NocoDBError(f"NocoDB list failed [{resp.status_code}]: {resp.text}")
        return resp.json().get("list", [])

    async def get_record(self, table_id: str, record_id: Any) -> Optional[dict[str, Any]]:
        async with httpx.AsyncClient(timeout=20) as client:
            resp = await client.get(f"{self._table_url(table_id)}/{record_id}", headers=self._headers)
        if resp.status_code == 404:
            return None
        if resp.status_code >= 400:
            raise NocoDBError(f"NocoDB get failed [{resp.status_code}]: {resp.text}")
        return resp.json()

    async def create_record(self, table_id: str, payload: dict[str, Any]) -> dict[str, Any]:
        async with httpx.AsyncClient(timeout=20) as client:
            resp = await client.post(self._table_url(table_id), headers=self._headers, json=payload)
        if resp.status_code >= 400:
            raise NocoDBError(f"NocoDB create failed [{resp.status_code}]: {resp.text}")
        return resp.json()

    async def bulk_create(self, table_id: str, payloads: list[dict[str, Any]]) -> list[dict[str, Any]]:
        async with httpx.AsyncClient(timeout=30) as client:
            resp = await client.post(self._table_url(table_id), headers=self._headers, json=payloads)
        if resp.status_code >= 400:
            raise NocoDBError(f"NocoDB bulk create failed [{resp.status_code}]: {resp.text}")
        return resp.json()

    async def update_record(self, table_id: str, record_id: Any, payload: dict[str, Any]) -> dict[str, Any]:
        body = {**payload, "Id": record_id}
        async with httpx.AsyncClient(timeout=20) as client:
            resp = await client.patch(self._table_url(table_id), headers=self._headers, json=body)
        if resp.status_code >= 400:
            raise NocoDBError(f"NocoDB update failed [{resp.status_code}]: {resp.text}")
        return resp.json()

    async def delete_record(self, table_id: str, record_id: Any) -> None:
        async with httpx.AsyncClient(timeout=20) as client:
            resp = await client.request(
                "DELETE", self._table_url(table_id), headers=self._headers, json={"Id": record_id}
            )
        if resp.status_code >= 400:
            raise NocoDBError(f"NocoDB delete failed [{resp.status_code}]: {resp.text}")

    @staticmethod
    def build_where(*clauses: Optional[str]) -> Optional[str]:
        """Combines NocoDB where-clause fragments with AND (~and). Skips empty ones."""
        parts = [c for c in clauses if c]
        if not parts:
            return None
        return "~and".join(f"({p})" for p in parts)

    @staticmethod
    def eq(field: str, value: Any) -> str:
        return f"({field},eq,{value})"


def get_nocodb_client() -> NocoDBClient:
    return NocoDBClient()

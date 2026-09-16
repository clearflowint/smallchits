"""
WhatsApp Hub endpoints (Blueprint section 7 Page 2, section 8 automation).

These endpoints are called EITHER:
  (a) manually from the Page 2 "1-Tap Reminder & Statement Triggers" UI, or
  (b) by n8n's scheduled cron jobs hitting this API on D-2 / D+10 / D+20 offsets.

Actual message delivery goes through Chatwoot's WhatsApp API. This module
builds the message payloads and delegates sending to Chatwoot; n8n owns the
cron scheduling itself (see n8n/workflows/).
"""
from typing import Optional

import httpx
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from app.core.config import get_settings
from app.core.nocodb_client import NocoDBClient, get_nocodb_client
from app.core.security import get_current_manager
from app.routers.shares import get_personal_statement

router = APIRouter(prefix="/api/whatsapp", tags=["whatsapp"])
settings = get_settings()


class BroadcastRequest(BaseModel):
    chitti_id: str
    target: str  # "all_pending" | "all_shares"
    message_type: str  # "pre_due" | "overdue" | "statement" | "custom"
    custom_message: Optional[str] = None
    share_ids: Optional[list[str]] = None  # for multi-select targeting


async def _send_chatwoot_message(phone_number: str, message: str) -> None:
    if not settings.CHATWOOT_BASE_URL:
        raise HTTPException(500, "Chatwoot is not configured (CHATWOOT_BASE_URL missing).")
    url = f"{settings.CHATWOOT_BASE_URL}/api/v1/accounts/1/conversations"
    headers = {"api_access_token": settings.CHATWOOT_API_TOKEN}
    payload = {
        "source_id": phone_number,
        "inbox_id": settings.CHATWOOT_INBOX_ID,
        "message": {"content": message},
    }
    async with httpx.AsyncClient(timeout=20) as client:
        resp = await client.post(url, headers=headers, json=payload)
    if resp.status_code >= 400:
        raise HTTPException(502, f"Chatwoot send failed: {resp.text}")


def build_pre_due_message(chitti_name: str, due_amount: str) -> str:
    return (
        f"👋 Reminder — {chitti_name}\n"
        f"Your chit payment of ₹{due_amount} is due in 2 days. "
        f"Please plan your payment. Thank you!"
    )


def build_overdue_message(chitti_name: str, pending_amount: str) -> str:
    return (
        f"⏰ Overdue Notice — {chitti_name}\n"
        f"You have a pending due of ₹{pending_amount}. "
        f"Please clear this at your earliest convenience."
    )


def build_statement_message(statement: dict) -> str:
    paid_lines = ", ".join(f"Month {p['month']} (₹{p['amount']}) ✅" for p in statement["paid_months"])
    return (
        f"📊 {statement['chitti_name'].upper()} - PERSONAL FINANCIAL STATEMENT\n"
        f"🆔 Share ID: {statement['share_id']} | 👤 Member: {statement['member_name']}\n"
        "----------------------------------------\n"
        f"📅 PAID MONTHS: {paid_lines or 'None yet'}\n"
        f"💰 CURRENT MONTH ({statement['current_active_month']}): "
        f"Due ₹{statement['current_due']} | Paid ₹{statement['current_paid']} | "
        f"Pending ₹{statement['current_pending']}\n"
        f"🎯 DRAW STATUS: {statement['draw_status'].upper()}"
        + (f" (Month {statement['month_drawn']})" if statement.get("month_drawn") else "")
        + "\n"
        f"💳 ADVANCE CREDIT RESERVE: ₹{statement['advance_credit_reserve']}\n"
        f"📈 NET FUTURE COMMITMENT: ₹{statement['net_future_commitment']} "
        f"over {statement['months_left']} months\n"
        "----------------------------------------\n"
        "Thank you!"
    )


@router.post("/broadcast")
async def broadcast(
    body: BroadcastRequest,
    manager_id: str = Depends(get_current_manager),
    client: NocoDBClient = Depends(get_nocodb_client),
):
    shares_where = client.build_where(
        client.eq("Chitti_ID", body.chitti_id), client.eq("Manager_ID", manager_id)
    )
    shares = await client.list_records(settings.NOCODB_TABLE_SHARES, where=shares_where, limit=500)

    if body.share_ids:
        shares = [s for s in shares if s["Share_ID"] in body.share_ids]

    chittis = await client.list_records(
        settings.NOCODB_TABLE_CHITTIS, where=client.eq("Chitti_ID", body.chitti_id), limit=1
    )
    chitti = chittis[0] if chittis else {}
    chitti_name = chitti.get("Chitti_Name", "Your Chitti Group")

    sent = 0
    for share in shares:
        if body.message_type == "statement":
            statement = await get_personal_statement(share["Share_ID"], manager_id, client)
            message = build_statement_message(statement)
        elif body.message_type == "pre_due":
            message = build_pre_due_message(chitti_name, str(chitti.get("Undrawn_Due", "0")))
        elif body.message_type == "overdue":
            message = build_overdue_message(chitti_name, "0.00")  # populate with real pending in prod
        elif body.message_type == "custom" and body.custom_message:
            message = body.custom_message
        else:
            continue

        await _send_chatwoot_message(share["Phone_Number"], message)
        sent += 1

    return {"status": "sent", "recipients": sent}

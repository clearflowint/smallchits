"""
Share-level operations: roster listing, Payment Drawer entry, Draw Control,
Contact Editor (Blueprint section 7 — Mobile-First UI operations).
"""
from datetime import datetime, timezone
from decimal import Decimal

from fastapi import APIRouter, Depends, HTTPException

from app.core.config import get_settings
from app.core.nocodb_client import NocoDBClient, get_nocodb_client
from app.core.security import get_current_manager
from app.models import ContactUpdateRequest, DrawUpdateRequest, PaymentEntryRequest
from app.services import chitti_math_engine as math_engine
from app.services.cycle_service import record_payment

router = APIRouter(prefix="/api/shares", tags=["shares"])
settings = get_settings()


async def _get_owned_share(client: NocoDBClient, share_id: str, manager_id: str) -> dict:
    where = client.build_where(
        client.eq("Share_ID", share_id),
        client.eq("Manager_ID", manager_id),
    )
    rows = await client.list_records(settings.NOCODB_TABLE_SHARES, where=where, limit=1)
    if not rows:
        raise HTTPException(404, "Share not found or not owned by this manager.")
    return rows[0]


async def _get_transaction(client: NocoDBClient, share_id: str, month_number: int) -> dict:
    where = client.build_where(
        client.eq("Share_ID", share_id),
        client.eq("Month_Number", month_number),
    )
    rows = await client.list_records(settings.NOCODB_TABLE_TRANSACTIONS, where=where, limit=1)
    if not rows:
        raise HTTPException(404, "No transaction spawned for this share/month yet.")
    return rows[0]


@router.get("/by-chitti/{chitti_id}")
async def list_shares_for_chitti(
    chitti_id: str,
    manager_id: str = Depends(get_current_manager),
    client: NocoDBClient = Depends(get_nocodb_client),
):
    """Powers the 5 sub-tab Active Share Cards on Page 1."""
    where = client.build_where(
        client.eq("Chitti_ID", chitti_id),
        client.eq("Manager_ID", manager_id),
    )
    rows = await client.list_records(settings.NOCODB_TABLE_SHARES, where=where, limit=500)
    return {"shares": rows}


@router.post("/payment")
async def record_payment_entry(
    body: PaymentEntryRequest,
    manager_id: str = Depends(get_current_manager),
    client: NocoDBClient = Depends(get_nocodb_client),
):
    """
    Payment Drawer entry point. Enforces the Smart Over/Under Warning rules:
    - amount_paid < amount_due requires explicit force_partial_confirm=true
    - amount_paid > amount_due auto-routes excess to Shares.Advance_Credit
    """
    share = await _get_owned_share(client, body.share_id, manager_id)
    tx = await _get_transaction(client, body.share_id, body.month_number)

    amount_due = Decimal(str(tx["Amount_Due"]))
    existing_paid = Decimal(str(tx.get("Amount_Paid", 0) or 0))

    result = record_payment(amount_due=amount_due, existing_paid=existing_paid, new_payment=body.amount_paid)

    if result["payment_status"] == "Partial" and not body.force_partial_confirm:
        raise HTTPException(
            409,
            detail={
                "message": "Amount paid is less than Amount_Due. Confirm to mark as Partial.",
                "amount_due": str(amount_due),
                "amount_paid": str(result["amount_paid"]),
                "requires_confirmation": True,
            },
        )

    await client.update_record(
        settings.NOCODB_TABLE_TRANSACTIONS,
        tx["Id"],
        {
            "Amount_Paid": str(result["amount_paid"]),
            "Payment_Status": result["payment_status"],
            "Pending_Dues": str(result["pending_dues"]),
            "Payment_Date": datetime.now(timezone.utc).isoformat(),
        },
    )

    if result["advance_credit_delta"] > 0:
        current_credit = Decimal(str(share.get("Advance_Credit", 0) or 0))
        new_credit = current_credit + result["advance_credit_delta"]
        await client.update_record(
            settings.NOCODB_TABLE_SHARES, share["Id"], {"Advance_Credit": str(new_credit)}
        )

    return {
        "status": "recorded",
        "payment_status": result["payment_status"],
        "amount_paid": str(result["amount_paid"]),
        "pending_dues": str(result["pending_dues"]),
        "advance_credit_added": str(result["advance_credit_delta"]),
    }


@router.post("/draw")
async def update_draw_status(
    body: DrawUpdateRequest,
    manager_id: str = Depends(get_current_manager),
    client: NocoDBClient = Depends(get_nocodb_client),
):
    """
    Unified Inline Draw Winner Entry (Blueprint section 7). No separate
    reversal screen — toggling back to 'Undrawn' is just another call here.
    """
    share = await _get_owned_share(client, body.share_id, manager_id)

    if body.draw_status.value == "Drawn" and body.month_drawn is None:
        raise HTTPException(400, "month_drawn is required when setting Draw_Status to 'Drawn'.")

    payload = {
        "Draw_Status": body.draw_status.value,
        "Month_Drawn": body.month_drawn if body.draw_status.value == "Drawn" else None,
    }
    await client.update_record(settings.NOCODB_TABLE_SHARES, share["Id"], payload)
    return {"status": "updated", "share_id": body.share_id, **payload}


@router.patch("/contact")
async def update_contact(
    body: ContactUpdateRequest,
    manager_id: str = Depends(get_current_manager),
    client: NocoDBClient = Depends(get_nocodb_client),
):
    """Single-line Contact Editor (Page 2)."""
    share = await _get_owned_share(client, body.share_id, manager_id)
    payload = {}
    if body.member_name:
        payload["Member_Name"] = body.member_name
    if body.phone_number:
        payload["Phone_Number"] = body.phone_number
    if not payload:
        raise HTTPException(400, "Nothing to update.")
    await client.update_record(settings.NOCODB_TABLE_SHARES, share["Id"], payload)
    return {"status": "updated", "share_id": body.share_id, **payload}


@router.get("/{share_id}/statement")
async def get_personal_statement(
    share_id: str,
    manager_id: str = Depends(get_current_manager),
    client: NocoDBClient = Depends(get_nocodb_client),
):
    """
    Builds the data behind the Share-ID Personal Finance WhatsApp Statement
    (Blueprint section 8). n8n calls this at Cycle Day D+20 for every share.
    """
    share = await _get_owned_share(client, share_id, manager_id)
    chitti_where = client.eq("Chitti_ID", share["Chitti_ID"])
    chittis = await client.list_records(settings.NOCODB_TABLE_CHITTIS, where=chitti_where, limit=1)
    if not chittis:
        raise HTTPException(404, "Parent Chitti not found.")
    chitti = chittis[0]

    tx_where = client.eq("Share_ID", share_id)
    transactions = await client.list_records(
        settings.NOCODB_TABLE_TRANSACTIONS, where=tx_where, sort="Month_Number", limit=500
    )

    paid_months = [t for t in transactions if t["Payment_Status"] == "Verified"]
    current_month = chitti["Current_Active_Month"]
    current_tx = next((t for t in transactions if t["Month_Number"] == current_month), None)

    months_left = chitti["Total_Months"] - current_month + 1
    rate = Decimal(str(chitti["Drawn_Due"] if share["Draw_Status"] == "Drawn" else chitti["Undrawn_Due"]))
    advance_credit = Decimal(str(share.get("Advance_Credit", 0) or 0))
    gross_future_commitment = math_engine._round(months_left * rate)
    net_future_commitment = gross_future_commitment - advance_credit
    if net_future_commitment < 0:
        net_future_commitment = Decimal("0.00")

    return {
        "share_id": share_id,
        "chitti_name": chitti["Chitti_Name"],
        "member_name": share["Member_Name"],
        "paid_months": [
            {"month": t["Month_Number"], "amount": str(t["Amount_Paid"])} for t in paid_months
        ],
        "current_active_month": current_month,
        "current_due": str(current_tx["Amount_Due"]) if current_tx else None,
        "current_paid": str(current_tx["Amount_Paid"]) if current_tx else "0.00",
        "current_pending": str(current_tx["Pending_Dues"]) if current_tx else None,
        "draw_status": share["Draw_Status"],
        "month_drawn": share.get("Month_Drawn"),
        "advance_credit_reserve": str(advance_credit),
        "months_left": months_left,
        "net_future_commitment": str(net_future_commitment),
    }

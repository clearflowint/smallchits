"""
On-Demand Cycle Spawning Engine (Blueprint section 6).

Guarantees:
  - Day 1 onboarding creates exactly 1 Chitti row + S Share rows. Zero
    Transaction rows exist yet.
  - When Month m begins, exactly S Transaction rows are spawned (one per Share),
    each with Amount_Due resolved from that share's current Draw_Status.
  - If a share carries Advance_Credit, the new month's due is auto-settled
    from that reserve (partially or fully) with zero manager intervention.
"""
from decimal import Decimal
from typing import Any

from app.core.nocodb_client import NocoDBClient
from app.services import chitti_math_engine as math_engine
from app.core.config import get_settings

settings = get_settings()


async def spawn_month_transactions(
    client: NocoDBClient,
    *,
    chitti: dict[str, Any],
    shares: list[dict[str, Any]],
    month_number: int,
) -> list[dict[str, Any]]:
    """
    Spawns Transaction rows for every share for the given month_number.
    Idempotent by convention: callers should check no Transactions already
    exist for (chitti, month_number) before calling this — Trans_ID is a
    composite key '{Chitti_ID}_M{Month}_{Share_ID}' which naturally prevents
    duplicates if enforced as a NocoDB unique index.
    """
    undrawn_due = chitti["Undrawn_Due"]
    drawn_due = chitti["Drawn_Due"]
    chitti_id = chitti["Chitti_ID"]

    created_rows: list[dict[str, Any]] = []
    updated_shares: list[dict[str, Any]] = []

    for share in shares:
        share_id = share["Share_ID"]
        draw_status = share.get("Draw_Status", "Undrawn")
        advance_credit = Decimal(str(share.get("Advance_Credit", 0) or 0))

        amount_due = math_engine.determine_share_due(draw_status, undrawn_due, drawn_due)

        # Advance Credit Settlement — auto-cover from reserve first.
        covered, remaining_credit = math_engine.apply_advance_credit(amount_due, advance_credit)
        amount_paid = covered
        payment_status = math_engine.determine_payment_status(amount_due, amount_paid)
        pending = math_engine.pending_dues(amount_due, amount_paid)

        trans_id = f"{chitti_id}_M{month_number}_{share_id}"

        payload = {
            "Trans_ID": trans_id,
            "Share_ID": share_id,
            "Month_Number": month_number,
            "Amount_Due": str(amount_due),
            "Amount_Paid": str(amount_paid),
            "Pending_Dues": str(pending),
            "Payment_Status": payment_status,
            "Payment_Date": None,
        }
        created_rows.append(payload)

        if remaining_credit != advance_credit:
            updated_shares.append({"Share_ID": share_id, "Advance_Credit": str(remaining_credit)})

    if created_rows:
        await client.bulk_create(settings.NOCODB_TABLE_TRANSACTIONS, created_rows)

    for update in updated_shares:
        share_record_id = update.pop("Share_ID")
        await client.update_record(settings.NOCODB_TABLE_SHARES, share_record_id, update)

    return created_rows


def record_payment(
    *,
    amount_due: Decimal,
    existing_paid: Decimal,
    new_payment: Decimal,
) -> dict[str, Any]:
    """
    Pure computation for a manual payment entry (Payment Drawer, Blueprint
    section 7). Returns the fields to persist on the Transaction row, plus
    any overflow that should be pushed to Shares.Advance_Credit.
    """
    total_paid = existing_paid + new_payment
    status = math_engine.determine_payment_status(amount_due, total_paid)
    pending = math_engine.pending_dues(amount_due, total_paid)
    overflow_to_credit = math_engine.compute_advance_from_overpayment(amount_due, total_paid)

    return {
        "amount_paid": total_paid,
        "payment_status": status,
        "pending_dues": pending,
        "advance_credit_delta": overflow_to_credit,
    }

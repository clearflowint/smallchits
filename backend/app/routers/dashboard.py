"""
Page 2 aggregate views: Overall Financial Ledger Cards and the
Color-Coded Pocket Cash Indicator (Blueprint section 7).
"""
from decimal import Decimal

from fastapi import APIRouter, Depends

from app.core.config import get_settings
from app.core.nocodb_client import NocoDBClient, get_nocodb_client
from app.core.security import get_current_manager

router = APIRouter(prefix="/api/dashboard", tags=["dashboard"])
settings = get_settings()


@router.get("/{chitti_id}/summary")
async def get_summary(
    chitti_id: str,
    manager_id: str = Depends(get_current_manager),
    client: NocoDBClient = Depends(get_nocodb_client),
):
    chitti_where = client.build_where(
        client.eq("Chitti_ID", chitti_id), client.eq("Manager_ID", manager_id)
    )
    chittis = await client.list_records(settings.NOCODB_TABLE_CHITTIS, where=chitti_where, limit=1)
    if not chittis:
        return {"error": "not found"}
    chitti = chittis[0]

    shares_where = client.eq("Chitti_ID", chitti_id)
    shares = await client.list_records(settings.NOCODB_TABLE_SHARES, where=shares_where, limit=500)

    tx_where = client.eq("Chitti_ID", chitti_id)  # requires Chitti_ID lookup/rollup on Transactions,
    # or fetch per-share and aggregate client-side as done below for portability across NocoDB setups.
    all_tx: list[dict] = []
    for share in shares:
        share_tx_where = client.eq("Share_ID", share["Share_ID"])
        rows = await client.list_records(settings.NOCODB_TABLE_TRANSACTIONS, where=share_tx_where, limit=500)
        all_tx.extend(rows)

    total_pending = sum((Decimal(str(t.get("Pending_Dues", 0) or 0)) for t in all_tx), Decimal("0.00"))
    total_collected = sum((Decimal(str(t.get("Amount_Paid", 0) or 0)) for t in all_tx), Decimal("0.00"))
    total_advance_reserve = sum(
        (Decimal(str(s.get("Advance_Credit", 0) or 0)) for s in shares), Decimal("0.00")
    )
    months_elapsed = chitti["Current_Active_Month"]
    earned_commission = Decimal(str(chitti["Monthly_Commission"])) * months_elapsed

    # Pocket Cash Indicator: cash the manager should be holding vs. what's actually
    # been collected. A deficit means the manager has fronted funds for unpaid dues.
    expected_collected_so_far = total_collected + total_pending  # what should have come in by now
    pocket_cash_with_advances = total_collected + total_advance_reserve - earned_commission
    pocket_cash_without_advances = total_collected - earned_commission

    is_surplus = pocket_cash_without_advances >= 0

    return {
        "chitti_id": chitti_id,
        "chitti_name": chitti["Chitti_Name"],
        "current_active_month": months_elapsed,
        "total_months": chitti["Total_Months"],
        "total_pending_dues": str(total_pending),
        "total_collected": str(total_collected),
        "advance_credit_reserve": str(total_advance_reserve),
        "earned_manager_commission": str(earned_commission),
        "pocket_cash": {
            "with_advances": str(pocket_cash_with_advances),
            "without_advances": str(pocket_cash_without_advances),
            "status": "surplus" if is_surplus else "deficit",
            "color": "green" if is_surplus else "red",
        },
    }

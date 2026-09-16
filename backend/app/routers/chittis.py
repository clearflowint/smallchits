"""
Chitti group management: listing, financial matrix preview, and month spawning.
"""
from fastapi import APIRouter, Depends, HTTPException

from app.core.config import get_settings
from app.core.nocodb_client import NocoDBClient, get_nocodb_client
from app.core.security import get_current_manager
from app.services import chitti_math_engine as math_engine
from app.services.cycle_service import spawn_month_transactions

router = APIRouter(prefix="/api/chittis", tags=["chittis"])
settings = get_settings()


async def _get_owned_chitti(client: NocoDBClient, chitti_id: str, manager_id: str) -> dict:
    where = client.build_where(
        client.eq("Chitti_ID", chitti_id),
        client.eq("Manager_ID", manager_id),
    )
    rows = await client.list_records(settings.NOCODB_TABLE_CHITTIS, where=where, limit=1)
    if not rows:
        raise HTTPException(404, "Chitti not found or not owned by this manager.")
    return rows[0]


@router.get("")
async def list_chittis(
    manager_id: str = Depends(get_current_manager),
    client: NocoDBClient = Depends(get_nocodb_client),
):
    """Strictly scoped: WHERE Manager_ID = user_email."""
    where = client.eq("Manager_ID", manager_id)
    rows = await client.list_records(settings.NOCODB_TABLE_CHITTIS, where=where, limit=200)
    return {"chittis": rows}


@router.get("/{chitti_id}")
async def get_chitti(
    chitti_id: str,
    manager_id: str = Depends(get_current_manager),
    client: NocoDBClient = Depends(get_nocodb_client),
):
    return await _get_owned_chitti(client, chitti_id, manager_id)


@router.get("/{chitti_id}/matrix")
async def get_financial_matrix(
    chitti_id: str,
    manager_id: str = Depends(get_current_manager),
    client: NocoDBClient = Depends(get_nocodb_client),
):
    """Returns the full M-month deterministic financial matrix for this group."""
    chitti = await _get_owned_chitti(client, chitti_id, manager_id)
    matrix = math_engine.compute_full_matrix(
        total_members=chitti["Total_Members"],
        total_months=chitti["Total_Months"],
        monthly_commission=chitti["Monthly_Commission"],
        undrawn_due=chitti["Undrawn_Due"],
        drawn_due=chitti["Drawn_Due"],
    )
    return {
        "chitti_id": chitti_id,
        "matrix": [
            {
                "month": row.month,
                "n_undrawn": row.n_undrawn,
                "n_drawn": row.n_drawn,
                "gross_pool": str(row.gross_pool),
                "manager_commission": str(row.manager_commission),
                "net_winner_payout": str(row.net_winner_payout),
            }
            for row in matrix
        ],
    }


@router.post("/{chitti_id}/spawn-month")
async def spawn_month(
    chitti_id: str,
    manager_id: str = Depends(get_current_manager),
    client: NocoDBClient = Depends(get_nocodb_client),
):
    """
    Cycle Spawning Engine: creates exactly S transaction rows for the group's
    Current_Active_Month. Called by the n8n cron on the cycle anchor day, or
    manually from Page 1.
    """
    chitti = await _get_owned_chitti(client, chitti_id, manager_id)
    month_number = chitti["Current_Active_Month"]

    # Idempotency guard: don't double-spawn if this month's rows already exist.
    existing_where = client.eq("Month_Number", month_number)
    shares_where = client.eq("Chitti_ID", chitti_id)
    shares = await client.list_records(settings.NOCODB_TABLE_SHARES, where=shares_where, limit=500)

    share_ids = {s["Share_ID"] for s in shares}
    existing_tx = await client.list_records(
        settings.NOCODB_TABLE_TRANSACTIONS, where=existing_where, limit=1000
    )
    existing_share_ids_this_month = {t["Share_ID"] for t in existing_tx if t["Share_ID"] in share_ids}
    if existing_share_ids_this_month:
        raise HTTPException(
            409, f"Month {month_number} already has {len(existing_share_ids_this_month)} transactions spawned."
        )

    created = await spawn_month_transactions(
        client, chitti=chitti, shares=shares, month_number=month_number
    )
    return {"status": "spawned", "month_number": month_number, "transactions_created": len(created)}


@router.post("/{chitti_id}/advance-month")
async def advance_month(
    chitti_id: str,
    manager_id: str = Depends(get_current_manager),
    client: NocoDBClient = Depends(get_nocodb_client),
):
    """Increments Current_Active_Month, e.g. after month-end close-out."""
    chitti = await _get_owned_chitti(client, chitti_id, manager_id)
    next_month = chitti["Current_Active_Month"] + 1
    if next_month > chitti["Total_Months"]:
        raise HTTPException(400, "Chitti has already completed its full tenure (M months).")
    await client.update_record(
        settings.NOCODB_TABLE_CHITTIS, chitti["Id"], {"Current_Active_Month": next_month}
    )
    return {"status": "advanced", "current_active_month": next_month}

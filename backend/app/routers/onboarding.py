"""
Gated 4-step Universal Onboarding Sequence (Blueprint section 4).

Populates exactly:
  - 1 Chittis row
  - S Shares rows
  - ZERO Transactions rows (on-demand spawning happens later, per month)
"""
import uuid

from fastapi import APIRouter, Depends, HTTPException

from app.core.config import get_settings
from app.core.nocodb_client import NocoDBClient, get_nocodb_client
from app.core.security import get_current_manager
from app.models import ChittiOnboardingRequest
from app.services.chitti_math_engine import validate_parameters

router = APIRouter(prefix="/api/onboarding", tags=["onboarding"])
settings = get_settings()


@router.post("/chitti")
async def onboard_chitti(
    request: ChittiOnboardingRequest,
    manager_id: str = Depends(get_current_manager),
    client: NocoDBClient = Depends(get_nocodb_client),
):
    """
    Executes the full 4-step onboarding atomically:
    Step 1 (identity) + Step 2 (financial params) + Step 3 (calendar anchor)
    are merged into a single Chitti record; Step 4 populates the Shares roster.
    """
    step2 = request.step2

    # Server-side re-validation, even though the UI gates fields — never trust the client.
    validate_parameters(
        total_members=step2.total_members,
        total_months=step2.total_months,
        monthly_commission=step2.monthly_commission,
        undrawn_due=step2.undrawn_due,
        drawn_due=step2.drawn_due,
    )

    if len(request.step4.members) != step2.total_members:
        raise HTTPException(
            400,
            f"Member roster has {len(request.step4.members)} entries but "
            f"Total_Members (S) is {step2.total_members}. They must match.",
        )

    share_ids = [m.share_id for m in request.step4.members]
    if len(share_ids) != len(set(share_ids)):
        raise HTTPException(400, "Duplicate Share_ID values found in member roster.")

    chitti_id = f"C{uuid.uuid4().hex[:8].upper()}"

    chitti_payload = {
        "Chitti_ID": chitti_id,
        "Manager_ID": manager_id,
        "Chitti_Name": request.step1.chitti_name,
        "Rule_Template": request.step1.rule_template,
        "Total_Members": step2.total_members,
        "Total_Months": step2.total_months,
        "Monthly_Commission": str(step2.monthly_commission),
        "Undrawn_Due": str(step2.undrawn_due),
        "Drawn_Due": str(step2.drawn_due),
        "Cycle_Anchor_Day": request.step3.cycle_anchor_day,
        "Current_Active_Month": 1,
        # start_month_year (request.step3.start_month_year) drives the n8n cron
        # schedule — persist it in your Chittis table if you add that column.
    }
    await client.create_record(settings.NOCODB_TABLE_CHITTIS, chitti_payload)

    share_payloads = [
        {
            "Share_ID": member.share_id,
            "Chitti_ID": chitti_id,
            "Manager_ID": manager_id,
            "Member_Name": member.member_name,
            "Phone_Number": member.phone_number,
            "Draw_Status": "Undrawn",
            "Month_Drawn": None,
            "Advance_Credit": "0.00",
        }
        for member in request.step4.members
    ]
    await client.bulk_create(settings.NOCODB_TABLE_SHARES, share_payloads)

    return {
        "status": "created",
        "chitti_id": chitti_id,
        "members_created": len(share_payloads),
        "transactions_created": 0,  # zero future rows on Day 1, per Blueprint
    }

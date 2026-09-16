"""
Pydantic request/response schemas mirroring the NocoDB field-by-field schema
in Blueprint section 6.
"""
from decimal import Decimal
from datetime import datetime
from enum import Enum
from typing import Optional

from pydantic import BaseModel, Field, field_validator


# ---------------------------------------------------------------------------
# Enums
# ---------------------------------------------------------------------------

class DrawStatus(str, Enum):
    UNDRAWN = "Undrawn"
    DRAWN = "Drawn"


class PaymentStatus(str, Enum):
    PENDING = "Pending"
    PARTIAL = "Partial"
    VERIFIED = "Verified"


CYCLE_ANCHOR_DAYS = ["1st", "5th", "10th", "15th", "20th", "25th"]


# ---------------------------------------------------------------------------
# Onboarding (4-step gated sequence — Blueprint section 4)
# ---------------------------------------------------------------------------

class OnboardingStep1(BaseModel):
    chitti_name: str = Field(..., min_length=1)
    rule_template: str = Field(default="Incremental Model V1")


class OnboardingStep2(BaseModel):
    total_members: int = Field(..., gt=0, description="S")
    total_months: int = Field(..., gt=0, description="M")
    monthly_commission: Decimal = Field(..., ge=0, description="C")
    undrawn_due: Decimal = Field(..., gt=0, description="D_undrawn")
    drawn_due: Decimal = Field(..., gt=0, description="D_drawn")

    @field_validator("total_months")
    @classmethod
    def months_not_exceed_members(cls, v: int, info):
        total_members = info.data.get("total_members")
        if total_members and v > total_members:
            raise ValueError("Total_Months cannot exceed Total_Members")
        return v


class OnboardingStep3(BaseModel):
    start_month_year: str = Field(..., description="e.g. '2026-10'")
    cycle_anchor_day: str

    @field_validator("cycle_anchor_day")
    @classmethod
    def anchor_must_be_fixed(cls, v: str):
        if v not in CYCLE_ANCHOR_DAYS:
            raise ValueError(f"cycle_anchor_day must be one of {CYCLE_ANCHOR_DAYS} (no custom dates)")
        return v


class MemberInput(BaseModel):
    member_name: str
    share_id: str = Field(..., description="Custom Share ID, e.g. 'CHAND1'")
    phone_number: str = Field(..., pattern=r"^\+91\d{10}$", description="+91 format")


class OnboardingStep4(BaseModel):
    members: list[MemberInput]


class ChittiOnboardingRequest(BaseModel):
    step1: OnboardingStep1
    step2: OnboardingStep2
    step3: OnboardingStep3
    step4: OnboardingStep4


# ---------------------------------------------------------------------------
# Core entities
# ---------------------------------------------------------------------------

class Chitti(BaseModel):
    id: Optional[str] = Field(default=None, alias="Chitti_ID")
    manager_id: Optional[str] = Field(default=None, alias="Manager_ID")
    chitti_name: str = Field(alias="Chitti_Name")
    rule_template: str = Field(alias="Rule_Template")
    total_members: int = Field(alias="Total_Members")
    total_months: int = Field(alias="Total_Months")
    monthly_commission: Decimal = Field(alias="Monthly_Commission")
    undrawn_due: Decimal = Field(alias="Undrawn_Due")
    drawn_due: Decimal = Field(alias="Drawn_Due")
    cycle_anchor_day: str = Field(alias="Cycle_Anchor_Day")
    current_active_month: int = Field(default=1, alias="Current_Active_Month")

    model_config = {"populate_by_name": True}


class Share(BaseModel):
    id: Optional[str] = Field(default=None, alias="Share_ID")
    chitti_id: str = Field(alias="Chitti_ID")
    manager_id: Optional[str] = Field(default=None, alias="Manager_ID")
    member_name: str = Field(alias="Member_Name")
    phone_number: str = Field(alias="Phone_Number")
    draw_status: DrawStatus = Field(default=DrawStatus.UNDRAWN, alias="Draw_Status")
    month_drawn: Optional[int] = Field(default=None, alias="Month_Drawn")
    advance_credit: Decimal = Field(default=Decimal("0.00"), alias="Advance_Credit")

    model_config = {"populate_by_name": True}


class Transaction(BaseModel):
    id: Optional[str] = Field(default=None, alias="Trans_ID")
    share_id: str = Field(alias="Share_ID")
    month_number: int = Field(alias="Month_Number")
    amount_due: Decimal = Field(alias="Amount_Due")
    amount_paid: Decimal = Field(default=Decimal("0.00"), alias="Amount_Paid")
    pending_dues: Decimal = Field(default=Decimal("0.00"), alias="Pending_Dues")
    payment_status: PaymentStatus = Field(default=PaymentStatus.PENDING, alias="Payment_Status")
    payment_date: Optional[datetime] = Field(default=None, alias="Payment_Date")

    model_config = {"populate_by_name": True}


# ---------------------------------------------------------------------------
# Action payloads
# ---------------------------------------------------------------------------

class PaymentEntryRequest(BaseModel):
    share_id: str
    month_number: int
    amount_paid: Decimal = Field(..., gt=0)
    force_partial_confirm: bool = Field(
        default=False, description="Explicit confirm required when amount_paid < amount_due"
    )


class DrawUpdateRequest(BaseModel):
    share_id: str
    draw_status: DrawStatus
    month_drawn: Optional[int] = None


class ContactUpdateRequest(BaseModel):
    share_id: str
    member_name: Optional[str] = None
    phone_number: Optional[str] = Field(default=None, pattern=r"^\+91\d{10}$")


class ReceiptUploadMeta(BaseModel):
    share_id: str
    drive_view_url: str
    upload_date: datetime = Field(default_factory=datetime.utcnow)

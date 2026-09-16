"""
chitti_math_engine.py

Pure, dependency-free, deterministic financial math engine for chit fund cycles.
Zero hardcoded values — every function is parameterized entirely by the group's
own financial parameters (S, M, C, D_undrawn, D_drawn), as mandated in the
Master Blueprint section 5.

This module has NO knowledge of the database, HTTP, or any I/O. It is pure
functions over plain Python numbers, which makes it trivially unit-testable
and safe to import anywhere (API layer, n8n webhook handlers, offline scripts).

Formal Mathematical Model (per cycle month m, where 1 <= m <= M):
    1. N_drawn(m)   = m - 1
    2. N_undrawn(m) = S - (m - 1)
    3. P(m)         = N_undrawn(m) * D_undrawn + N_drawn(m) * D_drawn
    4. W(m)         = P(m) - C
    5. C(m)         = C   (fixed every month)
"""
from dataclasses import dataclass
from decimal import Decimal, ROUND_HALF_UP
from typing import Union

Number = Union[int, float, Decimal]


class InvalidChittiParametersError(ValueError):
    """Raised when group parameters violate the required constraints."""


@dataclass(frozen=True)
class MonthlyLedger:
    month: int
    n_undrawn: int
    n_drawn: int
    undrawn_rate: Decimal
    drawn_rate: Decimal
    gross_pool: Decimal
    manager_commission: Decimal
    net_winner_payout: Decimal


def _to_decimal(value: Number) -> Decimal:
    return value if isinstance(value, Decimal) else Decimal(str(value))


def _round(value: Decimal) -> Decimal:
    return value.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)


def validate_parameters(
    total_members: int,
    total_months: int,
    monthly_commission: Number,
    undrawn_due: Number,
    drawn_due: Number,
) -> None:
    """Guards against the exact edge cases the Blueprint calls out: zero/negative
    values, S/M mismatches, and non-numeric contamination."""
    if total_members <= 0:
        raise InvalidChittiParametersError("Total_Members (S) must be > 0")
    if total_months <= 0:
        raise InvalidChittiParametersError("Total_Months (M) must be > 0")
    if total_months > total_members:
        raise InvalidChittiParametersError(
            "Total_Months (M) cannot exceed Total_Members (S) — one draw per month"
        )
    commission = _to_decimal(monthly_commission)
    undrawn = _to_decimal(undrawn_due)
    drawn = _to_decimal(drawn_due)
    if commission < 0:
        raise InvalidChittiParametersError("Monthly_Commission (C) cannot be negative")
    if undrawn <= 0 or drawn <= 0:
        raise InvalidChittiParametersError("Undrawn_Due and Drawn_Due must be > 0")
    if drawn < undrawn:
        raise InvalidChittiParametersError(
            "Drawn_Due should be >= Undrawn_Due (drawn members pay the higher premium)"
        )


def count_drawn(month: int) -> int:
    """N_drawn(m) = m - 1"""
    return month - 1


def count_undrawn(total_members: int, month: int) -> int:
    """N_undrawn(m) = S - (m - 1)"""
    return total_members - (month - 1)


def gross_monthly_pool(
    total_members: int,
    month: int,
    undrawn_due: Number,
    drawn_due: Number,
) -> Decimal:
    """P(m) = [N_undrawn(m) * D_undrawn] + [N_drawn(m) * D_drawn]"""
    n_undrawn = count_undrawn(total_members, month)
    n_drawn = count_drawn(month)
    pool = (n_undrawn * _to_decimal(undrawn_due)) + (n_drawn * _to_decimal(drawn_due))
    return _round(pool)


def net_winner_payout(gross_pool: Number, monthly_commission: Number) -> Decimal:
    """W(m) = P(m) - C"""
    return _round(_to_decimal(gross_pool) - _to_decimal(monthly_commission))


def manager_commission(monthly_commission: Number) -> Decimal:
    """C(m) = C, fixed across all M cycles."""
    return _round(_to_decimal(monthly_commission))


def compute_month(
    total_members: int,
    month: int,
    monthly_commission: Number,
    undrawn_due: Number,
    drawn_due: Number,
) -> MonthlyLedger:
    """Computes the full ledger row for a single cycle month m."""
    if month < 1:
        raise InvalidChittiParametersError("month must be >= 1")

    n_undrawn = count_undrawn(total_members, month)
    n_drawn = count_drawn(month)
    pool = gross_monthly_pool(total_members, month, undrawn_due, drawn_due)
    commission = manager_commission(monthly_commission)
    payout = net_winner_payout(pool, commission)

    return MonthlyLedger(
        month=month,
        n_undrawn=n_undrawn,
        n_drawn=n_drawn,
        undrawn_rate=_round(_to_decimal(undrawn_due)),
        drawn_rate=_round(_to_decimal(drawn_due)),
        gross_pool=pool,
        manager_commission=commission,
        net_winner_payout=payout,
    )


def compute_full_matrix(
    total_members: int,
    total_months: int,
    monthly_commission: Number,
    undrawn_due: Number,
    drawn_due: Number,
) -> list[MonthlyLedger]:
    """Generates the complete M-row financial matrix for a group, e.g. the
    20-month table shown in the Blueprint section 5."""
    validate_parameters(total_members, total_months, monthly_commission, undrawn_due, drawn_due)
    return [
        compute_month(total_members, m, monthly_commission, undrawn_due, drawn_due)
        for m in range(1, total_months + 1)
    ]


def determine_share_due(draw_status: str, undrawn_due: Number, drawn_due: Number) -> Decimal:
    """Given a share's current Draw_Status ('Undrawn' | 'Drawn'), returns the
    Amount_Due to spawn for that share's next transaction row."""
    status = draw_status.strip().lower()
    if status == "drawn":
        return _round(_to_decimal(drawn_due))
    if status == "undrawn":
        return _round(_to_decimal(undrawn_due))
    raise InvalidChittiParametersError(f"Unknown Draw_Status: {draw_status!r}")


def apply_advance_credit(amount_due: Number, advance_credit: Number) -> tuple[Decimal, Decimal]:
    """
    Advance Credit Settlement (Blueprint section 6):
    If a share has an Advance_Credit balance, auto-settle the current month's
    due from that reserve first.

    Returns (amount_covered_by_credit, remaining_advance_credit).
    amount_covered_by_credit is capped at amount_due; the transaction is then
    auto-verified for that portion, and any remaining due must still be
    collected from the member.
    """
    due = _to_decimal(amount_due)
    credit = _to_decimal(advance_credit)
    if credit <= 0 or due <= 0:
        return Decimal("0.00"), _round(credit)

    covered = min(due, credit)
    remaining_credit = credit - covered
    return _round(covered), _round(remaining_credit)


def compute_advance_from_overpayment(amount_due: Number, amount_paid: Number) -> Decimal:
    """When Amount_Paid > Amount_Due, the excess is pushed into Shares.Advance_Credit."""
    due = _to_decimal(amount_due)
    paid = _to_decimal(amount_paid)
    excess = paid - due
    return _round(excess) if excess > 0 else Decimal("0.00")


def determine_payment_status(amount_due: Number, amount_paid: Number) -> str:
    """Returns one of 'Pending' | 'Partial' | 'Verified' per Blueprint section 6."""
    due = _to_decimal(amount_due)
    paid = _to_decimal(amount_paid)
    if paid <= 0:
        return "Pending"
    if paid < due:
        return "Partial"
    return "Verified"


def pending_dues(amount_due: Number, amount_paid: Number) -> Decimal:
    """Pending_Dues = Amount_Due - Amount_Paid (floored at 0)."""
    remainder = _to_decimal(amount_due) - _to_decimal(amount_paid)
    return _round(remainder) if remainder > 0 else Decimal("0.00")

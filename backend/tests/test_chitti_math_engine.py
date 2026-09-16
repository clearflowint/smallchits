"""
Validates chitti_math_engine.py against the exact 20-month sample matrix
published in the Master Blueprint (S=20, M=20, C=4000, D_undrawn=5000, D_drawn=6000).
"""
from decimal import Decimal

import pytest

from app.services.chitti_math_engine import (
    InvalidChittiParametersError,
    apply_advance_credit,
    compute_advance_from_overpayment,
    compute_full_matrix,
    compute_month,
    determine_payment_status,
    determine_share_due,
    pending_dues,
)

S, M, C, D_UNDRAWN, D_DRAWN = 20, 20, 4000, 5000, 6000

# (month, n_undrawn, n_drawn, gross_pool, commission, net_payout)
EXPECTED_MATRIX = [
    (1, 20, 0, 100000, 4000, 96000),
    (2, 19, 1, 101000, 4000, 97000),
    (3, 18, 2, 102000, 4000, 98000),
    (4, 17, 3, 103000, 4000, 99000),
    (5, 16, 4, 104000, 4000, 100000),
    (6, 15, 5, 105000, 4000, 101000),
    (7, 14, 6, 106000, 4000, 102000),
    (8, 13, 7, 107000, 4000, 103000),
    (9, 12, 8, 108000, 4000, 104000),
    (10, 11, 9, 109000, 4000, 105000),
    (11, 10, 10, 110000, 4000, 106000),
    (12, 9, 11, 111000, 4000, 107000),
    (13, 8, 12, 112000, 4000, 108000),
    (14, 7, 13, 113000, 4000, 109000),
    (15, 6, 14, 114000, 4000, 110000),
    (16, 5, 15, 115000, 4000, 111000),
    (17, 4, 16, 116000, 4000, 112000),
    (18, 3, 17, 117000, 4000, 113000),
    (19, 2, 18, 118000, 4000, 114000),
    (20, 1, 19, 119000, 4000, 115000),
]


def test_full_matrix_matches_blueprint_table():
    matrix = compute_full_matrix(S, M, C, D_UNDRAWN, D_DRAWN)
    assert len(matrix) == 20
    for row, expected in zip(matrix, EXPECTED_MATRIX):
        m, n_u, n_d, pool, comm, payout = expected
        assert row.month == m
        assert row.n_undrawn == n_u
        assert row.n_drawn == n_d
        assert row.gross_pool == Decimal(pool)
        assert row.manager_commission == Decimal(comm)
        assert row.net_winner_payout == Decimal(payout)


def test_single_month_matches_matrix():
    row = compute_month(S, 11, C, D_UNDRAWN, D_DRAWN)
    assert row.n_undrawn == 10
    assert row.n_drawn == 10
    assert row.gross_pool == Decimal(110000)
    assert row.net_winner_payout == Decimal(106000)


@pytest.mark.parametrize(
    "S,M,C,U,D,msg_fragment",
    [
        (0, 20, 4000, 5000, 6000, "Total_Members"),
        (20, 0, 4000, 5000, 6000, "Total_Months"),
        (20, 25, 4000, 5000, 6000, "cannot exceed"),
        (20, 20, -1, 5000, 6000, "Commission"),
        (20, 20, 4000, 0, 6000, "must be > 0"),
        (20, 20, 4000, 6000, 5000, "Drawn_Due should be >="),
    ],
)
def test_validation_rejects_bad_parameters(S, M, C, U, D, msg_fragment):
    with pytest.raises(InvalidChittiParametersError, match=msg_fragment):
        compute_full_matrix(S, M, C, U, D)


def test_determine_share_due():
    assert determine_share_due("Undrawn", D_UNDRAWN, D_DRAWN) == Decimal("5000.00")
    assert determine_share_due("Drawn", D_UNDRAWN, D_DRAWN) == Decimal("6000.00")
    assert determine_share_due("undrawn", D_UNDRAWN, D_DRAWN) == Decimal("5000.00")
    with pytest.raises(InvalidChittiParametersError):
        determine_share_due("Unknown", D_UNDRAWN, D_DRAWN)


def test_advance_credit_overpayment_and_settlement():
    # Member pays 20000 against a 6000 due -> 14000 goes to Advance_Credit
    excess = compute_advance_from_overpayment(amount_due=6000, amount_paid=20000)
    assert excess == Decimal("14000.00")

    # Next month due is 6000, credit is 14000 -> fully covered, 8000 credit remains
    covered, remaining = apply_advance_credit(amount_due=6000, advance_credit=14000)
    assert covered == Decimal("6000.00")
    assert remaining == Decimal("8000.00")

    # Following month due is 6000, credit is 8000 -> fully covered, 2000 remains
    covered2, remaining2 = apply_advance_credit(amount_due=6000, advance_credit=8000)
    assert covered2 == Decimal("6000.00")
    assert remaining2 == Decimal("2000.00")


def test_advance_credit_partial_coverage():
    # Credit of 2000 against a due of 6000 only partially covers
    covered, remaining = apply_advance_credit(amount_due=6000, advance_credit=2000)
    assert covered == Decimal("2000.00")
    assert remaining == Decimal("0.00")


def test_payment_status_transitions():
    assert determine_payment_status(6000, 0) == "Pending"
    assert determine_payment_status(6000, 3000) == "Partial"
    assert determine_payment_status(6000, 6000) == "Verified"
    assert determine_payment_status(6000, 9000) == "Verified"


def test_pending_dues_never_negative():
    assert pending_dues(6000, 9000) == Decimal("0.00")
    assert pending_dues(6000, 3000) == Decimal("3000.00")
    assert pending_dues(6000, 6000) == Decimal("0.00")

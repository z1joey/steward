from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.core.db import get_db
from app.core.deps import StoreContext, require_role, require_store_membership
from app.enums import Role
from app.modules.claims.schemas import (
    ApproveClaimOut,
    ClaimListOut,
    RejectClaimOut,
    VersionIn,
)
from app.modules.claims.service import approve_claim, list_claims, reject_claim

router = APIRouter()


@router.get("/claims", response_model=ClaimListOut)
def list_claims_route(
    status: str | None = Query(default=None),
    ctx: StoreContext = Depends(require_store_membership),   # 两角色可查（B-specs §2.3）
    db: Session = Depends(get_db),
) -> ClaimListOut:
    return list_claims(db, ctx, status=status)


@router.post("/claims/{claim_id}/approve", response_model=ApproveClaimOut)
def approve_claim_route(
    claim_id: int,
    payload: VersionIn,
    ctx: StoreContext = Depends(require_role(Role.manager)),   # Deny：claims.approve（AC-LED-06）
    db: Session = Depends(get_db),
) -> ApproveClaimOut:
    return approve_claim(db, ctx, claim_id, payload.version)


@router.post("/claims/{claim_id}/reject", response_model=RejectClaimOut)
def reject_claim_route(
    claim_id: int,
    payload: VersionIn,
    ctx: StoreContext = Depends(require_role(Role.manager)),   # Deny：claims.reject（AC-LED-06）
    db: Session = Depends(get_db),
) -> RejectClaimOut:
    return reject_claim(db, ctx, claim_id, payload.version)

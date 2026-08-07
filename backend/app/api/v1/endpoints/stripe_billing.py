"""Stripe webhook receiver and status endpoints."""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.orm import Session

from app.database.session import get_db
from app.services.stripe_service import StripeBillingService, StripeSignatureError

router = APIRouter(prefix="/msp/billing/stripe", tags=["Stripe Billing"])


@router.get("/status")
def stripe_status(db: Session = Depends(get_db)):
    return StripeBillingService(db).status()


@router.post("/webhook")
async def stripe_webhook(request: Request, db: Session = Depends(get_db)):
    """Stripe webhook receiver. Verifies Stripe-Signature via STRIPE_WEBHOOK_SECRET."""
    payload = await request.body()
    sig = request.headers.get("Stripe-Signature") or request.headers.get("stripe-signature")
    try:
        return StripeBillingService(db).process_webhook(payload, sig)
    except StripeSignatureError as e:
        raise HTTPException(400, f"Invalid signature: {e}") from e
    except ValueError as e:
        raise HTTPException(400, str(e)) from e
    except Exception as e:
        # Non-2xx so Stripe retries
        raise HTTPException(500, f"Webhook processing failed: {e}") from e

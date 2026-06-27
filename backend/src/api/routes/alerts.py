"""Early warning alerts API — Phase 5."""
from datetime import datetime, timezone
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select, desc
from sqlalchemy.ext.asyncio import AsyncSession
from pydantic import BaseModel

from src.config.database import get_db
from src.models.core import User, AuditLog
from src.models.risk import (
    Alert, AlertStatus, AlertSeverity, AlertStatusHistory, RiskCategory,
    is_valid_alert_transition,
)
from src.middleware.auth import get_current_user, require_permission
from src.services.notification_service import dispatch_alert_notifications

router = APIRouter()


class AlertCreate(BaseModel):
    title: str
    description: str
    category: RiskCategory
    severity: AlertSeverity
    supplier_id: Optional[str] = None
    trigger_type: str = "manual"
    trigger_data: Optional[dict] = None
    notify_emails: Optional[list[str]] = None


class AlertStatusUpdate(BaseModel):
    status: str
    notes: Optional[str] = None
    assigned_to_id: Optional[str] = None


@router.get("")
async def list_alerts(
    severity: Optional[str] = Query(None),
    status_filter: Optional[str] = Query(None, alias="status"),
    supplier_id: Optional[str] = Query(None),
    limit: int = Query(50, ge=1, le=200),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    query = select(Alert).where(Alert.organization_id == current_user.organization_id)
    if severity:
        query = query.where(Alert.severity == severity)
    if status_filter:
        query = query.where(Alert.status == status_filter)
    if supplier_id:
        query = query.where(Alert.supplier_id == supplier_id)

    result = await db.execute(query.order_by(desc(Alert.created_at)).limit(limit))
    alerts = result.scalars().all()

    return {
        "alerts": [
            {
                "id": str(a.id),
                "title": a.title,
                "description": a.description,
                "category": a.category.value,
                "severity": a.severity.value,
                "status": a.status.value,
                "supplier_id": str(a.supplier_id) if a.supplier_id else None,
                "trigger_type": a.trigger_type,
                "created_at": a.created_at.isoformat(),
                "resolved_at": a.resolved_at.isoformat() if a.resolved_at else None,
            }
            for a in alerts
        ],
        "total": len(alerts),
    }


@router.post("", status_code=status.HTTP_201_CREATED)
async def create_alert(
    payload: AlertCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_permission("alerts:write")),
):
    """Create an early-warning alert and dispatch notifications to configured channels."""
    alert = Alert(
        organization_id=current_user.organization_id,
        supplier_id=payload.supplier_id,
        title=payload.title,
        description=payload.description,
        category=payload.category,
        severity=payload.severity,
        status=AlertStatus.CREATED,
        trigger_type=payload.trigger_type,
        trigger_data=payload.trigger_data,
        notifications_sent=[],
    )
    db.add(alert)
    await db.flush()

    # Dispatch notifications (Slack/email) — records what was actually sent.
    sent = await dispatch_alert_notifications(
        title=f"[{payload.severity.value.upper()}] {payload.title}",
        body=payload.description,
        email_recipients=payload.notify_emails,
    )
    alert.notifications_sent = sent

    db.add(AuditLog(
        user_id=current_user.id,
        organization_id=current_user.organization_id,
        action=f"alert_created:{payload.severity.value}",
        resource_type="alert",
        resource_id=str(alert.id),
    ))
    await db.refresh(alert)

    return {
        "id": str(alert.id),
        "title": alert.title,
        "severity": alert.severity.value,
        "status": alert.status.value,
        "created_at": alert.created_at.isoformat(),
        "notifications_sent": alert.notifications_sent,
    }


@router.get("/{alert_id}")
async def get_alert(
    alert_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    result = await db.execute(
        select(Alert).where(
            Alert.id == alert_id,
            Alert.organization_id == current_user.organization_id,
        )
    )
    alert = result.scalar_one_or_none()
    if not alert:
        raise HTTPException(status_code=404, detail="Alert not found")

    # Include status history
    history_result = await db.execute(
        select(AlertStatusHistory).where(AlertStatusHistory.alert_id == alert_id)
        .order_by(AlertStatusHistory.changed_at)
    )
    history = history_result.scalars().all()

    return {
        "id": str(alert.id),
        "title": alert.title,
        "description": alert.description,
        "category": alert.category.value,
        "severity": alert.severity.value,
        "status": alert.status.value,
        "supplier_id": str(alert.supplier_id) if alert.supplier_id else None,
        "trigger_type": alert.trigger_type,
        "trigger_data": alert.trigger_data,
        "notifications_sent": alert.notifications_sent,
        "created_at": alert.created_at.isoformat(),
        "resolved_at": alert.resolved_at.isoformat() if alert.resolved_at else None,
        "resolution_notes": alert.resolution_notes,
        "status_history": [
            {
                "from_status": h.from_status.value if h.from_status else None,
                "to_status": h.to_status.value,
                "notes": h.notes,
                "changed_at": h.changed_at.isoformat(),
            }
            for h in history
        ],
    }


@router.patch("/{alert_id}/status")
async def update_alert_status(
    alert_id: str,
    payload: AlertStatusUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_permission("alerts:write")),
):
    """Transition alert status with full audit trail."""
    result = await db.execute(
        select(Alert).where(
            Alert.id == alert_id,
            Alert.organization_id == current_user.organization_id,
        )
    )
    alert = result.scalar_one_or_none()
    if not alert:
        raise HTTPException(status_code=404, detail="Alert not found")

    # Coerce the raw string to the enum and reject unknown values explicitly.
    try:
        new_status = AlertStatus(payload.status)
    except ValueError:
        valid = ", ".join(s.value for s in AlertStatus)
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"Invalid alert status '{payload.status}'. Valid values: {valid}",
        )

    prev_status = alert.status
    if not is_valid_alert_transition(prev_status, new_status):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Cannot transition alert from '{prev_status.value}' to '{new_status.value}'",
        )

    alert.status = new_status

    now = datetime.now(timezone.utc)
    if new_status == AlertStatus.ASSIGNED:
        alert.assigned_at = now
        if payload.assigned_to_id:
            alert.assigned_to_id = payload.assigned_to_id
    elif new_status == AlertStatus.RESOLVED:
        alert.resolved_at = now
        alert.resolution_notes = payload.notes
    elif new_status == AlertStatus.CLOSED:
        alert.closed_at = now

    # Status history entry
    db.add(AlertStatusHistory(
        alert_id=alert.id,
        changed_by_id=current_user.id,
        from_status=prev_status,
        to_status=new_status,
        notes=payload.notes,
    ))

    db.add(AuditLog(
        user_id=current_user.id,
        organization_id=current_user.organization_id,
        action=f"alert_status_change:{prev_status.value}->{new_status.value}",
        resource_type="alert",
        resource_id=alert_id,
    ))

    return {"id": alert_id, "status": new_status.value}

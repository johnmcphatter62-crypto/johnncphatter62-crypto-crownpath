from sqlalchemy import select

from crownpath.database import session
from crownpath.models import AuditEvent


def record_audit(
    user_id,
    action,
    category,
    result,
    resource_type=None,
    resource_id=None,
    reason=None,
):
    db = session()
    try:
        event = AuditEvent(
            user_id=user_id,
            action=action,
            category=category,
            resource_type=resource_type,
            resource_id=resource_id,
            result=result,
            reason=reason,
        )
        db.add(event)
        db.commit()
    finally:
        db.close()


def recent_audit(limit=100):
    db = session()
    try:
        rows = db.scalars(
            select(AuditEvent)
            .order_by(AuditEvent.audit_id.desc())
            .limit(int(limit))
        ).all()
        return [
            {
                "audit_id": row.audit_id,
                "user_id": row.user_id,
                "action": row.action,
                "category": row.category,
                "resource_type": row.resource_type,
                "resource_id": row.resource_id,
                "result": row.result,
                "reason": row.reason,
                "created_at": row.created_at,
            }
            for row in rows
        ]
    finally:
        db.close()

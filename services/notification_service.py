from datetime import datetime, timezone
import logging
from models.database import NotificationRecord, EmergencyCase, EmergencyAlert, AuditLog

logger = logging.getLogger(__name__)

def utcnow():
    return datetime.now(timezone.utc)

class NotificationService:
    @staticmethod
    def create_notification(session, title, message, severity="HIGH", recipient_type="ALL", case_id=None, alert_id=None):
        notif = NotificationRecord(
            title=title,
            message=message,
            severity=severity,
            recipient_type=recipient_type,
            case_id=case_id,
            alert_id=alert_id,
            created_at=utcnow()
        )
        session.add(notif)
        session.commit()
        return notif

    @staticmethod
    def get_citizen_notifications(session, limit=20):
        return session.query(NotificationRecord).filter(
            NotificationRecord.recipient_type.in_(["CITIZEN", "ALL"])
        ).order_by(NotificationRecord.created_at.desc()).limit(limit).all()

    @staticmethod
    def get_operator_notifications(session, limit=30):
        return session.query(NotificationRecord).filter(
            NotificationRecord.recipient_type.in_(["OPERATOR", "ALL"])
        ).order_by(NotificationRecord.created_at.desc()).limit(limit).all()

    @staticmethod
    def get_active_buzzer_cases(session):
        """Returns all unacknowledged emergency cases that need the buzzer to sound."""
        return session.query(EmergencyCase).filter(
            EmergencyCase.requires_buzzer == True,
            EmergencyCase.buzzer_acknowledged == False,
            EmergencyCase.status.in_(["NEW", "ASSIGNED", "ESCALATED"])
        ).order_by(EmergencyCase.created_at.desc()).all()

    @staticmethod
    def acknowledge_notification(session, notification_id):
        notif = session.get(NotificationRecord, notification_id)
        if notif:
            notif.is_read = True
            notif.is_acknowledged = True
            notif.acknowledged_at = utcnow()
            session.commit()
            return True
        return False

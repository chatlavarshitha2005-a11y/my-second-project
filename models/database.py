from datetime import datetime, timezone
from sqlalchemy import (
    Column, Integer, String, Float, Text, Boolean, DateTime, ForeignKey, Index
)
from sqlalchemy.orm import declarative_base, relationship

Base = declarative_base()

def utcnow():
    return datetime.now(timezone.utc).replace(tzinfo=None)

class Employee(Base):
    __tablename__ = "employees"
    
    id = Column(Integer, primary_key=True)
    badge_id = Column(String(50), unique=True, nullable=False, index=True)
    name = Column(String(100), nullable=False)
    email = Column(String(120), unique=True, nullable=False)
    phone = Column(String(30), nullable=True)
    role = Column(String(80), nullable=False, default="Call Center Operator")
    department = Column(String(80), nullable=False, default="Emergency Response")
    status = Column(String(30), nullable=False, default="Available", index=True)  # Available, Busy, Offline, No response
    current_active_cases = Column(Integer, default=0)
    total_cases_handled = Column(Integer, default=0)
    avg_response_seconds = Column(Float, default=0.0)
    last_status_change = Column(DateTime, default=utcnow)
    created_at = Column(DateTime, default=utcnow)
    
    # Relationships
    assignments = relationship("CaseAssignment", back_populates="employee", cascade="all, delete-orphan")
    assigned_cases = relationship("EmergencyCase", back_populates="assigned_employee")

    def to_dict(self):
        return {
            "id": self.id,
            "badge_id": self.badge_id,
            "name": self.name,
            "email": self.email,
            "phone": self.phone or "N/A",
            "role": self.role,
            "department": self.department,
            "status": self.status,
            "current_active_cases": self.current_active_cases,
            "total_cases_handled": self.total_cases_handled,
            "avg_response_seconds": round(self.avg_response_seconds, 1),
            "last_status_change": self.last_status_change.isoformat() if self.last_status_change else None,
            "created_at": self.created_at.isoformat() if self.created_at else None
        }


class EmergencyCase(Base):
    __tablename__ = "emergency_cases"
    
    id = Column(Integer, primary_key=True)
    case_number = Column(String(50), unique=True, nullable=False, index=True)
    citizen_name = Column(String(100), nullable=True, default="Anonymous Citizen")
    citizen_phone = Column(String(30), nullable=True)
    emergency_type = Column(String(80), nullable=False, index=True)
    priority = Column(String(20), nullable=False, default="HIGH", index=True)  # CRITICAL, HIGH, MEDIUM, LOW
    status = Column(String(30), nullable=False, default="NEW", index=True)  # NEW, ASSIGNED, ACKNOWLEDGED, IN_PROGRESS, ESCALATED, RESOLVED, CANCELLED
    description = Column(Text, nullable=False)
    location_name = Column(String(200), nullable=False)
    latitude = Column(Float, nullable=True)
    longitude = Column(Float, nullable=True)
    people_affected = Column(Integer, default=1)
    attachment_path = Column(String(255), nullable=True)
    assigned_employee_id = Column(Integer, ForeignKey("employees.id"), nullable=True)
    
    # Buzzer & Alarm tracking
    requires_buzzer = Column(Boolean, default=True)
    buzzer_acknowledged = Column(Boolean, default=False)
    buzzer_acknowledged_at = Column(DateTime, nullable=True)
    buzzer_acknowledged_by = Column(String(100), nullable=True)
    
    # Timestamps
    created_at = Column(DateTime, default=utcnow, index=True)
    updated_at = Column(DateTime, default=utcnow, onupdate=utcnow)
    first_acknowledged_at = Column(DateTime, nullable=True)
    resolved_at = Column(DateTime, nullable=True)
    resolution_notes = Column(Text, nullable=True)
    
    # Relationships
    assigned_employee = relationship("Employee", back_populates="assigned_cases")
    assignments = relationship("CaseAssignment", back_populates="case", cascade="all, delete-orphan", order_by="CaseAssignment.id.desc()")
    status_history = relationship("CaseStatusHistory", back_populates="case", cascade="all, delete-orphan", order_by="CaseStatusHistory.id.desc()")
    ai_analyses = relationship("AIAnalysisRecord", back_populates="case", cascade="all, delete-orphan", order_by="AIAnalysisRecord.id.desc()")

    def to_dict(self):
        latest_ai = self.ai_analyses[0].to_dict() if self.ai_analyses else None
        return {
            "id": self.id,
            "case_number": self.case_number,
            "citizen_name": self.citizen_name or "Anonymous",
            "citizen_phone": self.citizen_phone or "Not provided",
            "emergency_type": self.emergency_type,
            "priority": self.priority,
            "status": self.status,
            "description": self.description,
            "location_name": self.location_name,
            "latitude": self.latitude,
            "longitude": self.longitude,
            "people_affected": self.people_affected,
            "attachment_path": self.attachment_path,
            "assigned_employee_id": self.assigned_employee_id,
            "assigned_employee_name": self.assigned_employee.name if self.assigned_employee else "Unassigned",
            "assigned_employee_badge": self.assigned_employee.badge_id if self.assigned_employee else None,
            "requires_buzzer": self.requires_buzzer and not self.buzzer_acknowledged,
            "buzzer_acknowledged": self.buzzer_acknowledged,
            "buzzer_acknowledged_at": self.buzzer_acknowledged_at.isoformat() if self.buzzer_acknowledged_at else None,
            "buzzer_acknowledged_by": self.buzzer_acknowledged_by,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
            "first_acknowledged_at": self.first_acknowledged_at.isoformat() if self.first_acknowledged_at else None,
            "resolved_at": self.resolved_at.isoformat() if self.resolved_at else None,
            "resolution_notes": self.resolution_notes,
            "latest_ai": latest_ai
        }


class CaseAssignment(Base):
    __tablename__ = "case_assignments"
    
    id = Column(Integer, primary_key=True)
    case_id = Column(Integer, ForeignKey("emergency_cases.id"), nullable=False, index=True)
    employee_id = Column(Integer, ForeignKey("employees.id"), nullable=False, index=True)
    assigned_at = Column(DateTime, default=utcnow)
    ack_deadline = Column(DateTime, nullable=False)
    acknowledged_at = Column(DateTime, nullable=True)
    status = Column(String(30), nullable=False, default="PENDING_ACK")  # PENDING_ACK, ACKNOWLEDGED, TIMED_OUT, REASSIGNED, OVERRIDDEN
    attempt_number = Column(Integer, default=1)
    notes = Column(Text, nullable=True)
    
    # Relationships
    case = relationship("EmergencyCase", back_populates="assignments")
    employee = relationship("Employee", back_populates="assignments")

    def to_dict(self):
        return {
            "id": self.id,
            "case_id": self.case_id,
            "employee_id": self.employee_id,
            "employee_name": self.employee.name if self.employee else "Unknown",
            "employee_badge": self.employee.badge_id if self.employee else "N/A",
            "assigned_at": self.assigned_at.isoformat() if self.assigned_at else None,
            "ack_deadline": self.ack_deadline.isoformat() if self.ack_deadline else None,
            "acknowledged_at": self.acknowledged_at.isoformat() if self.acknowledged_at else None,
            "status": self.status,
            "attempt_number": self.attempt_number,
            "notes": self.notes
        }


class EmergencyAlert(Base):
    __tablename__ = "emergency_alerts"
    
    id = Column(Integer, primary_key=True)
    alert_code = Column(String(50), unique=True, nullable=False, index=True)
    title = Column(String(150), nullable=False)
    alert_type = Column(String(80), nullable=False)  # Heavy Rainfall, Thunderstorm, Cyclone Alert, Flood, etc.
    severity = Column(String(20), nullable=False, default="HIGH")  # CRITICAL, HIGH, MEDIUM, LOW
    area_name = Column(String(150), nullable=False)
    latitude = Column(Float, nullable=True)
    longitude = Column(Float, nullable=True)
    radius_km = Column(Float, default=25.0)
    message = Column(Text, nullable=False)
    safety_guidelines = Column(Text, nullable=True)
    source = Column(String(120), nullable=False, default="IMD Regional Meteorological Centre (Simulated)")
    is_simulated = Column(Boolean, default=True)
    valid_from = Column(DateTime, default=utcnow)
    valid_until = Column(DateTime, nullable=True)
    is_active = Column(Boolean, default=True, index=True)
    created_at = Column(DateTime, default=utcnow)

    def to_dict(self):
        return {
            "id": self.id,
            "alert_code": self.alert_code,
            "title": self.title,
            "alert_type": self.alert_type,
            "severity": self.severity,
            "area_name": self.area_name,
            "latitude": self.latitude,
            "longitude": self.longitude,
            "radius_km": self.radius_km,
            "message": self.message,
            "safety_guidelines": self.safety_guidelines,
            "source": self.source,
            "is_simulated": self.is_simulated,
            "valid_from": self.valid_from.isoformat() if self.valid_from else None,
            "valid_until": self.valid_until.isoformat() if self.valid_until else None,
            "is_active": self.is_active,
            "created_at": self.created_at.isoformat() if self.created_at else None
        }


class NotificationRecord(Base):
    __tablename__ = "notification_records"
    
    id = Column(Integer, primary_key=True)
    recipient_type = Column(String(30), default="ALL")  # CITIZEN, OPERATOR, ALL
    case_id = Column(Integer, nullable=True)
    alert_id = Column(Integer, nullable=True)
    title = Column(String(150), nullable=False)
    message = Column(Text, nullable=False)
    severity = Column(String(20), default="HIGH")
    is_read = Column(Boolean, default=False)
    is_acknowledged = Column(Boolean, default=False)
    acknowledged_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=utcnow, index=True)

    def to_dict(self):
        return {
            "id": self.id,
            "recipient_type": self.recipient_type,
            "case_id": self.case_id,
            "alert_id": self.alert_id,
            "title": self.title,
            "message": self.message,
            "severity": self.severity,
            "is_read": self.is_read,
            "is_acknowledged": self.is_acknowledged,
            "acknowledged_at": self.acknowledged_at.isoformat() if self.acknowledged_at else None,
            "created_at": self.created_at.isoformat() if self.created_at else None
        }


class CaseStatusHistory(Base):
    __tablename__ = "case_status_history"
    
    id = Column(Integer, primary_key=True)
    case_id = Column(Integer, ForeignKey("emergency_cases.id"), nullable=False, index=True)
    old_status = Column(String(30), nullable=True)
    new_status = Column(String(30), nullable=False)
    action_by = Column(String(100), default="System")
    action_type = Column(String(50), nullable=False)  # CREATED, ASSIGNED, ACKNOWLEDGED, REASSIGNED, ESCALATED, RESOLVED
    notes = Column(Text, nullable=True)
    created_at = Column(DateTime, default=utcnow)
    
    case = relationship("EmergencyCase", back_populates="status_history")

    def to_dict(self):
        return {
            "id": self.id,
            "case_id": self.case_id,
            "old_status": self.old_status,
            "new_status": self.new_status,
            "action_by": self.action_by,
            "action_type": self.action_type,
            "notes": self.notes,
            "created_at": self.created_at.isoformat() if self.created_at else None
        }


class AIAnalysisRecord(Base):
    __tablename__ = "ai_analysis_records"
    
    id = Column(Integer, primary_key=True)
    case_id = Column(Integer, ForeignKey("emergency_cases.id"), nullable=False, index=True)
    model_used = Column(String(100), default="openai/gpt-oss-20b")
    summary = Column(Text, nullable=False)
    extracted_facts = Column(Text, nullable=True)        # JSON string
    missing_information = Column(Text, nullable=True)    # JSON string
    recommended_priority = Column(String(20), default="HIGH")
    recommended_actions = Column(Text, nullable=True)    # JSON string
    recommended_resources = Column(Text, nullable=True)  # JSON string
    transcript_summary = Column(Text, nullable=True)
    is_fallback = Column(Boolean, default=False)
    created_at = Column(DateTime, default=utcnow)
    
    case = relationship("EmergencyCase", back_populates="ai_analyses")

    def to_dict(self):
        import json
        def safe_json(val):
            if not val:
                return []
            try:
                return json.loads(val)
            except Exception:
                return [val]

        return {
            "id": self.id,
            "case_id": self.case_id,
            "model_used": self.model_used,
            "summary": self.summary,
            "extracted_facts": safe_json(self.extracted_facts),
            "missing_information": safe_json(self.missing_information),
            "recommended_priority": self.recommended_priority,
            "recommended_actions": safe_json(self.recommended_actions),
            "recommended_resources": safe_json(self.recommended_resources),
            "transcript_summary": self.transcript_summary,
            "is_fallback": self.is_fallback,
            "created_at": self.created_at.isoformat() if self.created_at else None
        }


class AuditLog(Base):
    __tablename__ = "audit_logs"
    
    id = Column(Integer, primary_key=True)
    actor = Column(String(100), default="System")
    action = Column(String(80), nullable=False)
    target_type = Column(String(50), nullable=False)  # CASE, EMPLOYEE, ALERT, SYSTEM
    target_id = Column(String(50), nullable=True)
    details = Column(Text, nullable=True)
    ip_address = Column(String(50), nullable=True)
    created_at = Column(DateTime, default=utcnow, index=True)

    def to_dict(self):
        return {
            "id": self.id,
            "actor": self.actor,
            "action": self.action,
            "target_type": self.target_type,
            "target_id": self.target_id,
            "details": self.details,
            "ip_address": self.ip_address,
            "created_at": self.created_at.isoformat() if self.created_at else None
        }

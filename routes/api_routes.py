from flask import Blueprint, request, jsonify, current_app
from datetime import datetime, timezone
import json
import uuid
import os
from werkzeug.utils import secure_filename
from config import Config
from models.database import (
    Employee, EmergencyCase, CaseAssignment, EmergencyAlert,
    NotificationRecord, CaseStatusHistory, AIAnalysisRecord, AuditLog
)
from services.ai_service import AIService
from services.routing_service import RoutingService
from services.weather_service import WeatherService
from services.notification_service import NotificationService

api_bp = Blueprint("api", __name__, url_prefix="/api")

def get_db():
    return current_app.db_session()

def utcnow():
    return datetime.now(timezone.utc)

@api_bp.route("/stats", methods=["GET"])
def get_dashboard_stats():
    """Returns overview card metrics calculated from actual database records."""
    session = get_db()
    try:
        # Check timeouts before calculating stats
        RoutingService.check_and_process_timeouts(session)

        total_active = session.query(EmergencyCase).filter(
            EmergencyCase.status.in_(["NEW", "ASSIGNED", "ACKNOWLEDGED", "IN_PROGRESS", "ESCALATED"])
        ).count()

        critical_active = session.query(EmergencyCase).filter(
            EmergencyCase.priority == "CRITICAL",
            EmergencyCase.status.in_(["NEW", "ASSIGNED", "ACKNOWLEDGED", "IN_PROGRESS", "ESCALATED"])
        ).count()

        awaiting_ack = session.query(EmergencyCase).filter(
            EmergencyCase.status.in_(["NEW", "ASSIGNED"])
        ).count()

        available_employees = session.query(Employee).filter(
            Employee.status == "Available"
        ).count()

        total_employees = session.query(Employee).count()

        # Calculate actual average response time from acknowledged assignments
        acknowledged_assignments = session.query(CaseAssignment).filter(
            CaseAssignment.status == "ACKNOWLEDGED",
            CaseAssignment.acknowledged_at != None
        ).all()

        if acknowledged_assignments:
            total_seconds = sum(
                (a.acknowledged_at - a.assigned_at).total_seconds()
                for a in acknowledged_assignments
                if a.acknowledged_at and a.assigned_at
            )
            avg_response_seconds = round(total_seconds / len(acknowledged_assignments), 1)
        else:
            avg_response_seconds = 0.0

        # Buzzer status
        active_buzzers = session.query(EmergencyCase).filter(
            EmergencyCase.requires_buzzer == True,
            EmergencyCase.buzzer_acknowledged == False,
            EmergencyCase.status.in_(["NEW", "ASSIGNED", "ESCALATED"])
        ).count()

        return jsonify({
            "success": True,
            "data": {
                "total_active": total_active,
                "critical_active": critical_active,
                "awaiting_ack": awaiting_ack,
                "available_employees": available_employees,
                "total_employees": total_employees,
                "avg_response_seconds": avg_response_seconds,
                "active_buzzers": active_buzzers
            }
        })
    finally:
        session.close()

@api_bp.route("/cases", methods=["GET"])
def list_cases():
    """Lists emergency cases with filters and search."""
    session = get_db()
    try:
        query = session.query(EmergencyCase)

        # Filters
        emergency_type = request.args.get("emergency_type")
        if emergency_type and emergency_type != "ALL":
            query = query.filter(EmergencyCase.emergency_type == emergency_type)

        priority = request.args.get("priority")
        if priority and priority != "ALL":
            query = query.filter(EmergencyCase.priority == priority)

        status = request.args.get("status")
        if status and status != "ALL":
            query = query.filter(EmergencyCase.status == status)

        employee_id = request.args.get("employee_id")
        if employee_id and employee_id.isdigit():
            query = query.filter(EmergencyCase.assigned_employee_id == int(employee_id))

        search = request.args.get("search", "").strip()
        if search:
            search_filter = f"%{search}%"
            query = query.filter(
                (EmergencyCase.case_number.ilike(search_filter)) |
                (EmergencyCase.location_name.ilike(search_filter)) |
                (EmergencyCase.description.ilike(search_filter)) |
                (EmergencyCase.citizen_name.ilike(search_filter))
            )

        cases = query.order_by(EmergencyCase.created_at.desc()).all()
        return jsonify({
            "success": True,
            "count": len(cases),
            "data": [c.to_dict() for c in cases]
        })
    finally:
        session.close()

@api_bp.route("/cases", methods=["POST"])
def create_case():
    """
    Submits a new emergency case (from Citizen Portal or Operator Intake).
    Performs validation, saves attachment if provided, creates DB record,
    triggers AI triage analysis, and executes automatic employee routing.
    """
    session = get_db()
    try:
        is_json = request.is_json
        data = request.get_json(silent=True) or request.form.to_dict()

        # Validation
        emergency_type = data.get("emergency_type", "").strip()
        description = data.get("description", "").strip()
        location_name = data.get("location_name", "").strip()

        if not emergency_type:
            return jsonify({"success": False, "error": "Emergency type is required."}), 400
        if not description or len(description) < 5:
            return jsonify({"success": False, "error": "Please provide a descriptive incident summary."}), 400
        if not location_name:
            return jsonify({"success": False, "error": "Location or address is required."}), 400

        citizen_name = data.get("citizen_name", "Anonymous Citizen").strip() or "Anonymous Citizen"
        citizen_phone = data.get("citizen_phone", "").strip() or None
        
        try:
            people_affected = int(data.get("people_affected", 1))
        except (ValueError, TypeError):
            people_affected = 1

        try:
            latitude = float(data.get("latitude")) if data.get("latitude") else None
            longitude = float(data.get("longitude")) if data.get("longitude") else None
        except (ValueError, TypeError):
            latitude, longitude = None, None

        # Handle attachment upload if present
        attachment_path = None
        if "attachment" in request.files:
            file = request.files["attachment"]
            if file and file.filename:
                filename = secure_filename(file.filename)
                ext = filename.rsplit(".", 1)[-1].lower() if "." in filename else ""
                if ext in Config.ALLOWED_EXTENSIONS:
                    safe_name = f"{uuid.uuid4().hex[:10]}_{filename}"
                    save_path = Config.UPLOAD_FOLDER / safe_name
                    file.save(str(save_path))
                    attachment_path = f"/static/uploads/{safe_name}"

        # Generate unique case number
        count = session.query(EmergencyCase).count() + 1001
        case_number = f"RESQ-2026-{count}"

        # Initial default priority
        priority = data.get("priority", "HIGH")
        if priority not in Config.PRIORITIES:
            priority = "HIGH"

        now = utcnow()
        case = EmergencyCase(
            case_number=case_number,
            citizen_name=citizen_name,
            citizen_phone=citizen_phone,
            emergency_type=emergency_type,
            priority=priority,
            status="NEW",
            description=description,
            location_name=location_name,
            latitude=latitude,
            longitude=longitude,
            people_affected=people_affected,
            attachment_path=attachment_path,
            requires_buzzer=True,
            buzzer_acknowledged=False,
            created_at=now,
            updated_at=now
        )
        session.add(case)
        session.commit()

        # Log case creation in status history
        history = CaseStatusHistory(
            case_id=case.id,
            old_status=None,
            new_status="NEW",
            action_by="Citizen Intake",
            action_type="CREATED",
            notes=f"Emergency case created by {citizen_name} at {location_name}."
        )
        session.add(history)

        # Trigger AI Analysis
        ai_service = AIService()
        ai_res = ai_service.analyze_emergency(
            emergency_type=case.emergency_type,
            description=case.description,
            location_name=case.location_name,
            people_affected=case.people_affected,
            contact_info=case.citizen_phone
        )

        # Update priority if recommended by AI and not explicitly set by operator
        if "priority" not in data and ai_res.get("recommended_priority"):
            case.priority = ai_res["recommended_priority"]

        ai_record = AIAnalysisRecord(
            case_id=case.id,
            model_used=ai_res.get("model_used", "Groq AI"),
            summary=ai_res.get("summary", ""),
            extracted_facts=json.dumps(ai_res.get("extracted_facts", [])),
            missing_information=json.dumps(ai_res.get("missing_information", [])),
            recommended_priority=ai_res.get("recommended_priority", case.priority),
            recommended_actions=json.dumps(ai_res.get("recommended_actions", [])),
            recommended_resources=json.dumps(ai_res.get("recommended_resources", [])),
            is_fallback=ai_res.get("is_fallback", False),
            created_at=now
        )
        session.add(ai_record)

        # Run automated employee routing
        assigned, msg = RoutingService.assign_case(session, case, operator_name="Intake Auto-Router")

        # In-app notification for dispatch team
        NotificationService.create_notification(
            session=session,
            title=f"NEW EMERGENCY: {case.case_number}",
            message=f"{case.emergency_type} at {case.location_name} (Priority: {case.priority}). {msg}",
            severity=case.priority,
            recipient_type="ALL",
            case_id=case.id
        )

        session.commit()
        return jsonify({
            "success": True,
            "message": "Emergency report submitted successfully.",
            "data": case.to_dict(),
            "routing_message": msg
        }), 201
    except Exception as e:
        session.rollback()
        current_app.logger.error(f"Error creating emergency case: {e}")
        return jsonify({"success": False, "error": str(e)}), 500
    finally:
        session.close()

@api_bp.route("/cases/<int:case_id>", methods=["GET"])
def get_case(case_id):
    """Returns single emergency case with history, assignments, and AI analysis."""
    session = get_db()
    try:
        case = session.get(EmergencyCase, case_id)
        if not case:
            return jsonify({"success": False, "error": "Case not found."}), 404

        case_dict = case.to_dict()
        case_dict["assignments_history"] = [a.to_dict() for a in case.assignments]
        case_dict["status_history"] = [h.to_dict() for h in case.status_history]
        case_dict["ai_history"] = [ai.to_dict() for ai in case.ai_analyses]

        return jsonify({"success": True, "data": case_dict})
    finally:
        session.close()

@api_bp.route("/cases/<int:case_id>/acknowledge", methods=["POST"])
def acknowledge_case(case_id):
    """Operator acknowledges case -> silences buzzer & starts response sequence."""
    session = get_db()
    try:
        data = request.get_json(silent=True) or {}
        responder_name = data.get("responder_name", "Operator")
        success, msg = RoutingService.acknowledge_case(session, case_id, responder_name=responder_name)
        if success:
            case = session.get(EmergencyCase, case_id)
            return jsonify({"success": True, "message": msg, "data": case.to_dict()})
        return jsonify({"success": False, "error": msg}), 400
    finally:
        session.close()

@api_bp.route("/cases/<int:case_id>/assign", methods=["POST"])
def reassign_case(case_id):
    """Operator manually reassigns case or overrides employee assignment."""
    session = get_db()
    try:
        data = request.get_json(silent=True) or {}
        employee_id = data.get("employee_id")
        operator_name = data.get("operator_name", "Manual Override")

        case = session.get(EmergencyCase, case_id)
        if not case:
            return jsonify({"success": False, "error": "Case not found."}), 404

        success, msg = RoutingService.assign_case(
            session, case, operator_name=operator_name, override_employee_id=employee_id
        )
        if success:
            return jsonify({"success": True, "message": msg, "data": case.to_dict()})
        return jsonify({"success": False, "error": msg}), 400
    finally:
        session.close()

@api_bp.route("/cases/<int:case_id>/priority", methods=["POST"])
def update_priority(case_id):
    """Employee reviews and manually overrides AI priority recommendation."""
    session = get_db()
    try:
        data = request.get_json(silent=True) or {}
        new_priority = data.get("priority")
        reason = data.get("reason", "Operator manual review and override")
        operator_name = data.get("operator_name", "Operator")

        if new_priority not in Config.PRIORITIES:
            return jsonify({"success": False, "error": f"Invalid priority: {new_priority}"}), 400

        case = session.get(EmergencyCase, case_id)
        if not case:
            return jsonify({"success": False, "error": "Case not found."}), 404

        old_priority = case.priority
        case.priority = new_priority
        case.updated_at = utcnow()

        history = CaseStatusHistory(
            case_id=case.id,
            old_status=case.status,
            new_status=case.status,
            action_by=operator_name,
            action_type="PRIORITY_OVERRIDE",
            notes=f"Priority adjusted from {old_priority} to {new_priority}. Reason: {reason}"
        )
        session.add(history)
        session.commit()
        return jsonify({"success": True, "message": f"Priority updated to {new_priority}.", "data": case.to_dict()})
    finally:
        session.close()

@api_bp.route("/cases/<int:case_id>/resolve", methods=["POST"])
def resolve_case(case_id):
    """Explicit human operator action to resolve an emergency incident."""
    session = get_db()
    try:
        data = request.get_json(silent=True) or {}
        resolution_notes = data.get("resolution_notes", "").strip()
        operator_name = data.get("operator_name", "Operator")

        if not resolution_notes:
            return jsonify({"success": False, "error": "Resolution summary notes are required."}), 400

        success, msg = RoutingService.resolve_case(session, case_id, resolution_notes, operator_name=operator_name)
        if success:
            case = session.get(EmergencyCase, case_id)
            return jsonify({"success": True, "message": msg, "data": case.to_dict()})
        return jsonify({"success": False, "error": msg}), 400
    finally:
        session.close()

@api_bp.route("/cases/<int:case_id>/ai-analyze", methods=["POST"])
def rerun_ai_analysis(case_id):
    """Reruns or refreshes AI analysis for a specific case with Groq or local fallback."""
    session = get_db()
    try:
        case = session.get(EmergencyCase, case_id)
        if not case:
            return jsonify({"success": False, "error": "Case not found."}), 404

        ai_service = AIService()
        ai_res = ai_service.analyze_emergency(
            emergency_type=case.emergency_type,
            description=case.description,
            location_name=case.location_name,
            people_affected=case.people_affected,
            contact_info=case.citizen_phone
        )

        ai_rec = AIAnalysisRecord(
            case_id=case.id,
            model_used=ai_res.get("model_used", "Groq AI"),
            summary=ai_res.get("summary", ""),
            extracted_facts=json.dumps(ai_res.get("extracted_facts", [])),
            missing_information=json.dumps(ai_res.get("missing_information", [])),
            recommended_priority=ai_res.get("recommended_priority", case.priority),
            recommended_actions=json.dumps(ai_res.get("recommended_actions", [])),
            recommended_resources=json.dumps(ai_res.get("recommended_resources", [])),
            is_fallback=ai_res.get("is_fallback", False),
            created_at=utcnow()
        )
        session.add(ai_rec)
        session.commit()

        return jsonify({"success": True, "data": ai_rec.to_dict()})
    finally:
        session.close()

@api_bp.route("/alerts", methods=["GET"])
def list_alerts():
    """Returns active weather and disaster alerts."""
    session = get_db()
    try:
        alerts = session.query(EmergencyAlert).filter(
            EmergencyAlert.is_active == True
        ).order_by(EmergencyAlert.created_at.desc()).all()
        return jsonify({"success": True, "count": len(alerts), "data": [a.to_dict() for a in alerts]})
    finally:
        session.close()

@api_bp.route("/alerts/simulate", methods=["POST"])
def simulate_alert():
    """
    Simulates a weather or disaster alert (heavy rain, thunderstorm, cyclone, flood, heatwave).
    Deduplicates and notifies citizen portal & operations dashboard.
    """
    session = get_db()
    try:
        data = request.get_json(silent=True) or {}
        template_key = data.get("template_key", "heavy_rain")
        location_name = data.get("location_name", "JNTU Anantapur Campus")
        lat = data.get("latitude", 14.6548)
        lng = data.get("longitude", 77.6074)

        alert, is_new = WeatherService.create_simulated_alert(session, template_key, location_name, lat, lng)
        
        if is_new:
            # Broadcast notification
            NotificationService.create_notification(
                session=session,
                title=alert.title,
                message=alert.message,
                severity=alert.severity,
                recipient_type="ALL",
                alert_id=alert.id
            )
            msg = f"Simulated {alert.alert_type} alert published successfully for {location_name}."
        else:
            msg = f"Active alert for {location_name} already exists. Duplicate prevented."

        return jsonify({"success": True, "is_new": is_new, "message": msg, "data": alert.to_dict()})
    finally:
        session.close()

@api_bp.route("/employees", methods=["GET"])
def list_employees():
    """Returns all emergency call-center and field employees with availability."""
    session = get_db()
    try:
        employees = session.query(Employee).order_by(Employee.id.asc()).all()
        return jsonify({"success": True, "count": len(employees), "data": [e.to_dict() for e in employees]})
    finally:
        session.close()

@api_bp.route("/employees/<int:emp_id>/status", methods=["POST"])
def change_employee_status(emp_id):
    """Updates employee availability: Available, Busy, Offline, No response."""
    session = get_db()
    try:
        data = request.get_json(silent=True) or {}
        new_status = data.get("status")
        operator_name = data.get("operator_name", "Supervisor")

        success, msg = RoutingService.update_employee_status(
            session, emp_id, new_status, operator_name=operator_name
        )
        if success:
            emp = session.get(Employee, emp_id)
            return jsonify({"success": True, "message": msg, "data": emp.to_dict()})
        return jsonify({"success": False, "error": msg}), 400
    finally:
        session.close()

@api_bp.route("/notifications", methods=["GET"])
def list_notifications():
    """Returns notifications for citizen portal or operator dashboard."""
    session = get_db()
    try:
        recipient = request.args.get("recipient", "ALL")
        if recipient == "CITIZEN":
            notifs = NotificationService.get_citizen_notifications(session)
        else:
            notifs = NotificationService.get_operator_notifications(session)
        return jsonify({"success": True, "count": len(notifs), "data": [n.to_dict() for n in notifs]})
    finally:
        session.close()

@api_bp.route("/notifications/<int:notif_id>/acknowledge", methods=["POST"])
def acknowledge_notification(notif_id):
    session = get_db()
    try:
        success = NotificationService.acknowledge_notification(session, notif_id)
        return jsonify({"success": success})
    finally:
        session.close()

@api_bp.route("/buzzer/active", methods=["GET"])
def get_buzzer_cases():
    """Returns all unacknowledged cases that require browser audible buzzer."""
    session = get_db()
    try:
        cases = NotificationService.get_active_buzzer_cases(session)
        return jsonify({"success": True, "count": len(cases), "data": [c.to_dict() for c in cases]})
    finally:
        session.close()

@api_bp.route("/routing/check-timeouts", methods=["POST"])
def check_timeouts():
    """Manual or cron trigger to evaluate assignment timeouts and execute reassignments."""
    session = get_db()
    try:
        results = RoutingService.check_and_process_timeouts(session)
        return jsonify({"success": True, "processed": len(results), "details": results})
    finally:
        session.close()

@api_bp.route("/weather/live", methods=["GET"])
def get_live_weather():
    """Fetches real-time weather telemetry from Open-Meteo for specified coordinates."""
    try:
        lat = float(request.args.get("lat", 14.6548))
        lng = float(request.args.get("lng", 77.6074))
        telemetry = WeatherService.get_live_weather(lat, lng)
        return jsonify({"success": True, "data": telemetry})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 400

@api_bp.route("/ai/transcript", methods=["POST"])
def analyze_call_transcript():
    """Analyzes a call transcript between citizen and dispatcher."""
    data = request.get_json(silent=True) or {}
    transcript = data.get("transcript", "").strip()
    caller_role = data.get("caller_role", "Citizen")

    if not transcript:
        return jsonify({"success": False, "error": "Transcript text is required."}), 400

    ai_service = AIService()
    summary_data = ai_service.summarize_transcript(transcript, caller_role)
    return jsonify({"success": True, "data": summary_data})

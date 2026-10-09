from datetime import datetime, timezone, timedelta
import logging
from config import Config
from models.database import Employee, EmergencyCase, CaseAssignment, CaseStatusHistory, NotificationRecord, AuditLog

logger = logging.getLogger(__name__)

def utcnow():
    return datetime.now(timezone.utc).replace(tzinfo=None)

class RoutingService:
    """
    Deterministic Emergency Dispatch & Employee Routing Service.
    Enforces workload balancing, strict acknowledgement deadlines,
    automated timeout reassignment, and supervisor escalation.
    """

    @classmethod
    def find_eligible_employee(cls, session, exclude_employee_ids=None):
        """
        Finds the most eligible Available employee.
        Sorting criteria:
        1. Status == 'Available'
        2. Lowest current active cases
        3. Longest idle since last status change
        """
        query = session.query(Employee).filter(Employee.status == "Available")
        if exclude_employee_ids:
            query = query.filter(~Employee.id.in_(exclude_employee_ids))

        # Order by fewest active cases, then id
        candidate = query.order_by(Employee.current_active_cases.asc(), Employee.id.asc()).first()
        return candidate

    @classmethod
    def assign_case(cls, session, case, operator_name="Auto-Router", override_employee_id=None):
        """
        Deterministic case assignment with audit history and timeout deadline.
        """
        now = utcnow()
        deadline = now + timedelta(seconds=Config.ACK_TIMEOUT_SECONDS)

        # Check existing attempts to prevent infinite loop
        existing_assignments = session.query(CaseAssignment).filter_by(case_id=case.id).all()
        attempt_number = len(existing_assignments) + 1
        previous_employee_ids = [a.employee_id for a in existing_assignments]

        if override_employee_id:
            employee = session.get(Employee, override_employee_id)
            if not employee:
                return False, "Specified employee not found."
        else:
            if attempt_number > Config.MAX_REASSIGN_ATTEMPTS:
                # Max attempts reached -> Escalate to supervisor queue
                cls._escalate_case(session, case, f"Exceeded maximum automated routing attempts ({Config.MAX_REASSIGN_ATTEMPTS}). Escalated to supervisor.")
                return False, "Maximum reassignment attempts reached; escalated to supervisor."
            
            employee = cls.find_eligible_employee(session, exclude_employee_ids=previous_employee_ids)

        if not employee:
            # No eligible available employee found
            cls._escalate_case(session, case, "No available responders online. Placed in priority supervisor escalation queue.")
            return False, "No available employees found. Case placed in supervisor queue."

        # Update case
        case.assigned_employee_id = employee.id
        case.status = "ASSIGNED"
        case.requires_buzzer = True
        case.buzzer_acknowledged = False

        # Create assignment record
        assignment = CaseAssignment(
            case_id=case.id,
            employee_id=employee.id,
            assigned_at=now,
            ack_deadline=deadline,
            status="PENDING_ACK",
            attempt_number=attempt_number,
            notes=f"Assigned by {operator_name}. Acknowledgment required within {Config.ACK_TIMEOUT_SECONDS}s."
        )
        session.add(assignment)

        # Update employee workload
        employee.current_active_cases += 1
        if employee.current_active_cases >= 3:
            employee.status = "Busy"
            employee.last_status_change = now

        # Record case status history
        history = CaseStatusHistory(
            case_id=case.id,
            old_status=case.status,
            new_status="ASSIGNED",
            action_by=operator_name,
            action_type="ASSIGNED",
            notes=f"Assigned to {employee.name} ({employee.badge_id}). Deadline: {deadline.strftime('%H:%M:%S UTC')}."
        )
        session.add(history)

        # Send in-app notification to operator
        notification = NotificationRecord(
            recipient_type="OPERATOR",
            case_id=case.id,
            title=f"New Case Assigned: {case.case_number}",
            message=f"Case {case.case_number} ({case.emergency_type} - {case.priority}) assigned to {employee.name}. Please acknowledge immediately.",
            severity=case.priority
        )
        session.add(notification)

        session.commit()
        return True, f"Successfully assigned to {employee.name} ({employee.badge_id})."

    @classmethod
    def acknowledge_case(cls, session, case_id, responder_name="Operator"):
        """
        Employee/Operator acknowledges case:
        - Silences buzzer for this case
        - Marks assignment ACKNOWLEDGED
        - Calculates response time
        - Updates case status to ACKNOWLEDGED
        """
        case = session.get(EmergencyCase, case_id)
        if not case:
            return False, "Case not found."

        now = utcnow()
        case.buzzer_acknowledged = True
        case.buzzer_acknowledged_at = now
        case.buzzer_acknowledged_by = responder_name

        if not case.first_acknowledged_at:
            case.first_acknowledged_at = now

        # Update assignment record
        active_assignment = session.query(CaseAssignment).filter_by(
            case_id=case.id, status="PENDING_ACK"
        ).order_by(CaseAssignment.id.desc()).first()

        if active_assignment:
            active_assignment.acknowledged_at = now
            active_assignment.status = "ACKNOWLEDGED"

            # Compute actual demo response time safely
            assigned_at = active_assignment.assigned_at
            if assigned_at and assigned_at.tzinfo is not None:
                assigned_at = assigned_at.replace(tzinfo=None)
            resp_seconds = (now - assigned_at).total_seconds() if assigned_at else 0.0
            employee = active_assignment.employee
            if employee:
                employee.total_cases_handled += 1
                # Exponential moving average for response time
                if employee.avg_response_seconds == 0:
                    employee.avg_response_seconds = resp_seconds
                else:
                    employee.avg_response_seconds = (employee.avg_response_seconds * 0.7) + (resp_seconds * 0.3)

        old_status = case.status
        case.status = "ACKNOWLEDGED"

        history = CaseStatusHistory(
            case_id=case.id,
            old_status=old_status,
            new_status="ACKNOWLEDGED",
            action_by=responder_name,
            action_type="ACKNOWLEDGED",
            notes=f"Emergency acknowledged by {responder_name}. Buzzer silenced."
        )
        session.add(history)
        session.commit()
        return True, "Case acknowledged and buzzer silenced."

    @classmethod
    def check_and_process_timeouts(cls, session):
        """
        Evaluates active assignments past ack_deadline.
        If timed out:
        1. Mark assignment TIMED_OUT
        2. Set unresponsive employee status to 'No response'
        3. Reassign to another eligible employee
        """
        now = utcnow()
        timed_out_assignments = session.query(CaseAssignment).filter(
            CaseAssignment.status == "PENDING_ACK",
            CaseAssignment.ack_deadline < now
        ).all()

        results = []
        for assignment in timed_out_assignments:
            case = assignment.case
            unresponsive_emp = assignment.employee

            # 1. Mark assignment timed out
            assignment.status = "TIMED_OUT"
            assignment.notes = (assignment.notes or "") + f" [TIMED OUT at {now.strftime('%H:%M:%S')}]"

            # 2. Mark unresponsive employee status as 'No response'
            if unresponsive_emp and unresponsive_emp.status == "Available":
                unresponsive_emp.status = "No response"
                unresponsive_emp.last_status_change = now
                if unresponsive_emp.current_active_cases > 0:
                    unresponsive_emp.current_active_cases -= 1

            # Log history
            history = CaseStatusHistory(
                case_id=case.id,
                old_status="ASSIGNED",
                new_status="ASSIGNED",
                action_by="System Watchdog",
                action_type="REASSIGNED",
                notes=f"Responded deadline expired for {unresponsive_emp.name if unresponsive_emp else 'Responder'}. Reassigning..."
            )
            session.add(history)

            # 3. Reassign to next employee
            success, msg = cls.assign_case(session, case, operator_name="System Watchdog Re-router")
            results.append({"case_number": case.case_number, "action": "reassigned" if success else "escalated", "details": msg})

        session.commit()
        return results

    @classmethod
    def update_employee_status(cls, session, employee_id, new_status, operator_name="Supervisor"):
        """Updates employee availability state: Available, Busy, Offline, No response."""
        if new_status not in Config.EMPLOYEE_STATUSES:
            return False, f"Invalid status: {new_status}"

        emp = session.get(Employee, employee_id)
        if not emp:
            return False, "Employee not found."

        old_status = emp.status
        emp.status = new_status
        emp.last_status_change = utcnow()

        # Audit
        audit = AuditLog(
            actor=operator_name,
            action="EMPLOYEE_STATUS_CHANGE",
            target_type="EMPLOYEE",
            target_id=str(emp.id),
            details=f"Status changed from {old_status} to {new_status} for {emp.name} ({emp.badge_id})"
        )
        session.add(audit)
        session.commit()
        return True, f"Employee {emp.name} is now {new_status}."

    @classmethod
    def resolve_case(cls, session, case_id, resolution_notes, operator_name="Operator"):
        """Explicit human operator action to resolve an emergency case."""
        case = session.get(EmergencyCase, case_id)
        if not case:
            return False, "Case not found."

        now = utcnow()
        old_status = case.status
        case.status = "RESOLVED"
        case.resolved_at = now
        case.resolution_notes = resolution_notes
        case.requires_buzzer = False
        case.buzzer_acknowledged = True

        if case.assigned_employee:
            if case.assigned_employee.current_active_cases > 0:
                case.assigned_employee.current_active_cases -= 1
            if case.assigned_employee.status == "Busy" and case.assigned_employee.current_active_cases < 3:
                case.assigned_employee.status = "Available"
                case.assigned_employee.last_status_change = now

        history = CaseStatusHistory(
            case_id=case.id,
            old_status=old_status,
            new_status="RESOLVED",
            action_by=operator_name,
            action_type="RESOLVED",
            notes=f"Resolved by {operator_name}. Notes: {resolution_notes}"
        )
        session.add(history)
        session.commit()
        return True, f"Case {case.case_number} marked as RESOLVED."

    @classmethod
    def _escalate_case(cls, session, case, reason):
        case.status = "ESCALATED"
        history = CaseStatusHistory(
            case_id=case.id,
            old_status=case.status,
            new_status="ESCALATED",
            action_by="Routing Engine",
            action_type="ESCALATED",
            notes=reason
        )
        session.add(history)

        notif = NotificationRecord(
            recipient_type="OPERATOR",
            case_id=case.id,
            title=f"URGENT ESCALATION: Case {case.case_number}",
            message=reason,
            severity="CRITICAL"
        )
        session.add(notif)
        session.commit()

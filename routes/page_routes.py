from flask import Blueprint, render_template, redirect, url_for, current_app
from config import Config
from models.database import Employee, EmergencyCase, EmergencyAlert, CaseAssignment

pages_bp = Blueprint("pages", __name__)

def get_db():
    return current_app.db_session()

@pages_bp.route("/")
def index():
    return redirect(url_for("pages.citizen_portal"))

@pages_bp.route("/citizen")
def citizen_portal():
    session = get_db()
    try:
        locations = Config.SAMPLE_LOCATIONS
        alerts = session.query(EmergencyAlert).filter(EmergencyAlert.is_active == True).order_by(EmergencyAlert.created_at.desc()).all()
        return render_template("citizen.html", sample_locations=locations, active_alerts=alerts, priorities=Config.PRIORITIES)
    finally:
        session.close()

@pages_bp.route("/dashboard")
def operator_dashboard():
    session = get_db()
    try:
        employees = session.query(Employee).all()
        active_cases = session.query(EmergencyCase).filter(
            EmergencyCase.status.in_(["NEW", "ASSIGNED", "ACKNOWLEDGED", "IN_PROGRESS", "ESCALATED"])
        ).order_by(EmergencyCase.created_at.desc()).all()
        return render_template(
            "dashboard.html",
            employees=employees,
            cases=active_cases,
            priorities=Config.PRIORITIES,
            locations=Config.SAMPLE_LOCATIONS
        )
    finally:
        session.close()

@pages_bp.route("/incidents")
def incidents_view():
    session = get_db()
    try:
        employees = session.query(Employee).all()
        cases = session.query(EmergencyCase).order_by(EmergencyCase.created_at.desc()).all()
        return render_template(
            "incidents.html",
            employees=employees,
            cases=cases,
            priorities=Config.PRIORITIES
        )
    finally:
        session.close()

@pages_bp.route("/ai-assistant")
def ai_assistant_view():
    session = get_db()
    try:
        cases = session.query(EmergencyCase).order_by(EmergencyCase.created_at.desc()).all()
        return render_template(
            "ai_assistant.html",
            cases=cases,
            groq_configured=bool(Config.GROQ_API_KEY),
            current_model=Config.GROQ_MODEL
        )
    finally:
        session.close()

@pages_bp.route("/employees")
def employees_view():
    session = get_db()
    try:
        employees = session.query(Employee).order_by(Employee.id.asc()).all()
        return render_template("employees.html", employees=employees, statuses=Config.EMPLOYEE_STATUSES)
    finally:
        session.close()

@pages_bp.route("/alerts")
def alerts_view():
    session = get_db()
    try:
        alerts = session.query(EmergencyAlert).order_by(EmergencyAlert.created_at.desc()).all()
        return render_template(
            "alerts.html",
            alerts=alerts,
            locations=Config.SAMPLE_LOCATIONS,
            priorities=Config.PRIORITIES
        )
    finally:
        session.close()

@pages_bp.route("/settings")
def settings_view():
    return render_template(
        "settings.html",
        config=Config,
        groq_configured=bool(Config.GROQ_API_KEY)
    )

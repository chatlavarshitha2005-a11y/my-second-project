from datetime import datetime, timezone, timedelta
import json
from config import Config
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from models.database import (
    Base, Employee, EmergencyCase, CaseAssignment, EmergencyAlert,
    NotificationRecord, CaseStatusHistory, AIAnalysisRecord, AuditLog
)
from services.ai_service import AIService
from services.routing_service import RoutingService
from services.weather_service import WeatherService

def utcnow():
    return datetime.now(timezone.utc)

def seed_database(db_uri=None):
    uri = db_uri or Config.SQLALCHEMY_DATABASE_URI
    engine = create_engine(uri)
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine)
    session = Session()

    print(f"[*] Checking database at {uri}...")

    # Only seed if no employees exist
    if session.query(Employee).count() > 0:
        print("[!] Database already populated. Skipping re-seed.")
        session.close()
        return

    print("[*] Seeding sample employees...")
    sample_employees = [
        {
            "badge_id": "EMP-101",
            "name": "Officer Rajesh Sharma",
            "email": "rajesh.sharma@resqai.org",
            "phone": "+91 98490 12345",
            "role": "Senior Dispatcher",
            "department": "Disaster Management",
            "status": "Available",
            "current_active_cases": 0,
            "total_cases_handled": 42,
            "avg_response_seconds": 18.5
        },
        {
            "badge_id": "EMP-102",
            "name": "Dr. Priya Ananth",
            "email": "priya.ananth@resqai.org",
            "phone": "+91 98490 23456",
            "role": "Medical Triage Specialist",
            "department": "Medical Response",
            "status": "Available",
            "current_active_cases": 0,
            "total_cases_handled": 37,
            "avg_response_seconds": 14.2
        },
        {
            "badge_id": "EMP-103",
            "name": "Inspector Vikram Reddy",
            "email": "vikram.reddy@resqai.org",
            "phone": "+91 98490 34567",
            "role": "Incident Commander",
            "department": "Fire & Rescue",
            "status": "Available",
            "current_active_cases": 0,
            "total_cases_handled": 58,
            "avg_response_seconds": 16.0
        },
        {
            "badge_id": "EMP-104",
            "name": "Operator Ananya Iyer",
            "email": "ananya.iyer@resqai.org",
            "phone": "+91 98490 45678",
            "role": "Emergency Call Handler",
            "department": "Public Safety",
            "status": "Available",
            "current_active_cases": 0,
            "total_cases_handled": 29,
            "avg_response_seconds": 21.0
        },
        {
            "badge_id": "EMP-105",
            "name": "Supervisor Suresh Babu",
            "email": "suresh.babu@resqai.org",
            "phone": "+91 98490 56789",
            "role": "Shift Operations Supervisor",
            "department": "Operations Command",
            "status": "Busy",
            "current_active_cases": 2,
            "total_cases_handled": 110,
            "avg_response_seconds": 12.8
        },
        {
            "badge_id": "EMP-106",
            "name": "Officer Meera Nair",
            "email": "meera.nair@resqai.org",
            "phone": "+91 98490 67890",
            "role": "Coastal Warning Coordinator",
            "department": "Disaster Management",
            "status": "Offline",
            "current_active_cases": 0,
            "total_cases_handled": 45,
            "avg_response_seconds": 19.4
        }
    ]

    employees = []
    for emp_data in sample_employees:
        emp = Employee(**emp_data)
        session.add(emp)
        employees.append(emp)
    session.commit()
    print(f"[+] Created {len(employees)} employees.")

    print("[*] Seeding emergency alerts...")
    WeatherService.create_simulated_alert(
        session, "heavy_rain", "JNTU Anantapur Campus", 14.6548, 77.6074
    )
    WeatherService.create_simulated_alert(
        session, "thunderstorm", "Amaravati Secretariat", 16.5131, 80.5165
    )
    WeatherService.create_simulated_alert(
        session, "cyclone", "Beach Road, Visakhapatnam", 17.7196, 83.3218
    )
    print("[+] Created simulated weather alerts.")

    print("[*] Seeding sample emergency cases...")
    sample_cases = [
        {
            "case_number": "RESQ-2026-1001",
            "citizen_name": "Kiran Kumar",
            "citizen_phone": "+91 99887 76655",
            "emergency_type": "Heavy Rain / Flood",
            "priority": "CRITICAL",
            "description": "Flash flooding near JNTUA engineering block after intense cloudburst. 4 students stranded on ground floor entrance with water level rising to 3 feet. Current is strong.",
            "location_name": "JNTU Anantapur Campus, Engineering Block A",
            "latitude": 14.6548,
            "longitude": 77.6074,
            "people_affected": 4
        },
        {
            "case_number": "RESQ-2026-1002",
            "citizen_name": "Sunita Verma",
            "citizen_phone": "+91 98765 43210",
            "emergency_type": "Road Accident",
            "priority": "HIGH",
            "description": "Two vehicles collided head-on near Clock Tower intersection during heavy rain downpour. Both drivers conscious but trapped by deformed steering wheels. Oil leaking onto road.",
            "location_name": "Clock Tower, Anantapur",
            "latitude": 14.6819,
            "longitude": 77.6006,
            "people_affected": 3
        },
        {
            "case_number": "RESQ-2026-1003",
            "citizen_name": "Ramesh Rao",
            "citizen_phone": "+91 97654 32109",
            "emergency_type": "Medical Emergency",
            "priority": "CRITICAL",
            "description": "Elderly patient (68 years) suffering severe crushing chest pain, profuse sweating, and loss of consciousness. Family cannot drive due to waterlogged street.",
            "location_name": "Collectorate Complex, Kurnool",
            "latitude": 15.8281,
            "longitude": 78.0373,
            "people_affected": 1
        },
        {
            "case_number": "RESQ-2026-1004",
            "citizen_name": "Lakshmi Narayana",
            "citizen_phone": "+91 96543 21098",
            "emergency_type": "Fire Incident",
            "priority": "HIGH",
            "description": "Short circuit transformer explosion ignited timber storage shed next to electrical substation. Dense black smoke billowing toward residential apartments.",
            "location_name": "Tirupati Central Bus Station, West Gate",
            "latitude": 13.6288,
            "longitude": 79.4192,
            "people_affected": 2
        }
    ]

    ai_service = AIService()

    for idx, c_data in enumerate(sample_cases):
        now = utcnow() - timedelta(minutes=(idx + 1) * 8)
        case = EmergencyCase(
            case_number=c_data["case_number"],
            citizen_name=c_data["citizen_name"],
            citizen_phone=c_data["citizen_phone"],
            emergency_type=c_data["emergency_type"],
            priority=c_data["priority"],
            status="NEW",
            description=c_data["description"],
            location_name=c_data["location_name"],
            latitude=c_data["latitude"],
            longitude=c_data["longitude"],
            people_affected=c_data["people_affected"],
            requires_buzzer=True,
            buzzer_acknowledged=False,
            created_at=now,
            updated_at=now
        )
        session.add(case)
        session.commit()

        # Generate AI analysis
        ai_result = ai_service.analyze_emergency(
            case.emergency_type, case.description, case.location_name, case.people_affected
        )
        ai_rec = AIAnalysisRecord(
            case_id=case.id,
            model_used=ai_result.get("model_used", "Groq AI"),
            summary=ai_result.get("summary", ""),
            extracted_facts=json.dumps(ai_result.get("extracted_facts", [])),
            missing_information=json.dumps(ai_result.get("missing_information", [])),
            recommended_priority=ai_result.get("recommended_priority", case.priority),
            recommended_actions=json.dumps(ai_result.get("recommended_actions", [])),
            recommended_resources=json.dumps(ai_result.get("recommended_resources", [])),
            is_fallback=ai_result.get("is_fallback", False),
            created_at=now
        )
        session.add(ai_rec)

        # Assign case deterministically
        RoutingService.assign_case(session, case, operator_name="Auto-Router Seed")

    print("[+] Successfully seeded emergency cases with AI triage and routing.")

    # Acknowledge the first case for demo realism (showing varied statuses in UI)
    case_1 = session.query(EmergencyCase).filter_by(case_number="RESQ-2026-1001").first()
    if case_1:
        RoutingService.acknowledge_case(session, case_1.id, responder_name="Officer Rajesh Sharma")
        print("[+] Acknowledged case RESQ-2026-1001 for demo status variety.")

    session.close()
    print("[*] Database initialization completed successfully!")

if __name__ == "__main__":
    seed_database()

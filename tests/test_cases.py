import unittest
from datetime import datetime, timezone
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from models.database import Base, EmergencyCase, Employee, CaseAssignment
from services.routing_service import RoutingService

class TestCaseManagement(unittest.TestCase):
    def setUp(self):
        self.engine = create_engine("sqlite:///:memory:")
        Base.metadata.create_all(self.engine)
        self.Session = sessionmaker(bind=self.engine)
        self.session = self.Session()

        # Create sample responder
        self.responder = Employee(
            badge_id="EMP-TEST-1",
            name="Test Officer",
            email="test@resqai.org",
            role="Dispatcher",
            status="Available",
            current_active_cases=0
        )
        self.session.add(self.responder)
        self.session.commit()

    def tearDown(self):
        self.session.close()

    def test_case_creation_and_fields(self):
        case = EmergencyCase(
            case_number="RESQ-TEST-001",
            citizen_name="John Citizen",
            emergency_type="Road Accident",
            priority="CRITICAL",
            status="NEW",
            description="Vehicle overturned on highway with passengers trapped.",
            location_name="NH-44 Mile 12",
            latitude=14.68,
            longitude=77.60,
            people_affected=2,
            requires_buzzer=True,
            buzzer_acknowledged=False
        )
        self.session.add(case)
        self.session.commit()

        fetched = self.session.query(EmergencyCase).filter_by(case_number="RESQ-TEST-001").first()
        self.assertIsNotNone(fetched)
        self.assertEqual(fetched.priority, "CRITICAL")
        self.assertEqual(fetched.status, "NEW")
        self.assertTrue(fetched.requires_buzzer)
        self.assertFalse(fetched.buzzer_acknowledged)

    def test_case_acknowledgement_silences_buzzer(self):
        case = EmergencyCase(
            case_number="RESQ-TEST-002",
            emergency_type="Medical Emergency",
            priority="HIGH",
            status="NEW",
            description="Cardiac chest pain.",
            location_name="Old Town",
            requires_buzzer=True
        )
        self.session.add(case)
        self.session.commit()

        # Assign case
        success, _ = RoutingService.assign_case(self.session, case, operator_name="Test Router")
        self.assertTrue(success)

        # Acknowledge case
        ack_success, _ = RoutingService.acknowledge_case(self.session, case.id, responder_name="Operator Sarah")
        self.assertTrue(ack_success)

        self.session.refresh(case)
        self.assertEqual(case.status, "ACKNOWLEDGED")
        self.assertTrue(case.buzzer_acknowledged)
        self.assertIsNotNone(case.first_acknowledged_at)

    def test_case_resolution(self):
        case = EmergencyCase(
            case_number="RESQ-TEST-003",
            emergency_type="Fire Incident",
            priority="HIGH",
            status="NEW",
            description="Electrical transformer spark.",
            location_name="Market Gate"
        )
        self.session.add(case)
        self.session.commit()

        success, _ = RoutingService.resolve_case(
            self.session, case.id, resolution_notes="Fire extinguished by local tender.", operator_name="Lead Officer"
        )
        self.assertTrue(success)
        self.session.refresh(case)
        self.assertEqual(case.status, "RESOLVED")
        self.assertEqual(case.resolution_notes, "Fire extinguished by local tender.")
        self.assertIsNotNone(case.resolved_at)

if __name__ == "__main__":
    unittest.main()

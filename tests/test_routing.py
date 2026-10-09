import unittest
from datetime import datetime, timezone, timedelta
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from config import Config
from models.database import Base, EmergencyCase, Employee, CaseAssignment, CaseStatusHistory
from services.routing_service import RoutingService

class TestRoutingAndAssignments(unittest.TestCase):
    def setUp(self):
        self.engine = create_engine("sqlite:///:memory:")
        Base.metadata.create_all(self.engine)
        self.Session = sessionmaker(bind=self.engine)
        self.session = self.Session()

        # Add 2 Available employees
        self.emp1 = Employee(
            badge_id="EMP-01",
            name="Alice Walker",
            email="alice@resqai.org",
            role="Dispatcher",
            status="Available",
            current_active_cases=0
        )
        self.emp2 = Employee(
            badge_id="EMP-02",
            name="Bob Martin",
            email="bob@resqai.org",
            role="Dispatcher",
            status="Available",
            current_active_cases=1
        )
        self.session.add_all([self.emp1, self.emp2])
        self.session.commit()

    def tearDown(self):
        self.session.close()

    def test_deterministic_assignment_least_busy(self):
        case = EmergencyCase(
            case_number="RESQ-ROUTING-01",
            emergency_type="Heavy Rain / Flood",
            priority="CRITICAL",
            status="NEW",
            description="Water entering ground floor apartments.",
            location_name="Zone 4"
        )
        self.session.add(case)
        self.session.commit()

        # Should assign to emp1 because emp1 has 0 active cases, while emp2 has 1
        success, msg = RoutingService.assign_case(self.session, case, operator_name="Test Router")
        self.assertTrue(success)
        self.assertEqual(case.assigned_employee_id, self.emp1.id)
        self.assertEqual(case.status, "ASSIGNED")
        self.assertEqual(self.emp1.current_active_cases, 1)

    def test_timeout_reassignment(self):
        case = EmergencyCase(
            case_number="RESQ-ROUTING-02",
            emergency_type="Road Accident",
            priority="HIGH",
            status="NEW",
            description="Highway fender bender.",
            location_name="Ring Road"
        )
        self.session.add(case)
        self.session.commit()

        # First assignment to emp1
        success, _ = RoutingService.assign_case(self.session, case, operator_name="Test Router")
        self.assertTrue(success)
        self.assertEqual(case.assigned_employee_id, self.emp1.id)

        # Force deadline into the past to simulate timeout
        assignment = self.session.query(CaseAssignment).filter_by(case_id=case.id, status="PENDING_ACK").first()
        self.assertIsNotNone(assignment)
        assignment.ack_deadline = datetime.now(timezone.utc).replace(tzinfo=None) - timedelta(seconds=10)
        self.session.commit()

        # Run timeout watchdog
        results = RoutingService.check_and_process_timeouts(self.session)
        self.assertEqual(len(results), 1)

        # emp1 should now have status 'No response'
        self.session.refresh(self.emp1)
        self.assertEqual(self.emp1.status, "No response")

        # case should be reassigned to emp2
        self.session.refresh(case)
        self.assertEqual(case.assigned_employee_id, self.emp2.id)

    def test_supervisor_escalation_when_no_employees(self):
        # Set all employees to Offline
        self.emp1.status = "Offline"
        self.emp2.status = "Offline"
        self.session.commit()

        case = EmergencyCase(
            case_number="RESQ-ROUTING-03",
            emergency_type="Fire Incident",
            priority="CRITICAL",
            status="NEW",
            description="Factory blaze.",
            location_name="Industrial Area"
        )
        self.session.add(case)
        self.session.commit()

        success, msg = RoutingService.assign_case(self.session, case, operator_name="Test Router")
        self.assertFalse(success)
        self.session.refresh(case)
        self.assertEqual(case.status, "ESCALATED")

if __name__ == "__main__":
    unittest.main()

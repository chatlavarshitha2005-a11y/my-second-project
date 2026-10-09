import unittest
from app import create_app

class TestEndpoints(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = create_app()
        cls.client = cls.app.test_client()

    def test_citizen_portal_page(self):
        resp = self.client.get("/citizen")
        self.assertEqual(resp.status_code, 200)
        self.assertIn(b"ResQAI Citizen Portal", resp.data)
        self.assertIn(b"SOS", resp.data)

    def test_dashboard_page(self):
        resp = self.client.get("/dashboard")
        self.assertEqual(resp.status_code, 200)
        self.assertIn(b"Emergency Call-Center Operations Command", resp.data)
        self.assertIn(b"emergencyMap", resp.data)

    def test_incidents_page(self):
        resp = self.client.get("/incidents")
        self.assertEqual(resp.status_code, 200)
        self.assertIn(b"Master Emergency Incident Queue", resp.data)

    def test_ai_assistant_page(self):
        resp = self.client.get("/ai-assistant")
        self.assertEqual(resp.status_code, 200)
        self.assertIn(b"AI Emergency Triage", resp.data)

    def test_employees_page(self):
        resp = self.client.get("/employees")
        self.assertEqual(resp.status_code, 200)
        self.assertIn(b"Emergency Call-Center Responder Roster", resp.data)

    def test_alerts_page(self):
        resp = self.client.get("/alerts")
        self.assertEqual(resp.status_code, 200)
        self.assertIn(b"Public Weather & Disaster Alerts", resp.data)

    def test_settings_page(self):
        resp = self.client.get("/settings")
        self.assertEqual(resp.status_code, 200)
        self.assertIn(b"System Configuration", resp.data)

    def test_api_stats(self):
        resp = self.client.get("/api/stats")
        self.assertEqual(resp.status_code, 200)
        data = resp.get_json()
        self.assertTrue(data["success"])
        self.assertIn("total_active", data["data"])
        self.assertIn("available_employees", data["data"])

    def test_api_cases_list(self):
        resp = self.client.get("/api/cases")
        self.assertEqual(resp.status_code, 200)
        data = resp.get_json()
        self.assertTrue(data["success"])
        self.assertGreater(data["count"], 0)

    def test_api_create_case(self):
        payload = {
            "emergency_type": "Road Accident",
            "location_name": "Clock Tower, Anantapur",
            "description": "Auto-rickshaw collision with 2 passengers slightly injured.",
            "people_affected": 2,
            "citizen_name": "Test Caller",
            "citizen_phone": "+91 9123456789"
        }
        resp = self.client.post("/api/cases", json=payload)
        self.assertEqual(resp.status_code, 201)
        data = resp.get_json()
        self.assertTrue(data["success"])
        self.assertIn("RESQ-2026-", data["data"]["case_number"])
        self.assertIsNotNone(data["data"]["assigned_employee_name"])

    def test_api_alerts_simulate(self):
        payload = {
            "template_key": "heavy_rain",
            "location_name": "JNTU Test Block",
            "latitude": 14.6548,
            "longitude": 77.6074
        }
        resp = self.client.post("/api/alerts/simulate", json=payload)
        self.assertEqual(resp.status_code, 200)
        data = resp.get_json()
        self.assertTrue(data["success"])
        self.assertIn("[SIMULATION]", data["data"]["title"])

    def test_api_buzzer_active(self):
        resp = self.client.get("/api/buzzer/active")
        self.assertEqual(resp.status_code, 200)
        data = resp.get_json()
        self.assertTrue(data["success"])

if __name__ == "__main__":
    unittest.main()

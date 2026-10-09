import unittest
from services.ai_service import AIService

class TestAIService(unittest.TestCase):
    def test_local_deterministic_analysis(self):
        # Instantiate AIService with empty API key to force local deterministic engine
        service = AIService(api_key="")
        
        result = service.analyze_emergency(
            emergency_type="Medical Emergency",
            description="Victim is unconscious, not breathing, and has severe bleeding from head injury.",
            location_name="Clock Tower Junction",
            people_affected=1,
            contact_info="+91 9988776655"
        )

        self.assertIsNotNone(result)
        self.assertTrue(result["is_fallback"])
        self.assertEqual(result["recommended_priority"], "CRITICAL")
        self.assertIn("summary", result)
        self.assertGreater(len(result["extracted_facts"]), 0)
        self.assertGreater(len(result["recommended_actions"]), 0)
        self.assertGreater(len(result["recommended_resources"]), 0)

    def test_local_weather_triage(self):
        service = AIService(api_key="")
        result = service.analyze_emergency(
            emergency_type="Heavy Rain / Flood",
            description="Water level rising on streets, some vehicles stalled.",
            location_name="Low lying colony",
            people_affected=2
        )

        self.assertIn(result["recommended_priority"], ["HIGH", "MEDIUM"])
        self.assertIn("Water Rescue", " ".join(result["recommended_resources"]))

    def test_transcript_summary_fallback(self):
        service = AIService(api_key="")
        result = service.summarize_transcript("Sample call dialogue between dispatcher and caller.")
        self.assertIn("summary", result)
        self.assertTrue(result["is_fallback"])

if __name__ == "__main__":
    unittest.main()

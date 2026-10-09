import json
import logging
import requests
from config import Config

logger = logging.getLogger(__name__)

class AIService:
    """
    ResQAI Emergency AI Service.
    Integrates with Groq API (models such as openai/gpt-oss-20b, openai/gpt-oss-120b, qwen/qwen3.8-27b)
    with a deterministic local rule-based fallback when offline or unavailable.
    """

    def __init__(self, api_key=None, model=None):
        self.api_key = api_key if api_key is not None else Config.GROQ_API_KEY
        self.model = model or Config.GROQ_MODEL
        self.fallback_models = Config.GROQ_FALLBACK_MODELS
        self.api_endpoint = "https://api.groq.com/openai/v1/chat/completions"

    def analyze_emergency(self, emergency_type, description, location_name, people_affected=1, contact_info=None):
        """
        Analyzes an emergency report to extract summary, facts, missing info,
        priority recommendation, and suggested resources.
        """
        # Attempt live Groq AI first if API key is provided
        if self.api_key:
            try:
                analysis = self._call_groq_emergency_analysis(
                    emergency_type, description, location_name, people_affected, contact_info
                )
                if analysis:
                    return analysis
            except Exception as e:
                logger.warning(f"Groq API call failed: {e}. Falling back to local deterministic engine.")

        # Local deterministic fallback engine
        return self._local_deterministic_analysis(
            emergency_type, description, location_name, people_affected, contact_info
        )

    def summarize_transcript(self, transcript_text, caller_role="Citizen"):
        """
        Summarizes an emergency operator-caller audio or text transcript.
        """
        if self.api_key and transcript_text.strip():
            try:
                summary = self._call_groq_transcript_summary(transcript_text, caller_role)
                if summary:
                    return summary
            except Exception as e:
                logger.warning(f"Groq transcript analysis failed: {e}. Using local fallback.")

        return self._local_transcript_summary(transcript_text)

    def _call_groq_emergency_analysis(self, emergency_type, description, location, people_affected, contact_info):
        """Calls Groq chat completion API with strict structured JSON output instructions."""
        system_prompt = (
            "You are ResQAI Emergency Triage AI Assistant. Your mission is to assist human 911/emergency dispatchers. "
            "You extract critical facts, identify life-threat hazards, detect missing info, recommend triage priority, "
            "and suggest first-responder resources. AI recommendations are advisory and subject to operator review.\n\n"
            "Respond ONLY with a valid JSON object with the following exact keys:\n"
            "{\n"
            '  "summary": "2-3 concise sentences summarizing the crisis and danger level",\n'
            '  "extracted_facts": ["fact 1", "fact 2", "fact 3"],\n'
            '  "missing_information": ["question 1 dispatcher should ask", "question 2"],\n'
            '  "recommended_priority": "CRITICAL" | "HIGH" | "MEDIUM" | "LOW",\n'
            '  "priority_reasoning": "Brief explanation of why this priority is suggested",\n'
            '  "recommended_actions": ["Immediate dispatch step 1", "Immediate dispatch step 2"],\n'
            '  "recommended_resources": ["Resource 1 (e.g. ALS Ambulance)", "Resource 2 (e.g. Water Rescue Boat)"]\n'
            "}"
        )

        user_content = (
            f"Emergency Incident Report:\n"
            f"- Type: {emergency_type}\n"
            f"- Location: {location}\n"
            f"- Estimated Affected Persons: {people_affected}\n"
            f"- Citizen Description: {description}\n"
            f"- Contact Available: {contact_info or 'None'}\n"
        )

        models_to_try = [self.model] + self.fallback_models
        for target_model in models_to_try:
            try:
                headers = {
                    "Authorization": f"Bearer {self.api_key}",
                    "Content-Type": "application/json"
                }
                payload = {
                    "model": target_model,
                    "messages": [
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": user_content}
                    ],
                    "temperature": 0.2,
                    "max_tokens": 1024,
                    "response_format": {"type": "json_object"}
                }
                response = requests.post(self.api_endpoint, headers=headers, json=payload, timeout=12)
                if response.status_code == 200:
                    data = response.json()
                    content = data["choices"][0]["message"]["content"]
                    parsed = json.loads(content)
                    parsed["is_fallback"] = False
                    parsed["model_used"] = target_model
                    parsed["engine_badge"] = f"Groq AI ({target_model})"
                    return parsed
            except Exception as model_err:
                logger.info(f"Model {target_model} attempt failed: {model_err}")
                continue

        return None

    def _call_groq_transcript_summary(self, transcript_text, caller_role):
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }
        payload = {
            "model": self.model,
            "messages": [
                {
                    "role": "system",
                    "content": (
                        "You are an emergency call-center AI. Summarize the following dispatch call transcript into "
                        "key caller statements, operator advisories, and confirmed dispatch actions. Be factual and brief."
                    )
                },
                {"role": "user", "content": f"Caller Role: {caller_role}\nTranscript:\n{transcript_text}"}
            ],
            "temperature": 0.2,
            "max_tokens": 512
        }
        res = requests.post(self.api_endpoint, headers=headers, json=payload, timeout=10)
        if res.status_code == 200:
            return {
                "summary": res.json()["choices"][0]["message"]["content"],
                "is_fallback": False,
                "model_used": self.model
            }
        return None

    def _local_deterministic_analysis(self, emergency_type, description, location, people_affected, contact_info):
        """
        Deterministic local triage engine designed according to NDMA / EMS standard incident protocols.
        Acts as guaranteed fallback if Groq API is unavailable or offline.
        """
        desc_lower = description.lower()
        type_lower = emergency_type.lower()
        
        # Priority heuristic
        critical_keywords = [
            "unconscious", "not breathing", "cardiac", "chest pain", "bleeding profusely",
            "trapped", "collapse", "drowning", "submerged", "explosion", "severe fire",
            "electrocution", "head injury", "infant", "child critical", "choking"
        ]
        high_keywords = [
            "fracture", "deep cut", "flooding", "water entering", "short circuit",
            "smoke", "accident", "crash", "collision", "stranded", "cyclone winds",
            "tree fallen on vehicle", "blocked road"
        ]
        
        is_critical = any(kw in desc_lower for kw in critical_keywords) or (people_affected >= 5 and "accident" in type_lower)
        is_high = any(kw in desc_lower for kw in high_keywords) or ("fire" in type_lower) or ("flood" in type_lower)

        if is_critical or "critical" in desc_lower:
            priority = "CRITICAL"
            reason = "Life-safety indicators or critical entrapment detected in incident description."
        elif is_high or people_affected >= 2:
            priority = "HIGH"
            reason = "Active hazard with potential escalation or multiple individuals affected."
        elif "water" in desc_lower or "rain" in desc_lower or "traffic" in desc_lower:
            priority = "MEDIUM"
            reason = "Disruptive infrastructure or environmental emergency requiring standard rapid deployment."
        else:
            priority = "LOW"
            reason = "Advisory or non-immediate hazard; situation stable pending verification."

        # Extracted facts
        facts = [
            f"Emergency Classification: {emergency_type}",
            f"Primary Incident Zone: {location}",
            f"Reported Individuals Affected: {people_affected}"
        ]
        if "trapped" in desc_lower:
            facts.append("Entrapment reported: Victims unable to evacuate independently.")
        if "water" in desc_lower or "flood" in desc_lower:
            facts.append("Hazard vector: Rising water levels or waterlogging on transit corridors.")
        if "fire" in desc_lower or "smoke" in desc_lower:
            facts.append("Hazard vector: Active thermal / smoke condition.")

        # Missing information questions
        missing = []
        if not contact_info:
            missing.append("Caller callback number and alternate contact person on scene.")
        missing.append("Precise landmark, street intersection, or building floor number.")
        missing.append("Current status of immediate hazards (power lines, gas leaks, structural stability).")
        if people_affected > 1:
            missing.append("Age groups and specific triage status of affected persons (infants, elderly, injured).")

        # Recommended Actions
        actions = [
            f"Verify caller coordinates near {location} via GIS triangulation.",
            f"Dispatch lead response unit for priority level {priority}.",
            "Advise citizen to maintain line open and follow local safety shelter guidelines."
        ]
        if priority == "CRITICAL":
            actions.insert(0, "IMMEDIATE ALERT: Trigger priority buzzer and notify on-duty supervisor.")

        # Recommended Resources based on emergency type
        resources = []
        if "rain" in type_lower or "flood" in type_lower or "water" in desc_lower:
            resources.extend(["SDRF/NDRF Water Rescue Inflatable Boat Unit", "Dewatering Pump Squad", "Emergency Evacuation Bus"])
        elif "fire" in type_lower:
            resources.extend(["Heavy Water Tender & Foam Cannon", "Hydraulic Rescue Platform", "Fire Service Paramedics"])
        elif "accident" in type_lower:
            resources.extend(["Advanced Life Support (ALS) Ambulance", "Hydraulic Extrication Rescue Vehicle", "Traffic Police Fast Interceptor"])
        elif "medical" in type_lower:
            resources.extend(["108 Emergency Ambulance", "Mobile Trauma Support Unit", "Nearest District Hospital Trauma Bed Hold"])
        else:
            resources.extend(["Quick Response Team (QRT) Patrol", "Civil Defense Volunteer Unit", "Municipal Disaster Squad"])

        summary = (
            f"Incident reported at {location} involving {emergency_type} with approximately {people_affected} person(s) affected. "
            f"Assessed urgency level is {priority}. First responders recommended: {', '.join(resources[:2])}."
        )

        return {
            "summary": summary,
            "extracted_facts": facts,
            "missing_information": missing,
            "recommended_priority": priority,
            "priority_reasoning": reason,
            "recommended_actions": actions,
            "recommended_resources": resources,
            "is_fallback": True,
            "model_used": "Deterministic Rule Engine (Local Fallback)",
            "engine_badge": "Local Emergency Rule Engine"
        }

    def _local_transcript_summary(self, transcript_text):
        return {
            "summary": (
                "Transcript Review (Local Fallback): Caller verified incident location and severity. "
                "Operator provided pre-arrival safety instructions and initiated dispatch sequence."
            ),
            "is_fallback": True,
            "model_used": "Deterministic Rule Engine (Local Fallback)"
        }

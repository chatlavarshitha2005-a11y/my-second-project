from datetime import datetime, timezone, timedelta
import logging
import requests
from config import Config
from models.database import EmergencyAlert

logger = logging.getLogger(__name__)

def utcnow():
    return datetime.now(timezone.utc)

class WeatherService:
    """
    ResQAI Weather & Disaster Alert Service Abstraction.
    Supports simulated emergency alerts (heavy rain, thunderstorms, cyclones, floods)
    and optional live weather telemetry queries via Open-Meteo public API.
    """

    SIMULATION_TEMPLATES = {
        "heavy_rain": {
            "title": "HEAVY RAINFALL & WATERLOGGING ADVISORY",
            "alert_type": "Heavy Rainfall",
            "severity": "HIGH",
            "message": "Continuous heavy precipitation (70-110 mm/hr) expected in your zone. Waterlogging likely on low-lying arterial roads and subway passes. Avoid flooded roads and follow official local safety advisories. Check the alert source and validity for updated information.",
            "safety_guidelines": "1. Stay indoors unless evacuation is ordered.\n2. Do not drive or walk through moving water.\n3. Keep emergency torches and mobile phones charged.\n4. Disconnect high-voltage household electrical appliances.",
            "source": "IMD Regional Weather Center (Simulated)",
            "duration_hours": 12
        },
        "thunderstorm": {
            "title": "SEVERE THUNDERSTORM & LIGHTNING SQUALL ALERT",
            "alert_type": "Thunderstorm",
            "severity": "CRITICAL",
            "message": "Intense convective thunderstorm cells accompanied by frequent cloud-to-ground lightning strikes and gusty winds up to 65 km/h detected over the region. Seek immediate structural shelter.",
            "safety_guidelines": "1. Take shelter in a sturdy building; avoid open sheds or trees.\n2. Unplug desktop computers and electronic devices.\n3. Stay away from metal poles, tin sheds, and water bodies.\n4. If trapped in the open, crouch low on the balls of your feet.",
            "source": "State Disaster Management Authority (Simulated)",
            "duration_hours": 6
        },
        "cyclone": {
            "title": "CYCLONIC GALE FORCE WIND & SURGE WARNING",
            "alert_type": "Cyclone Alert",
            "severity": "CRITICAL",
            "message": "Deep cyclonic depression intensifying with sustained gale winds between 85-105 km/h. High risk of tree uprooting, power infrastructure disruption, and tin roof displacement.",
            "safety_guidelines": "1. Secure or store loose objects outside homes.\n2. Board up or tape large glass windows.\n3. Prepare a go-bag with dry food, water, documents, and first-aid.\n4. Follow district administration evacuation instructions strictly.",
            "source": "Cyclone Warning Center (Simulated)",
            "duration_hours": 24
        },
        "urban_flood": {
            "title": "FLASH FLOOD & INUNDATION WARNING",
            "alert_type": "Urban Flood",
            "severity": "CRITICAL",
            "message": "Flash flood condition triggered due to drainage breach and heavy runoff. Floodwaters rising above curb height in low-lying residential sectors. Move to upper floors immediately.",
            "safety_guidelines": "1. Move immediately to higher ground or upper floor.\n2. Do not touch fallen electrical cables or submerged transformers.\n3. Boil drinking water before consumption.\n4. Signal for rescue if trapped by waving a bright cloth.",
            "source": "District Emergency Operations Center (Simulated)",
            "duration_hours": 18
        },
        "heatwave": {
            "title": "SEVERE HEATWAVE ADVISORY (HEAT STROKE RISK)",
            "alert_type": "Heatwave",
            "severity": "MEDIUM",
            "message": "Ambient temperatures forecast to cross 44°C with high relative humidity. Vulnerable populations face severe risk of heat exhaustion, cramps, and sunstroke.",
            "safety_guidelines": "1. Avoid direct outdoor exposure between 11:30 AM and 4:00 PM.\n2. Drink plenty of water and oral rehydration salts (ORS).\n3. Wear light-colored, loose cotton clothing.\n4. Never leave children or pets inside parked vehicles.",
            "source": "State Health & Meteorological Bureau (Simulated)",
            "duration_hours": 48
        }
    }

    @classmethod
    def create_simulated_alert(cls, session, template_key, location_name, lat=None, lng=None):
        """
        Creates and stores a simulated weather alert with duplicate prevention.
        """
        template = cls.SIMULATION_TEMPLATES.get(template_key, cls.SIMULATION_TEMPLATES["heavy_rain"])
        
        # Deduplication check: Is there already an active alert of this type in this area created in the last 2 hours?
        recent_cutoff = utcnow() - timedelta(hours=2)
        existing = session.query(EmergencyAlert).filter(
            EmergencyAlert.alert_type == template["alert_type"],
            EmergencyAlert.area_name == location_name,
            EmergencyAlert.is_active == True,
            EmergencyAlert.created_at >= recent_cutoff
        ).first()

        if existing:
            return existing, False  # Already exists, duplicate prevented

        import uuid
        now = utcnow()
        alert_code = f"SIM-{template_key[:3].upper()}-{uuid.uuid4().hex[:6].upper()}"
        valid_until = now + timedelta(hours=template["duration_hours"])

        alert = EmergencyAlert(
            alert_code=alert_code,
            title=f"[SIMULATION] {template['title']}",
            alert_type=template["alert_type"],
            severity=template["severity"],
            area_name=location_name,
            latitude=lat,
            longitude=lng,
            radius_km=Config.PRIORITIES[template["severity"]].get("sla_minutes", 25.0),
            message=template["message"],
            safety_guidelines=template["safety_guidelines"],
            source=f"{template['source']} — SIMULATED DRILL",
            is_simulated=True,
            valid_from=now,
            valid_until=valid_until,
            is_active=True,
            created_at=now
        )
        session.add(alert)
        session.commit()
        return alert, True

    @classmethod
    def get_live_weather(cls, lat, lng):
        """
        Fetches real-time weather telemetry from Open-Meteo free API (no key required).
        Provides clear data attribution and fallback if offline.
        """
        try:
            url = f"https://api.open-meteo.com/v1/forecast?latitude={lat}&longitude={lng}&current=temperature_2m,relative_humidity_2m,apparent_temperature,precipitation,rain,weather_code,wind_speed_10m&timezone=auto"
            resp = requests.get(url, timeout=5)
            if resp.status_code == 200:
                data = resp.json()
                current = data.get("current", {})
                return {
                    "available": True,
                    "provider": "Open-Meteo Weather API",
                    "latitude": lat,
                    "longitude": lng,
                    "temperature": current.get("temperature_2m"),
                    "apparent_temperature": current.get("apparent_temperature"),
                    "humidity": current.get("relative_humidity_2m"),
                    "precipitation": current.get("precipitation"),
                    "wind_speed": current.get("wind_speed_10m"),
                    "weather_code": current.get("weather_code"),
                    "issue_time": current.get("time"),
                    "is_official_warning": False,
                    "notice": "Informational weather telemetry only. Not an official disaster warning."
                }
        except Exception as e:
            logger.warning(f"Live weather telemetry unavailable: {e}")

        return {
            "available": False,
            "provider": "Open-Meteo Weather API (Offline/Unreachable)",
            "notice": "Live weather telemetry currently unavailable. Operating in local simulation mode."
        }

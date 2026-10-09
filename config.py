import os
from pathlib import Path
from dotenv import load_dotenv

# Base directory of the application
BASE_DIR = Path(__file__).resolve().parent

# Load environment variables from .env file
load_dotenv(BASE_DIR / ".env")

class Config:
    SECRET_KEY = os.getenv("SECRET_KEY", "resqai-super-secret-key-emergency-response-2026")
    
    # SQLite Database URI
    INSTANCE_DIR = BASE_DIR / "instance"
    INSTANCE_DIR.mkdir(exist_ok=True)
    DEFAULT_DB_PATH = INSTANCE_DIR / "resqai.db"
    SQLALCHEMY_DATABASE_URI = os.getenv("DATABASE_URL", f"sqlite:///{DEFAULT_DB_PATH.as_posix()}")
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    
    # Upload configuration
    UPLOAD_FOLDER = BASE_DIR / "static" / "uploads"
    UPLOAD_FOLDER.mkdir(parents=True, exist_ok=True)
    MAX_CONTENT_LENGTH = 16 * 1024 * 1024  # 16 MB max upload
    ALLOWED_EXTENSIONS = {"png", "jpg", "jpeg", "gif", "webp", "pdf"}
    
    # Groq AI Settings
    GROQ_API_KEY = os.getenv("GROQ_API_KEY", "").strip()
    GROQ_MODEL = os.getenv("GROQ_MODEL", "openai/gpt-oss-20b")
    GROQ_FALLBACK_MODELS = ["openai/gpt-oss-120b", "qwen/qwen3.8-27b", "llama-3.1-8b-instant"]
    
    # Dispatch & Routing Rules
    ACK_TIMEOUT_SECONDS = int(os.getenv("ACK_TIMEOUT_SECONDS", "45"))
    MAX_REASSIGN_ATTEMPTS = int(os.getenv("MAX_REASSIGN_ATTEMPTS", "3"))
    AUTO_DISPATCH_ENABLED = os.getenv("AUTO_DISPATCH_ENABLED", "true").lower() == "true"
    BUZZER_REPEAT_INTERVAL = int(os.getenv("BUZZER_REPEAT_INTERVAL", "10"))
    
    # Standard Priority Colors (as specified in requirements)
    PRIORITIES = {
        "CRITICAL": {
            "name": "CRITICAL",
            "color": "#dc3545",  # Red — immediate attention
            "badge_class": "badge-critical",
            "sla_minutes": 5,
            "description": "Life-threatening situation or severe disaster requiring immediate intervention"
        },
        "HIGH": {
            "name": "HIGH",
            "color": "#fd7e14",  # Orange — urgent response
            "badge_class": "badge-high",
            "sla_minutes": 15,
            "description": "Urgent emergency with potential casualties or escalating danger"
        },
        "MEDIUM": {
            "name": "MEDIUM",
            "color": "#ffc107",  # Yellow — timely response
            "badge_class": "badge-medium",
            "sla_minutes": 30,
            "description": "Disruptive incident requiring planned timely intervention"
        },
        "LOW": {
            "name": "LOW",
            "color": "#0d6efd",  # Blue — lower-priority queue
            "badge_class": "badge-low",
            "sla_minutes": 60,
            "description": "Advisory or non-immediate public safety concern"
        }
    }
    
    # Employee Statuses
    EMPLOYEE_STATUSES = ["Available", "Busy", "Offline", "No response"]
    
    # Sample Locations
    SAMPLE_LOCATIONS = [
        {"name": "JNTU Anantapur Campus", "lat": 14.6548, "lng": 77.6074, "district": "Anantapur", "state": "Andhra Pradesh"},
        {"name": "Clock Tower, Anantapur", "lat": 14.6819, "lng": 77.6006, "district": "Anantapur", "state": "Andhra Pradesh"},
        {"name": "Collectorate Complex, Kurnool", "lat": 15.8281, "lng": 78.0373, "district": "Kurnool", "state": "Andhra Pradesh"},
        {"name": "Tirupati Central Bus Station", "lat": 13.6288, "lng": 79.4192, "district": "Tirupati", "state": "Andhra Pradesh"},
        {"name": "Amaravati Secretariat", "lat": 16.5131, "lng": 80.5165, "district": "Guntur", "state": "Andhra Pradesh"},
        {"name": "Beach Road, Visakhapatnam", "lat": 17.7196, "lng": 83.3218, "district": "Visakhapatnam", "state": "Andhra Pradesh"},
        {"name": "HITEC City, Hyderabad", "lat": 17.4474, "lng": 78.3762, "district": "Hyderabad", "state": "Telangana"}
    ]

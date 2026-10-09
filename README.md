# ResQAI — AI-Powered Emergency Alert & Response System

> **Prototype Status**: Fully functional, interactive full-stack emergency response system with connected Citizen Safety Portal, Call-Center Operations Command, Web Audio API alarm buzzer, Groq AI triage integration, deterministic fallback rule engine, automated responder routing, and GIS mapping.

---

## 1. System Overview

**ResQAI** is a smart emergency-management platform built to bridge the critical gap between citizens facing natural disasters or life-threatening emergencies and municipal/state emergency call-center dispatchers.

The platform uses AI to assist human operators with complex incident triage, structured summarization, priority recommendation, and resource coordination—**while keeping human operators strictly in charge of all dispatch approvals and actions.**

### Supported Disaster & Emergency Scenarios
* **Heavy Rainfall & Urban Flooding**: Rapid waterlogging advisories, inflatable rescue boat dispatch, drainage breach alerts.
* **Thunderstorms & Severe Lightning**: High-speed squalls, power infrastructure failure, grounding advisories.
* **Cyclonic Gale Winds & Storm Surges**: Coastal and inland structural damage warnings.
* **Road Accidents & Highway Collisions**: Multi-vehicle entrapment, extrication squad routing.
* **Fire & Smoke Incidents**: Transformer blowouts, structure fires, high-expansion foam tender allocation.
* **Critical Medical Emergencies**: Cardiac arrest, trauma, unconscious victims, 108 ambulance dispatch.

---

## 2. Architecture & Technology Stack

| Component | Technology | Rationale |
|---|---|---|
| **Backend** | Python 3.10+ / Flask | Lightweight, robust WSGI framework with clean blueprint routing |
| **Database** | SQLite + SQLAlchemy ORM | ACID-compliant relational persistence, transactions, and audit history |
| **AI Engine** | Groq API (`openai/gpt-oss-20b`, `openai/gpt-oss-120b`, `qwen/qwen3.8-27b`) | Sub-second ultra-fast LLM emergency triage |
| **Fallback Engine** | Deterministic NDMA / EMS Rule Engine | 100% offline-resilient emergency triage fallback if internet or API fails |
| **Frontend** | HTML5, CSS3, JavaScript (ES6+), Bootstrap 5 | Mobile-first responsive layouts, deep navy slate theme |
| **Icons** | FontAwesome 6 | Intuitive emergency, medical, weather, and status iconography |
| **GIS Maps** | Leaflet + OpenStreetMap | Interactive spatial incident plotting with priority color-coded markers |
| **Audio Alerting** | Browser Web Audio API Synthesizer | Zero-dependency, reliable siren tone generation bypassing audio asset blocking |
| **Camera & Video**| Browser `getUserMedia` + Canvas Telemetry | Explicit permission webcam preview & simulated victim video panel |

---

## 3. Emergency Priority Levels & Exact Standard Colors

ResQAI enforces strict visual color codings across both citizen and operator dashboards:

| Priority | Exact Hex Color | SLA Response Target | Severity Description |
|---|---|---|---|
| **CRITICAL** | `#dc3545` (Red) | `< 5 minutes` | Life-threatening hazard, drowning, trapped victims, cardiac arrest |
| **HIGH** | `#fd7e14` (Orange) | `< 15 minutes` | Urgent emergency, structural fire, head-on crash, rising floodwater |
| **MEDIUM** | `#ffc107` (Yellow) | `< 30 minutes` | Timely intervention required, road blockages, non-critical injuries |
| **LOW** | `#0d6efd` (Blue) | `< 60 minutes` | Advisory concerns, public safety monitoring, minor incidents |

---

## 4. Key Workflows & Features

### A. Citizen Safety Portal (`/citizen`)
1. **Mobile-First Dashboard**: Optimized for mobile phones and tablet viewports.
2. **Zone Selection & GPS Triangulation**: Select regional hubs (e.g., JNTU Anantapur, Kurnool, Tirupati, Amaravati, Visakhapatnam, Hyderabad) or click **"Use GPS"** for browser geolocation.
3. **Local Weather & Disaster Advisories**: Displays active alerts with severity, affected zone, issuing agency, validity window, and protective guidelines.
4. **Prototype Drills Simulator**: Instant one-click triggers to simulate **Heavy Rain**, **Thunderstorm**, or **Cyclone** warnings.
5. **SOS Emergency Request Form**:
   * Incident category selection
   * Location / street landmark
   * Citizen description
   * Estimated affected persons count
   * Optional callback phone and citizen name
   * Optional photographic attachment upload
6. **Live Case Tracking**: Real-time polling card displaying Case Number, Lifecycle Status, Assigned Responder, and Operator Resolution Notes.

### B. Call-Center Operations Command (`/dashboard`)
1. **Overview KPI Cards**:
   * **Total Active Cases**
   * **Critical Cases** (highlighted in red)
   * **Awaiting Acknowledgement**
   * **Available Staff** (online dispatchers)
   * **Average Response Time** (computed from real demonstration events)
2. **Audible Siren Buzzer**:
   * Web Audio API synthesized pulsating siren alarm.
   * **Enable Sound** control button.
   * Visual warning banner when unacknowledged cases exist.
   * Case-specific **Acknowledge** button to immediately silence the alarm for that incident.
3. **GIS Incident Map**: Interactive Leaflet map displaying active emergencies with priority color pins and detailed popup modal drawers.
4. **Dispatch Video Desk**:
   * **Operator Webcam**: Starts video preview **only upon explicit user click**; includes a live "LIVE ON-AIR" indicator and "Stop Camera" control.
   * **Simulated Citizen Video**: Real-time canvas radar animation with telemetry and WebRTC-ready integration markers.
5. **Live Emergency Queue**:
   * Instant multi-filtering by Emergency Type, Priority, Status, and Search keywords.
   * Status badges: `NEW`, `ASSIGNED`, `ACKNOWLEDGED`, `IN_PROGRESS`, `ESCALATED`, `RESOLVED`.
6. **AI Decision Support Studio**:
   * Generates executive incident summaries.
   * Extracts verified facts (trapped individuals, hazards, location cues).
   * Identifies missing critical information (power lines status, medical conditions).
   * Recommends specific first responder units (e.g., ALS Ambulances, Water Rescue Inflatable Boats).
   * Analyzes 911 audio/call transcripts into structured dispatch orders.
7. **Employee Routing & Availability Management (`/employees`)**:
   * 4 availability statuses: `Available`, `Busy`, `Offline`, `No response`.
   * Deterministic round-robin / least-busy dispatch algorithm.
   * Configurable acknowledgement deadline (default: **45 seconds**).
   * Automated watchdog reassignment on timeout.
   * Automatic escalation to Supervisor Queue when all responders are occupied.
   * Explicit operator manual override capabilities.

---

## 5. Quickstart Setup Guide (Windows & VS Code)

### Step 1: Open the Project in VS Code
Open VS Code, navigate to **File > Open Folder...**, and select:
```text
C:\Users\chatl\OneDrive\Desktop\JNTUA
```

### Step 2: Open PowerShell Terminal
In VS Code, press ``Ctrl + ` `` or go to **Terminal > New Terminal**. Ensure you are in the project folder:
```powershell
cd "C:\Users\chatl\OneDrive\Desktop\JNTUA"
```

### Step 3: (Optional) Create & Activate Virtual Environment
```powershell
python -m venv venv
.\venv\Scripts\Activate.ps1
```
*(If script execution is restricted, run `Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass`)*

### Step 4: Install Dependencies
```powershell
pip install -r requirements.txt
```

### Step 5: Configure Environment (`.env`)
A configured `.env` file is included. To review or change settings:
```powershell
# Copy template if creating a fresh environment
Copy-Item .env.example .env
```
Inside `.env`:
```ini
FLASK_APP=app.py
PORT=5000
DATABASE_URL=sqlite:///instance/resqai.db
GROQ_API_KEY=your_groq_api_key_here
GROQ_MODEL=openai/gpt-oss-20b
ACK_TIMEOUT_SECONDS=45
MAX_REASSIGN_ATTEMPTS=3
```

### Step 6: Initialize / Seed Sample Emergency Data
Run the seed script to populate sample employees, weather alerts, and emergency cases:
```powershell
python seed.py
```

### Step 7: Run Automated Tests
Verify all 21 unit and integration tests pass:
```powershell
python -m unittest discover tests
```

### Step 8: Launch the Application
```powershell
python app.py
```
Open your browser to:
* **Citizen Safety Portal**: [http://127.0.0.1:5000/citizen](http://127.0.0.1:5000/citizen)
* **Call-Center Operations Command**: [http://127.0.0.1:5000/dashboard](http://127.0.0.1:5000/dashboard)
* **AI Triage Studio**: [http://127.0.0.1:5000/ai-assistant](http://127.0.0.1:5000/ai-assistant)
* **Responder Roster**: [http://127.0.0.1:5000/employees](http://127.0.0.1:5000/employees)
* **Public Alerts Broadcast**: [http://127.0.0.1:5000/alerts](http://127.0.0.1:5000/alerts)

---

## 6. Verification of Required Interactions

Follow this step-by-step checklist to test the application:

1. **Citizen Portal**: Navigate to `/citizen`. Select **JNTU Anantapur Campus**.
2. **Weather Simulation**: Click **"Simulate Heavy Rain"**. Verify that the alert appears with safety guidelines and a clear `[SIMULATION]` watermark.
3. **Emergency Submission**: Click the big red **SOS** button. Select **Heavy Rain / Flood**, enter `"Ground floor submerged, 4 students trapped on library steps"`, and click **Transmit Request**.
4. **Live Tracking**: Observe the tracking card displaying your Case Number (`RESQ-2026-XXXX`) and assigned responder name.
5. **Call-Center Operations**: Open `/dashboard` in another tab. Verify the new case appears in the emergency queue.
6. **Audible Buzzer**: Click **"Enable Sound"** in the top navbar. The synthesized alarm sounds for the unacknowledged critical case.
7. **Acknowledgement**: Click **"Ack"** on the case row. The buzzer silences, response time is calculated, and status transitions to `ACKNOWLEDGED`.
8. **AI Triage Drawer**: Click **"Details"** to view the AI summary, extracted facts, missing questions, and recommended units (e.g., *SDRF Water Rescue Inflatable Boat Unit*).
9. **Employee Routing Timeout**: Set an employee to `No response` or wait 45 seconds and click **"Trigger Timeout Watchdog"** to watch the case reassign to the next eligible responder.
10. **Resolution**: Click **"Resolve Incident"**, enter operator resolution notes, and confirm. The case marks as `RESOLVED`.

---

## 7. Feature Matrix: Implemented vs External Services

| Feature | Prototype Implementation | External Production Service |
|---|---|---|
| **AI Incident Triage** | Live Groq API (`openai/gpt-oss-20b`) + Deterministic Fallback Engine | Fully functional with configured key; fallback works without key |
| **Audible Alerts** | Web Audio API Oscillator synthesizer (zero mp3 dependency) | Works natively across all modern web browsers |
| **Weather Advisories** | Dynamic local simulation drills + Open-Meteo telemetry | Can connect to IMD / NOAA / NWS CAP feeds |
| **Employee Routing** | Deterministic round-robin & SLA deadline watchdog | In-memory + SQLite persistent transaction queue |
| **Operator Video** | Browser `getUserMedia` with explicit user toggle | WebRTC camera stream |
| **Victim Video** | Animated simulation canvas with GPS telemetry overlay | WebRTC peer-to-peer / Twilio Video integration point |
| **Notifications** | Real-time in-app notification center | Twilio SMS / WhatsApp Business API integration point |

---

## 8. Troubleshooting & Common Questions

* **Audio siren doesn't sound**: Modern browsers block audio autoplay. Click the **"Enable Sound"** button in the top bar to grant permission.
* **Camera permission error**: Click **"Start Camera"**; when the browser prompts "Allow camera access?", select **Allow**. If on a desktop without a webcam, a friendly notice is displayed.
* **Offline / No Internet**: ResQAI is built with zero external runtime dependencies—it automatically falls back to its internal deterministic triage engine if Groq or Open-Meteo are unreachable.

---

*ResQAI — Developed for JNTUA & Emergency Response Innovations (2026).*

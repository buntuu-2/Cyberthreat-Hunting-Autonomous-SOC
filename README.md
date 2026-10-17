# 🛡️ AI Cyberthreat Hunting & Autonomous SOC

**Final Year Major Project**  
**Prepared for:**  
- **Utkarsh Maurya** (Roll No: `2304231550021`)  
- **Prince Maurya** (Roll No: `2304231550009`)  
**College:** School of Management Sciences, Lucknow  

---

## 📋 Project Overview

The **AI Cyberthreat Hunting and Autonomous SOC** is a practical, semi-autonomous mini-Security Operations Center that bridges endpoint detection, network telemetry, external threat intelligence, AI-assisted investigation, deterministic risk scoring, and automated containment actions.

### Core Pipeline Flow:
```
[ Security Events ] (SSH auth.log / Wazuh / Suricata EVE)
       ↓
[ Alert Parser & Normalizer ] (Standard NormalizedAlert Schema)
       ↓
[ Threat Intelligence Enrichment ] (AbuseIPDB / Cache / Threat Tags)
       ↓
[ Deterministic Risk Engine ] (Evidence Points: +20, +30, etc. -> Score 0-100)
       ↓
[ AI Threat Analyst Layer ] (MITRE ATT&CK Mapping & Structured Summary)
       ↓
[ Response Policy Gatekeeper ] (Allowlist Check & Severity Threshold)
       ↓
[ Autonomous Containment ] (Temporary UFW Firewall Block with TTL)
       ↓
[ Glassmorphic SOC Command Center & Downloadable Incident Report ]
```

---

## 🏗️ High-Level System Architecture

```
┌────────────────────────────────────────────────────────┐
│                   CONTROLLED LAB HOST                  │
│       Kali Linux / Threat Simulator / Attack Probes    │
└──────────────────────────┬─────────────────────────────┘
                           │
                           ▼
┌────────────────────────────────────────────────────────┐
│                     UBUNTU SENSORS                     │
│    • Wazuh Agent (Endpoint auth logs, sudo, FIM)       │
│    • Suricata IDS (Network packet analysis, scans)     │
│    • UFW Firewall (Controlled port filtering)          │
└──────────────────────────┬─────────────────────────────┘
                           │
                           ▼
┌────────────────────────────────────────────────────────┐
│                   PYTHON SOC ENGINE                    │
│                                                        │
│  ┌───────────────────┐       ┌──────────────────────┐  │
│  │ Alert Parser &    │       │ Threat Intelligence  │  │
│  │ Normalizer        │──────▶│ Engine (AbuseIPDB)   │  │
│  └─────────┬─────────┘       └──────────┬───────────┘  │
│            │                            │              │
│            ▼                            ▼              │
│  ┌───────────────────┐       ┌──────────────────────┐  │
│  │ Deterministic     │◀──────│ AI Threat Analyst    │  │
│  │ Risk Engine       │       │ (Gemini/OpenAI/Mock) │  │
│  └─────────┬─────────┘       └──────────────────────┘  │
│            │                                           │
│            ▼                                           │
│  ┌───────────────────┐       ┌──────────────────────┐  │
│  │ Response Policy   │──────▶│ Firewall Manager     │  │
│  │ Gatekeeper        │       │ (UFW Block / TTL)    │  │
│  └───────────────────┘       └──────────────────────┘  │
└──────────────────────────┬─────────────────────────────┘
                           │
                           ▼
┌────────────────────────────────────────────────────────┐
│          REAL-TIME CYBER SOC COMMAND CENTER            │
│    • Live WebSocket Incident Stream                    │
│    • Interactive Attack Simulator (Workflows A, B, C)  │
│    • Deterministic Risk Gauge & Contributing Factors   │
│    • AI Executive Summary & Remediation Steps          │
│    • Active Firewall Rule Table with TTL Countdown     │
│    • Viva Defense Cheatsheet & Markdown Reports        │
└────────────────────────────────────────────────────────┘
```

---

## 🛠️ Technology Stack

| Layer | Tool / Component | Purpose |
|---|---|---|
| **Operating System** | Ubuntu Linux | Security lab, host monitoring, firewall, services |
| **SIEM / XDR** | Wazuh | Centralized endpoint log analysis, detection rules |
| **Network IDS/IPS** | Suricata | Real-time network traffic inspection and EVE JSON logs |
| **Threat Intelligence** | AbuseIPDB / VirusTotal | IP indicator reputation, geolocation, threat tagging |
| **AI Investigation** | Python + Gemini / OpenAI / Mock SOC AI | Contextual threat synthesis, MITRE ATT&CK mapping |
| **Risk Engine** | Python (Deterministic) | Transparent, auditable mathematical risk scoring |
| **Containment** | UFW (Uncomplicated Firewall) | Automated temporary IP blocking with auto-unblock TTL |
| **Web Dashboard** | FastAPI, WebSockets, Vanilla CSS | Glassmorphic dark cyberpunk SOC command center |
| **DevOps** | Docker, docker-compose, GitHub Actions | Containerization and automated CI test pipeline |

---

## 📂 Project Directory Structure

```
ai-soc/
├── ai_soc/
│   ├── config/
│   │   └── settings.py          # Central pydantic configuration & env loading
│   ├── alerts/
│   │   ├── models.py            # Pydantic schemas (NormalizedAlert, IncidentRecord, etc.)
│   │   ├── parser.py            # Log parser for Wazuh, Suricata, & auth.log
│   │   └── normalizer.py        # Normalizes raw inputs into unified alert format
│   ├── threat_intel/
│   │   └── reputation.py        # IP reputation engine with caching & mock database
│   ├── ai/
│   │   └── analyzer.py          # AI Threat Analyst (Gemini, OpenAI, Ollama, Heuristic)
│   ├── detection/
│   │   └── risk_engine.py       # Deterministic scoring engine (+20, +30 points)
│   ├── response/
│   │   ├── policy.py            # Policy gatekeeper & allowlist enforcer
│   │   └── firewall.py          # UFW firewall manager & audit trail logger
│   ├── reports/
│   │   └── incident_report.py   # Markdown, HTML, and JSON incident exporter
│   ├── pipeline.py              # Central pipeline orchestrator & WebSocket dispatcher
│   └── store.py                 # Persistent incident storage
├── dashboard/
│   ├── api.py                   # FastAPI application & WebSocket broadcast server
│   └── static/
│       ├── index.html           # Modern glassmorphic SOC command center interface
│       ├── css/style.css        # Premium dark cyberpunk styling
│       └── js/app.js            # Real-time WebSocket controller & UI logic
├── simulator/
│   ├── attack_simulator.py      # Simulator implementing Workflows A, B, C, & D
│   └── sample_logs/             # Realistic raw Wazuh and Suricata telemetry files
├── tests/
│   ├── test_risk.py             # Unit tests for scoring engine & thresholds
│   ├── test_parser.py           # Unit tests for alert ingestion & normalization
│   ├── test_threat_intel.py     # Unit tests for reputation lookup & caching
│   ├── test_response_policy.py  # Unit tests for allowlist & UFW containment
│   └── test_integration.py      # End-to-end integration tests
├── .github/workflows/ci.yml     # Automated CI/CD pipeline
├── Dockerfile                   # Production Docker container definition
├── docker-compose.yml           # Multi-container deployment compose file
├── requirements.txt             # Python dependencies
├── .env.example                 # Example configuration template
├── main.py                      # Master CLI and server launcher
├── VIVA_QUESTIONS_AND_ANSWERS.md# Viva preparation guide for examination
└── README.md                    # Project documentation
```

---

## ⚡ Quick Start Guide

### 1. Prerequisites
- Python 3.10+ (Tested on Python 3.11 & 3.14)
- (Optional) Docker & docker-compose

### 2. Setup Virtual Environment & Install Dependencies
```bash
cd /home/scarface/Cyberthreat/ai-soc
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

### 3. Launch the SOC Command Center Web Server
```bash
python main.py --serve --port 8000
```
Open your browser and navigate to:  
👉 **`http://localhost:8000`**

---

## 🚀 Demonstration Workflows (Section 7)

You can launch controlled attack simulations with a single click from the Web Dashboard or via the CLI:

### Workflow A: SSH Brute-Force Detection & Automated Containment
```bash
python main.py --simulate A
```
- **Scenario:** Attacker IP `198.51.100.42` launches rapid failed SSH logins against user `root`.
- **Detection:** Wazuh rule `5712` fires.
- **Enrichment:** AbuseIPDB reports 95% abuse confidence score.
- **Risk Score:** Assigned **85/100 [CRITICAL]** (+20 repeated failures, +20 root account, +30 malicious IP, +15 repeated behavior).
- **Automated Response:** Response policy triggers an automated **UFW firewall block** with 300s TTL.

### Workflow B: Network Port Scan Reconnaissance
```bash
python main.py --simulate B
```
- **Scenario:** Attacker IP `45.33.32.156` scans ports 80, 443, 22.
- **Detection:** Suricata IDS detects signature `ET SCAN Potential Nmap SYN Port Scan`.
- **Enrichment:** Abuse score 88% (Hosting provider).
- **Risk Score:** Evaluated at **45/100 [MEDIUM]**.

### Workflow C: Threat Intelligence Indicator Enrichment
```bash
python main.py --simulate C
```
- **Scenario:** Inbound connection from verified Tor Exit Node `185.220.101.5`.
- **Enrichment:** Threat intelligence tags: `Tor Exit Node`, `Anonymizer`, `Exploit Prober`.

### Workflow D: Credential Compromise
```bash
python main.py --simulate D
```
- **Scenario:** Successful login following consecutive authentication failures.
- **Risk Score:** Adds `+30` credential crack factor, escalating to **95/100 [CRITICAL]**.

---

## ⚖️ Deterministic Risk Scoring Model (Section 9)

| Evidence Observable | Points Awarded | Technical Justification |
|---|---|---|
| **Repeated Failed Login Attempts** | `+20` | ≥ 3 failed logins or brute-force signature within sliding window |
| **Privileged Account Targeted** | `+20` | Account targeted is `root`, `admin`, `wheel`, or `sudo` |
| **Known Malicious IP Reputation** | `+30` | Threat intelligence abuse confidence score ≥ 50% |
| **Repeated Behavior Over Time** | `+15` | Multiple suspicious events observed from same indicator |
| **Successful Login After Failures** | `+30` | High probability of brute-force password crack success |

### Severity Tier Thresholds:
- **`0 – 30`**: **LOW** (Passive logging, monitoring)
- **`31 – 60`**: **MEDIUM** (Alert generated, SOC analyst notification)
- **`61 – 80`**: **HIGH** (Automated temporary firewall block eligible)
- **`81 – 100`**: **CRITICAL** (Immediate network isolation & high-priority containment)

---

## 🧪 Running Automated Tests

Run the complete test suite:
```bash
pytest -v tests/
```
All 16 test cases validate:
- Risk calculation formulas and edge conditions
- Syslog, Wazuh JSON, and Suricata EVE parsing
- Threat intelligence caching and loopback isolation
- Response policy allowlist enforcement and UFW actions
- End-to-end integration and Markdown report generation

---

## 🐳 Docker Deployment

To launch the entire platform in an isolated container:
```bash
docker compose up --build
```
Access the dashboard at `http://localhost:8000`.

---

## 🎓 College Viva Preparation Guide
For full viva defense questions and answers (Section 11 of the Roadmap), see:  
📖 **[VIVA_QUESTIONS_AND_ANSWERS.md](VIVA_QUESTIONS_AND_ANSWERS.md)** or click the **"Viva Defense Guide"** button in the Web Dashboard.

# 🎓 Final Year Project Viva Preparation Guide & Defense Cheatsheet

**Project Title:** AI Cyberthreat Hunting and Autonomous SOC  
**Students:**  
- **Utkarsh Maurya** (Roll No: `2304231550021`)  
- **Prince Maurya** (Roll No: `2304231550009`)  
**College:** School of Management Sciences, Lucknow  

---

## 1. Quick Technical Summary (Elevator Pitch)
> "Our project is a **semi-autonomous mini-Security Operations Center (SOC)** that bridges telemetry, threat detection, threat intelligence, and deterministic automated response. It collects endpoint and network events (via Wazuh and Suricata), enriches indicators like IP addresses using Threat Intelligence, uses an AI layer to translate telemetry into structured MITRE ATT&CK narratives, evaluates a transparent, auditable **deterministic risk scoring model**, and automatically triggers predefined containment actions—such as temporary UFW firewall blocks—governed by allowlist policies."

---

## 2. Core Viva Questions & Expert Answers

### Q1: What is a SOC?
**Answer:**  
A **Security Operations Center (SOC)** is a centralized function or facility within an organization responsible for continuously monitoring, detecting, investigating, and responding to cyberthreats and security events across endpoints, servers, and network infrastructure.

### Q2: What is SIEM?
**Answer:**  
**Security Information and Event Management (SIEM)** is a security management architecture that:
1. Aggregates and centralizes logs from disparate systems (firewalls, endpoints, servers, routers).
2. Normalizes disparate log schemas into a standard format.
3. Correlates events in real-time against detection rule sets.
4. Generates security alerts and provides incident visualization and compliance reporting.

### Q3: Why Wazuh?
**Answer:**  
Wazuh is an open-source, enterprise-ready security platform that integrates:
- **Endpoint Detection & Response (EDR):** The Wazuh agent monitors processes, file integrity (FIM), system logs (`/var/log/auth.log`, `syslog`), and rootkits.
- **SIEM Engine:** Centralized correlation server that processes rules (e.g., Rule 5710 for single failed SSH login, Rule 5712 for multiple failed logins / brute force).
- **Extensibility:** Standard JSON output (`alerts.json`) allows custom Python automation engines to easily ingest and act upon alerts.

### Q4: What is Suricata?
**Answer:**  
Suricata is a high-performance, open-source network threat detection engine capable of:
- **Intrusion Detection System (IDS):** Inspects raw packets (promiscuous mode) and generates telemetry when signatures (like Nmap port scans or Tor exit node traffic) are matched.
- **Intrusion Prevention System (IPS):** Can actively drop packets inline when running with NFQUEUE.
- **Network Security Monitoring (NSM):** Produces detailed EVE JSON logs (`eve.json`) recording DNS queries, HTTP metadata, TLS handshakes, and flow statistics.

### Q5: What is Threat Hunting?
**Answer:**  
Unlike passive monitoring (waiting for an alert), **Threat Hunting** is a proactive, hypothesis-driven analytical process where security defenders search through telemetry and historical data to detect stealthy adversary activity or indicators of compromise (IOCs) that bypassed signature-based automated defenses.

### Q6: Why use Threat Intelligence?
**Answer:**  
Threat Intelligence enriches atomic indicators (such as an external IP address) with global reputation, context, and historical activity from databases like **AbuseIPDB** and **VirusTotal**. It tells an analyst:
- Is this IP a known Tor exit node or VPN proxy?
- Has it been reported by thousands of other servers for brute-force attacks in the last 24 hours?
- What country and ISP does it belong to?

### Q7: Why AI in the SOC?
**Answer:**  
AI assists human analysts facing alert fatigue by:
1. Translating technical logs into concise, human-readable executive summaries.
2. Mapping attacks to the **MITRE ATT&CK** matrix (e.g. `T1110.001 - Password Guessing`).
3. Synthesizing evidence across multiple telemetry feeds to explain *why* an event is dangerous.
4. Suggesting concrete investigation and remediation steps in seconds.

### Q8: Is the SOC fully autonomous?
**Answer:**  
**No, the SOC is designed as semi-autonomous.**  
- **AI is strictly advisory:** The AI model analyzes telemetry and provides summaries, but **is never given arbitrary shell access or permission to execute system commands directly**.
- **Deterministic containment:** Automated high-impact actions (such as firewall blocks) are controlled by explicit, auditable policy rules, allowlists (preventing self-lockout of localhost or gateways), and risk score thresholds.

### Q9: Why use a deterministic risk engine if AI already gives a severity?
**Answer:**  
A **deterministic risk engine** provides transparency, auditability, and mathematical consistency.
- Probabilistic AI models can suffer from hallucinations, non-determinism, or prompt injection.
- In contrast, our risk engine scores exact observables based on clear points:
  - Repeated failed login attempts: `+20` points
  - Privileged account (`root`) targeted: `+20` points
  - Known malicious IP reputation (AbuseIPDB ≥ 50%): `+30` points
  - Repeated activity over time: `+15` points
  - Successful login after repeated failures: `+30` points
- This ensures every automated containment decision can be legally defended, explained to auditors, and verified by administrators.

### Q10: What happens end-to-end when an alert arrives?
**Answer:**  
The workflow proceeds through 8 distinct stages:
1. **Event Ingestion:** Raw log (e.g. from `/var/log/auth.log` or Suricata) is received.
2. **Parsing & Detection:** Event format is identified and mapped to rule sets.
3. **Normalization:** Transformed into a unified `NormalizedAlert` schema.
4. **Threat Intelligence Enrichment:** Source IP is queried against AbuseIPDB/cache.
5. **Deterministic Risk Assessment:** Evidence factors are totaled (0–100 scale).
6. **AI Threat Investigation:** AI produces MITRE ATT&CK mapping and recommendations.
7. **Response Policy Check:** Verifies IP is not in allowlist and risk ≥ threshold.
8. **Automated Containment & Logging:** UFW firewall rule is applied with TTL, and the entire audit record is displayed on the dashboard.

---

## 3. Demonstration Workflow Scripts for the Examiner

| Workflow | Trigger Command / Button | Expected Outcome |
|---|---|---|
| **Workflow A: SSH Brute-Force** | Click **"Workflow A"** or run `python main.py --simulate A` | 4 failed SSH attempts against `root` from `198.51.100.42`. Risk score reaches **85/100 (CRITICAL)**. Automated UFW block executed. |
| **Workflow B: Port Scan** | Click **"Workflow B"** or run `python main.py --simulate B` | Suricata detects Nmap SYN scan from `45.33.32.156`. Threat intel enriches reputation. Risk score **45/100 (MEDIUM)**. |
| **Workflow C: Threat Intel** | Click **"Workflow C"** or run `python main.py --simulate C` | Inbound traffic from Tor Exit Node `185.220.101.5`. Abuse score 98%, ISP Zwiebelfreunde e.V. |
| **Workflow D: Credential Crack** | Click **"Workflow D"** or run `python main.py --simulate D` | Successful login following repeated failures. Triggers **+30 CRITICAL factor**, reaching score **95/100**. |

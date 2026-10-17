/**
 * AI Cyberthreat Hunting & Autonomous SOC - Frontend Application Controller
 * Handles WebSocket streaming, incident workbench rendering, attack simulations,
 * firewall management, and viva defense presentation.
 */

// Global State
let incidents = [];
let selectedIncidentId = null;
let socket = null;
let reconnectTimer = null;

// DOM Elements
const el = {
  kpiTotal: document.getElementById("kpi-total-val"),
  kpiCrit: document.getElementById("kpi-crit-val"),
  kpiHigh: document.getElementById("kpi-high-val"),
  kpiBlocks: document.getElementById("kpi-blocks-val"),
  headerBlockCount: document.getElementById("header-block-count"),
  wsIndicator: document.getElementById("ws-indicator"),
  wsText: document.getElementById("ws-text"),
  incidentList: document.getElementById("incident-list-container"),
  incidentCountDisplay: document.getElementById("incident-count-display"),
  feedSearch: document.getElementById("feed-search-input"),
  feedSeverity: document.getElementById("feed-severity-select"),
  emptyWorkbench: document.getElementById("empty-workbench-state"),
  activeWorkbench: document.getElementById("active-incident-details"),
  
  // Workbench Elements
  wbTitle: document.getElementById("wb-title"),
  wbId: document.getElementById("wb-id"),
  wbTimestamp: document.getElementById("wb-timestamp"),
  wbSourceBadge: document.getElementById("wb-source-badge"),
  wbStatus: document.getElementById("wb-status"),
  wbRiskScore: document.getElementById("wb-risk-score"),
  wbRiskSev: document.getElementById("wb-risk-sev"),
  wbRiskCircle: document.getElementById("wb-risk-circle"),
  wbRiskExplanation: document.getElementById("wb-risk-explanation"),
  wbFactorsTbody: document.getElementById("wb-factors-tbody"),
  wbAiSummary: document.getElementById("wb-ai-summary"),
  wbAiMitre: document.getElementById("wb-ai-mitre"),
  wbAiReasoning: document.getElementById("wb-ai-reasoning"),
  wbAiAction: document.getElementById("wb-ai-action"),
  wbIntelIp: document.getElementById("wb-intel-ip"),
  wbIntelScore: document.getElementById("wb-intel-score"),
  wbIntelIsp: document.getElementById("wb-intel-isp"),
  wbIntelGeo: document.getElementById("wb-intel-geo"),
  wbIntelReports: document.getElementById("wb-intel-reports"),
  wbIntelTags: document.getElementById("wb-intel-tags"),
  wbRespAction: document.getElementById("wb-resp-action"),
  wbRespIp: document.getElementById("wb-resp-ip"),
  wbRespStatus: document.getElementById("wb-resp-status"),
  wbRespRule: document.getElementById("wb-resp-rule"),
  wbRespTtl: document.getElementById("wb-resp-ttl"),
  wbRawLog: document.getElementById("wb-raw-log"),
  btnUnblockTarget: document.getElementById("btn-unblock-target"),
  btnExportReport: document.getElementById("btn-export-report"),

  // Modals
  modalViva: document.getElementById("modal-viva"),
  modalIngest: document.getElementById("modal-ingest"),
  modalFirewall: document.getElementById("modal-firewall"),
  vivaList: document.getElementById("viva-questions-list"),
  firewallTbody: document.getElementById("firewall-table-tbody"),
  toastContainer: document.getElementById("toast-container")
};

// Initialization
document.addEventListener("DOMContentLoaded", () => {
  initWebSocket();
  loadStats();
  loadIncidents();
  loadActiveFirewallBlocks();
  setupEventListeners();
});

// WebSocket Connection
function initWebSocket() {
  const protocol = window.location.protocol === "https:" ? "wss:" : "ws:";
  const wsUrl = `${protocol}//${window.location.host}/ws/events`;

  try {
    socket = new WebSocket(wsUrl);

    socket.onopen = () => {
      el.wsIndicator.className = "status-dot dot-green";
      el.wsText.innerText = "LIVE TELEMETRY";
      if (reconnectTimer) clearInterval(reconnectTimer);
    };

    socket.onmessage = (event) => {
      try {
        const msg = JSON.parse(event.data);
        if (msg.type === "NEW_INCIDENT" && msg.data) {
          handleIncomingIncident(msg.data);
        }
      } catch (e) {
        console.error("WS Parse error", e);
      }
    };

    socket.onclose = () => {
      el.wsIndicator.className = "status-dot";
      el.wsIndicator.style.background = "#ef4444";
      el.wsText.innerText = "OFFLINE (RETRYING)";
      if (!reconnectTimer) {
        reconnectTimer = setInterval(initWebSocket, 4000);
      }
    };
  } catch (err) {
    console.error("WebSocket init failed:", err);
  }
}

// Handle real-time push event
function handleIncomingIncident(inc) {
  // Add to local state (prepend)
  incidents.unshift(inc);
  showToast(`🚨 New Alert: ${inc.alert.title} [${inc.risk_assessment.severity}]`);
  
  loadStats();
  renderIncidentFeed();
  
  // If no incident selected or this is a critical incident, select it automatically
  if (!selectedIncidentId || inc.risk_assessment.severity === "CRITICAL") {
    selectIncident(inc.incident_id);
  }
}

// Fetch stats
async function loadStats() {
  try {
    const res = await fetch("/api/stats");
    const data = await res.json();
    el.kpiTotal.innerText = data.total_incidents || 0;
    el.kpiCrit.innerText = data.critical_incidents || 0;
    el.kpiHigh.innerText = data.high_incidents || 0;
    el.kpiBlocks.innerText = data.active_firewall_blocks || 0;
    el.headerBlockCount.innerText = data.active_firewall_blocks || 0;
  } catch (e) {
    console.error("Failed to load stats", e);
  }
}

// Fetch incident list
async function loadIncidents() {
  try {
    const sev = el.feedSeverity.value;
    const q = el.feedSearch.value;
    let url = `/api/incidents?limit=100`;
    if (sev) url += `&severity=${encodeURIComponent(sev)}`;
    if (q) url += `&query=${encodeURIComponent(q)}`;

    const res = await fetch(url);
    incidents = await res.json();
    renderIncidentFeed();

    if (incidents.length > 0 && !selectedIncidentId) {
      selectIncident(incidents[0].incident_id);
    }
  } catch (e) {
    console.error("Failed to load incidents", e);
  }
}

// Render left column feed
function renderIncidentFeed() {
  el.incidentCountDisplay.innerText = `${incidents.length} events`;
  
  if (incidents.length === 0) {
    el.incidentList.innerHTML = `
      <div style="padding:40px 20px; text-align:center; color:var(--text-muted);">
        <div style="font-size:2rem; margin-bottom:10px;">🛡️</div>
        <div>No matching events found.</div>
        <div style="font-size:0.78rem; margin-top:6px;">Run a simulation workflow to generate test traffic.</div>
      </div>
    `;
    return;
  }

  el.incidentList.innerHTML = incidents.map(inc => {
    const isAct = inc.incident_id === selectedIncidentId ? "active" : "";
    const sev = inc.risk_assessment.severity;
    const src = (inc.alert.source || "syslog").toLowerCase();
    const timeStr = formatTimestamp(inc.created_at);

    return `
      <div class="incident-card ${isAct}" onclick="selectIncident('${inc.incident_id}')" id="card-${inc.incident_id}">
        <div class="card-top">
          <span class="source-tag tag-${src}">${src}</span>
          <span class="badge-sev sev-${sev}">${sev} (${inc.risk_assessment.score})</span>
        </div>
        <div class="card-title">${escapeHtml(inc.alert.title)}</div>
        <div class="card-details">
          <span>IP: ${inc.alert.source_ip || "Internal"}</span>
          <span>${timeStr}</span>
        </div>
      </div>
    `;
  }).join("");
}

// Select and load detailed workbench
function selectIncident(id) {
  selectedIncidentId = id;
  const inc = incidents.find(i => i.incident_id === id);
  if (!inc) return;

  // Highlight card in feed
  document.querySelectorAll(".incident-card").forEach(c => c.classList.remove("active"));
  const currentCard = document.getElementById(`card-${id}`);
  if (currentCard) currentCard.classList.add("active");

  // Show workbench
  el.emptyWorkbench.style.display = "none";
  el.activeWorkbench.style.display = "flex";

  // Populate Hero
  el.wbTitle.innerText = inc.alert.title;
  el.wbId.innerText = inc.incident_id.substring(0, 13);
  el.wbTimestamp.innerText = formatTimestamp(inc.created_at);
  el.wbSourceBadge.className = `source-tag tag-${inc.alert.source.toLowerCase()}`;
  el.wbSourceBadge.innerText = inc.alert.source.toUpperCase();
  el.wbStatus.innerText = inc.status;
  el.wbStatus.style.color = inc.status === "CONTAINED" ? "var(--accent-emerald)" : "var(--accent-amber)";

  // Populate Risk Gauge
  const score = inc.risk_assessment.score;
  const sev = inc.risk_assessment.severity;
  el.wbRiskScore.innerText = score;
  el.wbRiskSev.innerText = sev;
  el.wbRiskCircle.style.borderColor = getSeverityColor(sev);
  el.wbRiskCircle.style.boxShadow = `0 0 15px ${getSeverityColor(sev)}40`;
  el.wbRiskExplanation.innerText = inc.risk_assessment.explanation;

  // Populate Risk Factors Table
  if (inc.risk_assessment.contributing_factors && inc.risk_assessment.contributing_factors.length > 0) {
    el.wbFactorsTbody.innerHTML = inc.risk_assessment.contributing_factors.map(f => `
      <tr>
        <td>
          <div style="font-weight:600; color:var(--text-primary);">${escapeHtml(f.name)}</div>
          <div style="color:var(--text-muted); font-size:0.72rem;">${escapeHtml(f.description)}</div>
        </td>
        <td style="text-align:right;">
          <span class="pts-badge">+${f.points}</span>
        </td>
      </tr>
    `).join("");
  } else {
    el.wbFactorsTbody.innerHTML = `<tr><td colspan="2" style="color:var(--text-muted); text-align:center;">No high-risk factors identified.</td></tr>`;
  }

  // Populate AI Panel
  if (inc.ai_analysis) {
    el.wbAiSummary.innerText = inc.ai_analysis.summary;
    el.wbAiMitre.innerText = `${inc.ai_analysis.attack_type} [${inc.ai_analysis.mitre_attack_technique}]`;
    el.wbAiReasoning.innerText = inc.ai_analysis.evidence_reasoning;
    el.wbAiAction.innerText = inc.ai_analysis.recommended_action;
  } else {
    el.wbAiSummary.innerText = "No AI investigation performed.";
    el.wbAiMitre.innerText = "--";
    el.wbAiReasoning.innerText = "--";
    el.wbAiAction.innerText = "--";
  }

  // Populate Threat Intel
  if (inc.threat_intel) {
    el.wbIntelIp.innerText = inc.threat_intel.indicator;
    el.wbIntelScore.innerText = `${inc.threat_intel.abuse_confidence_score}%`;
    el.wbIntelScore.style.color = inc.threat_intel.abuse_confidence_score >= 50 ? "var(--accent-crimson)" : "var(--accent-emerald)";
    el.wbIntelIsp.innerText = inc.threat_intel.isp || "Unknown";
    el.wbIntelGeo.innerText = `${inc.threat_intel.country_name} (${inc.threat_intel.country_code})`;
    el.wbIntelReports.innerText = `${inc.threat_intel.total_reports} abuse reports`;
    el.wbIntelTags.innerText = (inc.threat_intel.threat_tags && inc.threat_intel.threat_tags.length) 
      ? inc.threat_intel.threat_tags.join(", ") 
      : "None";
  } else {
    el.wbIntelIp.innerText = inc.alert.source_ip || "Internal / Not Applicable";
    el.wbIntelScore.innerText = "0%";
    el.wbIntelIsp.innerText = "Local Area Network";
    el.wbIntelGeo.innerText = "Internal Subnet";
    el.wbIntelReports.innerText = "0";
    el.wbIntelTags.innerText = "Internal Host";
  }

  // Populate Response Action
  if (inc.response_action) {
    el.wbRespAction.innerText = inc.response_action.action_type;
    el.wbRespIp.innerText = inc.response_action.target_ip || "N/A";
    el.wbRespStatus.innerText = inc.response_action.status;
    el.wbRespRule.innerText = inc.response_action.rule_applied;
    el.wbRespTtl.innerText = inc.response_action.ttl_seconds ? `${inc.response_action.ttl_seconds} seconds` : "Permanent / No TTL";

    if (inc.response_action.action_type === "UFW_BLOCK" && inc.response_action.is_active) {
      el.btnUnblockTarget.style.display = "inline-flex";
      el.btnUnblockTarget.onclick = () => unblockIp(inc.response_action.target_ip);
    } else {
      el.btnUnblockTarget.style.display = "none";
    }
  } else {
    el.wbRespAction.innerText = "NONE";
    el.wbRespIp.innerText = "--";
    el.wbRespStatus.innerText = "SKIPPED";
    el.wbRespRule.innerText = "NO_ACTION";
    el.wbRespTtl.innerText = "--";
    el.btnUnblockTarget.style.display = "none";
  }

  // Raw Log
  el.wbRawLog.innerText = inc.alert.raw_log || JSON.stringify(inc.alert, null, 2);

  // Setup report export
  el.btnExportReport.onclick = () => {
    window.open(`/api/incidents/${id}/report?format=markdown`, "_blank");
  };
}

// Attack Simulations
async function triggerWorkflow(type) {
  showToast(`🚀 Triggering Workflow ${type}...`);
  try {
    const res = await fetch(`/api/simulate/${type}`, { method: "POST" });
    const data = await res.json();
    if (data.status === "success") {
      showToast(`✅ Workflow ${type} successfully generated!`);
      await loadStats();
      await loadIncidents();
    } else {
      showToast(`❌ Simulation error: ${data.detail || "Failed"}`);
    }
  } catch (err) {
    showToast(`❌ Connection error during simulation`);
  }
}

// Firewall Management
async function loadActiveFirewallBlocks() {
  try {
    const res = await fetch("/api/firewall/blocks");
    const blocks = await res.json();
    el.headerBlockCount.innerText = blocks.length;
    el.kpiBlocks.innerText = blocks.length;

    if (blocks.length === 0) {
      el.firewallTbody.innerHTML = `<tr><td colspan="5" style="text-align:center; color:var(--text-muted);">No active firewall blocks.</td></tr>`;
      return;
    }

    el.firewallTbody.innerHTML = blocks.map(b => `
      <tr>
        <td><strong>${b.target_ip}</strong></td>
        <td><span style="color:var(--accent-emerald); font-weight:700;">${b.status}</span></td>
        <td style="font-size:0.75rem; color:var(--text-muted);">${escapeHtml(b.reason)}</td>
        <td style="font-family:var(--font-mono);">${b.ttl_seconds}s</td>
        <td>
          <button class="btn-action" style="padding:4px 8px; font-size:0.7rem; color:var(--accent-amber); border-color:var(--accent-amber);" onclick="unblockIp('${b.target_ip}')">Unblock</button>
        </td>
      </tr>
    `).join("");
  } catch (e) {
    console.error("Failed to load firewall blocks", e);
  }
}

async function unblockIp(ip) {
  if (!ip) return;
  try {
    const res = await fetch("/api/firewall/unblock", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ ip })
    });
    const data = await res.json();
    if (data.status === "success") {
      showToast(`🔓 Successfully unblocked IP: ${ip}`);
      await loadStats();
      await loadActiveFirewallBlocks();
      if (selectedIncidentId) selectIncident(selectedIncidentId);
    }
  } catch (err) {
    showToast(`❌ Failed to unblock IP`);
  }
}

async function manualBlockIp() {
  const ipInput = document.getElementById("manual-block-ip");
  const ip = ipInput.value.trim();
  if (!ip) return;

  try {
    const res = await fetch("/api/firewall/block", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ ip, reason: "Manual Analyst Containment" })
    });
    const data = await res.json();
    if (data.status === "success") {
      showToast(`🔥 Quarantined IP: ${ip}`);
      ipInput.value = "";
      await loadStats();
      await loadActiveFirewallBlocks();
    }
  } catch (e) {
    showToast(`❌ Failed to block IP`);
  }
}

// Load Viva Q&A
async function loadVivaQA() {
  try {
    const res = await fetch("/api/viva-qa");
    const qaList = await res.json();
    el.vivaList.innerHTML = qaList.map((item, idx) => `
      <div class="viva-card">
        <div class="viva-q">
          <span>Q${idx + 1}.</span> ${escapeHtml(item.question)}
        </div>
        <div class="viva-a">${escapeHtml(item.answer)}</div>
      </div>
    `).join("");
  } catch (e) {
    el.vivaList.innerHTML = `<div style="color:var(--text-muted);">Failed to load Viva questions.</div>`;
  }
}

// Event Listeners
function setupEventListeners() {
  // Simulator buttons
  document.getElementById("btn-sim-a").addEventListener("click", () => triggerWorkflow("A"));
  document.getElementById("btn-sim-b").addEventListener("click", () => triggerWorkflow("B"));
  document.getElementById("btn-sim-c").addEventListener("click", () => triggerWorkflow("C"));
  document.getElementById("btn-sim-d").addEventListener("click", () => triggerWorkflow("D"));
  document.getElementById("btn-refresh-feed").addEventListener("click", () => {
    loadStats();
    loadIncidents();
  });

  // Filter & Search
  el.feedSearch.addEventListener("input", debounce(loadIncidents, 300));
  el.feedSeverity.addEventListener("change", loadIncidents);

  // Modals Open/Close
  document.getElementById("btn-open-viva").addEventListener("click", () => {
    loadVivaQA();
    el.modalViva.classList.add("open");
  });
  document.getElementById("btn-close-viva").addEventListener("click", () => {
    el.modalViva.classList.remove("open");
  });

  document.getElementById("btn-open-ingest").addEventListener("click", () => {
    el.modalIngest.classList.add("open");
  });
  document.getElementById("btn-close-ingest").addEventListener("click", () => {
    el.modalIngest.classList.remove("open");
  });

  document.getElementById("btn-firewall-manager").addEventListener("click", () => {
    loadActiveFirewallBlocks();
    el.modalFirewall.classList.add("open");
  });
  document.getElementById("btn-close-firewall").addEventListener("click", () => {
    el.modalFirewall.classList.remove("open");
  });

  document.getElementById("btn-manual-block-submit").addEventListener("click", manualBlockIp);

  // Ingest sample
  document.getElementById("btn-submit-sample-auth").addEventListener("click", () => {
    document.getElementById("ingest-textarea").value = 
      "Oct 15 00:30:14 ubuntu-endpoint sshd[28419]: Failed password for invalid user root from 198.51.100.42 port 49152 ssh2";
  });

  document.getElementById("btn-submit-ingest").addEventListener("click", async () => {
    const raw = document.getElementById("ingest-textarea").value.trim();
    if (!raw) return;
    try {
      const res = await fetch("/api/ingest", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ raw_event: raw })
      });
      const data = await res.json();
      if (data.status === "success") {
        showToast("✅ Event ingested successfully!");
        el.modalIngest.classList.remove("open");
        document.getElementById("ingest-textarea").value = "";
        await loadStats();
        await loadIncidents();
        if (data.incident) selectIncident(data.incident.incident_id);
      }
    } catch (e) {
      showToast("❌ Failed to ingest event");
    }
  });
}

// Helpers
function getSeverityColor(sev) {
  switch (sev) {
    case "CRITICAL": return "var(--accent-crimson)";
    case "HIGH": return "var(--accent-amber)";
    case "MEDIUM": return "var(--accent-blue)";
    default: return "var(--accent-emerald)";
  }
}

function showToast(msg) {
  const toast = document.createElement("div");
  toast.className = "toast";
  toast.innerText = msg;
  el.toastContainer.appendChild(toast);
  setTimeout(() => {
    toast.remove();
  }, 4000);
}

function formatTimestamp(ts) {
  try {
    const d = new Date(ts);
    return d.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit', second: '2-digit' });
  } catch (e) {
    return String(ts);
  }
}

function escapeHtml(str) {
  if (!str) return "";
  return String(str)
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;")
    .replace(/'/g, "&#039;");
}

function debounce(func, wait) {
  let timeout;
  return function executedFunction(...args) {
    const later = () => {
      clearTimeout(timeout);
      func(...args);
    };
    clearTimeout(timeout);
    timeout = setTimeout(later, wait);
  };
}

/**
 * ResQAI Call-Center Operations Dashboard Controller
 * Real-time queue, KPI metrics, dispatch assignments, and AI drawer.
 */

let currentSelectedCaseId = null;

document.addEventListener("DOMContentLoaded", () => {
    initDashboard();
    setInterval(refreshDashboardStats, 5000);
    setInterval(refreshEmergencyQueue, 5000);
});

async function initDashboard() {
    refreshDashboardStats();
    setupFilters();
}

async function refreshDashboardStats() {
    try {
        const resp = await fetch("/api/stats");
        const json = await resp.json();
        if (!json.success) return;
        const d = json.data;

        updateStatEl("statTotalActive", d.total_active);
        updateStatEl("statCriticalActive", d.critical_active);
        updateStatEl("statAwaitingAck", d.awaiting_ack);
        updateStatEl("statAvailableEmployees", `${d.available_employees} / ${d.total_employees}`);
        updateStatEl("statAvgResponse", `${d.avg_response_seconds}s`);
    } catch (e) {
        console.debug("Failed refreshing stats:", e);
    }
}

function updateStatEl(id, val) {
    const el = document.getElementById(id);
    if (el) el.textContent = val;
}

function setupFilters() {
    const typeFilter = document.getElementById("filterType");
    const priorityFilter = document.getElementById("filterPriority");
    const statusFilter = document.getElementById("filterStatus");
    const searchInput = document.getElementById("searchInput");

    const onFilterChange = () => refreshEmergencyQueue();

    if (typeFilter) typeFilter.addEventListener("change", onFilterChange);
    if (priorityFilter) priorityFilter.addEventListener("change", onFilterChange);
    if (statusFilter) statusFilter.addEventListener("change", onFilterChange);
    if (searchInput) searchInput.addEventListener("input", debounce(onFilterChange, 350));
}

function debounce(func, wait) {
    let timeout;
    return (...args) => {
        clearTimeout(timeout);
        timeout = setTimeout(() => func.apply(this, args), wait);
    };
}

async function refreshEmergencyQueue() {
    const tableBody = document.getElementById("emergencyQueueBody");
    if (!tableBody) return;

    const type = document.getElementById("filterType")?.value || "ALL";
    const priority = document.getElementById("filterPriority")?.value || "ALL";
    const status = document.getElementById("filterStatus")?.value || "ALL";
    const search = document.getElementById("searchInput")?.value || "";

    const params = new URLSearchParams();
    if (type !== "ALL") params.append("emergency_type", type);
    if (priority !== "ALL") params.append("priority", priority);
    if (status !== "ALL") params.append("status", status);
    if (search.trim()) params.append("search", search.trim());

    try {
        const resp = await fetch(`/api/cases?${params.toString()}`);
        const json = await resp.json();
        if (!json.success) return;

        renderQueueTable(json.data);
    } catch (e) {
        console.debug("Queue refresh error:", e);
    }
}

function renderQueueTable(cases) {
    const tbody = document.getElementById("emergencyQueueBody");
    if (!tbody) return;

    if (cases.length === 0) {
        tbody.innerHTML = `
            <tr>
                <td colspan="8" class="text-center py-4 text-muted">
                    <i class="fa-solid fa-clipboard-check fs-3 mb-2 d-block"></i>
                    No emergency cases match the selected criteria.
                </td>
            </tr>
        `;
        return;
    }

    const priorityColors = {
        "CRITICAL": "#dc3545",
        "HIGH": "#fd7e14",
        "MEDIUM": "#ffc107",
        "LOW": "#0d6efd"
    };

    let html = "";
    cases.forEach(c => {
        const pColor = priorityColors[c.priority] || "#fd7e14";
        const needsAck = c.requires_buzzer && !c.buzzer_acknowledged;
        const timeAgo = formatTimeAgo(c.created_at);

        html += `
            <tr class="${needsAck ? 'table-danger' : ''}" style="cursor: pointer;" onclick="viewCaseDetails(${c.id})">
                <td class="fw-bold text-nowrap">
                    ${c.case_number}
                    ${needsAck ? '<span class="badge bg-danger ms-1 animate-pulse">BUZZER</span>' : ''}
                </td>
                <td>
                    <span class="badge" style="background-color: ${pColor}; color: ${c.priority === 'MEDIUM' ? '#111' : '#fff'};">
                        ${c.priority}
                    </span>
                </td>
                <td><strong>${escapeHtml(c.emergency_type)}</strong></td>
                <td>
                    <div class="text-truncate" style="max-width: 180px;" title="${escapeHtml(c.location_name)}">
                        <i class="fa-solid fa-location-dot text-danger me-1"></i>${escapeHtml(c.location_name)}
                    </div>
                </td>
                <td>
                    <span class="badge badge-status-${c.status.toLowerCase()}">${c.status}</span>
                </td>
                <td>
                    <small class="fw-semibold">${escapeHtml(c.assigned_employee_name || 'Unassigned')}</small>
                </td>
                <td class="text-muted text-nowrap"><small>${timeAgo}</small></td>
                <td class="text-end text-nowrap" onclick="event.stopPropagation();">
                    ${needsAck ? `
                        <button class="btn btn-sm btn-danger py-0 px-2 me-1" title="Acknowledge Case & Silence Buzzer" onclick="acknowledgeCaseDirect(${c.id})">
                            <i class="fa-solid fa-bell-slash"></i> Ack
                        </button>
                    ` : ''}
                    <button class="btn btn-sm btn-outline-primary py-0 px-2" onclick="viewCaseDetails(${c.id})">
                        <i class="fa-solid fa-eye"></i> Details
                    </button>
                </td>
            </tr>
        `;
    });

    tbody.innerHTML = html;
}

window.viewCaseDetails = async function(caseId) {
    currentSelectedCaseId = caseId;
    const modalEl = document.getElementById("caseDetailsModal");
    if (!modalEl) return;

    try {
        const resp = await fetch(`/api/cases/${caseId}`);
        const res = await resp.json();
        if (!res.success) return;
        const c = res.data;

        document.getElementById("modalCaseId").textContent = c.case_number;
        document.getElementById("modalCaseType").textContent = c.emergency_type;
        document.getElementById("modalCaseLocation").textContent = c.location_name;
        document.getElementById("modalCaseCitizen").textContent = `${c.citizen_name} (${c.citizen_phone})`;
        document.getElementById("modalCaseAffected").textContent = `${c.people_affected} person(s)`;
        document.getElementById("modalCaseDesc").textContent = c.description;
        document.getElementById("modalCaseStatus").textContent = c.status;
        document.getElementById("modalCaseStatus").className = `badge badge-status-${c.status.toLowerCase()}`;
        document.getElementById("modalCaseResponder").textContent = `${c.assigned_employee_name} (${c.assigned_employee_badge || 'N/A'})`;

        // Priority selector setup
        const prioritySelect = document.getElementById("modalPrioritySelect");
        if (prioritySelect) prioritySelect.value = c.priority;

        // Populate AI Box
        const aiContainer = document.getElementById("modalAiAnalysisContent");
        if (c.latest_ai) {
            const ai = c.latest_ai;
            aiContainer.innerHTML = `
                <div class="p-3 bg-light rounded border mb-2">
                    <div class="d-flex justify-content-between align-items-center mb-2">
                        <span class="badge bg-primary"><i class="fa-solid fa-brain me-1"></i> ${ai.is_fallback ? 'Local Emergency Rules Engine' : 'Groq AI (' + ai.model_used + ')'}</span>
                        <small class="text-muted">${ai.is_fallback ? 'Deterministic Fallback' : 'Live Groq LLM'}</small>
                    </div>
                    <p class="mb-2 fw-semibold">${escapeHtml(ai.summary)}</p>
                    
                    <div class="row g-2 mb-2">
                        <div class="col-md-6">
                            <strong class="text-secondary small d-block mb-1">Key Extracted Facts:</strong>
                            <ul class="small ps-3 mb-0">
                                ${(ai.extracted_facts || []).map(f => `<li>${escapeHtml(f)}</li>`).join('')}
                            </ul>
                        </div>
                        <div class="col-md-6">
                            <strong class="text-secondary small d-block mb-1">Recommended Dispatch Units:</strong>
                            <ul class="small ps-3 mb-0">
                                ${(ai.recommended_resources || []).map(r => `<li class="text-primary fw-semibold">${escapeHtml(r)}</li>`).join('')}
                            </ul>
                        </div>
                    </div>

                    ${(ai.missing_information && ai.missing_information.length > 0) ? `
                        <div class="mt-2 pt-2 border-top">
                            <strong class="text-danger small d-block mb-1">Questions Dispatcher Should Verify:</strong>
                            <ul class="small ps-3 mb-0 text-danger">
                                ${ai.missing_information.map(m => `<li>${escapeHtml(m)}</li>`).join('')}
                            </ul>
                        </div>
                    ` : ''}
                </div>
            `;
        } else {
            aiContainer.innerHTML = `<div class="text-muted small">No AI analysis generated yet. Click 'Run AI Analysis' below.</div>`;
        }

        // Timeline History
        const timelineList = document.getElementById("modalStatusHistory");
        if (timelineList) {
            timelineList.innerHTML = (c.status_history || []).map(h => `
                <li class="mb-2">
                    <div class="d-flex justify-content-between">
                        <strong>${escapeHtml(h.action_type)}: ${escapeHtml(h.new_status)}</strong>
                        <small class="text-muted">${formatTimeAgo(h.created_at)}</small>
                    </div>
                    <small class="text-muted d-block">${escapeHtml(h.notes || '')} (By: ${escapeHtml(h.action_by)})</small>
                </li>
            `).join('');
        }

        // Buzzer Ack Button visibility
        const ackBtn = document.getElementById("modalAckBtn");
        if (ackBtn) {
            ackBtn.style.display = (c.requires_buzzer && !c.buzzer_acknowledged) ? "inline-block" : "none";
        }

        // Resolve Button visibility
        const resolveBtn = document.getElementById("modalOpenResolveBtn");
        if (resolveBtn) {
            resolveBtn.style.display = (c.status !== "RESOLVED") ? "inline-block" : "none";
        }

        const modal = new bootstrap.Modal(modalEl);
        modal.show();

        // Also center map if coordinates exist
        if (window.resqMap && c.latitude && c.longitude) {
            window.resqMap.flyToIncident(c.latitude, c.longitude);
        }
    } catch (e) {
        console.error("Error opening case details:", e);
    }
};

window.acknowledgeCaseDirect = async function(caseId) {
    if (window.resqBuzzer) {
        const success = await window.resqBuzzer.acknowledgeCase(caseId, "Operator On-Duty");
        if (success) {
            refreshEmergencyQueue();
            refreshDashboardStats();
            alert("Incident acknowledged! Buzzer silenced.");
        }
    }
};

window.acknowledgeCurrentModalCase = async function() {
    if (currentSelectedCaseId) {
        await acknowledgeCaseDirect(currentSelectedCaseId);
        viewCaseDetails(currentSelectedCaseId);
    }
};

window.triggerRerunAI = async function() {
    if (!currentSelectedCaseId) return;
    const btn = document.getElementById("modalRerunAiBtn");
    const orig = btn.innerHTML;
    btn.disabled = true;
    btn.innerHTML = '<span class="spinner-border spinner-border-sm me-1"></span> Analyzing...';

    try {
        const resp = await fetch(`/api/cases/${currentSelectedCaseId}/ai-analyze`, { method: "POST" });
        const res = await resp.json();
        if (res.success) {
            viewCaseDetails(currentSelectedCaseId);
        } else {
            alert("AI Analysis Error: " + res.error);
        }
    } catch (e) {
        alert("Error requesting AI analysis: " + e.message);
    } finally {
        btn.disabled = false;
        btn.innerHTML = orig;
    }
};

window.updateCasePriority = async function() {
    if (!currentSelectedCaseId) return;
    const newPri = document.getElementById("modalPrioritySelect").value;
    try {
        const resp = await fetch(`/api/cases/${currentSelectedCaseId}/priority`, {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ priority: newPri, operator_name: "Dispatcher Manual Review" })
        });
        const res = await resp.json();
        if (res.success) {
            alert("Priority updated to " + newPri);
            refreshEmergencyQueue();
            refreshDashboardStats();
        }
    } catch (e) {
        alert("Error updating priority: " + e.message);
    }
};

window.openReassignModal = async function() {
    if (!currentSelectedCaseId) return;
    const empSelect = document.getElementById("reassignEmployeeSelect");
    if (!empSelect) return;

    try {
        const resp = await fetch("/api/employees");
        const json = await resp.json();
        if (json.success) {
            empSelect.innerHTML = json.data.map(e => `
                <option value="${e.id}">${e.name} (${e.badge_id}) — Status: ${e.status} (Active: ${e.current_active_cases})</option>
            `).join('');
            const modal = new bootstrap.Modal(document.getElementById("reassignModal"));
            modal.show();
        }
    } catch (e) {
        console.error("Error loading employees:", e);
    }
};

window.confirmReassignment = async function() {
    if (!currentSelectedCaseId) return;
    const empId = document.getElementById("reassignEmployeeSelect").value;
    try {
        const resp = await fetch(`/api/cases/${currentSelectedCaseId}/assign`, {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ employee_id: empId, operator_name: "Supervisor Dispatcher" })
        });
        const res = await resp.json();
        if (res.success) {
            bootstrap.Modal.getInstance(document.getElementById("reassignModal"))?.hide();
            viewCaseDetails(currentSelectedCaseId);
            refreshEmergencyQueue();
            refreshDashboardStats();
            alert("Case reassigned successfully.");
        } else {
            alert("Reassignment error: " + res.error);
        }
    } catch (e) {
        alert("Error reassigning: " + e.message);
    }
};

window.openResolveModal = function() {
    const modal = new bootstrap.Modal(document.getElementById("resolveCaseModal"));
    modal.show();
};

window.confirmResolution = async function() {
    if (!currentSelectedCaseId) return;
    const notes = document.getElementById("resolveNotesInput").value.trim();
    if (!notes) {
        alert("Please enter resolution summary notes.");
        return;
    }

    try {
        const resp = await fetch(`/api/cases/${currentSelectedCaseId}/resolve`, {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ resolution_notes: notes, operator_name: "Call-Center Lead" })
        });
        const res = await resp.json();
        if (res.success) {
            bootstrap.Modal.getInstance(document.getElementById("resolveCaseModal"))?.hide();
            viewCaseDetails(currentSelectedCaseId);
            refreshEmergencyQueue();
            refreshDashboardStats();
            alert("Emergency case successfully marked as RESOLVED.");
        } else {
            alert("Resolution failed: " + res.error);
        }
    } catch (e) {
        alert("Error resolving case: " + e.message);
    }
};

window.checkRoutingTimeouts = async function() {
    try {
        const resp = await fetch("/api/routing/check-timeouts", { method: "POST" });
        const res = await resp.json();
        alert(`Timeout Watchdog Executed.\nProcessed: ${res.processed} unacknowledged assignments.`);
        refreshEmergencyQueue();
        refreshDashboardStats();
    } catch (e) {
        alert("Timeout check failed: " + e.message);
    }
};

function formatTimeAgo(isoDate) {
    if (!isoDate) return "N/A";
    const diffSec = Math.floor((new Date() - new Date(isoDate)) / 1000);
    if (diffSec < 60) return `${diffSec}s ago`;
    if (diffSec < 3600) return `${Math.floor(diffSec / 60)}m ago`;
    return `${Math.floor(diffSec / 3600)}h ago`;
}

function escapeHtml(str) {
    if (!str) return "";
    return String(str).replace(/[&<>"']/g, m => ({
        '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;'
    })[m]);
}

/**
 * ResQAI Citizen Safety Portal Controller
 * Mobile-first emergency report submission, GPS locating, and live case tracking.
 */

document.addEventListener("DOMContentLoaded", () => {
    const reportForm = document.getElementById("emergencyReportForm");
    const gpsBtn = document.getElementById("useGpsBtn");
    const locationSelect = document.getElementById("sampleLocationSelect");
    const locationInput = document.getElementById("locationNameInput");
    const latInput = document.getElementById("latitudeInput");
    const lngInput = document.getElementById("longitudeInput");
    const caseTrackingCard = document.getElementById("caseTrackingCard");

    // Location selection dropdown handler
    if (locationSelect) {
        locationSelect.addEventListener("change", (e) => {
            const selectedOpt = e.target.selectedOptions[0];
            if (selectedOpt && selectedOpt.value) {
                locationInput.value = selectedOpt.value;
                latInput.value = selectedOpt.dataset.lat || "";
                lngInput.value = selectedOpt.dataset.lng || "";
                fetchLiveWeatherTelemetry(selectedOpt.dataset.lat, selectedOpt.dataset.lng);
            }
        });
    }

    // Geolocation API (User Permission Only)
    if (gpsBtn) {
        gpsBtn.addEventListener("click", () => {
            if (!navigator.geolocation) {
                alert("Geolocation is not supported by your browser.");
                return;
            }

            gpsBtn.innerHTML = '<span class="spinner-border spinner-border-sm me-1"></span> Locating...';
            gpsBtn.disabled = true;

            navigator.geolocation.getCurrentPosition(
                (pos) => {
                    const lat = pos.coords.latitude.toFixed(4);
                    const lng = pos.coords.longitude.toFixed(4);
                    latInput.value = lat;
                    lngInput.value = lng;
                    locationInput.value = `GPS: [${lat}, ${lng}] (Current Location)`;
                    gpsBtn.innerHTML = '<i class="fa-solid fa-location-crosshairs text-success me-1"></i> GPS Locked';
                    gpsBtn.disabled = false;
                    fetchLiveWeatherTelemetry(lat, lng);
                },
                (err) => {
                    gpsBtn.innerHTML = '<i class="fa-solid fa-location-crosshairs me-1"></i> Use My GPS';
                    gpsBtn.disabled = false;
                    alert("Location access denied or unavailable: " + err.message);
                },
                { enableHighAccuracy: true, timeout: 8000 }
            );
        });
    }

    // Emergency report form submission
    if (reportForm) {
        reportForm.addEventListener("submit", async (e) => {
            e.preventDefault();

            const submitBtn = document.getElementById("submitSosBtn");
            const originalBtnHtml = submitBtn.innerHTML;
            submitBtn.disabled = true;
            submitBtn.innerHTML = '<span class="spinner-border spinner-border-sm me-2"></span> Transmitting SOS...';

            const formData = new FormData(reportForm);

            try {
                const response = await fetch("/api/cases", {
                    method: "POST",
                    body: formData
                });

                const result = await response.json();

                if (result.success) {
                    reportForm.reset();
                    const newCase = result.data;
                    localStorage.setItem("resq_active_case_id", newCase.id);
                    startCaseTracking(newCase.id);
                    
                    // Show confirmation
                    const alertModal = document.getElementById("emergencySubmittedModal");
                    if (alertModal && window.bootstrap) {
                        const modal = new bootstrap.Modal(alertModal);
                        document.getElementById("modalCaseNumber").textContent = newCase.case_number;
                        modal.show();
                    } else {
                        alert(`Emergency Case Registered!\nCase ID: ${newCase.case_number}\nAssigned Responders: ${newCase.assigned_employee_name}`);
                    }
                } else {
                    alert("Error submitting request: " + (result.error || "Unknown error"));
                }
            } catch (err) {
                console.error("SOS submission failure:", err);
                alert("Network error. Please call emergency services directly.");
            } finally {
                submitBtn.disabled = false;
                submitBtn.innerHTML = originalBtnHtml;
            }
        });
    }

    // Check existing tracked case on page load
    const savedCaseId = localStorage.getItem("resq_active_case_id");
    if (savedCaseId) {
        startCaseTracking(savedCaseId);
    }

    // Weather Simulation trigger buttons
    window.triggerWeatherSimulation = async (type) => {
        const locName = locationInput ? locationInput.value || "JNTU Anantapur Campus" : "JNTU Anantapur Campus";
        const lat = latInput ? latInput.value || 14.6548 : 14.6548;
        const lng = lngInput ? lngInput.value || 77.6074 : 77.6074;

        try {
            const resp = await fetch("/api/alerts/simulate", {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({
                    template_key: type,
                    location_name: locName,
                    latitude: parseFloat(lat),
                    longitude: parseFloat(lng)
                })
            });
            const data = await resp.json();
            if (data.success) {
                alert(data.message);
                window.location.reload();
            } else {
                alert("Simulation failed: " + data.error);
            }
        } catch (e) {
            console.error("Failed to trigger simulation:", e);
        }
    };
});

let trackingInterval = null;

async function startCaseTracking(caseId) {
    const trackingCard = document.getElementById("caseTrackingCard");
    if (!trackingCard) return;

    trackingCard.classList.remove("d-none");

    const pollCaseStatus = async () => {
        try {
            const resp = await fetch(`/api/cases/${caseId}`);
            if (!resp.ok) return;
            const res = await resp.json();
            if (!res.success) return;

            const c = res.data;
            document.getElementById("trackCaseNum").textContent = c.case_number;
            document.getElementById("trackCaseType").textContent = c.emergency_type;
            document.getElementById("trackLocation").textContent = c.location_name;
            document.getElementById("trackResponder").textContent = c.assigned_employee_name || "Assigning responder...";
            document.getElementById("trackBadge").textContent = c.assigned_employee_badge || "—";
            
            const statusBadge = document.getElementById("trackStatusBadge");
            if (statusBadge) {
                statusBadge.textContent = c.status;
                statusBadge.className = `badge badge-status-${c.status.toLowerCase()}`;
            }

            const notesEl = document.getElementById("trackResolutionNotes");
            if (c.status === "RESOLVED" && c.resolution_notes) {
                notesEl.textContent = `Resolution Summary: ${c.resolution_notes}`;
                notesEl.classList.remove("d-none");
            }

            // If resolved, stop tracking interval after a while
            if (c.status === "RESOLVED" && trackingInterval) {
                clearInterval(trackingInterval);
                trackingInterval = null;
            }
        } catch (e) {
            console.error("Tracking poll error:", e);
        }
    };

    pollCaseStatus();
    if (trackingInterval) clearInterval(trackingInterval);
    trackingInterval = setInterval(pollCaseStatus, 4000);
}

async function fetchLiveWeatherTelemetry(lat, lng) {
    const weatherBox = document.getElementById("liveWeatherWidget");
    if (!weatherBox || !lat || !lng) return;

    try {
        const resp = await fetch(`/api/weather/live?lat=${lat}&lng=${lng}`);
        const data = await resp.json();
        if (data.success && data.data.available) {
            const w = data.data;
            weatherBox.innerHTML = `
                <div class="d-flex align-items-center justify-content-between p-2 rounded bg-light border">
                    <div>
                        <div class="fw-bold" style="font-size:0.85rem;"><i class="fa-solid fa-cloud-sun-rain me-1 text-primary"></i> Local Ambient Weather</div>
                        <small class="text-muted">${w.provider}</small>
                    </div>
                    <div class="text-end">
                        <span class="fs-5 fw-bold text-dark">${w.temperature}°C</span>
                        <div style="font-size:0.75rem;" class="text-muted">Wind: ${w.wind_speed} km/h | Rain: ${w.rain || 0} mm</div>
                    </div>
                </div>
            `;
            weatherBox.classList.remove("d-none");
        }
    } catch (e) {
        console.debug("Could not fetch live weather:", e);
    }
}

/**
 * ResQAI Leaflet GIS Emergency Incident Map
 * Plots active incidents with priority color markers, popups, and offline fallback.
 */

class EmergencyMap {
    constructor(elementId = "emergencyMap") {
        this.elementId = elementId;
        this.map = null;
        this.markers = [];
        this.priorityColors = {
            "CRITICAL": "#dc3545",
            "HIGH": "#fd7e14",
            "MEDIUM": "#ffc107",
            "LOW": "#0d6efd"
        };
        this.init();
    }

    init() {
        const container = document.getElementById(this.elementId);
        if (!container) return;

        // Default center: Anantapur / Andhra Pradesh regional view
        this.map = L.map(this.elementId).setView([14.6819, 77.6006], 7);

        // OpenStreetMap Tile Layer
        const tileLayer = L.tileLayer("https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png", {
            maxZoom: 19,
            attribution: '&copy; <a href="https://openstreetmap.org/copyright">OpenStreetMap</a> contributors'
        }).addTo(this.map);

        tileLayer.on("tileerror", () => {
            const fallbackBadge = document.getElementById("mapFallbackBadge");
            if (fallbackBadge) fallbackBadge.classList.remove("d-none");
        });

        this.loadMarkers();
    }

    createMarkerIcon(priority) {
        const color = this.priorityColors[priority] || "#fd7e14";
        const svgIcon = `
            <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" width="32" height="32">
                <path fill="${color}" stroke="#ffffff" stroke-width="2" d="M12 2C8.13 2 5 5.13 5 9c0 5.25 7 13 7 13s7-7.75 7-13c0-3.87-3.13-7-7-7z"/>
                <circle cx="12" cy="9" r="3.5" fill="#ffffff"/>
            </svg>
        `;
        return L.divIcon({
            html: svgIcon,
            className: "emergency-pin-marker",
            iconSize: [32, 32],
            iconAnchor: [16, 32],
            popupAnchor: [0, -30]
        });
    }

    async loadMarkers() {
        if (!this.map) return;
        try {
            const resp = await fetch("/api/cases");
            const result = await resp.json();
            if (!result.success) return;

            // Clear old markers
            this.markers.forEach(m => this.map.removeLayer(m));
            this.markers = [];

            const bounds = [];

            result.data.forEach(item => {
                if (item.latitude && item.longitude) {
                    const lat = parseFloat(item.latitude);
                    const lng = parseFloat(item.longitude);
                    bounds.push([lat, lng]);

                    const icon = this.createMarkerIcon(item.priority);
                    const marker = L.marker([lat, lng], { icon: icon }).addTo(this.map);

                    const popupContent = `
                        <div style="min-width: 220px; font-family: sans-serif;">
                            <div class="d-flex justify-content-between align-items-center mb-1">
                                <span class="badge" style="background:${this.priorityColors[item.priority]}; color:#fff;">${item.priority}</span>
                                <small class="text-muted">${item.status}</small>
                            </div>
                            <strong style="font-size: 0.95rem;">${item.case_number}</strong>
                            <div style="font-size: 0.85rem; color: #334155; margin-top: 4px;">${item.emergency_type}</div>
                            <div style="font-size: 0.8rem; color: #64748b;"><i class="fa-solid fa-location-dot me-1"></i>${item.location_name}</div>
                            <div style="font-size: 0.8rem; margin-top: 6px; border-top: 1px solid #eee; padding-top: 4px;">
                                <strong>Responder:</strong> ${item.assigned_employee_name}
                            </div>
                            <div class="mt-2 text-end">
                                <button class="btn btn-sm btn-primary py-0 px-2" onclick="window.viewCaseDetails(${item.id})">Open Details</button>
                            </div>
                        </div>
                    `;
                    marker.bindPopup(popupContent);
                    this.markers.push(marker);
                }
            });

            if (bounds.length > 0) {
                this.map.fitBounds(bounds, { padding: [50, 50], maxZoom: 12 });
            }
        } catch (e) {
            console.error("Failed to load map markers:", e);
        }
    }

    flyToIncident(lat, lng) {
        if (this.map && lat && lng) {
            this.map.flyTo([lat, lng], 14, { duration: 1.5 });
        }
    }
}

// Global initialization
window.addEventListener("DOMContentLoaded", () => {
    if (document.getElementById("emergencyMap")) {
        window.resqMap = new EmergencyMap("emergencyMap");
    }
});

/**
 * ResQAI Webcam & Video Module
 * Explicit consent employee preview and simulated citizen live feed.
 */

class EmergencyVideoManager {
    constructor() {
        this.localStream = null;
        this.videoElement = document.getElementById("operatorWebcam");
        this.startBtn = document.getElementById("startCameraBtn");
        this.stopBtn = document.getElementById("stopCameraBtn");
        this.cameraBadge = document.getElementById("cameraStatusBadge");
        this.victimCanvas = document.getElementById("simulatedVictimCanvas");

        this.init();
    }

    init() {
        if (this.startBtn) {
            this.startBtn.addEventListener("click", () => this.startCamera());
        }
        if (this.stopBtn) {
            this.stopBtn.addEventListener("click", () => this.stopCamera());
        }

        // Initialize simulated victim video stream canvas
        if (this.victimCanvas) {
            this.initSimulatedVictimStream();
        }
    }

    async startCamera() {
        try {
            if (!navigator.mediaDevices || !navigator.mediaDevices.getUserMedia) {
                alert("Camera access is not supported by your browser or environment.");
                return;
            }

            // Explicit permission request
            this.localStream = await navigator.mediaDevices.getUserMedia({
                video: { width: { ideal: 640 }, height: { ideal: 480 }, facingMode: "user" },
                audio: false
            });

            if (this.videoElement) {
                this.videoElement.srcObject = this.localStream;
                this.videoElement.classList.remove("d-none");
            }

            const placeholder = document.getElementById("operatorCameraPlaceholder");
            if (placeholder) placeholder.classList.add("d-none");

            if (this.startBtn) this.startBtn.classList.add("d-none");
            if (this.stopBtn) this.stopBtn.classList.remove("d-none");

            if (this.cameraBadge) {
                this.cameraBadge.innerHTML = '<span class="badge bg-success"><i class="fa-solid fa-circle me-1 text-danger"></i> LIVE ON-AIR</span>';
            }
        } catch (err) {
            console.error("Camera access error:", err);
            let msg = "Could not access camera. ";
            if (err.name === "NotAllowedError" || err.name === "PermissionDeniedError") {
                msg += "Camera permission was denied in your browser settings.";
            } else if (err.name === "NotFoundError" || err.name === "DevicesNotFoundError") {
                msg += "No camera device was detected on your computer.";
            } else {
                msg += err.message;
            }
            alert(msg);
        }
    }

    stopCamera() {
        if (this.localStream) {
            this.localStream.getTracks().forEach(track => track.stop());
            this.localStream = null;
        }

        if (this.videoElement) {
            this.videoElement.srcObject = null;
            this.videoElement.classList.add("d-none");
        }

        const placeholder = document.getElementById("operatorCameraPlaceholder");
        if (placeholder) placeholder.classList.remove("d-none");

        if (this.startBtn) this.startBtn.classList.remove("d-none");
        if (this.stopBtn) this.stopBtn.classList.add("d-none");

        if (this.cameraBadge) {
            this.cameraBadge.innerHTML = '<span class="badge bg-secondary">Offline</span>';
        }
    }

    initSimulatedVictimStream() {
        const ctx = this.victimCanvas.getContext("2d");
        const w = this.victimCanvas.width;
        const h = this.victimCanvas.height;

        let frame = 0;

        const drawSimulatedVictim = () => {
            frame++;
            // Dark surveillance background
            ctx.fillStyle = "#09121d";
            ctx.fillRect(0, 0, w, h);

            // Grid lines
            ctx.strokeStyle = "rgba(56, 189, 248, 0.15)";
            ctx.lineWidth = 1;
            for (let x = 0; x < w; x += 40) {
                ctx.beginPath();
                ctx.moveTo(x, 0);
                ctx.lineTo(x, h);
                ctx.stroke();
            }
            for (let y = 0; y < h; y += 40) {
                ctx.beginPath();
                ctx.moveTo(0, y);
                ctx.lineTo(w, y);
                ctx.stroke();
            }

            // Radar pulse circle
            const pulseRadius = (frame % 80) * 1.5;
            ctx.beginPath();
            ctx.arc(w / 2, h / 2, pulseRadius, 0, 2 * Math.PI);
            ctx.strokeStyle = `rgba(239, 68, 68, ${1 - (pulseRadius / 120)})`;
            ctx.lineWidth = 2;
            ctx.stroke();

            // Animated target box
            ctx.strokeStyle = "#38bdf8";
            ctx.lineWidth = 2;
            const boxSize = 70;
            const bx = (w / 2) - (boxSize / 2) + Math.sin(frame * 0.05) * 15;
            const by = (h / 2) - (boxSize / 2) + Math.cos(frame * 0.04) * 8;
            ctx.strokeRect(bx, by, boxSize, boxSize);

            // Watermark & Telemetry
            ctx.fillStyle = "#ffffff";
            ctx.font = "bold 11px monospace";
            ctx.fillText("[SIMULATED VICTIM STREAM — TEST DRILL ONLY]", 12, 22);

            ctx.fillStyle = "#38bdf8";
            ctx.font = "10px monospace";
            ctx.fillText(`GPS LAT: 14.6819° N  LNG: 77.6006° E`, 12, h - 28);
            ctx.fillText(`STATUS: CONNECTED  ENCRYPTION: AES-256 (WEBRTC READY)`, 12, h - 14);

            requestAnimationFrame(drawSimulatedVictim);
        };

        requestAnimationFrame(drawSimulatedVictim);
    }
}

window.addEventListener("DOMContentLoaded", () => {
    window.resqVideo = new EmergencyVideoManager();
});

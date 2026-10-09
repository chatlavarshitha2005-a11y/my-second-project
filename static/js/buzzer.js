/**
 * ResQAI Audible Emergency Buzzer Module
 * Uses Web Audio API for synthesized emergency alarm sounds.
 * Fully compliant with browser autoplay policies.
 */

class EmergencyBuzzer {
    constructor() {
        this.audioCtx = null;
        this.isPlaying = false;
        this.soundEnabled = localStorage.getItem("resqai_sound_enabled") === "true";
        this.activeBuzzerCases = [];
        this.oscillator = null;
        this.gainNode = null;
        this.intervalId = null;

        this.initUI();
        this.startBuzzerPolling();
    }

    initUI() {
        this.soundToggleBtn = document.getElementById("toggleSoundBtn");
        this.soundStatusBadge = document.getElementById("soundStatusBadge");
        this.buzzerBanner = document.getElementById("buzzerAlertBanner");
        this.buzzerCaseCount = document.getElementById("buzzerCaseCount");

        if (this.soundToggleBtn) {
            this.updateButtonUI();
            this.soundToggleBtn.addEventListener("click", () => this.toggleSound());
        }
    }

    updateButtonUI() {
        if (!this.soundToggleBtn) return;
        if (this.soundEnabled) {
            this.soundToggleBtn.innerHTML = '<i class="fa-solid fa-volume-high me-1"></i> Sound: Active';
            this.soundToggleBtn.classList.remove("btn-outline-danger", "btn-secondary");
            this.soundToggleBtn.classList.add("btn-danger");
            if (this.soundStatusBadge) this.soundStatusBadge.textContent = "Buzzer Ready";
        } else {
            this.soundToggleBtn.innerHTML = '<i class="fa-solid fa-volume-xmark me-1"></i> Enable Sound';
            this.soundToggleBtn.classList.remove("btn-danger");
            this.soundToggleBtn.classList.add("btn-outline-danger");
            if (this.soundStatusBadge) this.soundStatusBadge.textContent = "Audio Muted";
        }
    }

    toggleSound() {
        this.soundEnabled = !this.soundEnabled;
        localStorage.setItem("resqai_sound_enabled", this.soundEnabled);
        this.updateButtonUI();

        if (this.soundEnabled) {
            this.ensureAudioContext();
            this.playTestBeep();
            if (this.activeBuzzerCases.length > 0) {
                this.startAlarm();
            }
        } else {
            this.stopAlarm();
        }
    }

    ensureAudioContext() {
        if (!this.audioCtx) {
            const AudioContext = window.AudioContext || window.webkitAudioContext;
            this.audioCtx = new AudioContext();
        }
        if (this.audioCtx.state === "suspended") {
            this.audioCtx.resume();
        }
    }

    playTestBeep() {
        try {
            this.ensureAudioContext();
            const osc = this.audioCtx.createOscillator();
            const gain = this.audioCtx.createGain();
            osc.type = "sine";
            osc.frequency.setValueAtTime(880, this.audioCtx.currentTime);
            gain.gain.setValueAtTime(0.1, this.audioCtx.currentTime);
            gain.gain.exponentialRampToValueAtTime(0.001, this.audioCtx.currentTime + 0.3);
            osc.connect(gain);
            gain.connect(this.audioCtx.destination);
            osc.start();
            osc.stop(this.audioCtx.currentTime + 0.3);
        } catch (e) {
            console.warn("Could not play test beep:", e);
        }
    }

    startAlarm() {
        if (!this.soundEnabled || this.isPlaying) return;
        this.ensureAudioContext();
        this.isPlaying = true;

        const pulseAlarm = () => {
            if (!this.isPlaying) return;
            try {
                const now = this.audioCtx.currentTime;
                const osc = this.audioCtx.createOscillator();
                const gain = this.audioCtx.createGain();

                osc.type = "sawtooth";
                // Modulating emergency frequency pattern (European / Indian siren tone)
                osc.frequency.setValueAtTime(800, now);
                osc.frequency.linearRampToValueAtTime(1050, now + 0.25);
                osc.frequency.linearRampToValueAtTime(800, now + 0.5);

                gain.gain.setValueAtTime(0.18, now);
                gain.gain.linearRampToValueAtTime(0.01, now + 0.5);

                osc.connect(gain);
                gain.connect(this.audioCtx.destination);

                osc.start(now);
                osc.stop(now + 0.5);
            } catch (err) {
                console.error("Buzzer playback error:", err);
            }
        };

        pulseAlarm();
        this.intervalId = setInterval(pulseAlarm, 750);
    }

    stopAlarm() {
        this.isPlaying = false;
        if (this.intervalId) {
            clearInterval(this.intervalId);
            this.intervalId = null;
        }
    }

    async startBuzzerPolling() {
        const poll = async () => {
            try {
                const resp = await fetch("/api/buzzer/active");
                if (resp.ok) {
                    const data = await resp.json();
                    this.activeBuzzerCases = data.data || [];
                    this.handleBuzzerState(this.activeBuzzerCases);
                }
            } catch (err) {
                console.debug("Buzzer polling error:", err);
            }
        };

        // Poll immediately and then every 4 seconds
        poll();
        setInterval(poll, 4000);
    }

    handleBuzzerState(activeCases) {
        if (activeCases.length > 0) {
            if (this.buzzerBanner) {
                this.buzzerBanner.classList.remove("d-none");
                if (this.buzzerCaseCount) {
                    this.buzzerCaseCount.textContent = activeCases.length;
                }
            }

            if (this.soundEnabled) {
                this.startAlarm();
            }
        } else {
            if (this.buzzerBanner) {
                this.buzzerBanner.classList.add("d-none");
            }
            this.stopAlarm();
        }
    }

    async acknowledgeCase(caseId, responderName = "Operator") {
        try {
            const resp = await fetch(`/api/cases/${caseId}/acknowledge`, {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({ responder_name: responderName })
            });
            const data = await resp.json();
            if (data.success) {
                // Remove from local active list
                this.activeBuzzerCases = this.activeBuzzerCases.filter(c => c.id !== caseId);
                this.handleBuzzerState(this.activeBuzzerCases);
                return true;
            }
            return false;
        } catch (e) {
            console.error("Failed to acknowledge case:", e);
            return false;
        }
    }
}

// Global instance
window.resqBuzzer = new EmergencyBuzzer();

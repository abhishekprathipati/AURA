// AURA Voice Commands - "Hey AURA" Wake Word System
class AURAVoiceCommands {
    constructor() {
        this.recognition = null;
        this.isListening = false;
        this.wakeWordActive = false;
        this.commands = {
            'mood': ['mood', 'feeling', 'emotion'],
            'stress': ['stress', 'stressed', 'anxious'],
            'relax': ['relax', 'calm', 'breathe', 'meditation'],
            'study': ['study', 'learn', 'help'],
            'chat': ['talk', 'chat', 'speak']
        };
    }

    init() {
        // Check browser support
        const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;
        
        if (!SpeechRecognition) {
            console.warn('[Voice] Speech recognition not supported');
            return false;
        }

        this.recognition = new SpeechRecognition();
        this.recognition.continuous = true;
        this.recognition.interimResults = false;
        this.recognition.lang = 'en-US';

        this.recognition.onstart = () => {
            console.log('[Voice] Listening...');
            this.isListening = true;
            this.showListeningIndicator();
        };

        this.recognition.onresult = (event) => {
            const last = event.results.length - 1;
            const text = event.results[last][0].transcript.toLowerCase().trim();
            console.log('[Voice] Heard:', text);
            
            this.processCommand(text);
        };

        this.recognition.onerror = (event) => {
            console.error('[Voice] Error:', event.error);
            if (event.error === 'no-speech') {
                // Restart listening
                setTimeout(() => this.start(), 1000);
            }
        };

        this.recognition.onend = () => {
            console.log('[Voice] Stopped');
            this.isListening = false;
            this.hideListeningIndicator();
            
            // Auto-restart if wake word was active
            if (this.wakeWordActive) {
                setTimeout(() => this.start(), 500);
            }
        };

        return true;
    }

    start() {
        if (!this.recognition) {
            const initialized = this.init();
            if (!initialized) return;
        }

        try {
            this.recognition.start();
            this.wakeWordActive = true;
        } catch (e) {
            console.warn('[Voice] Already listening');
        }
    }

    stop() {
        if (this.recognition) {
            this.recognition.stop();
            this.wakeWordActive = false;
        }
    }

    processCommand(text) {
        // Check for wake word
        if (text.includes('hey aura') || text.includes('hey ora') || text.includes('ok aura')) {
            this.speak('Yes, how can I help?');
            this.highlightWakeWord();
            return;
        }

        // Only process commands after wake word detected recently
        if (!this.wakeWordActive && !text.includes('aura')) {
            return;
        }

        // Mood logging feature removed

        // Navigate to relaxation
        else if (this.matchesCommand(text, this.commands.relax)) {
            this.speak('Taking you to the relaxation zone');
            window.location.href = '/student/relax';
        }

        // Navigate to study assistant
        else if (this.matchesCommand(text, this.commands.study)) {
            this.speak('Opening study assistant');
            window.location.href = '/student/chat/study';
        }

        // Navigate to chat
        else if (this.matchesCommand(text, this.commands.chat)) {
            this.speak('Opening mental wellness chat');
            window.location.href = '/student/chat/mental';
        }

        // Check stress
        else if (this.matchesCommand(text, this.commands.stress)) {
            this.speak('Let me check your stress level');
            this.checkStress();
        }

        // Help command
        else if (text.includes('help') || text.includes('what can you do')) {
            this.speak('You can ask me to: log your mood, relax, start studying, chat, or check stress');
        }
    }

    matchesCommand(text, keywords) {
        return keywords.some(keyword => text.includes(keyword));
    }

    speak(message) {
        const utterance = new SpeechSynthesisUtterance(message);
        utterance.rate = 1.0;
        utterance.pitch = 1.0;
        utterance.volume = 0.8;
        speechSynthesis.speak(utterance);
    }

    async checkStress() {
        try {
            const response = await fetch('/student/api/stress/today');
            const data = await response.json();
            const stress = data.score || 50;
            
            if (stress < 40) {
                this.speak(`Your stress is low at ${stress} out of 100. Great job!`);
            } else if (stress < 70) {
                this.speak(`Your stress is moderate at ${stress} out of 100. Consider taking a break.`);
            } else {
                this.speak(`Your stress is high at ${stress} out of 100. I recommend the relaxation zone.`);
                setTimeout(() => {
                    if (confirm('Would you like to go to the relaxation zone?')) {
                        window.location.href = '/student/relax';
                    }
                }, 2000);
            }
        } catch (err) {
            this.speak('Sorry, I could not check your stress level');
        }
    }

    showListeningIndicator() {
        let indicator = document.getElementById('voice-indicator');
        
        if (!indicator) {
            indicator = document.createElement('div');
            indicator.id = 'voice-indicator';
            indicator.innerHTML = `
                <div class="voice-indicator-content">
                    <div class="voice-wave"></div>
                    <div class="voice-wave"></div>
                    <div class="voice-wave"></div>
                    <span class="voice-text">🎤 Listening...</span>
                </div>
            `;
            document.body.appendChild(indicator);
        }

        indicator.style.display = 'flex';
    }

    hideListeningIndicator() {
        const indicator = document.getElementById('voice-indicator');
        if (indicator) {
            indicator.style.display = 'none';
        }
    }

    highlightWakeWord() {
        const indicator = document.getElementById('voice-indicator');
        if (indicator) {
            indicator.classList.add('wake-word-detected');
            setTimeout(() => {
                indicator.classList.remove('wake-word-detected');
            }, 1000);
        }
    }
}

// Initialize voice commands
const voiceCommands = new AURAVoiceCommands();

// Add toggle button to page
function addVoiceToggle() {
    const toggle = document.createElement('button');
    toggle.id = 'voice-toggle';
    toggle.className = 'voice-toggle-btn';
    toggle.innerHTML = '🎤';
    toggle.title = 'Toggle voice commands (Say "Hey AURA")';
    
    toggle.addEventListener('click', () => {
        if (voiceCommands.wakeWordActive) {
            voiceCommands.stop();
            toggle.innerHTML = '🎤';
            toggle.classList.remove('active');
        } else {
            voiceCommands.start();
            toggle.innerHTML = '🔴';
            toggle.classList.add('active');
        }
    });
    
    document.body.appendChild(toggle);
}

// Add CSS for voice interface
const voiceStyles = document.createElement('style');
voiceStyles.textContent = `
    #voice-indicator {
        position: fixed;
        bottom: 80px;
        right: 20px;
        z-index: 10000;
        display: none;
        background: linear-gradient(135deg, rgba(102, 126, 234, 0.95), rgba(118, 75, 162, 0.95));
        backdrop-filter: blur(10px);
        color: white;
        padding: 1rem 1.5rem;
        border-radius: 50px;
        box-shadow: 0 8px 24px rgba(0, 0, 0, 0.3);
        animation: voicePulse 2s ease-in-out infinite;
    }

    .voice-indicator-content {
        display: flex;
        align-items: center;
        gap: 0.8rem;
    }

    .voice-wave {
        width: 3px;
        height: 20px;
        background: white;
        border-radius: 3px;
        animation: voiceWave 1s ease-in-out infinite;
    }

    .voice-wave:nth-child(2) {
        animation-delay: 0.2s;
    }

    .voice-wave:nth-child(3) {
        animation-delay: 0.4s;
    }

    @keyframes voiceWave {
        0%, 100% { height: 10px; }
        50% { height: 25px; }
    }

    @keyframes voicePulse {
        0%, 100% { box-shadow: 0 8px 24px rgba(0, 0, 0, 0.3); }
        50% { box-shadow: 0 8px 24px rgba(102, 126, 234, 0.6), 0 0 20px rgba(102, 126, 234, 0.4); }
    }

    #voice-indicator.wake-word-detected {
        animation: wakeWordFlash 0.5s ease;
    }

    @keyframes wakeWordFlash {
        0%, 100% { transform: scale(1); }
        50% { transform: scale(1.1); filter: brightness(1.3); }
    }

    .voice-toggle-btn {
        position: fixed;
        bottom: 20px;
        right: 20px;
        width: 60px;
        height: 60px;
        border-radius: 50%;
        border: none;
        background: linear-gradient(135deg, #667eea, #764ba2);
        color: white;
        font-size: 1.5rem;
        cursor: pointer;
        box-shadow: 0 4px 15px rgba(0, 0, 0, 0.3);
        transition: all 0.3s ease;
        z-index: 9999;
    }

    .voice-toggle-btn:hover {
        transform: translateY(-2px);
        box-shadow: 0 6px 20px rgba(0, 0, 0, 0.4);
    }

    .voice-toggle-btn.active {
        background: linear-gradient(135deg, #ff6b6b, #ee5a6f);
        animation: voiceRecordingPulse 1s ease-in-out infinite;
    }

    @keyframes voiceRecordingPulse {
        0%, 100% { box-shadow: 0 4px 15px rgba(255, 107, 107, 0.5); }
        50% { box-shadow: 0 6px 30px rgba(255, 107, 107, 0.8), 0 0 30px rgba(255, 107, 107, 0.5); }
    }
`;
document.head.appendChild(voiceStyles);

// Initialize on page load
if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', addVoiceToggle);
} else {
    addVoiceToggle();
}

// Export for global access
window.AURAVoiceCommands = voiceCommands;

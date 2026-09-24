// 🔥 ADVANCED AUDIO INJECTION FRAMEWORK 🔥
// Real-time mic input → spectrum analysis → data encoding → injection simulation

class AudioInjectionTester {
    constructor() {
        this.audioContext = null;
        this.analyser = null;
        this.microphone = null;
        this.dataArray = null;
        this.isRecording = false;
        this.canvas = null;
        this.injectBuffer = [];
        this.init();
    }
    
    async init() {
        try {
            this.audioContext = new (window.AudioContext || window.webkitAudioContext)({ sampleRate: 44100 });
            this.analyser = this.audioContext.createAnalyser();
            this.analyser.fftSize = 2048;
            this.analyser.smoothingTimeConstant = 0.8;
            
            this.dataArray = new Uint8Array(this.analyser.frequencyBinCount);
            
            // Create visualization
            this.createVisualizer();
            
            // Request mic access
            const stream = await navigator.mediaDevices.getUserMedia({ audio: {
                echoCancellation: false,
                noiseSuppression: false,
                autoGainControl: false,
                sampleRate: 44100
            }});
            
            this.microphone = this.audioContext.createMediaStreamSource(stream);
            this.microphone.connect(this.analyser);
            
            this.startAnalysis();
            console.log('🎤 Audio Injection Tester ACTIVE');
            console.log('📊 Analyzing 0-22kHz spectrum in real-time');
            
        } catch(e) {
            console.error('❌ Mic access denied:', e);
        }
    }
    
    createVisualizer() {
        this.canvas = document.createElement('canvas');
        this.canvas.id = 'audio-injection-vis';
        this.canvas.width = 1200;
        this.canvas.height = 400;
        this.canvas.style.cssText = `
            position:fixed;top:20px;left:20px;z-index:99999;
            background:linear-gradient(135deg,#1a1a2e,#16213e,#0f3460);
            border-radius:25px;padding:20px;box-shadow:0 25px 50px rgba(0,0,0,0.5);
            border:2px solid #533a93;backdrop-filter:blur(20px);
        `;
        document.body.appendChild(this.canvas);
        
        this.canvasCtx = this.canvas.getContext('2d');
        this.drawInterface();
    }
    
    drawInterface() {
        const ctx = this.canvasCtx;
        ctx.fillStyle = 'rgba(0,0,0,0.3)';
        ctx.fillRect(0, 0, this.canvas.width, this.canvas.height);
        
        // Title
        ctx.fillStyle = '#ffffff';
        ctx.font = 'bold 24px -apple-system, sans-serif';
        ctx.textAlign = 'center';
        ctx.fillText('🎵 ADVANCED AUDIO INJECTION TESTER', this.canvas.width/2, 40);
        
        // Status
        ctx.font = '16px monospace';
        ctx.fillStyle = '#4ade80';
        ctx.fillText(`Status: ${this.isRecording ? '🔴 RECORDING' : '⚪ IDLE'}`, this.canvas.width/2, 70);
        
        // Frequency bins
        ctx.strokeStyle = '#3b82f6';
        ctx.lineWidth = 1;
        ctx.beginPath();
        for (let i = 0; i < 100; i++) {
            const x = (i / 100) * this.canvas.width;
            ctx.moveTo(x, this.canvas.height - 50);
            ctx.lineTo(x, this.canvas.height - 40);
        }
        ctx.stroke();
    }
    
    startAnalysis() {
        const loop = () => {
            this.analyser.getByteFrequencyData(this.dataArray);
            this.processSpectrum();
            this.renderSpectrum();
            requestAnimationFrame(loop);
        };
        loop();
    }
    
    processSpectrum() {
        // Detect dominant frequencies (injection candidates)
        let maxFreq = 0, maxAmp = 0;
        for (let i = 0; i < this.dataArray.length; i++) {
            if (this.dataArray[i] > maxAmp) {
                maxAmp = this.dataArray[i];
                maxFreq = (i / this.dataArray.length) * (this.audioContext.sampleRate / 2);
            }
        }
        
        // Detect injection signals (specific freqs > threshold)
        if (maxAmp > 60) {
            this.detectInjection(maxFreq, maxAmp);
        }
    }
    
    detectInjection(freq, amplitude) {
        // Common injection frequencies
        const injectionFreqs = [440, 523, 659, 784, 880, 1047]; // A4-C6 range
        const closest = injectionFreqs.reduce((prev, curr) => 
            Math.abs(curr - freq) < Math.abs(prev - freq) ? curr : prev
        );
        
        if (Math.abs(freq - closest) < 20 && amplitude > 80) {
            const bit = Math.floor((amplitude - 80) / 20) % 2; // Amplitude → bit
            this.injectBuffer.push({ freq: closest, bit, time: Date.now() });
            
            if (this.injectBuffer.length > 32) {
                this.processInjectionData();
            }
        }
    }
    
    processInjectionData() {
        // Decode binary from frequency sequence
        const bits = this.injectBuffer.slice(-32).map(b => b.bit);
        const binary = bits.join('');
        const decimal = parseInt(binary, 2);
        const hex = decimal.toString(16).toUpperCase().padStart(8, '0');
        
        console.log(`💉 INJECTION DETECTED!`);
        console.log(`📡 Freq seq: ${this.injectBuffer.slice(-8).map(b=>b.freq).join(' ')}`);
        console.log(`🔢 Binary: ${binary}`);
        console.log(`🔠 Hex: 0x${hex}`);
        console.log(`📦 Payload: ${this.decodePayload(hex)}`);
        
        this.injectBuffer = []; // Reset buffer
    }
    
    decodePayload(hex) {
        // Simulate payload decoding
        const payloads = {
            'DEADBEEF': '🚨 CRITICAL ALERT',
            'CAFEBABE': '🐙 OCTOPUS MODE',
            'B00B1E5H': '😂 BOOBIES DETECTED',
            '4144414D': '💿 ADAM ADMIN',
            '4B494D49': '🎵 KIMI HACK'
        };
        return payloads[hex.slice(0,8)] || `Data: ${hex}`;
    }
    
    renderSpectrum() {
        const ctx = this.canvasCtx;
        const width = this.canvas.width;
        const height = this.canvas.height - 100;
        const barWidth = (width / this.dataArray.length) * 2.5;
        let x = 0;
        
        ctx.fillStyle = 'rgba(0,0,0,0.2)';
        ctx.fillRect(0, 80, width, height);
        
        for (let i = 0; i < this.dataArray.length; i++) {
            const barHeight = (this.dataArray[i] / 255) * height;
            
            const hue = i / this.dataArray.length * 360;
            ctx.fillStyle = `hsl(${hue}, 80%, ${50 + barHeight/height * 30}%)`;
            ctx.fillRect(x, height - barHeight, barWidth, barHeight);
            
            x += barWidth + 1;
        }
        
        // Draw injection markers
        this.drawInjectionMarkers();
        
        // Draw buffer status
        ctx.fillStyle = 'rgba(255,255,255,0.8)';
        ctx.font = '14px monospace';
        ctx.textAlign = 'right';
        ctx.fillText(`Buffer: ${this.injectBuffer.length}/32`, width - 20, height + 25);
    }
    
    drawInjectionMarkers() {
        const ctx = this.canvasCtx;
        this.injectBuffer.slice(-5).forEach((inj, i) => {
            const x = width * 0.8 + (i * 30);
            ctx.fillStyle = inj.bit ? '#ff6b9d' : '#4ade80';
            ctx.beginPath();
            ctx.arc(x, 60, 8, 0, Math.PI * 2);
            ctx.fill();
            ctx.fillStyle = 'white';
            ctx.font = '12px monospace';
            ctx.textAlign = 'center';
            ctx.textBaseline = 'middle';
            ctx.fillText(inj.bit ? '1' : '0', x, 60);
        });
    }
}

// 🚀 LAUNCH INJECTION TESTER
if (!window.audioInjection) {
    window.audioInjection = new AudioInjectionTester();
    console.log(`
🔥 ADVANCED AUDIO INJECTION TESTER ACTIVE! 🔥

🎤 Mic ON - Analyzing 0-22kHz spectrum
📊 Real-time FFT visualization
💉 Detecting injection frequencies (440-1047Hz)
🔢 Decoding amplitude → binary data
📦 Payload extraction simulation

🎯 INSTRUCTIONS:
1. Play musical notes/sounds near mic
2. Watch for injection markers (green/red circles)  
3. See decoded hex payload in console!

💾 Common injection tones: A4(440Hz), C5(523Hz), E5(659Hz), G5(784Hz)
    `);
}
# Virtual Microphone Bug Bounty Platform

Advanced audio injection and browser security testing framework for bug bounty hunting. Creates virtual microphone environment to test web application audio handling, detect security anomalies, and document findings.

## Features

- **Virtual Microphone Injection**: Spoof audio input to browser applications
- **Browser Trap Setting**: Intercept XHR, Fetch, WebSocket, media API calls
- **Anomaly Detection**: Automated detection of suspicious behavior  
- **Forensic Documentation**: Screenshots, audio evidence, network captures
- **Real-time Dashboard**: WebSocket-based monitoring interface

## Quick Start

```bash
./setup.sh
source venv/bin/activate
python dashboard/app.py
# Open http://localhost:5000
```

## Usage

### Web Dashboard
Access the cyberpunk-themed interface at `http://localhost:5000` to configure and launch tests.

### Programmatic API
```python
from src.core.virtual_mic_controller import BugBountyTestSuite

suite = BugBountyTestSuite()
result = suite.run_test(
    target_url="https://target.example.com",
    payload_path="tests/payloads/test_tone.wav",
    test_name="Audio_Test"
)
suite.generate_report(result)
zip_path = suite.package_evidence(result)
```

## Payload Types

| Payload | Description |
|---------|-------------|
| test_tone | 440Hz reference tone |
| ultrasonic | 19kHz frequency injection |
| silent | Null audio stream |
| malformed | Corrupted WAV header |

## Security Testing

- Web Audio API fingerprinting detection
- getUserMedia permission analysis
- Audio-based XSS vector testing
- Data exfiltration detection
- Cross-channel scripting (XCS) detection

## Evidence Collection

Each test generates:
- `TECHNICAL_REPORT.md`: Detailed analysis
- `test_data.json`: Raw structured data
- `screenshot_*.png`: Visual capture
- `audio_evidence_*.wav`: Audio proof
- `evidence_*.zip`: Complete package

## Architecture

```
virtual_mic_bugbounty/
├── src/core/virtual_mic_controller.py
├── src/audio/payload_generator.py
├── dashboard/app.py
├── tests/payloads/
└── reports/
```

## Ethical Use

For authorized security testing only. Follow responsible disclosure.

## License

MIT License

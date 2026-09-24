#!/usr/bin/env python3
"""Audio Payload Generator"""
import numpy as np
import soundfile as sf
import struct
from pathlib import Path
import json

class AudioPayloadGenerator:
    def __init__(self, output_dir="tests/payloads"):
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.sample_rate = 44100

    def generate_test_tone(self, filename="test_tone.wav", duration=5.0, freq=440):
        t = np.linspace(0, duration, int(self.sample_rate * duration), False)
        tone = np.sin(freq * t * 2 * np.pi)
        tone += 0.5 * np.sin(2 * freq * t * 2 * np.pi)
        tone += 0.25 * np.sin(3 * freq * t * 2 * np.pi)
        tone = tone / np.max(np.abs(tone)) * 0.7
        stereo = np.column_stack((tone, tone))
        path = self.output_dir / filename
        sf.write(str(path), stereo, self.sample_rate)
        return str(path)

    def generate_ultrasonic(self, filename="ultrasonic.wav", duration=3.0, freq=19000):
        t = np.linspace(0, duration, int(self.sample_rate * duration), False)
        tone = np.sin(freq * t * 2 * np.pi)
        modulation = np.sin(2 * np.pi * 20 * t)
        tone = tone * (0.5 + 0.5 * modulation)
        stereo = np.column_stack((tone, tone))
        path = self.output_dir / filename
        sf.write(str(path), stereo, self.sample_rate)
        return str(path)

    def generate_silent_audio(self, filename="silent.wav", duration=5.0):
        samples = np.zeros((int(self.sample_rate * duration), 2))
        path = self.output_dir / filename
        sf.write(str(path), samples, self.sample_rate)
        return str(path)

    def generate_malformed_wav(self, filename="malformed.wav"):
        path = self.output_dir / filename
        with open(path, 'wb') as f:
            f.write(b'RIFF')
            f.write(struct.pack('<I', 0xFFFFFFFF))
            f.write(b'WAVEfmt ')
            f.write(struct.pack('<I', 16))
            f.write(struct.pack('<H', 1))
            f.write(struct.pack('<H', 2))
            f.write(struct.pack('<I', self.sample_rate))
            f.write(struct.pack('<I', self.sample_rate * 4))
            f.write(struct.pack('<H', 4))
            f.write(struct.pack('<H', 16))
            f.write(b'data')
            f.write(struct.pack('<I', 0))
            f.write(b'\x00\x01\x02\x03' * 1000)
        return str(path)

    def generate_from_spec(self, spec_path, out_name=None, overrides=None):
        """Bottom-up lab bridge: build a payload from a lab spec JSON via
        tools/build_payload.py (spec-driven construction, not fuzzing)."""
        import subprocess
        lab_root = Path(__file__).resolve().parents[4].parents[0]
        builder = lab_root / "tools" / "build_payload.py"
        out_name = out_name or (Path(spec_path).stem + ".bin")
        out_path = self.output_dir / out_name
        cmd = ["python3", str(builder), str(spec_path), "-o", str(out_path)]
        for k, v in (overrides or {}).items():
            cmd += ["--set", f"{k}={v}"]
        subprocess.run(cmd, check=True)
        return str(out_path)

    def generate_battery_sample(self, battery_dir=None, limit=12):
        """Pull N samples from the lab's metadata-attachment battery output."""
        lab_root = Path(__file__).resolve().parents[4].parents[0]
        battery_dir = Path(battery_dir) if battery_dir else lab_root / "battery_out"
        copied = []
        for i, p in enumerate(sorted(battery_dir.glob("*.bin"))[:limit]):
            dst = self.output_dir / f"battery_{i:03d}_{p.name[:80]}"
            dst.write_bytes(p.read_bytes())
            copied.append(str(dst))
        return copied

    def generate_all_payloads(self):
        payloads = {
            'test_tone': self.generate_test_tone(),
            'ultrasonic': self.generate_ultrasonic(),
            'silent': self.generate_silent_audio(),
            'malformed': self.generate_malformed_wav()
        }
        manifest = {
            'generated_at': str(Path.cwd()),
            'payloads': payloads,
            'descriptions': {
                'test_tone': 'Standard 440Hz test tone with harmonics',
                'ultrasonic': '19kHz ultrasonic frequency with modulation',
                'silent': 'Null/empty audio stream',
                'malformed': 'Corrupted WAV header for parser testing'
            }
        }
        with open(self.output_dir / 'manifest.json', 'w') as f:
            json.dump(manifest, f, indent=2)
        return payloads

if __name__ == '__main__':
    gen = AudioPayloadGenerator()
    payloads = gen.generate_all_payloads()
    print("Generated payloads:", list(payloads.keys()))

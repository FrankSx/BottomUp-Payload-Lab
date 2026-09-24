#!/usr/bin/env python3
"""
pipeline_scan.py - Bottom-up Phase 1: map the real parser chain on a host.
Read-only. For systems you own or are authorized to assess.
"""
import json, os, re, subprocess, sys

MAGICS = {b"fLaC": "FLAC", b"OggS": "OGG", b"RIFF": "RIFF/WAV",
          b"ftyp": "MP4/M4A", b"FORM": "AIFF", b"ID3": "MP3(ID3)"}
# 'rare' magics are strong signal alone; 'common' ones need corroboration.
# ftyp excluded: it appears in random ASCII data (perl/node falsely flagged).
RARE = {"FLAC", "OGG"}
COMMON = {"RIFF/WAV", "AIFF", "MP3(ID3)", "MP4/M4A"}
DR_LIB_SIGS = [b"drflac__read_and_decode_metadata", b"drwav__", b"drmp3__"]

def sh(cmd):
    try:
        return subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=60).stdout
    except Exception:
        return ""

def pip_audio_pkgs():
    out = sh("pip freeze 2>/dev/null || pip3 freeze 2>/dev/null")
    audio = ("soundfile", "torchaudio", "librosa", "audioread", "pydub",
             "av", "whisper", "faster-whisper", "onnxruntime", "gstreamer")
    return [l for l in out.splitlines() if any(a in l.lower() for a in audio)]

def ldd_of(path):
    return [l.strip() for l in sh(f"ldd {path} 2>/dev/null").splitlines() if "=>" in l]

def ascii_ratio(data):
    if not data:
        return 1.0
    return sum(1 for b in data[:8192] if 32 <= b < 127 or b in (9, 10, 13)) / min(len(data), 8192)

def scan_bin(path):
    try:
        with open(path, "rb") as f:
            data = f.read()
    except Exception:
        return None
    hits = {name: data.count(m) for m, name in MAGICS.items() if m in data}
    dr = [s.decode() for s in DR_LIB_SIGS if s in data]
    if dr:
        return {"path": path, "formats": hits, "dr_libs_symbols": dr,
                "size": len(data), "verdict": "DR_LIBS-VENDORED"}
    rare = [n for n in hits if n in RARE]
    if rare:
        return {"path": path, "formats": hits, "dr_libs_symbols": dr,
                "size": len(data), "verdict": "LIKELY-PARSER"}
    # common-only magics: corroborate with 2+ distinct formats and not a text blob
    if len(hits) >= 2 and ascii_ratio(data) < 0.95:
        return {"path": path, "formats": hits, "dr_libs_symbols": dr,
                "size": len(data), "verdict": "POSSIBLE"}
    return None

def main():
    print("== pip audio packages ==")
    for p in pip_audio_pkgs():
        print(" ", p)

    print("\n== shared libs + extensions ==")
    exts = sh("find /usr /opt /app -name '*.so' -o -name '*.so.*' "
              "-o -name '*.pyd' 2>/dev/null | head -400").splitlines()
    for p in exts:
        libs = ldd_of(p)
        interesting = [l for l in libs if any(k in l for k in
                       ("sndfile", "avcodec", "avformat", "flac", "ogg", "mpg123"))]
        if interesting:
            print(f"  {p}")
            for l in interesting:
                print(f"     {l}")

    print("\n== format-marker / dr_libs scan on binaries ==")
    found = []
    bins_ = sh("find /usr/bin /usr/local/bin /opt -type f -executable 2>/dev/null | head -300").splitlines()
    for p in exts + bins_:
        r = scan_bin(p)
        if r:
            found.append(r)
            print(f"  [{r['verdict']}] {r['path']}: {r['formats']} {r['dr_libs_symbols']}")

    json.dump(found, open("scan_results.json", "w"), indent=1)
    print(f"\n[+] scan_results.json ({len(found)} binaries with format parsers)")

if __name__ == "__main__":
    main()

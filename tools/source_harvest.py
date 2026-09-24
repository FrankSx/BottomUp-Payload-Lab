#!/usr/bin/env python3
"""
source_harvest.py - Bottom-up Phase 2a: pin, fetch, and map parser sources.
Fetches the exact source version a target ships so payloads are built
against the parser that actually runs.

Usage:
  python3 source_harvest.py --target dr_libs --version v0.13.3 --out src/
  python3 source_harvest.py --target libsndfile --version 1.2.2 --out src/
"""
import argparse, os, re, subprocess, sys, urllib.request

REPOS = {
    "dr_libs":    ("mackron/dr_libs", True),   # single-header: header only
    "libsndfile": ("libsndfile/libsndfile", False),
    "ffmpeg":     ("FFmpeg/FFmpeg", False),
    "torchaudio": ("pytorch/audio", False),
    "gstreamer":  ("GStreamer/gstreamer", False),
}

def sh(cmd, cwd=None):
    return subprocess.run(cmd, shell=True, cwd=cwd, capture_output=True, text=True)

def harvest(target, version, out):
    repo, header_only = REPOS.get(target, (target, False))
    dest = os.path.join(out, f"{target}_{version.replace('/','_')}")
    if not os.path.exists(dest):
        print(f"[*] cloning {repo} @ {version} -> {dest}")
        r = sh(f"git clone --depth 1 --branch {version} https://github.com/{repo} {dest}")
        if r.returncode != 0:
            # fall back to default branch then checkout commit
            r = sh(f"git clone --depth 50 https://github.com/{repo} {dest}")
            if r.returncode != 0:
                sys.exit(f"[!] clone failed: {r.stderr[:300]}")
            sh(f"git checkout {version}", cwd=dest)
    # map parser entry points and length fields
    print("[*] mapping parser entry points / length fields:")
    pats = re.compile(r"(read_and_decode_metadata|_read_metadata|chunkSize|"
                      r"atomSize|mimeLength|descriptionLength|blockSize|"
                      r"nsegs|segment)", re.I)
    exts = (".c", ".h", ".cpp") if not header_only else (".h",)
    for root, _, files in os.walk(dest):
        for f in files:
            if f.endswith(exts):
                p = os.path.join(root, f)
                try:
                    src = open(p, errors="ignore").read()
                except Exception:
                    continue
                for i, line in enumerate(src.splitlines(), 1):
                    if pats.search(line) and ("malloc" in line or
                       "Length" in line or "Size" in line or "metadata" in line.lower()):
                        rel = os.path.relpath(p, dest)
                        print(f"  {rel}:{i}: {line.strip()[:100]}")
    print(f"[+] {dest} ready — build payloads against THIS version")

if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--target", required=True, help="key from REPOS or owner/repo")
    ap.add_argument("--version", required=True, help="tag/branch/commit shipped by target")
    ap.add_argument("--out", default="src")
    a = ap.parse_args()
    harvest(a.target, a.version, a.out)

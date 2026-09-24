#!/usr/bin/env python3
"""
wasm_hunt.py - Strategic WASM hunt across a pipeline's dependencies.
Scans node_modules / site-packages / target dirs for:
  1. WASM audio decoders (dr_libs, libFLAC, ffmpeg, stb_vorbis fingerprints)
  2. Carrier channels: wasm modules smuggled in metadata-bearing packages
  3. Runtime exposure: which wasm runtime version is present (vs known CVEs)

Usage: python3 wasm_hunt.py [search_root]    (default: ./node_modules)
"""
import json, os, re, struct, sys

WASM_MAGIC = b"\x00asm"
# fingerprints inside wasm binaries / packages -> decoder family
SIGS = {
    b"drflac__read_and_decode_metadata": ("dr_libs FLAC", "CVE-2026-32836 grammar"),
    b"drwav__": ("dr_libs WAV", None),
    b"drmp3__": ("dr_libs MP3", None),
    b"FLAC__read_metadata": ("libFLAC", None),
    b"stb_vorbis": ("stb_vorbis OGG", None),
    b"fdk_aac": ("fdk-aac AAC", None),
    b"libavformat": ("ffmpeg", None),
}
RUNTIME_CVE = [
    ("vm2", "3.10.4", "CVE-2026-26956 JSTag sandbox escape (Node 25+)"),
    ("@ffmpeg/ffmpeg", None, "worker memory exhaustion via crafted input"),
    ("wasmtime", "36.0.6|42.0.1|43.0.0", "CVE-2026-34987/34971 compiler-backend escapes"),
]

def scan_wasm(path):
    try:
        data = open(path, "rb").read()
    except Exception:
        return None
    if not data.startswith(WASM_MAGIC):
        return None
    ver = struct.unpack("<I", data[4:8])[0]
    hits = {name: tag for sig, (name, tag) in SIGS.items() if sig in data}
    return {"path": path, "wasm_version": ver, "size": len(data),
            "decoders": hits, "imports_wasi": b"wasi_snapshot" in data}

def package_versions(root):
    vers = {}
    for nm in ("package.json",):
        for dirpath, _, files in os.walk(root):
            if nm in files:
                try:
                    pj = json.load(open(os.path.join(dirpath, nm)))
                    if pj.get("name"):
                        vers[pj["name"]] = pj.get("version")
                except Exception:
                    pass
            if dirpath.count(os.sep) - root.count(os.sep) > 3:
                break  # don't descend deep
    return vers

def main():
    root = sys.argv[1] if len(sys.argv) > 1 else "node_modules"
    if not os.path.isdir(root):
        sys.exit(f"[!] {root} not found")
    print(f"[*] scanning {root} for wasm modules...")
    found = []
    for dirpath, _, files in os.walk(root):
        for f in files:
            if f.endswith((".wasm", ".so", ".node", ".bin")) or "." not in f:
                p = os.path.join(dirpath, f)
                r = scan_wasm(p)
                if r:
                    found.append(r)
                    tag = " | ".join(f"{k}{' ['+v+']' if v else ''}"
                                     for k, v in r["decoders"].items()) or "unknown module"
                    print(f"  [wasm] {p} ({r['size']}B v{r['wasm_version']}) {tag}"
                          f"{' WASI' if r['imports_wasi'] else ''}")
    print("\n[*] runtime exposure:")
    vers = package_versions(root)
    for pkg, bad, note in RUNTIME_CVE:
        v = vers.get(pkg)
        if v and (bad is None or re.search(bad, v)):
            print(f"  [!] {pkg}@{v}: {note}")
        elif v:
            print(f"  [+] {pkg}@{v} present")
    print("\n[*] carrier check: wasm modules inside metadata-bearing packages")
    for dirpath, _, files in os.walk(root):
        for f in files:
            if f.endswith((".flac", ".mp3", ".ogg", ".webp", ".png", ".jpg", ".pdf")):
                print(f"  [media-in-dep] {os.path.join(dirpath, f)}")
    json.dump(found, open("wasm_hunt_results.json", "w"), indent=1)
    print(f"\n[+] wasm_hunt_results.json ({len(found)} wasm modules)")

if __name__ == "__main__":
    main()

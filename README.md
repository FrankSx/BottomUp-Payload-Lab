# Bottom-Up Payload Lab

**Construct payloads from the parser's own grammar instead of fuzzing.**
frankSx — 2026-09-23. Authorized security research only.

Fuzzing finds bugs; construction demonstrates impact. This lab maps the
real parser chain an audio file travels through in AI/audio pipelines,
then builds minimal payloads from source (or reversed binaries), delivers
them via a virtual-mic/browser layer, and discovers targets from the web
rather than from your own machines.

## Layers

| Layer | Path | What it does |
|---|---|---|
| Method | `METHODOLOGY.md` | four phases: surface -> inventory -> source-driven construction -> binary fallback -> validation |
| Inventory | `targets/pipeline_inventory.json` | pipeline families (whisper, dr_libs/wasm, libsndfile, ffmpeg, cloud) mapped to their real parser layer |
| Recon | `tools/pipeline_scan.py` | host scanner: pip pkgs, `ldd` chains, magic fingerprints with false-positive verdict ladder |
| Harvest | `tools/source_harvest.py` | pin + clone the exact shipped parser version, map length fields |
| Construct | `tools/build_payload.py` | parametric spec-driven builder (specs are JSON, not corpora) |
| Battery | `tools/meta_battery.py` + `payloads/meta_attachment_matrix.json` | 682 files: 12 container families x metadata channels x hostile content classes (fmt strings, HTML/JS, active SVG, weird chars, length traps, wasm carriers) |
| WASM | `tools/wasm_hunt.py` + `targets/wasm_package_inventory.json` | three-role hunt: parser-targets (wasm twins of native CVEs), carriers, escape-surface CVEs |
| Discover | `tools/target_discovery.py` + `targets/interest_queries.json` | web-first target discovery; 18 scored voice-AI domains from 2 searches (see `targets_tts_voice_ai.json`) |
| Deliver | `delivery/audionpolys/` | virtual-mic/Selenium injection platform with lab bridges (`generate_from_spec`, `generate_battery_sample`) |
| Notes | `notes/` | opus metadata channels, wasm channels, host triage, target discovery method |

Worked example: `payloads/flac_picture_oom.json` builds the CVE-2026-32836
78-byte reproducer byte-exact (`sha256:49ed6ca3...`, 55M amplification);
`--set description_length=0xFFFFFFFE` arms the second stage.

Not committed (regenerate locally): `battery_out/` binaries
(`python3 tools/meta_battery.py battery_out/`), warel TLS keypair.

Legal: proof-of-concept for authorized security research and defensive
patch verification only.

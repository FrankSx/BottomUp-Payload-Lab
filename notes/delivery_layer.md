# Delivery Layer — virtual-mic / browser-injection platform
**frankSx — 2026-09-23** (integrated from `audionpolys.zip`)

## Role in the lab

The battery *constructs* payloads; this layer *delivers* them to a live web
application and *records* what happens. It is the Phase-4 validator for
browser-side pipelines (WebAudio, MediaRecorder, getUserMedia, audio-upload
endpoints) — where native tooling can't reach.

## Components (`delivery/audionpolys/`)

| Component | What it does |
|---|---|
| `virtual_mic_bugbounty/` | Python platform: virtual-mic injection via Selenium, browser trap controller (XHR/Fetch/WebSocket/media-API interception), anomaly detector, forensic evidence packaging (screenshots, audio, network captures), Flask dashboard |
| `audio_research_suite_v10.2_csp_hardened.js` | In-page WebAudio tester: frequency detection → data-injection simulation, CSP-hardened variant |
| `enhanced_audio_research_suite_v10.1.js` / `fixed_audio_research_suite_v9.1.js` | Earlier iterations (kept for diffing hardening decisions) |
| `polyglot_security_platform_v11.0.js` | Polyglot-focused in-browser suite — pairs with the battery's carrier files |
| `blackbox-output-code-S79SJRVVK8.js` | Blackbox harness |

## Lab integration points (already wired)

- `AudioPayloadGenerator.generate_from_spec(spec_path, overrides=)` —
  builds any lab spec (`payloads/flac_picture_oom.json`, or a new spec you
  wrote in Phase 2) straight into the delivery payload dir, with CLI
  overrides (e.g. `description_length=0xFFFFFFFE`).
- `AudioPayloadGenerator.generate_battery_sample(limit=N)` — pulls samples
  from `battery_out/` so the full metadata-attachment matrix (format
  strings, HTML/JS, active SVG, weird chars, length traps, wasm carriers)
  can be swept through the virtual mic.

## End-to-end flow

```
Phase 2 spec  ──>  build_payload.py  ──>  delivery payload dir
battery_out/  ──>  generate_battery_sample()
                        │
                        ▼
            virtual_mic_controller (Selenium, target web app)
                        │
            trap_controller intercepts upload/analysis requests
                        │
            anomaly_detector flags parser crashes, XSS ignition,
            metadata re-render, memory blowups
                        │
            evidence packaging → report for the writeup
```

## Where each battery class lands in a browser pipeline

| Battery class | Browser-side sink |
|---|---|
| wasm_module carriers | app uses WebAudio/WASM decoders (matches `wasm_hunt.py` findings) |
| html_js / active_svg | metadata rendered into DOM (music libraries, chat UIs) → stored XSS observed via trap_controller DOM hooks |
| fmt_string | less common browser-side; still logged via network capture for native backends behind the API |
| weird (nul/bidi/ctrl) | sanitizer differentials — trap logs the pre/post sanitize forms |
| length_trap | upload handlers whose backend parses FLAC/PNG/etc. — anomaly detector watches for 5xx/OOM/restart |

Run order: `pipeline_scan.py` → `wasm_hunt.py` → pick specs →
`generate_from_spec` / `generate_battery_sample` → virtual-mic sweep →
evidence package.

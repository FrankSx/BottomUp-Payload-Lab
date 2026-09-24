# WASM Channels — Strategic Hunting Notes
**frankSx — 2026-09-23**

WASM shows up in audio/AI pipelines in three roles, and each role gets a
different hunt.

## Role 1 — Parser target: audio decoders compiled to WASM

This is the 2026 sleeper. Native parser bugs have **wasm twins** because
the same C source is being shipped compiled to WebAssembly inside npm
packages:

| Package | WASM decoder | Why it matters |
|---|---|---|
| `webaudio-node` | **dr_libs (MP3/WAV/FLAC)** + stb_vorbis + fdk-aac | dr_flac.h ≤ 0.13.3 grammar reaches Node/browser pipelines. CVE-2026-32836's `malloc(4GiB)` becomes Emscripten heap exhaustion → `RangeError`/trap → worker death. DoS class survives translation; check the vendored dr_libs version string inside the `.wasm` |
| `@wasm-audio-decoders/*` | libFLAC, mpg123, ogg-opus, aac | codec-parser runs container metadata in **JS** before wasm decode — a JS-side length-handling surface that never appears in native CVE lists |
| `ffmpeg.wasm` | full ffmpeg | worker memory caps turn parser OOM into crash-restart churn |
| pyodide-based audio tools | libsndfile ports | same version-pinning discipline as Phase 2 |

Hunt method: `tools/wasm_hunt.py` scans `node_modules` for `.wasm` files,
fingerprints decoder families by symbol strings inside the binary
(`drflac__read_and_decode_metadata` is greppable inside a wasm file), and
flags runtime CVE exposure (vm2 3.10.4, old wasmtime). Then apply the
**bottom-up method to the wasm build**: pin the dr_libs version baked into
the wasm (version strings survive), fetch that source, and reuse the FLAC
PICTURE spec — the payload spec is container-grammar, and the grammar
doesn't care whether the parser is native or wasm.

## Role 2 — Carrier: wasm smuggled in metadata (SIREN v1 vector, expanded)

A minimal valid wasm module is 8 bytes (`00 61 73 6d 01 00 00 00`) — the
same size class as a magic marker, so every metadata channel in
`meta_attachment_matrix.json` can carry one. Growth paths:

- **FLAC PADDING** (v1 vector): survives metadata stripping in tools that
  preserve padding; an extractor that instantiates anything from padding
  bytes has no validation layer at all.
- **ID3 GEOB** with `mime=application/wasm`: an honest label most players
  ignore; a tool that "opens attachments" may run them.
- **MP4 `uuid` atoms**: arbitrary 16-byte-UUID + payload; invisible to
  validators that only walk known boxes.
- **PDF /EmbeddedFiles**: the polyglot bridge — carries any of the above.
- **JXL JUMBF / brotli boxes**: compression defeats magic-scanning EDR;
  the wasm only materializes after decode.

The battery's `wasm_module` content class injects a real, minimal,
instantiable module (export `siren_activated`, per the v1 lineage) into
every carrier channel.

## Role 3 — Escape surface: runtime/compiler CVEs turn "wasm runs" into RCE

2026 demonstrated that the sandbox boundary is implemented per-runtime and
breaks regularly:

- **CVE-2026-2796** (SpiderMonkey): `Function.prototype.call.bind` import
  optimization skips the signature check — type-confused wasm import →
  arbitrary R/W → native code exec in the content process.
- **CVE-2026-26956** (vm2 3.10.4, Node 25+): `try_table` + `JSTag` catches a
  host-realm exception *below* vm2's JS-layer sanitizer → host `Function`
  → RCE. Any LLM/sandbox plugin running untrusted code through vm2 that can
  embed a wasm module is exposed.
- **CVE-2026-34987 / 34971** (Wasmtime, Apr 2026): compiler-backend escapes
  — Winch memory-offset bug and Cranelift-aarch64 miscompiled bounds check.
  Server-side wasm ingestion of untrusted modules (plugin architectures,
  audio-decoder plugins included) is the exposure.
- **CVE-2026-5752** (Terrarium/Pyodide): prototype-chain container escape —
  AI code-exec sandboxes that also accept audio uploads are the overlap.

Strategic search for these surfaces (`targets/wasm_package_inventory.json`):
npm dependents of the decoder packages; GitHub code search for
`EMSCRIPTEN` + `dr_flac.h` in build files; packages shipping `.wasm` >100KB
with decoder strings; pip packages bundling wasm (pyodide lineage).

## The combined play

The endgame for a pipeline: **carrier gets the module in (Role 2) →
parser-target DoS or confusion (Role 1, incl. wasm twins of native CVEs) →
where a sandbox executes anything wasm-shaped, escape-surface CVEs decide
whether that's RCE (Role 3)**. Map all three layers per pipeline in Phase 1
before choosing the payload — the expensive bug is usually in the layer you
didn't scan.

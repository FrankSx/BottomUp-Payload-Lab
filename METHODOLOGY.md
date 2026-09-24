# Bottom-Up Payload Construction Lab
**frankSx — 2026-09-23**

The norm is blind fuzzing: throw mutations at a parser and hope. This lab
inverts that. We enumerate the *real* parser chain an audio file travels
through in common AI/audio pipelines, read the source (or reverse the
binary), identify the **length fields and trust boundaries**, and then
*construct* minimal payloads that hit those exact fields. Fuzzing finds
bugs; construction demonstrates impact.

---

## Phase 0 — Define the target surface

Pick the pipeline first, the bug second. See
`targets/pipeline_inventory.json` for the maintained map. Key insight for
2026-era AI pipelines: most of them do NOT parse audio themselves.

| Pipeline family | Actual parser layer | Source available? |
|---|---|---|
| openai-whisper, whisperX | **ffmpeg** (libavcodec/libavformat) | yes — git.ffmpeg.org |
| whisper.cpp, ggerganov tools | **dr_libs** single-header | yes — github.com/mackron/dr_libs |
| Coqui/TTS, speechbrain, pyannote | **libsndfile** via soundfile/torchaudio | yes — libsndfile |
| gstreamer ingest | gst-plugins typefind + parsers | yes — freedesktop gitlab |
| Cloud TTS APIs | proprietary | **no → Phase 3 fallback** |

A file an AI system "accepts" is decoded by exactly one of these. That is
your real attack surface, and it is a short list.

## Phase 1 — Parser-chain inventory (recon)

Run `tools/pipeline_scan.py` against the host/container you control:

1. `pip freeze` + import-graph crawl → which audio package does the app
   actually load (`soundfile`? `torchaudio`? `av`?).
2. Shared-object / vendored-header scan:
   - `find / -name 'dr_*.h'` → single-header libs leave fingerprints;
     check for `drflac__read_and_decode_metadata` symbols in any `.so` or
     binary (`strings -a` + `grep`).
   - `ldd` on loaded extensions → resolves `libsndfile.so`, `libavcodec.so`.
3. **Format-marker scan** of every shipped binary/lib: look for `fLaC`,
   `OggS`, `RIFF`, `ftyp` magic strings near code sections — presence means
   a parser for that format is compiled in, even if it's vendored and
   invisible to package managers.

Output: a chain like
`upload.wav → soundfile → libsndfile.so.1 → FLAC__read_metadata`.
One chain = one target parser.

## Phase 2 — Source-driven payload construction (preferred path)

When source exists (it usually does), do NOT fuzz. Read the decode path and
build the payload from the parser's own expectations:

1. **Harvest the source** — `tools/source_harvest.py` clones/downloads the
   exact version the target ships (pin by commit/tag from the binary's
   build strings, or take the oldest ≤ shipped version). Version drift
   matters: `0.13.3` vs `663239a` is the difference between vulnerable and
   patched.
2. **Walk the metadata/chunk path** — for each format the parser handles,
   list the length fields it reads *before* validating them:
   - FLAC: `blockSize` (24b), `mimeLength`, `descriptionLength`,
     `pictureDataSize` (32b each)
   - WAV: every `chunkSize`
   - Ogg: `nsegs` + segment table
   - MP4/M4A: `atomSize` (32/64-bit), sample tables
3. **Build, don't fuzz** — `tools/build_payload.py` takes a small spec
   (magic, block headers, offset/value of the hostile length field) and
   emits the minimal file. The FLAC spec `payloads/flac_picture_oom.json`
   produces the 78-byte CVE-2026-32836 reproducer. Iterate the spec until
   a single read reaches the target line — this is minutes, not CPU-days.
4. **Confirm the line** — GDB watchpoint on the length read or the malloc;
   `tools/binary_recon.sh --trace` automates the breakpoint-on-`malloc`
   pattern. You should be able to name the exact line your file triggers.

Deliverable per finding: spec JSON (rebuildable payload) + the minimal
file + the line number. Not a fuzzer corpus.

## Phase 3 — Binary fallback (no source)

For closed pipelines (proprietary TTS APIs, mobile SDKs):

1. **Acquire the library**: extract from the package
   (pip wheel → bundled `.so`; APK/AAR → JNI libs; Docker image layers;
   node_modules `bindings`).
2. **Recon the binary** (`tools/binary_recon.sh`):
   - `readelf -p .comment`, `strings -a | grep -i version` → version pin
   - DWARF? `readelf -S | grep debug` — if present, source-level line info
     survives; GDB gives you the exact function names and lines.
   - Symbols stripped? `nm -D` for dynamic, `objdump -d` + FLIRT-style
     signature matching against known open-source builds (compile the open
     version, diff function hashes — same source ≈ same basic-block layout).
3. **Format-grammar reverse**: find the magic-string references
   (`xrefs to "fLaC"` in GDB/IDA/Ghidra), work backward to the block
   parser, record the length-field offsets — these are stable across
   versions and are your payload construction parameters.
4. **GDB-driven confirmation**: scripted breakpoints on the parser entry,
   `commands` blocks to log each read offset/size, run the file through,
   diff the trace against the open-source version. When traces align, the
   payload spec you built for the open version transfers verbatim.

## Phase 4 — Validation matrix

| Signal | Meaning |
|---|---|
| Spec file ≤ ~100 bytes, triggers | construction success; record amplification ratio |
| ASan abort with symbolized stack | confirm exact line |
| Patched build returns clean | confirms the finding is the intended field |
| `malloc` size == your spec value | payload-to-line traceability proven |

If the patched build behaves identically, your payload isn't exercising the
bug — go back to Phase 2 and re-read.

## Rules of engagement

- Only against systems/images you own. All inventory scripts are read-only
  on the host, but payloads must be run in a sandboxed target.
- Every payload ships as a **spec** (JSON) so it's reproducible and
  diffable — no opaque binaries in reports.

# Host Triage — Debian 12 scan (user-submitted pipeline_scan output)
**2026-09-23**

## Verdicts

| Verdict | Meaning | Action |
|---|---|---|
| `DR_LIBS-VENDORED` | `drflac__*`/`drwav__*` symbols found | direct CVE-2026-32836 relevance — version-pin immediately |
| `LIKELY-PARSER` | rare magic (`fLaC`/`OggS`/`ftyp`) present | real parser, build specs for its formats |
| `POSSIBLE` | 2+ common magics, non-text binary | corroborate with symbols/`ldd` before investing |
| (not shown) | `AIFF`/`FORM`/`ID3` alone | false positive — 4-byte ASCII matches random data (e.g. 225 "AIFF" in QtGui, 8 in `/bin/ls`) |

## This host's actual attack surface

1. **Firefox-ESR media stack** — `libxul.so` (FLAC/OGG/WAV/MP4/MP3),
   `libmozavcodec.so`, `libgkcodecs.so`. This is a full browser engine with
   its own demuxers+codecs (not ffmpeg's, not dr_libs'). If audio reaches
   this host through a browser (upload, WebAudio decode, `<audio>`), THIS
   is the parser chain. Next: `apt policy firefox-esr` → pin version →
   source harvest on the matching mozilla-central tag.
2. **libsndfile** (via `libSDL-1.2`) — check `apt policy libsndfile1`.
   Metadata path: FLAC/OGG comments + chunk handling. Specs to build:
   OpusTags-length class, LIST/INFO, ID3-in-WAV.
3. **libjxl.so.0.7** — 2022-era JPEG XL. Edge-container family: Exif box,
   `xml ` box, JUMBF, brotli codestream. Version-check for known CVEs,
   then harvest 0.7 source and build JXL box specs.
4. **7z.so** — WAV/AIFF handler inside the archiver (preview/extract path
   when unpacking audio from archives — a real ingestion vector).
5. **libmwaw**, **libwebrtc_audio_processing** (WAV), gstreamer — lower
   priority unless the app under test loads them.

## What is NOT here

- No `dr_libs` anywhere → CVE-2026-32836 / SIREN v3 minimal PoC does not
  apply to this host. Don't waste cycles on it here.
- No `ffmpeg` proper, no `@wasm-audio-decoders`, no python audio packages
  (`pip audio packages` section was empty) → no wasm parser-targets; the
  WASM layer on this host is browser-internal (SpiderMonkey JIT/wasm engine
  inside libxul — relevant to Role 3 escape-surface notes if wasm ever runs).

## Immediate commands for this host

```bash
apt policy firefox-esr libsndfile1 libjxl1 2>/dev/null
# then per METHODOLOGY Phase 2:
python3 tools/source_harvest.py --target libsndfile --version <pinned> --out src/
python3 tools/source_harvest.py --target libjxl --version 0.7 --out src/
```

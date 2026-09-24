# Opus Metadata Channels — Hunting Notes
**frankSx — 2026-09-23**

## Why Opus is a different hunting ground

Opus sits in an Ogg (or WebM/MP4/Matroska) envelope, and its metadata
surface is wider than most parsers assume — because metadata enters and
*leaves* Opus files through several bridges that re-parse length fields at
each hop.

## Channel 1 — OpusTags (the comment header)

The Opus comment header is **Vorbis-comment grammar with 4-byte
little-endian lengths**:

```
"OpusTags"
vendor_len  : u32 LE
vendor      : vendor_len bytes
count       : u32 LE
per comment: len u32 LE | len bytes (KEY=value)
```

Attack surface: three consecutive unchecked-length reads per file. Any
parser that mallocs `vendor_len` / `len` before validating against the
actual page payload inherits the CWE-789 class *without any FLAC involved*.
`libopusfile` (`opusfile.h`, `op_tags.c` path) and every language binding
that exposes raw tags walks this code. Field offsets are fixed — construct,
don't fuzz:

- vendor_len @ offset 8 (after "OpusTags")
- comment[i].len @ offset 16 + len(vendor) + 4 + Σ(4 + len(comment[j<i]))

## Channel 2 — METADATA_BLOCK_PICTURE bridge (FLAC ↔ Opus)

This is the important one. The de-facto standard for cover art in Opus is
the **FLAC PICTURE block verbatim**, base64-encoded into a comment:
`METADATA_BLOCK_PICTURE=<base64 of a FLAC PICTURE block>`.

Implications for the hunt:

1. The FLAC PICTURE grammar (pictureType, mimeLength, descriptionLength,
   dataLength — all attacker u32) **reaches Opus files** through any tool
   that converts FLAC→Opus with artwork (ffmpeg, opus-tools, SoundCloud-
   style transcoders). One grammar, two containers.
2. The round trip is the exploit: an ingest pipeline that *extracts* cover
   art from Opus often decodes the base64 blob and **re-parses it with a
   FLAC picture parser** (or worse, re-parses it with a *vendored dr_libs*
   because "it's just metadata"). CVE-2026-32836's vulnerable function can
   be reached with an `.opus` upload.
3. Payload spec: craft the PICTURE block (mimeLength = 0xFFFFFFFE),
   base64 it, wrap as an OpusTags comment inside a minimal Ogg Opus stream.
   `payloads/opus_metadatablockpicture_oom.json` builds exactly this.

## Channel 3 — Ogg multiplexing (logical streams)

Ogg pages carry a 32-bit granule position and an 8-bit segment count with
a 255-byte-quantized segment table. Attack surface:

- **Segment table accumulation**: continued packets across pages make
  decoders accumulate until a page terminates the packet — a length
  accumulation primitive, not a single alloc.
- **Multiplexed extra streams**: nothing stops an Ogg Opus file from
  carrying a second logical stream (theora, or arbitrary codec id). Parsers
  that assume "Opus file = one stream" skip the second stream's packets —
  or hand them to a codec they didn't expect to load. Container confusion
  at the mux layer, before any codec runs.
- **Chained streams**: concatenated Opus streams re-initialize decoder
  state per chain — a state-reset differential between tools that honor
  chains and tools that don't.

## Channel 4 — Ogg page sizing (pre-codec)

Every Ogg page header: `capture(4) version(1) flags(1) granule(8) serial(4)
seq(4) crc(4) nsegs(1) segs(nsegs)`, body = Σ segs[i]. Fields to watch in
any Ogg consumer: `nsegs` vs actual body length (mismatch = desync),
granulepos vs page count (timestamp confusion → desync in ASR pipelines),
and zero-length segments (EOS markers mid-chain).

## Construction targets (bottom-up, from source)

| Parser | Source | Length fields to read first |
|---|---|---|
| libopusfile | github.com/xiph/opusfile | OpusTags lens, picture blob decode-then-parse |
| opus-tools (opusenc) | github.com/xiph/opus-tools | same, on the encode side |
| ffmpeg ogg demuxer | git.ffmpeg.org | nsegs, segment table, chained streams |
| libsndfile (ogg/vorbis path) | github.com/libsndfile/libsndfile | comment lens via vorbiscomment grammar |
| PyAV / av bindings | github.com/PyAV/PyAV | whatever ffmpeg does, plus Python-side buffer copies |

## Rule of thumb for Opus

If a pipeline "supports FLAC and Opus", assume the *same metadata grammars
flow through both* and the vulnerable parse may happen on either side of a
transcode. Always map the transcode step in Phase 1 before picking a
container — the bug may live in the bridge, not the container.

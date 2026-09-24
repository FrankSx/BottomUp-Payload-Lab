#!/usr/bin/env bash
# binary_recon.sh - Bottom-up Phase 3: closed-binary fallback recon
# Usage: ./binary_recon.sh <binary> [trace_cmd...]
#   ./binary_recon.sh libtarget.so
#   ./binary_recon.sh ingestd --trace './ingestd payload.flac'
set -u
BIN="$1"; shift || true
MODE="${1:-recon}"; shift || true

hr(){ printf '\n== %s ==\n' "$*"; }

hr "identity"
file "$BIN"
readelf -p .comment "$BIN" 2>/dev/null | head -8
strings -a "$BIN" | grep -iE 'gcc|clang|version [0-9]|dr_libs|libsndfile|libav' | sort -u | head -20

hr "debug info (source lines survive?)"
if readelf -S "$BIN" 2>/dev/null | grep -q debug; then
  echo "[+] DWARF present — GDB will show source lines"
else
  echo "[-] stripped/no DWARF — rely on symbols + signature match"
fi

hr "symbols"
nm -D "$BIN" 2>/dev/null | grep -iE 'flac|wav|mp3|ogg|sndfile|avcodec|metadata|picture' | head -30
nm "$BIN" 2>/dev/null | grep -iE 'read.*metadata|picture|chunk|demux' | head -30

hr "format magic xrefs (parser presence)"
for m in fLaC OggS RIFF ftyp FORM ID3; do
  n=$(strings -a "$BIN" | grep -c "$m" || true)
  [ "$n" -gt 0 ] && echo "  '$m' referenced x$n"
done

hr "dr_libs / vendored fingerprints"
strings -a "$BIN" | grep -E 'drflac__|drwav__|drmp3__' | sort -u | head -15

hr "gdb scripted trace (malloc origin)"
if [ "$MODE" = "--trace" ]; then
  CMD="${*:-./harness payload.flac}"
  gdb -q -batch \
    -ex "break malloc if size > 1073741824" \
    -ex "commands
print size
bt 8
continue
end" \
    -ex "run" \
    -ex "quit" --args $CMD
fi

echo; echo "[+] next: pin version -> fetch/compile same-version open source ->"
echo "    diff function hashes -> transfer payload spec from payloads/"

#!/usr/bin/env python3
"""
meta_battery.py - Generate the metadata-attachment battery.
Every channel from payloads/meta_attachment_matrix.json gets a real file
with every content class injected — format strings, HTML/JS, active SVG,
weird characters (nul/bidi/ctrl/overlong), and length traps — into that
container's native metadata grammar.

Output: one file per (container, channel, content-class) combo in out/.

Authorized security research only. All JS is alert-style markers.
"""
import base64, json, os, struct, sys, zlib

M = json.load(open(os.path.join(os.path.dirname(__file__),
                                "..", "payloads", "meta_attachment_matrix.json")))
CC = M["content_classes"]
def _minimal_wasm():
    """Valid, instantiable wasm module: magic+version, export 'siren_activated'."""
    return (bytes.fromhex("0061736d01000000")
            + bytes.fromhex("01 05 01 60 00 01 7f")
            + bytes.fromhex("03 02 01 00")
            + bytes.fromhex("07 12 01 0e 73 69 72 65 6e 5f 61 63 74 69 76 61 74 65 64 00 00")
            + bytes.fromhex("0a 06 01 04 00 41 c0 00 0b"))
CC["wasm_module"] = [_minimal_wasm()]
MARK = "SIREN-META"

def u16be(n): return struct.pack(">H", n)
def u32be(n): return struct.pack(">I", n)
def u32le(n): return struct.pack("<I", n)

def load_matrix():
    return {c["name"]: c["channels"] for c in M["containers"]}

# ---------- per-container builders: (channel_id, content:bytes) -> bytes ----------

def b_flac_vendor(c):  return u32le(len(c)) + c
def b_flac_comment(c):
    return u32le(4) + b"SIRE" + u32le(1) + u32le(len(c)) + c
def b_flac_picture(c):  # PICTURE block with data = content, real lengths
    mime, desc, data = b"image/svg+xml", c[:32], c
    body = u32be(3) + u32be(len(mime)) + mime + u32be(len(desc)) + desc + u32be(1)+u32be(1)+u32be(0)+u32be(0)+u32be(len(data)) + data
    return bytes([0x86]) + len(body).to_bytes(3, "big") + body
def b_opustags(c):
    body = b"OpusTags" + u32le(4) + b"SIRE" + u32le(1) + u32le(len(c)) + c
    return body
def b_mb_picture(c):
    pic = b_flac_picture(c)  # strip block header -> raw picture body
    raw = pic[4:]
    payload = b"METADATA_BLOCK_PICTURE=" + base64.b64encode(raw)
    return b_opustags(payload)

def b_id3_frame(fid, c):  # id3v2.4 frame, synchsafe size
    body = b"\x03" + c            # encoding UTF-8
    sz = len(body)
    ss = bytes([(sz >> 21) & 0x7F, (sz >> 14) & 0x7F, (sz >> 7) & 0x7F, sz & 0x7F])
    return fid + ss + b"\x00\x00" + body
def b_id3(c):  return b"ID3\x04\x00\x00" + b_id3_frame(b"TXXX", b"desc\x00" + c)

def b_riff_chunk(tag, c, pad=True):
    d = c + (b"\x00" if pad and len(c) % 2 else b"")
    return tag + u32le(len(c)) + d

def b_webp(c):  # VP8X + the given chunk family handled by caller; minimal VP8X container
    return b"RIFF" + u32le(0) + b"WEBPVP8X" + u32le(10) + b"\x00\x00\x00" + u32le(16)+u32le(16)

def b_jpeg_app(marker, c): return b"\xff" + bytes([marker]) + u16be(len(c) + 2) + c
def b_jpeg(c): return b"\xff\xd8" + b_jpeg_app(0xFE, c) + b"\xff\xd9"

def b_png_chunk(tag, c):
    return u32be(len(c)) + tag + c + u32be(zlib.crc32(tag + c) & 0xFFFFFFFF)
def b_png(c):  # IHDR + injected text chunk
    ihdr = b_png_chunk(b"IHDR", u32be(1)+u32be(1)+b"\x08\x06\x00\x00\x00")
    idat = b_png_chunk(b"IDAT", zlib.compress(b"\x00\x00\x00\x00\x00"))
    iend = b_png_chunk(b"IEND", b"")
    return b"\x89PNG\r\n\x1a\n" + ihdr + b_png_chunk(b"tEXt", b"Title\x00" + c) + idat + iend

def b_jxl_box(tag, c, small=False):  # JXL container box: size u32 or 64-bit
    if small: return u32be(8 + 4 + len(c)) + tag + c
    return u32be(1) + tag + struct.pack(">Q", 16 + len(c)) + c   # largesize path
def b_jxl(c): return bytes.fromhex("0000000c4a584c200d0a870a") + b_jxl_box(b"xml ", c)

def b_ebml_element(eid, c):  # id bytes + 8-byte unknown-size style len
    return eid + b"\x01" + c                               # 0x01 = unknown size (valid EBML)
def b_webm(c): return b"\x1a\x45\xdf\xa3" + b"\x01" + b_ebml_element(b"\xa9", c)  # Tags-ish

def b_wav_list(c):  # LIST INFO with INAM subchunk
    inam = b"INAM" + u32le(len(c)) + c + (b"\x00" if len(c) % 2 else b"")
    lst = b"INFO" + inam
    return b"RIFF" + u32le(4 + 8 + len(lst)) + b"WAVE" + b"LIST" + u32le(len(lst)) + lst

def b_mp4_atom(tag, c):  # atom with 64-bit largesize
    return u32be(1) + tag + struct.pack(">Q", 16 + len(c)) + c
def b_mp4(c): return u32be(20) + b"ftyp" + b"M4A " + u32be(0) + b"M4A " + b_mp4_atom(b"xml ", c)

def b_pdf(c):  # minimal 1-page PDF with hostile Info dict + XMP stream
    info = f"<< /Title ({c.decode('latin1', 'ignore')}) /Author (SIREN) >>".encode('latin1','ignore')
    return (b"%PDF-1.7\n1 0 obj<<>>endobj\ntrailer\n" + info + b"\n%%EOF")

def minimal_wasm():
    """Valid, instantiable wasm module: magic+version, export 'siren_activated'."""
    return (bytes.fromhex("0061736d01000000")
            + bytes.fromhex("01 05 01 60 00 01 7f")        # type: ()->i32
            + bytes.fromhex("03 02 01 00")                  # func 0 : type 0
            + bytes.fromhex("07 12 01 0e 73 69 72 65 6e 5f 61 63 74 69 76 61 74 65 64 00 00")  # export
            + bytes.fromhex("0a 06 01 04 00 41 c0 00 0b"))  # body: i32.const 64; end

def b_tiff(c):
    # TIFF with tag 270 (ImageDescription) pointing to content
    data_off = 8 + 2 + 12 + 4
    ifd = u16be(1) + u16be(270) + u16be(2) + u16be(len(c)) + u32be(data_off) + u32be(0)
    return b"II*\x00" + u32le(8) + ifd + c

BUILDERS = {
 "flac": {"vorbis_vendor": b_flac_vendor, "vorbis_user_comment": b_flac_comment, "picture_block": b_flac_picture},
 "ogg/opus": {"opustags_vendor": b_opustags, "metadatablockpicture": b_mb_picture},
 "mp3_id3v2": {"TXXX": b_id3, "COMM": b_id3, "USLT": b_id3, "GEOB": b_id3},
 "webp": {"EXIF": lambda c: b_riff_chunk(b"EXIF", b"II*\x00\x08\x00\x00\x00" + c),
          "XMP ": lambda c: b_riff_chunk(b"XMP ", c),
          "ICCP": lambda c: b_riff_chunk(b"iCCP", c)},
 "jpeg": {"APP1_EXIF": lambda c: b"\xff\xd8" + b_jpeg_app(1, b"Exif\x00\x00II*\x00\x08\x00\x00\x00" + c) + b"\xff\xd9",
          "APP1_XMP": lambda c: b"\xff\xd8" + b_jpeg_app(1, b"http://ns.adobe.com/xap/1.0/\x00" + c) + b"\xff\xd9",
          "COM": b_jpeg},
 "png": {"tEXt": b_png, "iTXt": b_png, "zTXt": b_png, "eXIf": b_png},
 "jxl": {"Exif_box": lambda c: bytes.fromhex("0000000c4a584c200d0a870a") + b_jxl_box(b"Exif", c, small=True),
         "xml_box": b_jxl},
 "webm/ebml": {"Tags": b_webm, "ChapProcess": b_webm, "Attachments_FileDescription": b_webm},
 "wav": {"LIST_INFO": b_wav_list, "id3_in_wav": lambda c: b"RIFF" + u32le(4+8+len(c)) + b"WAVE" + b"id3 " + u32le(len(c)) + c},
 "mp4/isobmff": {"udta_meta_ilst": b_mp4, "xml_": b_mp4, "uuid": b_mp4},
 "avif/heic": {"iinf/infe": b_mp4, "XMP_in_mdat": b_mp4},
 "pdf": {"Info_dict": b_pdf, "xmp_metadata_stream": b_pdf, "javascript_in_names": b_pdf},
 "tiff": {"IFD_tags": b_tiff, "XMP tag 700": b_tiff, "ImageSourceData tag 37724": b_tiff},
}

BUILDERS.setdefault("flac", {})["padding_wasm"] = lambda c: b"fLaC" + bytes([0x81]) + len(c).to_bytes(3, "big") + c
BUILDERS.setdefault("mp3_id3v2", {})["GEOB_wasm"] = lambda c: b_id3(c)
BUILDERS.setdefault("mp4_isobmff", {})["uuid_wasm"] = b_mp4
BUILDERS.setdefault("pdf", {})["embedded_wasm"] = b_pdf

def main():
    out = sys.argv[1] if len(sys.argv) > 1 else "battery_out"
    os.makedirs(out, exist_ok=True)
    n = 0
    for cname, channels in load_matrix().items():
        for ch in channels:
            fn = BUILDERS.get(cname, {}).get(ch["id"])
            if not fn:
                continue
            for cls, payloads in CC.items():
                for i, p in enumerate(payloads):
                    data = p.encode("utf-8", "surrogatepass") if isinstance(p, str) else p
                    try:
                        blob = fn(data)
                    except Exception as e:
                        continue
                    if isinstance(p, bytes):
                        safe = "wasm_" + p[:6].hex()
                    else:
                        safe = "".join(ch if ch.isalnum() or ch in "%._-" else "_"
                                       for ch in p)[:18] or "x"
                    csafe = cname.replace('/', '_').replace(' ', '_')
                    chsafe = ch['id'].replace('/', '_').replace(' ', '_')
                    path = f"{out}/{csafe}__{chsafe}__{cls}_{i}__{safe}.bin"
                    open(path, "wb").write(blob)
                    n += 1
    print(f"[+] {n} battery files in {out}/")
    print("[*] sweep each against the pipeline: scanner, transcode bridge,")
    print("    metadata renderer, and LLM-ingest text extractor (see growth_hooks)")

if __name__ == "__main__":
    main()

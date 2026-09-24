#!/usr/bin/env python3
"""
target_discovery.py - Interest-driven target harvesting for the bottom-up lab.

Your host scan finds what's installed; this finds what's WORTH scanning.
Flow: interest -> queries -> search results (paste/API/DDG HTML) -> domains
-> dedupe -> signal score -> targets.json -> warel/domcap collector.

Usage:
  # 1. print ready-to-run searches for an interest
  python3 tools/target_discovery.py --interest tts_voice_ai --print-queries

  # 2. feed collected results (paste JSON [{"title":..., "url":...}] or a
  #    text blob of "Title - URL" lines / raw HTML) -> scored targets
  python3 tools/target_discovery.py --interest tts_voice_ai --ingest results.json
  python3 tools/target_discovery.py --interest podcast_music_hosting --ingest -
     (paste, Ctrl-D)

  # 3. score an existing domain list
  python3 tools/target_discovery.py --interest web_audio_apps --domains a.com b.com

Output: targets_<interest>.json with per-domain score + rationale, ready to
hand to the warel/domcap collector for Phase-1 confirmation.
"""
import argparse, json, os, re, sys, urllib.parse

ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..")
QUERIES = json.load(open(os.path.join(ROOT, "targets", "interest_queries.json")))
ENGINES = ["https://html.duckduckgo.com/html/?q={q}",
           "https://www.bing.com/search?q={q}",
           "https://www.google.com/search?q={q}"]
URL_RE = re.compile(r"https?://([a-z0-9.-]+\.[a-z]{2,})(?:[/:?#]|$)", re.I)
SKIP_SUBSTR = ("google.", "bing.", "duckduckgo.", "youtube.", "github.com/",
               "stackoverflow.com/", "reddit.com/", "medium.com/",
               "wikipedia.org/", "linkedin.com/", "facebook.", "twitter.",
               "x.com/", "quora.com/", "npmjs.com/", "pypi.org/")

def print_queries(interest):
    for i, q in enumerate(QUERIES["interests"][interest]["queries"], 1):
        print(f"[{i}] {q}")
        for e in ENGINES:
            print(f"      {e.format(q=urllib.parse.quote(q))}")

SIGNAL_PHRASES = ("audio upload", "speech-to-text", "text to speech", "voice api",
                  "voice agent", "voice cloning", "transcription api", "stt", "tts",
                  "realtime voice", "audio file", "sound", "podcast", "music",
                  "ssml", "transcrib", "voice", "audio")

def extract_urls(text):
    urls = []
    try:  # JSON [{"title","url"}]
        items = json.loads(text)
        return [(it.get("url", ""), it.get("title", "")) for it in items]
    except Exception:
        pass
    for line in text.splitlines():
        m = URL_RE.search(line)
        if m:
            urls.append((m.group(0).rstrip(").,;"), line.strip()))
    return urls

def base_domain(u):
    h = urllib.parse.urlparse(u if "//" in u else "//" + u).netloc.lower()
    parts = h.split(".")
    return ".".join(parts[-2:]) if len(parts) >= 2 else h

def score_domain(domain, interest, title=""):
    q = QUERIES["interests"][interest]
    d = domain.lower()
    t = (title or "").lower()
    score, why = 0, []
    # domain-name heuristics
    kw_hit = sum(1 for k in ("voice", "tts", "speech", "audio", "sound",
                             "podcast", "music", "sonic", "vox", "listen",
                             "transcrib", "talk", "rec") if k in d)
    if kw_hit:
        score += min(30, kw_hit * 12); why.append(f"{kw_hit} interest keywords in domain")
    # title/signal-phrase heuristics (search-result titles carry the real signal)
    ph_hit = sum(1 for p in SIGNAL_PHRASES if p in t)
    if ph_hit:
        score += min(40, ph_hit * 10); why.append(f"{ph_hit} signal phrases in title")
    if any(s in t for s in ("api", "docs", "platform", "developers", "documentation")):
        score += 10; why.append("api/docs in title")
    if any(s in d for s in ("api.", "dev.", "docs.", "platform", "cloud")):
        score += 10; why.append("api/dev surface in domain")
    if any(s in d for s in ("convert", "editor", "online", "app.")):
        score += 10; why.append("web tool (client-side decode likely)")
    if any(s in d for s in ("hackerone", "bugcrowd")):
        score += 15; why.append("bounty reference")
    return min(score, 100), "; ".join(why) or "no strong signal"

def ingest(text, interest, outdir):
    urls = extract_urls(text)
    domains = {}
    titles = {}
    for u, t in urls:
        try:
            bd = base_domain(u)
        except Exception:
            continue
        if any(s in bd for s in SKIP_SUBSTR) or not bd or "." not in bd:
            continue
        domains.setdefault(bd, set()).add(u)
        titles.setdefault(bd, set()).add(t)
    rows = []
    for d, us in sorted(domains.items()):
        s, why = score_domain(d, interest, title=" | ".join(titles.get(d, ())))
        rows.append({"domain": d, "score": s, "rationale": why,
                     "sample_urls": sorted(us)[:3], "interest": interest})
    rows.sort(key=lambda r: -r["score"])
    out = os.path.join(outdir, f"targets_{interest}.json")
    json.dump(rows, open(out, "w"), indent=1)
    print(f"[+] {len(rows)} unique domains -> {out}")
    for r in rows[:15]:
        print(f"  {r['score']:3d}  {r['domain']:40s} {r['rationale'][:60]}")
    print("\n[*] next: hand sample_urls to the warel/domcap collector for "
          "Phase-1 pipeline confirmation, then pick specs from payloads/")

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--interest", required=True, choices=list(QUERIES["interests"]))
    ap.add_argument("--print-queries", action="store_true")
    ap.add_argument("--ingest", metavar="FILE", help="'-' = stdin")
    ap.add_argument("--domains", nargs="*")
    ap.add_argument("--outdir", default=".")
    a = ap.parse_args()
    if a.print_queries:
        print_queries(a.interest)
    elif a.ingest is not None:
        text = sys.stdin.read() if a.ingest == "-" else open(a.ingest).read()
        ingest(text, a.interest, a.outdir)
    elif a.domains:
        ingest("\n".join("https://" + d for d in a.domains), a.interest, a.outdir)
    else:
        print_queries(a.interest)

if __name__ == "__main__":
    main()

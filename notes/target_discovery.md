# Target Discovery — finding ideal targets from the web
**frankSx — 2026-09-23**

Host scans tell you what a machine runs. They don't tell you what machines
are worth scanning. This layer inverts the direction: start from the
*interest* (TTS APIs, podcast ingest, multimodal AI), harvest candidate
services from search results, score them, and only then spend collection
time (warel/domcap) confirming the pipeline.

## Flow

```
interest (targets/interest_queries.json)
   -> ready-to-run searches (--print-queries: DDG/Bing/Google URLs)
   -> collect results (API output pasted as JSON, or text, or HTML)
   -> target_discovery.py --ingest
        - domain extraction + dedupe (blog/aggregator noise filtered)
        - scoring: domain keywords + TITLE signal phrases + api/docs surface
   -> targets_<interest>.json (scored, rationale, sample_urls)
   -> warel/domcap collector on the top-scored domains
        (confirms: upload endpoints, accepted formats, metadata rendering)
   -> pick specs from payloads/ + battery, deliver via delivery layer
```

## Why titles carry the signal

Domain strings alone under-score the best targets: `deepgram.com` has no
interest keyword, but its result title ("speech recognition voice agent
API - streaming ASR") carries 2-3 signal phrases. Always harvest
title+URL pairs, not bare URLs. Search APIs and result pages both provide
them; the ingestor accepts either JSON `[{"title","url"}]` or raw text.

## Scoring tiers (heuristic, human-confirmed)

| Score | Meaning | Action |
|---|---|---|
| >=60 | multiple strong signals | priority: warel collect + docs read + spec pick |
| 40-59 | clear audio-API surface | collect, check bounty scope first |
| 20-39 | adjacent (frameworks/SDKs) | collect only if interest is supply-chain |
| <20 | landed here incidentally | drop |

Worked example (tts_voice_ai, 2026-09-23, 18 domains from 2 searches):
speechmatics 52, elevenlabs 50, inworld 50, bandwidth/cartesia/twilio/vapi/
zegocloud 40, assemblyai/deepgram/livekit/pipecat/retell/rev 30. Two web
searches produced a prioritized 18-target list in seconds — against hosts
you'd never find by scanning your own machines.

## Scaling the collection

- `--print-queries` emits all engines per query; rotate engines to avoid
  rate limits; store results per query and re-ingest incrementally (the
  dedupe is per-run, so merge targets_*.json lists afterward).
- For bug_bounty interest, the queries target program platforms directly —
  every harvested domain is pre-authorized by construction.
- After collection, run the full lab chain per domain:
  `pipeline_scan`-equivalent via warel fingerprints (wasm/decoder strings in
  their JS bundles), then `build_payload.py` specs matched to the formats
  their docs claim to accept.

## Demo provenance

targets_tts_voice_ai.json in this repo was generated live from two web
searches on 2026-09-23 (see chat). Reproduce: run `--print-queries`, paste
fresh results into a JSON file, `--ingest`.

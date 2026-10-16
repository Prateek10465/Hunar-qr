# API

| Method | Path | Notes |
|---|---|---|
| GET | /healthz | liveness |
| GET | /api/meta | mode, providers in use, demo flag |
| GET | /api/stats | passports issued, messages checked by verdict |
| GET | /.well-known/did.json | issuer DID document and public key |
| POST | /api/analyze | JSON `{text, qr_text?}` → score, verdict, findings, urls, upis |
| POST | /api/analyze-image | multipart `image` (+ optional `text`): decode the QR, then analyze its content |
| POST | /api/passports | **demo-gated**. multipart: `name`, `trade`, `language`, `mentor_name`, `hours`, `learner_type`, `photo` (or `use_sample_photo`), `audio` (or `use_sample_voice`) |
| GET | /api/demo-passport | **demo-gated**. Mints or returns a sample passport |
| GET | /api/passports/{id}?s=sig | credential JSON (404 without a valid sig) |
| POST | /api/verify | JSON `{payload, credential?}`: a verification URL or `HQR1.<id>.<sig>` |
| GET | /v/{id}?s=sig | hosted verification page |
| GET | /v/{id}/evidence.jpg, /v/{id}/qr.png | same capability rule |
| POST | /api/chat | **demo-gated**. Web demo chat against the real bot |
| GET/POST | /webhook/whatsapp | Meta handshake and inbound messages (POST needs valid `X-Hub-Signature-256`) |

Errors are JSON `{detail}`. Limits: body size (`MAX_UPLOAD_BYTES`) and per-IP rate limits.

## ASR provider contract (`ASR_PROVIDER=http`)
`POST ASR_URL` multipart with `audio` (file) and `lang_hint`; bearer `ASR_TOKEN` if set. Expected JSON: `{"text": "...", "english": "..." (optional), "language": "ta" (optional), "liveness": "passed|failed|not_checked" (optional)}`. A Bhashini pipeline needs a thin service in front that speaks this. Adapt `HttpASR` in providers.py if yours differs.

## Vision provider (`VISION_PROVIDER=claude`)
Calls the Anthropic Messages API with the photo and the trade rubric. The image is treated as untrusted; only numeric scores are used, and item names come from our own rubric.

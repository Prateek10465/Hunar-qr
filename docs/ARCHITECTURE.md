# Architecture

```
WhatsApp user ─► Meta Cloud API ─► POST /webhook/whatsapp ─┐
Web demo ───────────────────────► POST /api/chat ──────────┤
                                                           ▼
                                                    Bot (state machine)
                                      ┌──────────────┬─────┴───────┬──────────────┐
                                      ▼              ▼             ▼              ▼
                               fraud.analyze   PassportService   imaging       Store (SQLite)
                                               ASR / Vision      QR, quality
                                               Issuer (ECDSA)
Employer ─► /v/{id}?s=sig ─► hosted verification page
```

## Modules (backend/app)
| File | Role |
|---|---|
| main.py | `create_app()`: routes, rate limits, security headers, static web |
| bot.py | Conversation flow shared by WhatsApp and the web chat. LANG → MENU; passport: NAME → TRADE → MENTOR → HOURS → CONSENT → PHOTO → VOICE |
| passports.py | Mint pipeline (receive, Aadhaar anchor, live face verification, craftsmanship check, sign, QR) and verification |
| credentials.py | Canonical JSON, ECDSA P-256 sign/verify (raw r‖s), DID document |
| providers.py | Pluggable ASR, vision and TTS. Mock by default |
| fraud.py | Rule-based scam scoring. Port of the browser engine |
| imaging.py | Blur/brightness/size checks, EXIF strip via re-encode, QR decode/generate |
| store.py | SQLite (WAL): passports, conversations, seen message IDs, check counters |
| whatsapp.py | Signature check, webhook parsing, media download/upload, sending |
| pages.py | Server-rendered verification page, all values HTML-escaped |

## Credential
W3C VC-style JSON with an `assurance` block. Level is `demo` if any provider is a mock, otherwise `ai-assisted`. The signature covers canonical JSON (sorted keys, no whitespace). The issuer public key is at `/.well-known/did.json`.

## Verification link
`/v/{id}?s={signature}`. The signature is a capability: without it the endpoints return 404, so IDs cannot be enumerated.

## Fraud engine parity
`web/index.html` contains the JS engine; `fraud.py` ports it. `tests/test_fraud_parity.py` runs a 28-message corpus (including Tamil text and a Cyrillic look-alike) through both and requires identical results.

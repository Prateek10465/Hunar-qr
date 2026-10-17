# Hunar-QR

AI-verified vernacular **Skill Passport** + anti-phishing **Job Shield**, delivered over WhatsApp.
Built for the Seva First Innovation Challenge (Level 3 Open, Track A).

> Not an official Government of India service. The government-style palette is a design choice for familiarity; it carries no emblem and no official endorsement.

## What it does
- **Skill Passport**: a worker answers a few questions in any of India's 22 scheduled languages (Tamil, Hindi, Telugu, Bengali, Marathi, Gujarati, Kannada, Malayalam, Punjabi, Odia, Assamese, Urdu, Sanskrit, etc.) or English, verifies their Aadhaar identity, sends a live selfie with their workpiece and an optional demonstration video. The backend validates physical presence and craftsmanship, and issues a tamper-evident signed credential with a QR code. An employer scans it and sees the verification page.
- **Job Shield**: forward any job message or QR code. The bot flags fee demands, shortened links, look-alike domains and blocklisted UPI IDs, and replies in the worker's language.

## Quick start

### On Windows (PowerShell)
From the repository root (`hunar-qr`):
```powershell
# Option A: Activate venv and run
.\.venv\Scripts\Activate.ps1
python -m uvicorn app.main:create_app --factory --app-dir backend --port 8000 --reload

# Option B: Run directly using the virtual environment python
.\.venv\Scripts\python.exe -m uvicorn app.main:create_app --factory --app-dir backend --port 8000 --reload
```

### On macOS / Linux (or with Make)
```bash
make install          # venv, Python deps, e2e deps
make run              # http://localhost:8000 (demo UI + API)
make test             # backend tests
# or manually:
source .venv/bin/activate
python -m uvicorn app.main:create_app --factory --app-dir backend --port 8000 --reload
```
Or with Docker:
```bash
cp .env.example .env && docker compose up --build
```
Open **http://localhost:8000** in your browser. Use the **Chat** tab to interact with the bot, and the **Verify** tab to scan and verify passports.

## Status: what is verified and what is not
| Area | State |
|---|---|
| Fraud engine (Python and JS, kept identical by a parity test) | Tested |
| Credential signing and verification (ECDSA P-256) | Tested |
| Photo checks, QR decode/generate, EXIF stripping | Tested |
| API, bot state machine, privacy properties | Tested |
| WhatsApp Cloud API, Claude vision and HTTP ASR adapters | Tested against **mock transports only**. Never run against the real services. |
| Mock ASR and vision | Return sample values. Credentials made with them are labelled assurance `demo`. |
| Docker image and CI workflow | Written, **not built or run**. |
| Tamil and Hindi bot text | Machine-written. Needs native-speaker review before real use. |
| Real-network CDN loading of the demo page's QR libraries | Not checked from a real browser. |

## Layout
```
backend/   FastAPI app (app/), tests (tests/)
web/       demo page, served at / by the backend, also works standalone
e2e/       jsdom end-to-end tests
docs/      ARCHITECTURE, API, SECURITY, WHATSAPP_SETUP, DEMO_SCRIPT
```
Run the server with `python -m uvicorn app.main:create_app --factory --app-dir backend --port 8000` (or `cd backend && python -m uvicorn app.main:create_app --factory`). Note that `--factory` is required because `create_app` is an application factory.

## Going beyond the demo
1. Set `ENABLE_DEMO_API=false` and a real `PUBLIC_BASE_URL`.
2. Set `VISION_PROVIDER=claude` with an API key, and `ASR_PROVIDER=http` with your speech service (contract in docs/API.md).
3. Connect WhatsApp: docs/WHATSAPP_SETUP.md.
4. Back up `DATA_DIR`. It holds the issuer key; losing it invalidates every credential you issued.

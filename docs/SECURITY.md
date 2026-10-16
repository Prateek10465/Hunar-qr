# Security and privacy

## What is protected
- Phone numbers are stored only as an HMAC hash. Scam-check text is stored only as SHA-256 plus verdict. Tests assert both.
- Photos have EXIF/GPS removed (JPEG re-encode) and are stored only with a passport the worker consented to.
- Verification links are capability URLs; passports cannot be enumerated.
- WhatsApp webhooks require a valid HMAC signature unless `ALLOW_UNSIGNED_WEBHOOK=true` (testing only) and are de-duplicated by message ID.
- Verification page: CSP, escaped output, security headers. Rate limits and a request size guard are on.
- The vision prompt treats the image as untrusted and takes only scores from the reply.

## Known limitations
- Mock ASR/vision return sample values. `demo` assurance credentials must not be treated as verified skills.
- A photo cannot prove who made the work. Mentor attestation and consent are recorded, not independently checked.
- The fraud engine is rule-based. It will miss novel scams and may flag legitimate messages; the verdict is advice, not proof.
- Rate limiting is in-memory and per process. Use a gateway for multi-instance deployments.
- SQLite suits one instance. Move to Postgres for scale.
- Losing the issuer key invalidates all credentials; there is no rotation flow yet.
- Tamil/Hindi text has not been reviewed by native speakers.
- Production needs: `ENABLE_DEMO_API=false`, HTTPS, a real data-protection review (DPDP Act consent and retention), and an independent security audit.

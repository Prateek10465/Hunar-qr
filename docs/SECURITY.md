# Security and privacy

## What is protected
- Phone numbers are stored only as an HMAC hash. Scam-check text is stored only as SHA-256 plus verdict. Tests assert both.
- Photos have EXIF/GPS removed (JPEG re-encode) and are stored only with a passport the worker consented to.
- Verification links are capability URLs; passports cannot be enumerated.
- WhatsApp webhooks require a valid HMAC signature unless `ALLOW_UNSIGNED_WEBHOOK=true` (testing only) and are de-duplicated by message ID.
- Verification page: CSP, escaped output, security headers. Rate limits and a request size guard are on.
- The vision prompt treats the image as untrusted and takes only scores from the reply.
- Live Face Biometric Anchor: The worker is required to submit a live selfie holding the workpiece. Facial presence is verified via YuNet deep learning face detection and anchored directly to the verified UIDAI Aadhaar identity, preventing stock image uploads and impersonation.
- Hands-on Work Showcase Video: Workers can submit a 30–60 second video demonstrating their trade craftsmanship. The video is hashed with SHA-256 into the Verifiable Credential and hosted directly on their capability verification profile page (`/v/{pid}`), giving employers and clients verifiable proof of actual hands-on technique.

## Known limitations
- Mock ASR/vision return sample values. `demo` assurance credentials must not be treated as verified skills.
- The fraud engine is rule-based. It will miss novel scams and may flag legitimate messages; the verdict is advice, not proof.
- Rate limiting is in-memory and per process. Use a gateway for multi-instance deployments.
- SQLite suits one instance. Move to Postgres for scale.
- Losing the issuer key invalidates all credentials; there is no rotation flow yet.
- Tamil/Hindi text has not been reviewed by native speakers.
- Production needs: `ENABLE_DEMO_API=false`, HTTPS, a real data-protection review (DPDP Act consent and retention), and an independent security audit.

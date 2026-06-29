# Business Model Brainstorm

**Status:** Reference doc — not yet implemented. Captured 2026-06-28.

The goal: introduce a free tier and a premium subscription so that AI inference costs (Claude) don't scale linearly with user growth. Free tier uses already-cached Genius/community data; premium unlocks Claude.

---

## Tier breakdown

### Free tier (no AI inference cost)

Composed entirely from data we already fetch and store:

| Source | What it contributes |
|---|---|
| **Genius annotations (referents)** | Community-written explanations of specific lyrics. Currently bundled as "community commentary." Promote to main analysis slot. |
| **Genius song description** | Editorial blurb when present |
| **Album + artist context** | "From [album] (2023), produced by [producer]" |
| **YouTube top comments** | Already scraped — one or two appear as "what fans are saying" |
| **Top lyric (most-annotated)** | Highlight the line with the most community engagement |

User experience: song page renders fast; analysis panel shows community commentary; CTA in place of the AI section: **"🔒 Get Lyriq's deep analysis"**.

### Premium tier (Claude-powered)

Everything we currently generate:
- TL;DR
- Overall meaning
- Emotional tone
- Themes
- Per-line breakdowns
- (Future) audio previews, related artists, recommendations

---

## Authentication

**Recommendation: Supabase Auth.** Already using Supabase; built-in email/password + Google OAuth; free up to 50k MAU; integrates with existing tables via Row Level Security.

Alternatives considered:
- **Clerk** — more polished UI components, pay-per-MAU pricing
- **NextAuth.js** — free, self-hosted, more setup work
- **Auth0** — enterprise-grade, expensive

---

## Payments

**Recommendation: Stripe Checkout + Customer Portal.** Hosted UI, PCI-compliant, free to use beyond the 2.9% + $0.30 per transaction. Three backend endpoints:

1. `POST /billing/checkout` → returns Stripe Checkout URL → redirect user
2. `POST /billing/portal` → returns Customer Portal URL for self-service management
3. `POST /webhooks/stripe` → receives subscription created/updated/cancelled events, updates `subscription_tier` column

Net at $4.99/mo: ~$4.55 per subscriber after fees.

Alternatives:
- **Paddle / Lemon Squeezy** — Merchant of Record (handle international tax). Higher fees, less compliance burden.

---

## Pricing brainstorm

| Tier | Sweet spot | Logic |
|---|---|---|
| Free | Unlimited basic analysis | Discovery, viral loop |
| Premium | $4.99–$7.99/mo or $39–$49/year | Below Spotify/Apple Music ($11). Lyric analysis is not daily-use — needs to feel like a small commitment. |
| Annual discount | 33–40% off | Standard SaaS lever, reduces churn |

Risks: too cheap signals low value; too expensive deters trial. **$4.99/mo with 7-day free trial** is the safe MVP starting point.

---

## Beta strategy

Add `subscription_tier` column to users with values `free` / `premium` / `beta`. Beta is functionally identical to premium but bypasses Stripe. Workflow:

1. Launch with all new signups defaulting to `beta`
2. Validate auth + features without Stripe complexity
3. When beta ends: change default for new signups to `free`; existing betas get an email — "one free month of premium, then standard pricing applies"
4. Add Stripe wiring as a separate later phase

This keeps payments out of the critical path during early validation.

---

## Security concerns (organized by severity)

### Critical (must fix before any paying users)

- **Tier enforcement on backend.** Never trust the frontend's claim of "I'm premium." Every `/songs/{id}/deep-analyze` request must check the JWT and look up the user's tier server-side.
- **Stripe webhook signature verification.** Anyone can POST to your webhook URL. Stripe signs requests — verify the signature or attackers can spoof "subscription created" events.
- **JWT in httpOnly cookies, not localStorage.** Protects against XSS token theft.
- **CORS lockdown.** Current `allow_origins=["*"]` is dev-only — must restrict to specific frontend domain in production.
- **Rate limiting.** Otherwise a free user could spam `/analyze` (lyric scraping). Add per-IP and per-user limits via `slowapi` or similar FastAPI middleware.

### Important (handle within first month of launch)

- Email verification on signup (prevents farming the free tier)
- Audit existing endpoints for injection vulnerabilities (already caught one in `search_cached_albums`)
- Privacy Policy + Terms of Service live before taking payments (Stripe requires this)
- Account deletion endpoint (GDPR/CCPA compliance)
- Logging that doesn't include PII (no emails or tokens in logs)

### Nice to have

- 2FA support (Supabase Auth has TOTP built-in)
- Anti-abuse: rate-limit signups per IP, require email verification
- Audit log of subscription tier changes

---

## Open questions

1. **Free tier limits** — truly unlimited basic analysis, or X songs/month? Limits create conversion urgency but frustrate casual users.
2. **When premium expires** — does the user lose access to previously-analyzed deep interpretations, or keep them read-only? (Most SaaS keeps read-only.)
3. **Existing analyzed songs** — DB already has deep interpretations for many songs. Are those public (anyone can read) or do free users still see the CTA on them? Public is friendlier; gated is more revenue.
4. **Beta exit** — how long is the beta? What's the comms plan when it ends?
5. **Refunds + chargebacks** — Stripe gives you a dashboard; you need a policy ("no refunds after 14 days" is standard).
6. **Geographic restrictions** — selling internationally adds tax complexity. Paddle/Lemon Squeezy handle this at higher fees; Stripe leaves it to you.

---

## Migration path (when ready to implement)

Each phase ships independently:

1. **Add Supabase Auth.** Gate nothing yet — login optional. Validate it works.
2. **Add `subscription_tier` column to users**, default `beta`. Wire backend to read tier from JWT.
3. **Modify `/songs/{id}/deep-analyze` to require premium/beta tier.** Free users get 403 with upgrade prompt.
4. **Add Stripe Checkout + webhook + Customer Portal.**
5. **Flip default for new signups from `beta` → `free`.** Existing betas get grandfather email.

The current deep-analyze split (basic on `/analyze`, AI on `/songs/{id}/deep-analyze`) is already the architectural seam — the paywall lives on that one endpoint.

---

## Cost projections

Rough Claude API cost per analysis: $0.01–0.05 (Sonnet, ~2-3k tokens).

| Scenario | Analyses/mo | Claude cost/mo | Subscribers needed @ $5 |
|---|---|---|---|
| 1k users × 10 analyses | 10k | $100–$500 | 100 |
| 10k users × 5 analyses | 50k | $500–$2500 | 500 |
| 100k users × 5 analyses | 500k | $5k–$25k | 5000 |

Conversion rates for freemium SaaS typically run 2–5%. At 2% conversion, you need 5,000 free users to get 100 paying subscribers ($500/mo). Math is workable but requires real distribution.

---

## Related files

- [Legal templates](./legal-templates.md) — Terms of Service / Privacy Policy / DMCA scaffolds
- `backend/services/musixmatch.py` — wired up but not used; swap before public/monetized launch
- `backend/routes/songs.py` — `/songs/{id}/deep-analyze` is the paywall seam

# Cost-Capped Launch Plan

**Status:** Current operating plan. Captured 2026-06-30.

This is the realistic shape for going public with Lyriq: free for everyone, capped Claude spending from the owner's pocket, optional tip jar to offset costs. No auth, no Stripe subscriptions, no tier code. The full freemium model in [business-model-brainstorm.md](./business-model-brainstorm.md) is preserved as a future option if traffic actually justifies it.

---

## Core decisions

| Decision | Choice |
|---|---|
| Pricing model | **Free for all** |
| Cost coverage | Owner-funded with hard monthly cap |
| Cost-offset mechanism | Optional tip jar (Stripe Payment Link or Ko-fi) |
| Claude model | **Switch from Sonnet to Haiku 4.5** (~3× cost reduction, minor quality drop) |
| Trigger | **On-demand only.** User clicks "Generate analysis" — no auto-trigger |
| Corpus seeding | **Pre-analyze ~200 popular songs** one-time at owner expense (~$5 with Haiku) |
| Authentication | **None.** Anonymous usage |
| Lyrics source | Genius (dev) → Musixmatch (only if scale justifies) |

---

## Cost math

### Realistic monthly cost ranges (after Haiku swap)

| Scenario | Analyses/mo | Haiku cost | Within $20 cap? |
|---|---|---|---|
| 10 friends, occasional use | ~50 | ~$1.50 | Yes |
| 100 visitors, 30% try analysis | ~300 | ~$9 | Yes |
| Mildly viral, 1,000 visits | ~1,500 | ~$45 | **Triggers cap** |
| Hacker News hug-of-death day | ~10,000 | ~$300 | **Cap blocks excess** |

### Fixed costs

| Item | Amount/mo |
|---|---|
| Supabase | Free tier (sufficient at this scale) |
| Backend hosting (Railway/Render) | ~$5 |
| Domain | ~$1 (amortized) |
| Stripe Payment Link or Ko-fi | $0 (no platform fees on the free model) |
| **Total fixed** | **~$6** |

Plus owner-capped Claude budget of **$20/mo** = total worst-case exposure **~$26/mo**.

### What happens at the cap

When the monthly Claude budget is hit:
- `/songs/{id}/deep-analyze` returns 429 with a friendly message
- Frontend shows: "Monthly analysis budget reached. New analyses resume next month. Want to help cover costs? [Tip jar →]"
- Browsing existing analyses (community + pre-seeded corpus) continues to work freely
- Caps reset on the 1st of each month

---

## Implementation pieces

### 1. Switch Claude model

Single config change in `backend/services/anthropic.py`:
```python
MODEL = "claude-haiku-4-5-20251001"  # was: claude-sonnet-4-6
MAX_TOKENS = 2500  # may need to increase slightly for Haiku's verbosity
```

Test that the output quality is acceptable on a few sample songs. If not, fall back to Sonnet for new analyses and accept the 3× cost.

### 2. Monthly budget tracker

Track Claude usage server-side. Simplest implementation:

```python
# backend/services/claude_budget.py
import time
from datetime import datetime, timezone

_spend_this_month: float = 0.0
_month_started: str = ""

MONTHLY_BUDGET_USD = 20.0

# Haiku 4.5 pricing per 1M tokens
HAIKU_INPUT_PER_1M = 1.0
HAIKU_OUTPUT_PER_1M = 5.0


def reset_if_new_month():
    global _spend_this_month, _month_started
    current = datetime.now(timezone.utc).strftime("%Y-%m")
    if _month_started != current:
        _spend_this_month = 0.0
        _month_started = current


def record_usage(input_tokens: int, output_tokens: int):
    reset_if_new_month()
    cost = (input_tokens / 1_000_000) * HAIKU_INPUT_PER_1M
    cost += (output_tokens / 1_000_000) * HAIKU_OUTPUT_PER_1M
    global _spend_this_month
    _spend_this_month += cost


def within_budget() -> bool:
    reset_if_new_month()
    return _spend_this_month < MONTHLY_BUDGET_USD


def remaining_usd() -> float:
    reset_if_new_month()
    return max(0.0, MONTHLY_BUDGET_USD - _spend_this_month)
```

In `routes/songs.py`'s `deep_analyze` endpoint:
```python
if not claude_budget.within_budget():
    raise HTTPException(429, detail="Monthly analysis budget reached. Try again next month.")
```

And in `anthropic.py`, record usage from each response:
```python
claude_budget.record_usage(
    response.usage.input_tokens,
    response.usage.output_tokens,
)
```

**Limitation of in-memory counter:** resets on every backend restart, undercounting actual spend. For more accuracy, persist to a `claude_spend` table in Supabase. For MVP, the in-memory counter is fine — generally biased toward under-counting, which means you might run a few dollars over the cap. Tolerable.

### 3. Tip jar link

No need to integrate Stripe Checkout for this. Two simple options:

**Option A: Stripe Payment Link** (5 minutes)
- Go to Stripe Dashboard → Payment Links
- Create a one-time payment ($5, $10, $20 options)
- Use the URL as a footer link: "Support hosting ☕"

**Option B: Ko-fi or Buy Me a Coffee** (10 minutes)
- Sign up for free Ko-fi account
- Link to your Ko-fi page from the footer
- Lower platform fees, more recognizable UX for casual users

Either works. Stripe is more general; Ko-fi feels more "indie-creator." Pick whichever feels right.

**Footer copy (important):**
> ☕ Support hosting — Lyriq is a free hobby project. Tips help cover AI costs but are completely optional. Donations don't unlock any features.

That last sentence matters legally — it makes clear there's no quid-pro-quo between tips and content access. Removes any "you're selling access to copyrighted derivatives" framing.

### 4. Pre-seeded corpus

One-off script to pre-analyze popular songs:
```python
# backend/scripts/seed_corpus.py
from services import billboard, ...

async def seed():
    songs = await billboard.get_hot_100(100)
    for song in songs:
        # Skip if already analyzed
        existing = supabase.find_song(song["title"], song["artist"])
        if existing and has_interpretation(existing):
            continue
        # Run full analyze + deep-analyze flow
        ...
```

Run once after launch. Costs ~$3-5 with Haiku. Result: the homepage's Billboard cards are mostly clickable into pre-analyzed content from day one.

### 5. No auth, no tier check

The architecture from the analysis-first refactor stays — `/songs/{id}/deep-analyze` is still the gate, just with a budget check instead of a tier check. No `users` table, no Supabase Auth, no Stripe subscription products.

If the project ever justifies a paid tier, the deep-analyze endpoint is still the natural seam.

---

## Compliance checklist (lighter than the paywall version)

| Item | Required? | Effort |
|---|---|---|
| Terms of Service | Yes (Stripe/Ko-fi require it) | Use [legal-templates.md](./legal-templates.md), ~1 hour |
| Privacy Policy | Yes (Stripe/Ko-fi require it) | Same template, ~1 hour |
| DMCA designated agent | Recommended | $6 + 15 min at copyright.gov |
| AI-generated content disclaimer | Yes | One line on each analysis page |
| "Lyrics from Genius" attribution | Yes | Footer + below lyrics drawer |
| Takedown email (`dmca@yourdomain`) | Yes | Set up forwarding to your inbox |
| No-quid-pro-quo tip messaging | Yes | One line near the tip button |
| Cookie consent (if EU users) | If applicable | Use a free banner library |
| GDPR account deletion | **No** (no accounts) | N/A |
| Refund policy | **No** (no purchases) | N/A |
| Subscription tier enforcement code | **No** | N/A |

Total compliance effort: roughly **4-5 hours + $6**. Much lighter than the full paywall path.

---

## Legal risk summary (with tip jar)

| Threat | Likelihood at hobby scale | Worst case |
|---|---|---|
| Genius sends C&D | Low | Take down lyrics, move to Musixmatch faster |
| Music publisher C&D | Very low | Take down specific songs |
| Lawsuit | Effectively zero | N/A |
| Stripe/Ko-fi account suspension | Low | Switch platforms |
| User defamation complaint over AI analysis | Low | Remove that analysis, disclaimer covers most cases |
| Tax obligations | Low (small tips) | Just track income from day one |

Tips do bump the legal posture slightly because you can't claim "no commercial activity" — but the practical risk delta is small at hobby scale. Same level of caution as any small free site that accepts donations.

---

## Trigger conditions to revisit this model

Switch to the paywall path (or another model) if:

- **Monthly traffic exceeds your cap regularly**: 3+ months hitting the $20 ceiling, with users complaining about the lockout. Demand is real → time to think about charging.
- **Tip jar income exceeds $200/month consistently**: Worth formalizing into a real tier so you can scale costs accordingly.
- **Specific feature request shows up repeatedly**: Like "I want my analysis history" or "I want priority queue" — these are signals users would pay for value-adds beyond just the base analysis.
- **Threat letter arrives**: From Genius or a publisher. Time to seriously consider Musixmatch migration.

Until any of those happen, the cost-capped + tip jar model is sustainable indefinitely.

---

## Migration if you ever do go paid

The analysis-first architecture already has the seam:
- Add `user_id` column to analyses (currently anonymous)
- Wire Supabase Auth
- Add `subscription_tier` check in `/songs/{id}/deep-analyze` BEFORE the budget check:
  - If `free` and song not yet analyzed: 402 Payment Required
  - If `premium` or `beta`: proceed (subject to budget)
- Stripe Checkout + Customer Portal as described in business-model-brainstorm.md

No fundamental refactor needed. The cost-capped phase is forward-compatible with a future paywall phase.

---

## Related files

- [business-model-brainstorm.md](./business-model-brainstorm.md) — Deferred paywall plan, retained as future option
- [musixmatch-migration-plan.md](./musixmatch-migration-plan.md) — Lyrics licensing path, triggered by traffic/legal needs
- [legal-templates.md](./legal-templates.md) — ToS, Privacy, DMCA templates

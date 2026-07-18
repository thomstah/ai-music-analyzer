# Analysis-First Refactor (Cost-Capped Edition)

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Reframe the song page as analysis-first while staying on Genius lyrics indefinitely. Add monthly Claude budget cap and tip jar so launch is sustainable.

**Architecture:** Two-column song page — analysis main (left, ~60%), lyrics column (right, ~40%). Lyrics stay cached in `songs.lyrics` (Genius is free). Claude prompt updated for self-contained breakdowns. Model swapped to Haiku 4.5. One-off re-analysis pass updates all stored songs.

**Cost-cap context:** Implements the [cost-capped launch plan](../../notes/cost-capped-launch-plan.md). No paywall. No auth. Budget enforced via in-memory monthly tracker on the `/songs/{id}/deep-analyze` endpoint.

**Tech Stack:** Same as today. No new dependencies.

---

## Decisions locked in

| Decision | Choice |
|---|---|
| Layout | Two-column: analysis main (left), lyrics column (right). Stacks on mobile. |
| Lyrics caching | Keep `songs.lyrics` column. Cache from Genius as today. |
| Breakdown style | Self-contained — each card has the quoted lyric + commentary |
| Click-to-explain | **Removed** (breakdown cards are self-sufficient now) |
| Claude model | Switch Sonnet 4.6 → Haiku 4.5 |
| Re-analysis | Yes — re-analyze every stored song under new prompt + Haiku |
| Budget cap | $20/mo Claude budget, in-memory tracker |
| Out-of-budget UX | Friendly lockout + tip-jar nudge |
| Tip jar | **Deferred until launch.** Footer carries disclaimers only for now. |
| Seed corpus | Defer to a separate pass after refactor lands |

---

## File Map

### Backend
| File | Change |
|---|---|
| `backend/services/anthropic.py` | Switch `MODEL` to Haiku 4.5. Update `SYSTEM_PROMPT` to require verbatim quoted lyrics in each breakdown. Wire in budget tracker. |
| `backend/services/claude_budget.py` | NEW — in-memory monthly spend tracker with `record_usage`, `within_budget`, `remaining_usd` |
| `backend/routes/songs.py` | `deep-analyze` checks budget before calling Claude, returns 429 with friendly message when over cap. Add `POST /admin/reanalyze-all` for backfill. |
| `backend/tests/` | Update anthropic prompt test, add budget tracker tests, add reanalyze test |

### Frontend
| File | Change |
|---|---|
| `frontend/app/song/[id]/page.tsx` | Flip column priority: analysis on left (~60%), lyrics on right (~40%). |
| `frontend/components/AnalysisPanel.tsx` | Becomes the primary content area (no longer sticky sidebar). Breakdown cards prominent. |
| `frontend/components/BreakdownCard.tsx` | Each card shows quoted lyric block prominently (multi-line, bordered) + commentary below |
| `frontend/components/LyricsPanel.tsx` | Becomes the right column. Removes click-to-explain props. Read-only display. |
| `frontend/components/Footer.tsx` | NEW — site-wide footer with tip-jar link, AI disclaimer, attribution |
| `frontend/app/layout.tsx` | Mount Footer |

---

## Task 1: Backend — model, prompt, budget

- [ ] **Step 1: Switch Claude model in `backend/services/anthropic.py`**

```python
MODEL = "claude-haiku-4-5-20251001"
MAX_TOKENS = 2500
```

- [ ] **Step 2: Update `SYSTEM_PROMPT` to require verbatim quotes**

Add explicit instruction: each `key_lyric_breakdowns.lyric` field must contain 5-10 verbatim consecutive lyric lines (newline-separated). The `breakdown` is commentary on those specific lines. Never reference "the bridge" or "this line" — always include the actual quoted lines.

- [ ] **Step 3: Create `backend/services/claude_budget.py`**

```python
import time
from datetime import datetime, timezone

MONTHLY_BUDGET_USD = 20.0
HAIKU_INPUT_PER_1M = 1.0
HAIKU_OUTPUT_PER_1M = 5.0

_state: dict = {"month": "", "spend": 0.0}


def _reset_if_new_month():
    current = datetime.now(timezone.utc).strftime("%Y-%m")
    if _state["month"] != current:
        _state["month"] = current
        _state["spend"] = 0.0


def record_usage(input_tokens: int, output_tokens: int) -> None:
    _reset_if_new_month()
    cost = (input_tokens / 1_000_000) * HAIKU_INPUT_PER_1M
    cost += (output_tokens / 1_000_000) * HAIKU_OUTPUT_PER_1M
    _state["spend"] += cost


def within_budget() -> bool:
    _reset_if_new_month()
    return _state["spend"] < MONTHLY_BUDGET_USD


def remaining_usd() -> float:
    _reset_if_new_month()
    return max(0.0, MONTHLY_BUDGET_USD - _state["spend"])
```

- [ ] **Step 4: Wire budget check into `/songs/{id}/deep-analyze`**

Before calling Claude, check budget. If exceeded, raise:
```python
raise HTTPException(
    status_code=429,
    detail="Monthly AI budget reached. New analyses resume on the 1st. "
           "Browse already-analyzed songs or support hosting via the tip jar.",
)
```

After Claude returns, record usage:
```python
claude_budget.record_usage(response.usage.input_tokens, response.usage.output_tokens)
```

- [ ] **Step 5: Add `POST /admin/reanalyze-all` for backfill**

Iterates over all songs with stored interpretations. For each, re-runs analysis under the new prompt + Haiku model and updates the interpretation. Used once after deploy.

- [ ] **Step 6: Backend tests + commit**

```bash
cd backend && pytest tests/ -q
git add backend/ && git commit -m "feat: Haiku model + verbatim-quote breakdowns + monthly Claude budget cap"
```

---

## Task 2: Frontend — layout flip + standalone cards

- [ ] **Step 7: Restructure `app/song/[id]/page.tsx`**

Today's layout: `flex-col-reverse lg:flex-row` with lyrics left (flex-1), analysis right (w-80 sticky).

New layout: Analysis is the primary content (lg:flex-1, takes most space), lyrics are the secondary column (lg:w-96 sticky). Mobile: analysis first, lyrics below.

- [ ] **Step 8: Update `AnalysisPanel.tsx` for primary-content role**

Remove sticky sidebar styling. Make it a long-form reading experience: TL;DR, themes/tone, meaning, then standalone breakdown cards stacked vertically, then community.

- [ ] **Step 9: Rewrite `BreakdownCard.tsx`**

Each card prominently displays the quoted lyric as a multi-line block (left-bordered, italic, slightly larger). Commentary follows in regular paragraph style underneath. Self-contained — readable without scrolling to lyrics.

- [ ] **Step 10: Update `LyricsPanel.tsx`**

Remove click-to-explain logic: drop `onLineSelect`, `selectedLyric` props. Just renders lyrics line-by-line in a scroll-able sticky column. No interactions.

- [ ] **Step 11: Remove click-handler state from song page**

Drop `selectedBreakdown`, `selectedLyric`, `handleLineSelect`. Simpler component.

- [ ] **Step 12: Run TypeScript + build checks + commit**

```bash
cd frontend && npx tsc --noEmit && npx next build
git add frontend/ && git commit -m "feat: analysis-first two-column song page with self-contained breakdown cards"
```

---

## Task 3: Footer with disclaimers (tip jar deferred)

- [ ] **Step 13: Create `frontend/components/Footer.tsx`**

Site-wide footer with disclaimers only for now:
- "Lyriq's analyses are AI-generated commentary, not endorsed by artists or rights holders."
- "Lyrics and community annotations provided by Genius."

Tip jar will be added in a separate pre-launch pass.

- [ ] **Step 14: Mount Footer in `app/layout.tsx`**

Wraps `{children}` so it appears on every page.

- [ ] **Step 15: Commit**

```bash
git add frontend/components/Footer.tsx frontend/app/layout.tsx && git commit -m "feat: site footer with AI disclaimer and Genius attribution"
```

---

## Task 4: One-off backfill

- [ ] **Step 16: Run `POST /admin/reanalyze-all` locally**

After backend deploys with the new model + prompt. Re-generates every stored interpretation under Haiku + new prompt. Cost: ~$0.30 total (rough estimate).

- [ ] **Step 17: Spot-check 3-5 re-analyzed songs**

Verify the breakdown cards now show quoted lyrics prominently and read well standalone.

---

## Push

```bash
git push
```

---

## What's deferred

Items NOT in this refactor — to be done in later phases:

- **Seed corpus** (~200 pre-analyzed Billboard songs) — separate pass, can run anytime after this lands
- **ToS / Privacy / DMCA pages** — separate pre-launch task
- **DMCA agent registration** — owner action, not code
- **Cookie consent banner** — pre-launch task
- **Production hosting setup** — pre-launch task
- **Persist budget tracker to DB** — current in-memory tracker resets on backend restart; acceptable for MVP

---

## Risk notes

- **In-memory budget tracker resets on restart.** Spend could exceed cap if backend restarts often. Acceptable for MVP; persist later if needed.
- **Haiku quality vs Sonnet.** Watch the first few re-analyzed songs. If quality drops noticeably, can revert to Sonnet by changing one constant.
- **Tip jar URL is a placeholder.** Owner picks Stripe Payment Link or Ko-fi, hard-codes the URL, no app changes needed beyond that.

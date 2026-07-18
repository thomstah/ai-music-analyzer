# Rate Limits + Budget-Exhausted State Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Protect the $20/mo Claude budget and Genius/Deezer quotas from being drained by one enthusiastic user, and give the frontend a warm degraded state when the monthly cap is hit instead of a raw 500.

**Architecture:**
- **Rate limiter:** in-memory token bucket keyed by client IP; wrapped as a FastAPI dependency and applied to `/analyze` and `/songs/{id}/deep-analyze`. Single-process only — good enough for one uvicorn worker; a docstring note flags what to swap for Redis if the app is ever scaled horizontally.
- **Budget state:** existing `claude_budget.within_budget()` already exists; we (a) enforce it earlier with a friendlier 402 payload, and (b) expose a public `GET /status` so the frontend can render a top-of-page pill without waiting for a failing request.
- **Frontend:** typed error classes for 402 and 429; an inline card in `AnalysisPanel` when analysis is rejected; a tiny `GlobalStatusBar` that reads `/status` once per session.

**Tech Stack:** FastAPI dependencies, asyncio.Lock, existing `services/claude_budget.py`, Next.js App Router (client-side status fetch).

**Non-goals:** No authentication. No fraud prevention. IP-based limiting has known holes (VPNs, shared NAT); the point is a soft cap, not gating.

---

## File Structure

- **Create:** `backend/services/rate_limit.py` — token bucket + `check(key, capacity, refill_per_sec)`.
- **Create:** `backend/routes/status.py` — `GET /status`.
- **Modify:** `backend/main.py` — mount the new status router.
- **Modify:** `backend/routes/songs.py` — attach rate-limit dependency to `/analyze` and `/songs/{id}/deep-analyze`; short-circuit with 402 when budget exhausted.
- **Modify:** `backend/services/claude_budget.py` — add `reset_date_iso()` helper for the status payload.
- **Modify:** `backend/tests/test_routes.py` — coverage for 402 + 429 + status.
- **Create:** `backend/tests/test_rate_limit.py` — unit test for the token bucket.
- **Modify:** `frontend/lib/api.ts` — typed `BudgetExhaustedError` and `RateLimitedError`.
- **Modify:** `frontend/components/AnalysisPanel.tsx` — warm inline card for 402/429.
- **Create:** `frontend/components/GlobalStatusBar.tsx` — session-level "degraded" pill.
- **Modify:** `frontend/app/layout.tsx` — mount the status bar.

---

### Task 1: Token bucket helper

**Files:**
- Create: `backend/services/rate_limit.py`
- Create: `backend/tests/test_rate_limit.py`

- [ ] **Step 1: Write the failing test**

```python
import asyncio
import pytest
import services.rate_limit as rl


@pytest.fixture(autouse=True)
def _clear_state():
    rl._buckets.clear()
    yield


@pytest.mark.asyncio
async def test_bucket_allows_up_to_capacity_then_denies():
    for _ in range(3):
        assert await rl.check("ip:1.2.3.4:analyze", capacity=3, refill_per_sec=0.0) is True
    assert await rl.check("ip:1.2.3.4:analyze", capacity=3, refill_per_sec=0.0) is False


@pytest.mark.asyncio
async def test_bucket_refills_over_time(monkeypatch):
    now = {"t": 0.0}
    monkeypatch.setattr(rl.time, "monotonic", lambda: now["t"])
    key = "ip:5.6.7.8:analyze"

    # Drain 2 tokens.
    assert await rl.check(key, capacity=2, refill_per_sec=1.0) is True
    assert await rl.check(key, capacity=2, refill_per_sec=1.0) is True
    assert await rl.check(key, capacity=2, refill_per_sec=1.0) is False

    # Advance one second: one token should have refilled.
    now["t"] = 1.0
    assert await rl.check(key, capacity=2, refill_per_sec=1.0) is True
    assert await rl.check(key, capacity=2, refill_per_sec=1.0) is False


@pytest.mark.asyncio
async def test_buckets_are_isolated_per_key():
    assert await rl.check("a", capacity=1, refill_per_sec=0.0) is True
    assert await rl.check("a", capacity=1, refill_per_sec=0.0) is False
    # Different key still has its full bucket.
    assert await rl.check("b", capacity=1, refill_per_sec=0.0) is True
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd backend && python3 -m pytest tests/test_rate_limit.py -v`
Expected: FAIL — `ModuleNotFoundError: services.rate_limit`.

- [ ] **Step 3: Implement the bucket**

Create `backend/services/rate_limit.py`:

```python
"""In-memory token bucket rate limiter.

Single-process only. If the app is ever run with multiple uvicorn workers or
horizontally scaled, swap `_buckets` for a Redis-backed store — the `check`
signature can stay the same.
"""
import asyncio
import time

_buckets: dict[str, tuple[float, float]] = {}  # key -> (tokens, last_refill_ts)
_lock = asyncio.Lock()


async def check(key: str, capacity: int, refill_per_sec: float) -> bool:
    """Attempt to consume one token from `key`'s bucket. Returns True if allowed.

    - capacity: max tokens the bucket holds (also the initial fill).
    - refill_per_sec: tokens added per second (0.0 disables refill for the test path).
    """
    now = time.monotonic()
    async with _lock:
        tokens, last = _buckets.get(key, (float(capacity), now))
        if refill_per_sec > 0:
            tokens = min(float(capacity), tokens + (now - last) * refill_per_sec)
        if tokens < 1.0:
            _buckets[key] = (tokens, now)
            return False
        _buckets[key] = (tokens - 1.0, now)
        return True
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd backend && python3 -m pytest tests/test_rate_limit.py -v`
Expected: 3 passed.

- [ ] **Step 5: Commit**

```bash
git add backend/services/rate_limit.py backend/tests/test_rate_limit.py
git commit -m "feat(rate-limit): in-memory token bucket helper"
```

---

### Task 2: FastAPI dependency + wire to routes

**Files:**
- Modify: `backend/routes/songs.py`
- Modify: `backend/tests/test_routes.py`

Budgets:
- `/analyze`: capacity 5, refill 5/min → sustained ~5/min per IP; short bursts of 5 allowed.
- `/songs/{id}/deep-analyze`: capacity 3, refill 3/min.

- [ ] **Step 1: Write the failing test**

Add to `backend/tests/test_routes.py`:

```python
def test_analyze_returns_429_when_rate_limit_exceeded():
    with patch("routes.songs.rate_limit.check", new_callable=AsyncMock, return_value=False):
        response = client.post("/analyze", json={"title": "T", "artist": "A"})
    assert response.status_code == 429
    assert "retry" in response.json()["detail"].lower()
    assert response.headers.get("Retry-After") == "60"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd backend && python3 -m pytest tests/test_routes.py -k rate_limit -v`
Expected: FAIL — currently `/analyze` doesn't consult the limiter.

- [ ] **Step 3: Wire the dependency**

In `backend/routes/songs.py`, add near the other service imports:

```python
import services.rate_limit as rate_limit
from fastapi import Request
```

Add a dependency factory below the imports:

```python
def _client_ip(request: Request) -> str:
    """Best-effort IP: prefer X-Forwarded-For's first hop when running behind a proxy."""
    xff = request.headers.get("x-forwarded-for")
    if xff:
        return xff.split(",")[0].strip()
    return request.client.host if request.client else "unknown"


def rate_limit_dep(capacity: int, refill_per_sec: float, bucket: str):
    async def _dep(request: Request):
        ok = await rate_limit.check(
            f"ip:{_client_ip(request)}:{bucket}",
            capacity=capacity,
            refill_per_sec=refill_per_sec,
        )
        if not ok:
            raise HTTPException(
                status_code=429,
                detail="You're going a bit fast — retry in a minute.",
                headers={"Retry-After": "60"},
            )
    return _dep
```

Attach to the analyze routes. Modify the two existing decorators:

```python
@router.post("/analyze", dependencies=[Depends(rate_limit_dep(5, 5 / 60.0, "analyze"))])
async def analyze(request: AnalyzeRequest):
    ...

@router.post(
    "/songs/{song_id}/deep-analyze",
    dependencies=[Depends(rate_limit_dep(3, 3 / 60.0, "deep"))],
)
async def deep_analyze(song_id: str):
    ...
```

Add `Depends` to the imports if not already present:

```python
from fastapi import APIRouter, HTTPException, Query, Depends
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd backend && python3 -m pytest tests/test_routes.py -k rate_limit -v`
Expected: 1 passed.

- [ ] **Step 5: Commit**

```bash
git add backend/routes/songs.py backend/tests/test_routes.py
git commit -m "feat(rate-limit): apply per-IP limits to /analyze and /deep-analyze"
```

---

### Task 3: Budget-exhausted 402 on `/analyze`

**Files:**
- Modify: `backend/routes/songs.py`
- Modify: `backend/tests/test_routes.py`
- Modify: `backend/services/claude_budget.py`

The existing budget check lives inside the deep-analyze flow; extend the same logic to `/analyze` for new-song analysis (which also calls Claude for the first interpretation the moment deep-analyze fires). Return a warm 402 instead of a generic 500 when the cap is out.

- [ ] **Step 1: Write the failing test**

Add to `backend/tests/test_routes.py`:

```python
def test_deep_analyze_returns_402_when_budget_exhausted():
    song_row = {
        "id": "s1", "title": "T", "artist": "A", "lyrics": "line",
        "genius_id": None, "created_at": None, "metadata": {},
        "interpretations": [],
    }
    with patch("routes.songs.supabase_service.get_song_by_id", return_value=song_row), \
         patch("routes.songs.claude_budget.within_budget", return_value=False):
        response = client.post("/songs/s1/deep-analyze")
    assert response.status_code == 402
    body = response.json()
    assert "budget" in body["detail"].lower()
    assert "resets_on" in body
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd backend && python3 -m pytest tests/test_routes.py -k budget_exhausted -v`
Expected: FAIL — current path either 200s with an unbudgeted call or 500s.

- [ ] **Step 3: Add `reset_date_iso` helper**

In `backend/services/claude_budget.py`, add:

```python
from datetime import date, timedelta

def reset_date_iso() -> str:
    """Return the ISO date the monthly budget resets (the 1st of next month)."""
    today = date.today()
    year = today.year + (1 if today.month == 12 else 0)
    month = 1 if today.month == 12 else today.month + 1
    return date(year, month, 1).isoformat()
```

- [ ] **Step 4: Short-circuit in the deep-analyze route**

Locate the deep-analyze handler in `backend/routes/songs.py`. Before it calls `anthropic_service.generate_interpretation`, insert:

```python
if not claude_budget.within_budget():
    raise HTTPException(
        status_code=402,
        detail=(
            "Lyriq's monthly analysis budget is out. "
            "Existing analyses still work — new ones resume on the 1st."
        ),
        headers={"X-Budget-Resets-On": claude_budget.reset_date_iso()},
    )
```

Also update the response to include `resets_on` in the JSON body when raising. FastAPI's `HTTPException` doesn't support a structured body directly, so use a custom exception handler OR replace the `raise` with:

```python
if not claude_budget.within_budget():
    from fastapi.responses import JSONResponse
    return JSONResponse(
        status_code=402,
        content={
            "detail": (
                "Lyriq's monthly analysis budget is out. "
                "Existing analyses still work — new ones resume on the 1st."
            ),
            "resets_on": claude_budget.reset_date_iso(),
        },
    )
```

- [ ] **Step 5: Apply the same guard to `/analyze` for new songs**

In the `/analyze` handler, after `cached = supabase_service.find_song(...)` and inside the "new song" branch (right before `genius_data = await genius_service.search_song(...)`), add the same guard. New-song analysis eventually enqueues Claude work when the user requests deep analysis, but we still want to fail fast if the budget is already gone — otherwise a user could spam new-song requests, get an empty analysis page, and be confused.

Actually, `/analyze` in the current code path doesn't call Claude (deep analysis is on-demand). So the guard belongs only on `/songs/{id}/deep-analyze` and any admin re-run routes. Remove the `/analyze` block; add a comment there instead:

```python
# NOTE: /analyze itself never calls Claude — deep interpretation is on-demand via
# /songs/{id}/deep-analyze, which is where the budget guard lives.
```

- [ ] **Step 6: Run test to verify it passes**

Run: `cd backend && python3 -m pytest tests/test_routes.py -k budget_exhausted -v`
Expected: 1 passed.

- [ ] **Step 7: Commit**

```bash
git add backend/routes/songs.py backend/services/claude_budget.py backend/tests/test_routes.py
git commit -m "feat(budget): friendly 402 when Claude monthly cap is exhausted"
```

---

### Task 4: `GET /status`

**Files:**
- Create: `backend/routes/status.py`
- Modify: `backend/main.py`
- Modify: `backend/tests/test_routes.py`

- [ ] **Step 1: Write the failing test**

Add to `backend/tests/test_routes.py`:

```python
def test_status_returns_degraded_when_budget_exhausted():
    with patch("routes.status.claude_budget.within_budget", return_value=False), \
         patch("routes.status.claude_budget.remaining_usd", return_value=0.0), \
         patch("routes.status.claude_budget.reset_date_iso", return_value="2026-08-01"):
        response = client.get("/status")
    assert response.status_code == 200
    body = response.json()
    assert body["degraded"] is True
    assert body["claude_budget"]["remaining_usd"] == 0.0
    assert body["claude_budget"]["resets_on"] == "2026-08-01"


def test_status_returns_healthy_when_budget_ok():
    with patch("routes.status.claude_budget.within_budget", return_value=True), \
         patch("routes.status.claude_budget.remaining_usd", return_value=15.42), \
         patch("routes.status.claude_budget.reset_date_iso", return_value="2026-08-01"):
        response = client.get("/status")
    assert response.status_code == 200
    body = response.json()
    assert body["degraded"] is False
    assert body["claude_budget"]["remaining_usd"] == 15.42
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd backend && python3 -m pytest tests/test_routes.py -k status -v`
Expected: FAIL — 404.

- [ ] **Step 3: Create the router**

Create `backend/routes/status.py`:

```python
from fastapi import APIRouter
import services.claude_budget as claude_budget

router = APIRouter()


@router.get("/status")
def status():
    within = claude_budget.within_budget()
    return {
        "degraded": not within,
        "claude_budget": {
            "remaining_usd": round(claude_budget.remaining_usd(), 2),
            "resets_on": claude_budget.reset_date_iso(),
        },
    }
```

- [ ] **Step 4: Mount in `main.py`**

Add the import and `include_router` call in `backend/main.py`:

```python
from routes import status as status_routes
...
app.include_router(status_routes.router)
```

- [ ] **Step 5: Run test to verify it passes**

Run: `cd backend && python3 -m pytest tests/test_routes.py -k status -v`
Expected: 2 passed.

- [ ] **Step 6: Commit**

```bash
git add backend/routes/status.py backend/main.py backend/tests/test_routes.py
git commit -m "feat(status): GET /status exposes degraded flag and budget"
```

---

### Task 5: Frontend — typed errors on 402 / 429

**Files:**
- Modify: `frontend/lib/api.ts`

- [ ] **Step 1: Add error classes**

At the top of `frontend/lib/api.ts`, add:

```typescript
export class BudgetExhaustedError extends Error {
  resetsOn: string | null;
  constructor(message: string, resetsOn: string | null) {
    super(message);
    this.name = 'BudgetExhaustedError';
    this.resetsOn = resetsOn;
  }
}

export class RateLimitedError extends Error {
  retryAfterSeconds: number;
  constructor(message: string, retryAfterSeconds: number) {
    super(message);
    this.name = 'RateLimitedError';
    this.retryAfterSeconds = retryAfterSeconds;
  }
}
```

- [ ] **Step 2: Wire them into `analyzeSong` and `deepAnalyzeSong`**

Replace the current fetch-then-throw in `analyzeSong`:

```typescript
export async function analyzeSong(title: string, artist: string): Promise<Song> {
  const res = await fetch(`${BASE_URL}/analyze`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ title, artist }),
  });
  if (res.status === 429) {
    const retry = parseInt(res.headers.get('Retry-After') ?? '60', 10);
    const body = await res.json().catch(() => ({})) as { detail?: string };
    throw new RateLimitedError(body.detail ?? 'Slow down for a moment.', retry);
  }
  if (!res.ok) {
    const err = await res.json().catch(() => ({})) as { detail?: string };
    throw new Error(err.detail ?? `Request failed: ${res.status}`);
  }
  return res.json();
}
```

Do the same for `deepAnalyzeSong`, additionally handling 402:

```typescript
export async function deepAnalyzeSong(songId: string): Promise<Song> {
  const res = await fetch(`${BASE_URL}/songs/${songId}/deep-analyze`, { method: 'POST' });
  if (res.status === 429) {
    const retry = parseInt(res.headers.get('Retry-After') ?? '60', 10);
    const body = await res.json().catch(() => ({})) as { detail?: string };
    throw new RateLimitedError(body.detail ?? 'Slow down for a moment.', retry);
  }
  if (res.status === 402) {
    const body = await res.json().catch(() => ({})) as { detail?: string; resets_on?: string };
    throw new BudgetExhaustedError(
      body.detail ?? "Lyriq's analysis budget is out for the month.",
      body.resets_on ?? null,
    );
  }
  if (!res.ok) {
    const err = await res.json().catch(() => ({})) as { detail?: string };
    throw new Error(err.detail ?? `Request failed: ${res.status}`);
  }
  return res.json();
}
```

- [ ] **Step 3: Commit**

```bash
git add frontend/lib/api.ts
git commit -m "feat(status): typed BudgetExhausted / RateLimited errors"
```

---

### Task 6: Frontend — warm inline card in `AnalysisPanel`

**Files:**
- Modify: `frontend/components/AnalysisPanel.tsx`
- Modify: `frontend/app/song/[id]/page.tsx` (only the deep-error handling)

- [ ] **Step 1: Type the deep error**

In `frontend/app/song/[id]/page.tsx`, change the deep-error state to carry a discriminated shape:

```tsx
type DeepError =
  | { kind: 'generic'; message: string }
  | { kind: 'rate-limited'; retryAfter: number }
  | { kind: 'budget-out'; resetsOn: string | null };

const [deepError, setDeepError] = useState<DeepError | null>(null);
```

Update `handleRequestDeep`:

```tsx
import { deepAnalyzeSong, BudgetExhaustedError, RateLimitedError } from '@/lib/api';

async function handleRequestDeep() {
  if (!song || deepLoading) return;
  setDeepLoading(true);
  setDeepError(null);
  try {
    const updated = await deepAnalyzeSong(song.id);
    setSong(updated);
    sessionStorage.setItem(`song-${updated.id}`, JSON.stringify(updated));
  } catch (err: unknown) {
    if (err instanceof BudgetExhaustedError) {
      setDeepError({ kind: 'budget-out', resetsOn: err.resetsOn });
    } else if (err instanceof RateLimitedError) {
      setDeepError({ kind: 'rate-limited', retryAfter: err.retryAfterSeconds });
    } else {
      setDeepError({ kind: 'generic', message: err instanceof Error ? err.message : 'Something went wrong' });
    }
  } finally {
    setDeepLoading(false);
  }
}
```

- [ ] **Step 2: Render the warm card in `AnalysisPanel`**

Update `AnalysisPanel`'s `deepAnalysisError` prop type to `DeepError | null` (re-export the type from a shared spot if you prefer; inline is fine for now). Replace the plain red `<p>` under the deep-analysis button with:

```tsx
{deepAnalysisError && (
  <div className="mt-3 border border-amber-700/50 bg-amber-950/30 rounded-lg p-3">
    {deepAnalysisError.kind === 'budget-out' ? (
      <p className="text-amber-200 text-sm">
        Lyriq&apos;s monthly analysis budget is out.
        {deepAnalysisError.resetsOn && ` New analyses resume on ${deepAnalysisError.resetsOn}.`}
        {' '}Existing analyses across the site still work.
      </p>
    ) : deepAnalysisError.kind === 'rate-limited' ? (
      <p className="text-amber-200 text-sm">
        You&apos;re going a bit fast. Try again in about {deepAnalysisError.retryAfter}s.
      </p>
    ) : (
      <p className="text-red-400 text-sm">{deepAnalysisError.message}</p>
    )}
  </div>
)}
```

- [ ] **Step 3: Manual verify**

Run: `cd frontend && npm run dev`
Temporarily force 402 by setting `_state["spend"] = 999` at the top of `services/claude_budget.py` in the backend, restart uvicorn, click the Lyriq Deep Analysis button — the amber card should show. Undo the tweak.

- [ ] **Step 4: Commit**

```bash
git add frontend/components/AnalysisPanel.tsx frontend/app/song/[id]/page.tsx
git commit -m "feat(status): warm inline card for rate-limited and budget-out states"
```

---

### Task 7: `GlobalStatusBar`

**Files:**
- Create: `frontend/components/GlobalStatusBar.tsx`
- Modify: `frontend/app/layout.tsx`
- Modify: `frontend/lib/api.ts` — add `getStatus()`

- [ ] **Step 1: Add `getStatus`**

In `frontend/lib/api.ts`:

```typescript
export interface StatusResponse {
  degraded: boolean;
  claude_budget: { remaining_usd: number; resets_on: string };
}

export async function getStatus(): Promise<StatusResponse | null> {
  try {
    const res = await fetch(`${BASE_URL}/status`, { cache: 'no-store' });
    if (!res.ok) return null;
    return res.json();
  } catch {
    return null;
  }
}
```

- [ ] **Step 2: Create the bar**

Create `frontend/components/GlobalStatusBar.tsx`:

```tsx
'use client';
import { useEffect, useState } from 'react';
import { getStatus } from '@/lib/api';

export default function GlobalStatusBar() {
  const [degraded, setDegraded] = useState(false);
  const [resetsOn, setResetsOn] = useState<string | null>(null);

  useEffect(() => {
    getStatus().then(s => {
      if (!s) return;
      setDegraded(s.degraded);
      setResetsOn(s.claude_budget.resets_on);
    });
  }, []);

  if (!degraded) return null;

  return (
    <div className="bg-amber-950/60 border-b border-amber-800/60 px-6 py-2 text-center text-amber-200 text-xs">
      Lyriq&apos;s monthly analysis budget is out — browsing still works.
      {resetsOn && ` New analyses resume on ${resetsOn}.`}
    </div>
  );
}
```

- [ ] **Step 3: Mount in `layout.tsx`**

Add above `<Navbar />`:

```tsx
import GlobalStatusBar from '@/components/GlobalStatusBar';

// inside the layout body, before Navbar:
<GlobalStatusBar />
<Navbar />
```

- [ ] **Step 4: Manual verify**

Run: `cd frontend && npm run dev`
With the same "force spend to 999" trick from Task 6, reload any page — the amber pill should sit above the navbar. Undo the tweak.

- [ ] **Step 5: Commit**

```bash
git add frontend/components/GlobalStatusBar.tsx frontend/app/layout.tsx frontend/lib/api.ts
git commit -m "feat(status): global degraded-state pill above navbar"
```

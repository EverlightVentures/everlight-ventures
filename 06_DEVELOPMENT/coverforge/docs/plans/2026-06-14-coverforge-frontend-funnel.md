# COVERFORGE Frontend Funnel - Implementation Plan (Plan 3 of 3)

> **For agentic workers:** REQUIRED SUB-SKILL: superpowers:subagent-driven-development. When building React components, also use the **frontend-design** skill / the 62-66 frontend agents for distinctive, non-generic UI. Steps use checkbox (`- [ ]`).
> **Commit trailer:** every commit ends with `Co-Authored-By: Claude Opus 4.8 (1M context) <noreply@anthropic.com>`.

**Goal:** The public freemium funnel: a visitor fills the book form, gets a free watermarked cover + partial bundle, then pays credits to unlock the print-ready files + full listing bundle and download them.

**Architecture:** Next.js (App Router) on Cloudflare Pages, following the existing `vantaris` shell. The logic layer (form validation, credit-state machine, job poller, typed API client) is pure TypeScript with **vitest** unit tests. The React pages are thin and verified on a CF preview deploy. Backend is the Plan 2 edge functions (`coverforge-create-job`, `coverforge-job-status`) + the existing Stripe `create-checkout`. Auth is a **dedicated Supabase auth context for COVERFORGE** (domain-locked, per the logins doctrine - never cross-routed with AK/casino).

**Tech Stack:** Next.js 14 (App Router), React 18, TypeScript, `@supabase/supabase-js`, Tailwind, vitest. Build + deploy on **e5** (phone SSL aborts CF uploads).

> ⚠️ **Execution environment:** vitest unit tests (Tasks T1-T4) run wherever Node is available (e5 or a dev box). The Next.js build + CF Pages deploy (T9) run on **e5** via `03_AUTOMATION_CORE/01_Scripts/deploy/cf_pages_direct_upload.py` (wrangler segfaults in phone-proot - verify the live edge, never the tool exit code).
> ⚠️ **Depends on Plan 2 Part B being deployed** (the edge functions + Stripe SKUs must be live in test mode) before T6-T8 can be verified end-to-end. T1-T5 can be built and unit-tested first.

---

## File Structure

```
06_DEVELOPMENT/coverforge/web/
  package.json, next.config.js, tailwind.config.ts, tsconfig.json
  .env.local.example
  lib/
    types.ts          # BookInput, JobStatus, Bundle shapes (shared with edge fns)
    validation.ts     # validateBookInput() - pure, unit-tested
    credits.ts        # uiState() credit/tier state machine - pure, unit-tested
    poll.ts           # pollJob() - polls job-status until terminal - unit-tested w/ fake fetch
    supabase.ts       # COVERFORGE-scoped Supabase client (own auth context)
    api.ts            # createJob(), jobStatus(), startCheckout() - typed fetch wrappers
  app/
    layout.tsx, globals.css
    page.tsx          # landing + generator host
    components/
      CoverForm.tsx, PreviewCard.tsx, Paywall.tsx, BundlePanel.tsx, DownloadPanel.tsx
  __tests__/
    validation.test.ts, credits.test.ts, poll.test.ts
```

---

## Task T0: scaffold

**Files:** `web/package.json`, `next.config.js`, `tsconfig.json`, `tailwind.config.ts`, `.env.local.example`

- [ ] **Step 1:** scaffold a Next.js App-Router + TS + Tailwind project under `06_DEVELOPMENT/coverforge/web/`. Add `vitest` + `@vitest/ui` as dev deps.
- [ ] **Step 2:** `.env.local.example` with `NEXT_PUBLIC_SUPABASE_URL`, `NEXT_PUBLIC_SUPABASE_ANON_KEY`, `NEXT_PUBLIC_FUNCTIONS_URL` (Supabase edge base), `NEXT_PUBLIC_CF_GENRES=romance,thriller,fantasy`.
- [ ] **Step 3:** verify `npx vitest run` finds no tests yet and `npm run build` compiles an empty app (run on e5/dev).
- [ ] **Step 4: commit** `chore(coverforge-web): scaffold Next.js + vitest`

---

## Task T1: input validation (TDD, pure)

**Files:** Create `web/lib/types.ts`, `web/lib/validation.ts`; Test `web/__tests__/validation.test.ts`

- [ ] **Step 1: failing tests**
```ts
import { describe, it, expect } from "vitest";
import { validateBookInput } from "../lib/validation";

const ok = { title:"Midnight", author:"A. Author", genre:"thriller",
  vibe:"rainy rooftop", trim:"6x9", pageCount:200, paper:"white" };

describe("validateBookInput", () => {
  it("accepts a complete valid input", () => {
    expect(validateBookInput(ok).valid).toBe(true);
  });
  it("rejects empty title", () => {
    const r = validateBookInput({ ...ok, title:"" });
    expect(r.valid).toBe(false);
    expect(r.errors.title).toBeDefined();
  });
  it("rejects page count below KDP minimum (24)", () => {
    expect(validateBookInput({ ...ok, pageCount:10 }).valid).toBe(false);
  });
  it("rejects an unsupported genre", () => {
    expect(validateBookInput({ ...ok, genre:"western" }).valid).toBe(false);
  });
});
```
- [ ] **Step 2: run, fail** - `npx vitest run __tests__/validation.test.ts`
- [ ] **Step 3: implement**
```ts
// lib/types.ts
export type Trim = "5x8" | "6x9" | "5.5x8.5";
export type Paper = "white" | "cream";
export interface BookInput {
  title: string; author: string; genre: string; vibe: string;
  trim: Trim | string; pageCount: number; paper: Paper | string;
}
export const GENRES = ["romance", "thriller", "fantasy"] as const;

// lib/validation.ts
import { BookInput, GENRES } from "./types";
export function validateBookInput(i: BookInput) {
  const errors: Record<string, string> = {};
  if (!i.title?.trim()) errors.title = "Title is required";
  if (!i.author?.trim()) errors.author = "Author is required";
  if (!GENRES.includes(i.genre as any)) errors.genre = "Pick a supported genre";
  if (!i.pageCount || i.pageCount < 24) errors.pageCount = "KDP minimum is 24 pages";
  if (i.pageCount > 828) errors.pageCount = "Max 828 pages";
  return { valid: Object.keys(errors).length === 0, errors };
}
```
- [ ] **Step 4: run, pass** - [ ] **Step 5: commit** `feat(coverforge-web): validated book input`

---

## Task T2: credit/tier state machine (TDD, pure)

**Files:** Create `web/lib/credits.ts`; Test `web/__tests__/credits.test.ts`

- [ ] **Step 1: failing tests**
```ts
import { describe, it, expect } from "vitest";
import { uiState } from "../lib/credits";

describe("uiState", () => {
  it("new user with no free use -> can generate free preview", () => {
    expect(uiState({ balance:0, usedFree:false }).action).toBe("free_generate");
  });
  it("used free, no credits -> must buy", () => {
    expect(uiState({ balance:0, usedFree:true }).action).toBe("buy");
  });
  it("has credits -> can paid generate", () => {
    expect(uiState({ balance:3, usedFree:true }).action).toBe("paid_generate");
  });
});
```
- [ ] **Step 2: run, fail**
- [ ] **Step 3: implement**
```ts
// lib/credits.ts
export interface CreditCtx { balance: number; usedFree: boolean; }
export function uiState(ctx: CreditCtx): { action: "free_generate"|"paid_generate"|"buy"; canDownload: boolean } {
  if (ctx.balance > 0) return { action: "paid_generate", canDownload: true };
  if (!ctx.usedFree) return { action: "free_generate", canDownload: false };
  return { action: "buy", canDownload: false };
}
```
- [ ] **Step 4: pass** - [ ] **Step 5: commit** `feat(coverforge-web): credit/tier UI state machine`

---

## Task T3: job poller (TDD, fake fetch)

**Files:** Create `web/lib/poll.ts`; Test `web/__tests__/poll.test.ts`

- [ ] **Step 1: failing tests**
```ts
import { describe, it, expect, vi } from "vitest";
import { pollJob } from "../lib/poll";

function fakeStatus(seq: string[]) {
  let i = 0;
  return vi.fn(async () => ({ status: seq[Math.min(i++, seq.length-1)], outputs:{}, signed:{} }));
}

describe("pollJob", () => {
  it("resolves when status becomes done", async () => {
    const r = await pollJob("j1", fakeStatus(["queued","running","done"]), { intervalMs:0, maxTries:5 });
    expect(r.status).toBe("done");
  });
  it("rejects on failed", async () => {
    await expect(pollJob("j2", fakeStatus(["running","failed"]), { intervalMs:0, maxTries:5 }))
      .rejects.toThrow(/failed/);
  });
  it("times out after maxTries", async () => {
    await expect(pollJob("j3", fakeStatus(["queued"]), { intervalMs:0, maxTries:3 }))
      .rejects.toThrow(/timeout/);
  });
});
```
- [ ] **Step 2: run, fail**
- [ ] **Step 3: implement**
```ts
// lib/poll.ts
type StatusFn = (jobId: string) => Promise<{ status: string; outputs: any; signed: any }>;
export async function pollJob(jobId: string, getStatus: StatusFn,
  opts: { intervalMs?: number; maxTries?: number } = {}) {
  const { intervalMs = 1500, maxTries = 60 } = opts;
  for (let i = 0; i < maxTries; i++) {
    const s = await getStatus(jobId);
    if (s.status === "done") return s;
    if (s.status === "failed") throw new Error("render failed");
    if (intervalMs) await new Promise(r => setTimeout(r, intervalMs));
  }
  throw new Error("poll timeout");
}
```
- [ ] **Step 4: pass** - [ ] **Step 5: commit** `feat(coverforge-web): job-status poller with timeout + fail handling`

---

## Task T4: Supabase client + typed API wrappers

**Files:** Create `web/lib/supabase.ts`, `web/lib/api.ts`

- [ ] **Step 1:** `supabase.ts` - a COVERFORGE-scoped client from `NEXT_PUBLIC_SUPABASE_URL/ANON_KEY` with its OWN auth storageKey (`cf-auth`) so it never shares a session with AK/casino (domain-locked logins doctrine).
- [ ] **Step 2:** `api.ts` - `createJob(input, tier)`, `jobStatus(jobId)`, `startCheckout(slug)`. Each attaches the user's access token (`Authorization: Bearer`) and calls `${FUNCTIONS_URL}/coverforge-create-job` etc. `startCheckout` POSTs to the existing `create-checkout` with `{ slug, product_type:"cover_credits" }` and redirects to the returned Stripe URL.
- [ ] **Step 3:** light unit test that `createJob` posts the right body shape to a mocked `fetch` (no network).
- [ ] **Step 4: commit** `feat(coverforge-web): supabase auth client + typed edge-function API`

---

## Task T5: CoverForm component

**Files:** Create `web/app/components/CoverForm.tsx`, host in `web/app/page.tsx`

- [ ] **Step 1:** build the form (title, author, genre dropdown from GENRES, subgenre/vibe, trim, page count, paper). Use `validateBookInput`; disable submit + show inline errors when invalid. Use the **frontend-design skill** for a distinctive, non-generic look (Everlight gold accents, Playfair display).
- [ ] **Step 2 (verify):** CF preview deploy; eyeball the form, confirm validation gating.
- [ ] **Step 3: commit** `feat(coverforge-web): book input form with live validation`

---

## Task T6: free-tier generate + PreviewCard

**Files:** Create `web/app/components/PreviewCard.tsx`; wire generate flow in `page.tsx`

- [ ] **Step 1:** on submit when `uiState().action === "free_generate"`: `createJob(input,"free")` -> `pollJob` -> render the watermarked preview PNG + partial bundle (3 of 7 keywords, blurb teaser) in `PreviewCard`, with an "Unlock print-ready + full bundle" CTA.
- [ ] **Step 2 (verify, needs Plan 2 Part B live in test mode):** generate one free preview end-to-end on the preview deploy.
- [ ] **Step 3: commit** `feat(coverforge-web): free preview generate flow`

---

## Task T7: Paywall + Stripe checkout

**Files:** Create `web/app/components/Paywall.tsx`

- [ ] **Step 1:** when `action === "buy"`, show the credit packs (free first cover used; `$15 / 3 batches` front door, `$29` & `$49`/mo later). Clicking a pack calls `startCheckout(slug)` and redirects to Stripe. On return (`?checkout=success`), refresh the balance via `cover_credit_balance`.
- [ ] **Step 2 (verify, test mode):** complete a Stripe **test** purchase, confirm balance increments (proves the Plan 2 B4 webhook end-to-end).
- [ ] **Step 3: commit** `feat(coverforge-web): credit paywall + Stripe checkout redirect`

---

## Task T8: paid unlock - DownloadPanel + BundlePanel

**Files:** Create `web/app/components/DownloadPanel.tsx`, `web/app/components/BundlePanel.tsx`

- [ ] **Step 1:** when `action === "paid_generate"`: `createJob(input,"paid")` -> `pollJob` -> `DownloadPanel` shows signed-URL download buttons for the ebook cover + full-wrap PDF; `BundlePanel` shows all 7 keywords + 3 categories + blurb + 5 ad headlines with copy-to-clipboard.
- [ ] **Step 2 (verify, test mode + funded FAL/ANTHROPIC keys):** run one full paid generate, download the wrap PDF, confirm it opens at correct dimensions.
- [ ] **Step 3: commit** `feat(coverforge-web): paid unlock - downloads + full bundle panel`

---

## Task T9: landing polish + deploy

**Files:** `web/app/page.tsx`, `web/app/globals.css`

- [ ] **Step 1:** add the hero/landing copy above the generator (positioning: "Print-ready KDP covers + the listing that sells them, in one click"). Run the **everlight_seo** pass on public copy.
- [ ] **Step 2 (e5):** `npm run build`, then deploy via `cf_pages_direct_upload.py` to the `coverforge` CF Pages project. **Verify the LIVE edge** (HTTP 200, real content), never the tool exit code.
- [ ] **Step 3: commit** `feat(coverforge-web): landing + first CF Pages deploy`

---

## Self-Review

**Spec coverage (design doc sections 1, 5, 9):** input form (T5), free preview vs paid unlock (T6/T8), paywall + credits (T7), download of validated print files (T8), distribution/landing (T9). Auth domain-locking (T4) honors the logins doctrine. **Logic fully unit-tested** (T1-T3); UI verified on preview deploy. **Hard dependencies surfaced:** T6-T8 need Plan 2 Part B live (test mode) + funded FAL/ANTHROPIC keys for a real end-to-end. **Placeholder scan:** logic tasks are complete TDD; UI tasks are build-and-verify by design (React isn't phone-TDD'able, per the e5 doctrine).

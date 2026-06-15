"use client";

import { useState, useEffect } from "react";
import { useSearchParams } from "next/navigation";
import { Suspense } from "react";
import { supabase } from "../lib/supabase";
import { uiState, type CreditCtx } from "../lib/credits";
import { createJob, jobStatus, getCreditBalance } from "../lib/api";
import { pollJob } from "../lib/poll";
import type { BookInput, JobResult } from "../lib/types";
import CoverForm from "./components/CoverForm";
import PreviewCard from "./components/PreviewCard";
import Paywall from "./components/Paywall";
import BundlePanel from "./components/BundlePanel";
import DownloadPanel from "./components/DownloadPanel";

type Phase =
  | "idle"
  | "auth_loading"
  | "generating"
  | "free_preview"
  | "paywall"
  | "paid_done"
  | "error";

function CoverforgeApp() {
  const searchParams = useSearchParams();
  const checkoutResult = searchParams.get("checkout");

  const [phase, setPhase] = useState<Phase>("auth_loading");
  const [creditCtx, setCreditCtx] = useState<CreditCtx>({
    balance: 0,
    usedFree: false,
  });
  const [jobResult, setJobResult] = useState<JobResult | null>(null);
  const [pendingInput, setPendingInput] = useState<BookInput | null>(null);
  const [errorMsg, setErrorMsg] = useState<string | null>(null);
  const [statusMsg, setStatusMsg] = useState<string | null>(null);

  // -- Auth bootstrap --
  useEffect(() => {
    let mounted = true;

    async function bootstrap() {
      try {
        // Check for existing session
        const { data: { session } } = await supabase.auth.getSession();

        if (!session) {
          // Auto sign-in anonymously so edge functions get a valid JWT
          const { error } = await supabase.auth.signInAnonymously();
          if (error) {
            console.warn("Anon sign-in failed:", error.message);
          }
        }

        // Load credit balance + usedFree from localStorage
        const usedFree = localStorage.getItem("cf_used_free") === "1";
        const balance = await getCreditBalance();

        if (!mounted) return;
        setCreditCtx({ balance, usedFree });

        // Handle post-Stripe redirect
        if (checkoutResult === "success") {
          const freshBalance = await getCreditBalance();
          if (mounted) {
            setCreditCtx((prev) => ({ ...prev, balance: freshBalance }));
          }
        }

        setPhase("idle");
      } catch (e) {
        console.error("Bootstrap error:", e);
        if (mounted) {
          setPhase("idle"); // Degrade gracefully
        }
      }
    }

    bootstrap();
    return () => { mounted = false; };
  }, [checkoutResult]);

  async function handleSubmit(input: BookInput) {
    const state = uiState(creditCtx);
    setErrorMsg(null);
    setPendingInput(input);

    if (state.action === "buy") {
      setPhase("paywall");
      return;
    }

    const tier = state.action === "paid_generate" ? "paid" : "free";
    setPhase("generating");
    setStatusMsg("Sending to render queue...");

    try {
      const { job_id } = await createJob(input, tier);
      setStatusMsg("Rendering your cover - this takes ~30s...");

      const result = await pollJob(job_id, jobStatus, {
        intervalMs: 2000,
        maxTries: 60,
      });

      const typedResult = result as unknown as JobResult;
      setJobResult(typedResult);

      if (tier === "free") {
        // Mark free tier as used
        localStorage.setItem("cf_used_free", "1");
        setCreditCtx((prev) => ({ ...prev, usedFree: true }));
        setPhase("free_preview");
      } else {
        // Deduct one credit optimistically
        setCreditCtx((prev) => ({ ...prev, balance: Math.max(0, prev.balance - 1) }));
        setPhase("paid_done");
      }
      setStatusMsg(null);
    } catch (e) {
      setPhase("error");
      setErrorMsg(
        e instanceof Error ? e.message : "Generation failed. Please try again."
      );
      setStatusMsg(null);
    }
  }

  function handleUnlock() {
    if (creditCtx.balance > 0 && pendingInput) {
      // User has credits - re-submit as paid
      handleSubmit(pendingInput);
    } else {
      setPhase("paywall");
    }
  }

  function handleReset() {
    setPhase("idle");
    setJobResult(null);
    setErrorMsg(null);
    setStatusMsg(null);
  }

  const uiS = uiState(creditCtx);

  return (
    <div className="min-h-screen" style={{ background: "#0A0A0A" }}>
      {/* Nav */}
      <nav
        className="border-b px-6 py-4 flex items-center justify-between"
        style={{ borderColor: "#1a1a1a" }}
      >
        <div className="flex items-center gap-3">
          <div
            className="w-7 h-7 rounded flex items-center justify-center font-bold text-sm"
            style={{ background: "#D4AF37", color: "#0A0A0A" }}
          >
            CF
          </div>
          <span
            className="font-semibold text-sm"
            style={{ fontFamily: "Playfair Display, serif", color: "#E8E8E8" }}
          >
            CoverForge
          </span>
        </div>

        <div className="flex items-center gap-4">
          {creditCtx.balance > 0 && (
            <span
              className="text-xs px-3 py-1 rounded-full"
              style={{ background: "#1a1500", color: "#D4AF37", border: "1px solid #3a3000" }}
            >
              {creditCtx.balance} {creditCtx.balance === 1 ? "credit" : "credits"}
            </span>
          )}
        </div>
      </nav>

      {/* Hero */}
      <div className="max-w-2xl mx-auto px-6 pt-14 pb-8 text-center">
        <p className="text-xs font-semibold uppercase tracking-widest mb-3" style={{ color: "#D4AF37" }}>
          KDP Self-Publishing Tool
        </p>
        <h1
          className="text-3xl sm:text-4xl font-bold leading-tight mb-4"
          style={{ color: "#E8E8E8" }}
        >
          Print-Ready KDP Covers +{" "}
          <span style={{ color: "#D4AF37" }}>the Listing That Sells Them</span>
          {" "}&mdash; In One Click
        </h1>
        <p className="text-base mb-6" style={{ color: "#888" }}>
          Fill the form, get a watermarked preview free. Unlock the print-ready full-wrap PDF,
          all 7 keywords, categories, blurb, and 5 ad headlines with one credit.
        </p>

        {/* Trust line */}
        <div className="flex items-center justify-center gap-6 text-xs" style={{ color: "#555" }}>
          <span>KDP bleed spec</span>
          <span>No subscription</span>
          <span>Instant download</span>
        </div>
      </div>

      {/* Main content */}
      <div className="max-w-2xl mx-auto px-6 pb-20 space-y-6">

        {/* Auth loading */}
        {phase === "auth_loading" && (
          <div className="card text-center py-8">
            <div className="w-6 h-6 border-2 border-t-transparent rounded-full animate-spin mx-auto mb-3" style={{ borderColor: "#D4AF37", borderTopColor: "transparent" }} />
            <p className="text-sm" style={{ color: "#888" }}>Loading...</p>
          </div>
        )}

        {/* Form - show when idle or after error */}
        {(phase === "idle" || phase === "error") && (
          <div className="card">
            <h2 className="text-xl font-semibold mb-5" style={{ color: "#E8E8E8" }}>
              {uiS.action === "free_generate"
                ? "Generate Free Preview"
                : uiS.action === "paid_generate"
                ? "Generate Cover (1 Credit)"
                : "Generate Cover"}
            </h2>
            <CoverForm
              onSubmit={handleSubmit}
              submitLabel={
                uiS.action === "free_generate"
                  ? "Generate Free Preview"
                  : uiS.action === "paid_generate"
                  ? "Generate Cover (1 Credit)"
                  : "Get Started"
              }
            />
            {phase === "error" && errorMsg && (
              <div
                className="mt-4 p-3 rounded-lg text-sm"
                style={{ background: "#1a0000", color: "#f87171", border: "1px solid #3a0000" }}
              >
                {errorMsg}
              </div>
            )}
          </div>
        )}

        {/* Generating */}
        {phase === "generating" && (
          <div className="card text-center py-10 space-y-4">
            <div
              className="w-12 h-12 rounded-full border-2 border-t-transparent animate-spin mx-auto"
              style={{ borderColor: "#D4AF37", borderTopColor: "transparent" }}
            />
            <div>
              <p className="font-semibold" style={{ color: "#E8E8E8" }}>
                Generating your cover...
              </p>
              <p className="text-sm mt-1" style={{ color: "#888" }}>
                {statusMsg ?? "This usually takes 30-60 seconds."}
              </p>
            </div>
          </div>
        )}

        {/* Free preview result */}
        {phase === "free_preview" && jobResult && (
          <>
            <PreviewCard result={jobResult} onUnlock={handleUnlock} />
            <button
              onClick={handleReset}
              className="text-xs underline w-full text-center"
              style={{ color: "#555" }}
            >
              Start over with a new book
            </button>
          </>
        )}

        {/* Paywall */}
        {phase === "paywall" && (
          <>
            {jobResult && (
              <PreviewCard result={jobResult} onUnlock={() => {}} />
            )}
            <Paywall />
            <button
              onClick={handleReset}
              className="text-xs underline w-full text-center"
              style={{ color: "#555" }}
            >
              Back
            </button>
          </>
        )}

        {/* Paid done */}
        {phase === "paid_done" && jobResult && (
          <>
            <DownloadPanel result={jobResult} />
            <BundlePanel result={jobResult} />
            <div className="text-center">
              <button
                onClick={handleReset}
                className="text-xs underline"
                style={{ color: "#555" }}
              >
                Generate another cover
              </button>
            </div>
          </>
        )}

        {/* Checkout success banner */}
        {checkoutResult === "success" && phase !== "auth_loading" && (
          <div
            className="fixed bottom-6 left-1/2 -translate-x-1/2 px-5 py-3 rounded-xl text-sm font-medium shadow-xl z-50"
            style={{ background: "#0d2200", color: "#22c55e", border: "1px solid #166534" }}
          >
            Credits added to your account!
          </div>
        )}
      </div>
    </div>
  );
}

export default function Page() {
  return (
    <Suspense fallback={
      <div className="min-h-screen flex items-center justify-center" style={{ background: "#0A0A0A" }}>
        <div className="w-6 h-6 border-2 border-t-transparent rounded-full animate-spin" style={{ borderColor: "#D4AF37", borderTopColor: "transparent" }} />
      </div>
    }>
      <CoverforgeApp />
    </Suspense>
  );
}

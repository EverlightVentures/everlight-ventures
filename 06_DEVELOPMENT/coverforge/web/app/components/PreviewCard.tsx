"use client";

import type { JobResult } from "../../lib/types";

interface PreviewCardProps {
  result: JobResult;
  onUnlock: () => void;
}

export default function PreviewCard({ result, onUnlock }: PreviewCardProps) {
  const { outputs } = result;
  const keywords = outputs.keywords?.slice(0, 3) ?? [];
  const blurbTeaser = outputs.blurb
    ? outputs.blurb.slice(0, 120) + (outputs.blurb.length > 120 ? "..." : "")
    : null;

  return (
    <div className="card space-y-5">
      {/* Header */}
      <div className="flex items-center gap-2">
        <div
          className="w-2 h-6 rounded-full"
          style={{ background: "#D4AF37" }}
        />
        <h3 className="text-lg font-semibold" style={{ color: "#D4AF37" }}>
          Free Preview
        </h3>
        <span
          className="ml-auto text-xs px-2 py-1 rounded"
          style={{ background: "#1a1a1a", color: "#888" }}
        >
          Watermarked
        </span>
      </div>

      {/* Preview image */}
      {outputs.preview_url ? (
        <div className="relative">
          <img
            src={outputs.preview_url}
            alt="Watermarked cover preview"
            className="w-full max-w-xs mx-auto rounded-lg block"
            style={{ border: "1px solid #2a2a2a" }}
          />
          {/* Watermark overlay indicator */}
          <div
            className="absolute inset-0 flex items-end justify-center pb-3 pointer-events-none"
            style={{ maxWidth: "320px", margin: "0 auto" }}
          >
            <span
              className="text-xs font-semibold px-3 py-1 rounded"
              style={{ background: "rgba(0,0,0,0.7)", color: "#D4AF37" }}
            >
              COVERFORGE PREVIEW
            </span>
          </div>
        </div>
      ) : (
        <div
          className="h-48 rounded-lg flex items-center justify-center"
          style={{ background: "#1a1a1a", border: "1px dashed #2a2a2a" }}
        >
          <p style={{ color: "#444" }}>Preview image not available</p>
        </div>
      )}

      {/* Partial bundle teaser */}
      <div
        className="rounded-lg p-4 space-y-3"
        style={{ background: "#0d0d0d", border: "1px solid #1e1e1e" }}
      >
        <p className="text-xs font-semibold uppercase tracking-widest" style={{ color: "#888" }}>
          Partial Listing Bundle (3 of 7 keywords)
        </p>

        {keywords.length > 0 && (
          <div className="flex flex-wrap gap-2">
            {keywords.map((kw, i) => (
              <span
                key={i}
                className="text-xs px-2 py-1 rounded"
                style={{ background: "#1a1a1a", color: "#D4AF37", border: "1px solid #2a2a2a" }}
              >
                {kw}
              </span>
            ))}
            <span
              className="text-xs px-2 py-1 rounded"
              style={{ background: "#1a1a1a", color: "#444" }}
            >
              + 4 more locked
            </span>
          </div>
        )}

        {blurbTeaser && (
          <div>
            <p className="text-xs" style={{ color: "#888" }}>
              Blurb preview:{" "}
              <span style={{ color: "#ccc" }}>{blurbTeaser}</span>
            </p>
          </div>
        )}
      </div>

      {/* Unlock CTA */}
      <div
        className="rounded-xl p-5 text-center space-y-3"
        style={{
          background: "linear-gradient(135deg, #1a1500 0%, #0d0d00 100%)",
          border: "1px solid #3a3000",
        }}
      >
        <p className="text-base font-semibold" style={{ fontFamily: "Playfair Display, serif", color: "#D4AF37" }}>
          Unlock Print-Ready Files + Full Bundle
        </p>
        <ul className="text-xs space-y-1" style={{ color: "#aaa" }}>
          <li>+ Full-wrap PDF (cover + spine + back) at KDP bleed spec</li>
          <li>+ Ebook front cover PNG (2560 x 1600)</li>
          <li>+ All 7 keywords + 3 BISAC categories</li>
          <li>+ Full back-cover blurb + 5 ad headlines</li>
        </ul>
        <button
          onClick={onUnlock}
          className="gold-btn px-8 py-2.5 rounded-lg text-sm"
        >
          Unlock for 1 Credit
        </button>
        <p className="text-xs" style={{ color: "#555" }}>
          3 credits for $15 - No subscription required
        </p>
      </div>
    </div>
  );
}

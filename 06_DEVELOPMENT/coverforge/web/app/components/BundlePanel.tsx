"use client";

import { useState } from "react";
import type { JobResult } from "../../lib/types";

interface BundlePanelProps {
  result: JobResult;
}

function CopyButton({ text }: { text: string }) {
  const [copied, setCopied] = useState(false);

  async function handleCopy() {
    try {
      await navigator.clipboard.writeText(text);
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    } catch {
      // Clipboard not available
    }
  }

  return (
    <button onClick={handleCopy} className={`copy-btn${copied ? " copied" : ""}`}>
      {copied ? "Copied" : "Copy"}
    </button>
  );
}

export default function BundlePanel({ result }: BundlePanelProps) {
  const { outputs } = result;

  const keywords = outputs.keywords ?? [];
  const categories = outputs.categories ?? [];
  const blurb = outputs.blurb ?? "";
  const adHeadlines = outputs.ad_headlines ?? [];

  return (
    <div className="card space-y-6">
      {/* Header */}
      <div className="flex items-center gap-2">
        <div className="w-2 h-6 rounded-full" style={{ background: "#D4AF37" }} />
        <h3 className="text-lg font-semibold" style={{ color: "#D4AF37" }}>
          Full Listing Bundle
        </h3>
      </div>

      {/* Keywords */}
      <div className="space-y-2">
        <div className="flex items-center justify-between">
          <p className="text-xs font-semibold uppercase tracking-widest" style={{ color: "#888" }}>
            KDP Keywords ({keywords.length}/7)
          </p>
          <CopyButton text={keywords.join(", ")} />
        </div>
        <div className="flex flex-wrap gap-2">
          {keywords.map((kw, i) => (
            <span
              key={i}
              className="text-xs px-2 py-1 rounded"
              style={{
                background: "#1a1a1a",
                color: "#D4AF37",
                border: "1px solid #2a2a2a",
              }}
            >
              {kw}
            </span>
          ))}
        </div>
      </div>

      {/* Categories */}
      <div className="space-y-2">
        <div className="flex items-center justify-between">
          <p className="text-xs font-semibold uppercase tracking-widest" style={{ color: "#888" }}>
            BISAC Categories ({categories.length}/3)
          </p>
          <CopyButton text={categories.join("\n")} />
        </div>
        <ul className="space-y-1">
          {categories.map((cat, i) => (
            <li key={i} className="text-sm" style={{ color: "#ccc" }}>
              <span style={{ color: "#D4AF37" }}>{i + 1}.</span> {cat}
            </li>
          ))}
        </ul>
      </div>

      {/* Blurb */}
      <div className="space-y-2">
        <div className="flex items-center justify-between">
          <p className="text-xs font-semibold uppercase tracking-widest" style={{ color: "#888" }}>
            Back-Cover Blurb
          </p>
          <CopyButton text={blurb} />
        </div>
        <div
          className="rounded-lg p-4 text-sm leading-relaxed"
          style={{
            background: "#0d0d0d",
            border: "1px solid #1e1e1e",
            color: "#ccc",
          }}
        >
          {blurb || <span style={{ color: "#444" }}>No blurb generated.</span>}
        </div>
      </div>

      {/* Ad Headlines */}
      <div className="space-y-2">
        <div className="flex items-center justify-between">
          <p className="text-xs font-semibold uppercase tracking-widest" style={{ color: "#888" }}>
            Ad Headlines ({adHeadlines.length}/5)
          </p>
          <CopyButton text={adHeadlines.join("\n")} />
        </div>
        <ul className="space-y-2">
          {adHeadlines.map((hl, i) => (
            <li key={i} className="flex items-start gap-2">
              <span
                className="text-xs font-bold mt-0.5 flex-shrink-0"
                style={{ color: "#D4AF37" }}
              >
                H{i + 1}
              </span>
              <span className="text-sm" style={{ color: "#ccc" }}>
                {hl}
              </span>
            </li>
          ))}
        </ul>
      </div>
    </div>
  );
}

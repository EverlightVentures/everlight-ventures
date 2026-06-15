"use client";

import { useState } from "react";
import { startCheckout } from "../../lib/api";

interface CreditPack {
  slug: string;
  label: string;
  price: string;
  credits: number;
  perCredit: string;
  highlight?: boolean;
  badge?: string;
}

const PACKS: CreditPack[] = [
  {
    slug: "cover-3",
    label: "Starter Pack",
    price: "$15",
    credits: 3,
    perCredit: "$5 / cover",
    highlight: true,
    badge: "Most Popular",
  },
  {
    slug: "cover-pro-20",
    label: "Pro Pack",
    price: "$29",
    credits: 20,
    perCredit: "$1.45 / cover",
    badge: "Best Value",
  },
  {
    slug: "cover-pro-50",
    label: "Studio Pack",
    price: "$49",
    credits: 50,
    perCredit: "$0.98 / cover",
  },
];

interface PaywallProps {
  onSuccess?: () => void;
}

export default function Paywall({ onSuccess: _ }: PaywallProps) {
  const [loading, setLoading] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  async function handleBuy(slug: string) {
    setError(null);
    setLoading(slug);
    try {
      await startCheckout(slug);
      // startCheckout redirects -- execution won't reach here on success
    } catch (e) {
      setError(e instanceof Error ? e.message : "Checkout failed. Please try again.");
      setLoading(null);
    }
  }

  return (
    <div className="card space-y-6">
      {/* Header */}
      <div>
        <div className="flex items-center gap-2 mb-1">
          <div className="w-2 h-6 rounded-full" style={{ background: "#D4AF37" }} />
          <h3 className="text-lg font-semibold" style={{ color: "#D4AF37" }}>
            Unlock Credits
          </h3>
        </div>
        <p className="text-sm" style={{ color: "#888" }}>
          Your free preview is ready above. Buy credits to unlock the print-ready
          PDF + full listing bundle.
        </p>
      </div>

      {/* Packs */}
      <div className="grid grid-cols-1 sm:grid-cols-3 gap-3">
        {PACKS.map((pack) => (
          <div
            key={pack.slug}
            className="rounded-xl p-4 space-y-3 relative"
            style={{
              background: pack.highlight ? "#1a1500" : "#111",
              border: pack.highlight ? "1px solid #D4AF37" : "1px solid #2a2a2a",
            }}
          >
            {pack.badge && (
              <span
                className="absolute -top-2.5 left-3 text-xs font-semibold px-2 py-0.5 rounded-full"
                style={{
                  background: pack.highlight ? "#D4AF37" : "#222",
                  color: pack.highlight ? "#0A0A0A" : "#D4AF37",
                  border: pack.highlight ? "none" : "1px solid #D4AF37",
                }}
              >
                {pack.badge}
              </span>
            )}

            <div>
              <p
                className="text-xs uppercase tracking-widest font-medium"
                style={{ color: "#888" }}
              >
                {pack.label}
              </p>
              <p
                className="text-2xl font-bold mt-1"
                style={{ fontFamily: "Playfair Display, serif", color: "#E8E8E8" }}
              >
                {pack.price}
              </p>
              <p className="text-xs mt-0.5" style={{ color: "#D4AF37" }}>
                {pack.credits} covers · {pack.perCredit}
              </p>
            </div>

            <button
              onClick={() => handleBuy(pack.slug)}
              className="gold-btn w-full py-2 rounded-lg text-xs"
              disabled={loading !== null}
            >
              {loading === pack.slug ? "Redirecting..." : "Buy Now"}
            </button>
          </div>
        ))}
      </div>

      {error && (
        <p className="text-sm text-red-400 text-center">{error}</p>
      )}

      <p className="text-xs text-center" style={{ color: "#555" }}>
        Secure checkout via Stripe · Credits never expire · No subscription
      </p>
    </div>
  );
}

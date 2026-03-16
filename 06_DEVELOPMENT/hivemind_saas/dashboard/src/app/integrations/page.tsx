"use client";

import React from "react";
import { useRouter } from "next/navigation";
import { Plug, ArrowLeft } from "lucide-react";
import Sidebar from "@/components/layout/Sidebar";
import IntegrationSetup from "@/components/onboarding/IntegrationSetup";

export default function IntegrationsPage() {
  const router = useRouter();

  return (
    <div className="flex min-h-screen bg-void">
      <Sidebar />

      <div className="flex-1 flex flex-col" style={{ marginLeft: "260px" }}>
        {/* Minimal header */}
        <header
          className="sticky top-0 z-30 flex items-center gap-3 px-6"
          style={{
            height: "64px",
            background: "rgba(10,10,15,0.85)",
            borderBottom: "1px solid #1E1E2E",
            backdropFilter: "blur(12px)",
            WebkitBackdropFilter: "blur(12px)",
          }}
        >
          <button
            onClick={() => router.back()}
            className="w-8 h-8 rounded-lg flex items-center justify-center text-[#5C5C7A] hover:bg-white/[0.05] hover:text-[#A0A0B8] transition-colors"
          >
            <ArrowLeft size={16} />
          </button>
          <div
            className="w-8 h-8 rounded-lg flex items-center justify-center"
            style={{
              background: "rgba(124,58,237,0.12)",
              border: "1px solid rgba(124,58,237,0.2)",
            }}
          >
            <Plug size={15} className="text-violet-400" />
          </div>
          <div>
            <h1
              className="text-[15px] font-semibold text-[#F1F1F8] leading-none"
              style={{ fontFamily: "'DM Sans', sans-serif" }}
            >
              Integrations
            </h1>
            <p className="text-[11px] text-[#5C5C7A] mt-0.5">
              Connect your tools and AI services
            </p>
          </div>
        </header>

        <main className="flex-1 overflow-auto px-6 py-8">
          {/* Page intro */}
          <div className="max-w-2xl mx-auto mb-8 text-center">
            <div
              className="inline-flex items-center gap-2 px-3 py-1.5 rounded-full mb-4 text-[12px] font-medium text-violet-400"
              style={{
                background: "rgba(124,58,237,0.1)",
                border: "1px solid rgba(124,58,237,0.2)",
              }}
            >
              <span className="pulse-dot pulse-dot-violet" style={{ width: 6, height: 6 }} />
              Setup Wizard
            </div>
            <h2
              className="text-[26px] font-bold mb-3"
              style={{
                fontFamily: "'DM Sans', sans-serif",
                background: "linear-gradient(135deg, #A78BFA 0%, #7C3AED 50%, #F59E0B 100%)",
                WebkitBackgroundClip: "text",
                WebkitTextFillColor: "transparent",
                backgroundClip: "text",
              }}
            >
              Power Up Your Hive
            </h2>
            <p className="text-[14px] text-[#5C5C7A] max-w-md mx-auto leading-relaxed">
              Connect your AI services and productivity tools in three steps.
              The Hive coordinates them autonomously to handle your workflows.
            </p>
          </div>

          {/* Integration setup wizard */}
          <IntegrationSetup
            onComplete={() => router.push("/war-room")}
            className="max-w-2xl mx-auto"
          />

          {/* Already configured section */}
          <div className="max-w-2xl mx-auto mt-8">
            <div
              className="rounded-xl p-4 flex items-center gap-4"
              style={{
                background: "rgba(16,185,129,0.05)",
                border: "1px solid rgba(16,185,129,0.12)",
              }}
            >
              <div
                className="w-8 h-8 rounded-lg flex items-center justify-center flex-shrink-0"
                style={{
                  background: "rgba(16,185,129,0.1)",
                  border: "1px solid rgba(16,185,129,0.2)",
                }}
              >
                <Plug size={14} className="text-emerald-400" />
              </div>
              <div className="flex-1">
                <p className="text-[13px] font-medium text-[#F1F1F8]">
                  Manage existing integrations
                </p>
                <p className="text-[11.5px] text-[#5C5C7A]">
                  Revoke access, refresh tokens, or adjust permissions for connected services
                </p>
              </div>
              <button className="btn-ghost text-[12px] py-2 px-3">
                Manage
              </button>
            </div>
          </div>
        </main>
      </div>
    </div>
  );
}

"use client";

import { useState } from "react";
import { motion, AnimatePresence } from "framer-motion";
import {
  Mail, MessageSquare, Phone, Inbox, ChevronDown, ChevronUp, Eye, Clock,
  CornerDownRight,
} from "lucide-react";
import type { Lead } from "@/lib/types";
import { timeAgo } from "@/lib/utils";

type Entry = NonNullable<Lead["conversation"]>[number];

const CHANNEL_ICONS: Record<string, any> = {
  email: Mail,
  sms: MessageSquare,
  call: Phone,
};

function relTime(iso: string): string {
  try {
    const d = new Date(iso);
    return d.toLocaleString("en-US", {
      month: "short", day: "numeric",
      hour: "numeric", minute: "2-digit",
    });
  } catch {
    return iso;
  }
}

function previewText(body?: string, maxLen = 240): string {
  if (!body) return "";
  const cleaned = body
    .replace(/\n{3,}/g, "\n\n")
    .replace(/^\s+|\s+$/g, "");
  return cleaned.length <= maxLen ? cleaned : cleaned.slice(0, maxLen) + "..";
}

export function ConversationTimeline({ lead }: { lead: Lead }) {
  const entries = (lead.conversation ?? []).slice().sort((a, b) =>
    (a.timestamp < b.timestamp ? 1 : -1)
  );

  // Default: most recent message is expanded so the owner instantly sees
  // what was just sent.
  const initialKey = entries[0]
    ? `${entries[0].timestamp}-0`
    : "";
  const [expanded, setExpanded] = useState<Set<string>>(
    initialKey ? new Set([initialKey]) : new Set()
  );

  const toggle = (k: string) => {
    setExpanded((s) => {
      const n = new Set(s);
      n.has(k) ? n.delete(k) : n.add(k);
      return n;
    });
  };
  const expandAll = () => setExpanded(new Set(entries.map((_, i) => `${entries[i].timestamp}-${i}`)));
  const collapseAll = () => setExpanded(new Set());

  if (entries.length === 0) {
    return (
      <div className="text-center py-12 border border-dashed border-ash rounded-xl">
        <Inbox className="w-6 h-6 text-smoke mx-auto mb-2" />
        <div className="text-sm text-fog">No outreach touches yet.</div>
        <div className="text-[11px] text-smoke mt-1">
          The next Belfort cron will land here in real time.
        </div>
      </div>
    );
  }

  return (
    <div className="space-y-3">
      <div className="flex items-center justify-between text-[11px]">
        <div className="text-smoke">
          Most recent is open by default. Click any card to toggle.
        </div>
        <div className="flex gap-2">
          <button
            onClick={expandAll}
            className="text-gold/80 hover:text-gold px-2 py-1 rounded hover:bg-ash/40"
          >
            expand all
          </button>
          <button
            onClick={collapseAll}
            className="text-fog hover:text-ivory px-2 py-1 rounded hover:bg-ash/40"
          >
            collapse all
          </button>
        </div>
      </div>

      {entries.map((e, idx) => {
        const key = `${e.timestamp}-${idx}`;
        const open = expanded.has(key);
        const Icon = CHANNEL_ICONS[e.channel ?? "email"] || Mail;
        const inbound = e.direction === "inbound";
        return (
          <motion.div
            key={key}
            layout
            initial={{ opacity: 0, y: 4 }}
            animate={{ opacity: 1, y: 0 }}
            className={`border rounded-xl overflow-hidden ${
              inbound
                ? "border-success/40 bg-success/5"
                : "border-ash bg-card-gradient"
            }`}
          >
            <button
              onClick={() => toggle(key)}
              className="w-full p-4 hover:bg-graphite/30 transition-colors text-left"
            >
              <div className="flex items-start gap-3">
                <div
                  className={`flex-none w-9 h-9 rounded-full flex items-center justify-center ${
                    inbound ? "bg-success/20 text-success" : "bg-gold/10 text-gold"
                  }`}
                >
                  {inbound ? <CornerDownRight className="w-4 h-4" /> : <Icon className="w-4 h-4" />}
                </div>

                <div className="flex-1 min-w-0">
                  <div className="flex items-center gap-2 flex-wrap">
                    <span className="text-[11px] tracking-[0.2em] uppercase text-fog">
                      {e.channel || "email"}
                      {e.step !== undefined && <span className="ml-1.5 text-smoke">step {e.step + 1}/7</span>}
                    </span>
                    <span className="text-[11px] text-smoke">
                      {inbound ? "from seller" : `from ${e.agent_name || "Piper"}`}
                    </span>
                    {e.reconstructed && (
                      <span className="text-[10px] bg-ash text-smoke px-1.5 py-0.5 rounded">
                        reconstructed
                      </span>
                    )}
                  </div>
                  <div className="font-medium text-ivory mt-0.5 truncate">
                    {e.subject || (inbound ? "Reply" : "Outreach")}
                  </div>
                  <div className="text-[11px] text-smoke mt-0.5 truncate">
                    {inbound
                      ? `to ${e.from || lead.owner_name || "us"}`
                      : `to ${e.to || lead.email || lead.owner_email || lead.phone || "?"}`
                    }
                  </div>
                  {/* Always show a preview line or two -- visible without clicking */}
                  {!open && (
                    <p className="text-[12px] text-fog/80 mt-2 whitespace-pre-wrap line-clamp-2 leading-snug">
                      {previewText(e.message, 240)}
                    </p>
                  )}
                </div>

                <div className="flex-none flex items-center gap-2 text-[11px] text-fog whitespace-nowrap">
                  <Clock className="w-3 h-3 text-smoke" />
                  <span>{relTime(e.timestamp)}</span>
                  <span className="text-smoke">/</span>
                  <span>{timeAgo(e.timestamp)}</span>
                  {open ? <ChevronUp className="w-4 h-4" /> : <ChevronDown className="w-4 h-4" />}
                </div>
              </div>
            </button>

            <AnimatePresence initial={false}>
              {open && (
                <motion.div
                  initial={{ height: 0, opacity: 0 }}
                  animate={{ height: "auto", opacity: 1 }}
                  exit={{ height: 0, opacity: 0 }}
                  className="overflow-hidden"
                >
                  <div className="border-t border-ash p-4 space-y-3">
                    {e.message_html ? (
                      <div>
                        <div className="flex items-center justify-between gap-2 text-[10px] tracking-[0.25em] uppercase text-fog mb-2">
                          <div className="flex items-center gap-2">
                            <Eye className="w-3 h-3" />
                            <span>The email that was delivered</span>
                          </div>
                          <span className="text-smoke">branded html preview</span>
                        </div>
                        <iframe
                          title={e.subject || "email"}
                          srcDoc={e.message_html}
                          sandbox="allow-same-origin"
                          className="w-full bg-obsidian rounded-lg border border-ash"
                          style={{ height: 720 }}
                        />
                      </div>
                    ) : (
                      <div>
                        <div className="text-[10px] tracking-[0.25em] uppercase text-fog mb-2">
                          {e.channel === "sms" ? "SMS body" : "Plain-text body"}
                        </div>
                        <pre className="whitespace-pre-wrap break-words text-sm text-ivory bg-graphite border border-ash rounded-lg p-4 leading-relaxed">
                          {e.message}
                        </pre>
                      </div>
                    )}
                  </div>
                </motion.div>
              )}
            </AnimatePresence>
          </motion.div>
        );
      })}
    </div>
  );
}

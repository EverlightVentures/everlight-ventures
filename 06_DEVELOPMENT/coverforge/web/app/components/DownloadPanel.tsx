"use client";

import type { JobResult } from "../../lib/types";

interface DownloadPanelProps {
  result: JobResult;
}

interface DownloadItem {
  label: string;
  description: string;
  url: string | undefined;
  filename: string;
  badge: string;
}

export default function DownloadPanel({ result }: DownloadPanelProps) {
  const { signed } = result;

  const items: DownloadItem[] = [
    {
      label: "Ebook Cover",
      description: "2560 x 1600 PNG - Digital storefronts & preview",
      url: signed.ebook_cover,
      filename: "coverforge-ebook-cover.png",
      badge: "PNG",
    },
    {
      label: "Full-Wrap Print PDF",
      description: "KDP bleed spec - Cover + spine + back at correct DPI",
      url: signed.full_wrap_pdf,
      filename: "coverforge-full-wrap.pdf",
      badge: "PDF",
    },
  ];

  return (
    <div className="card space-y-5">
      {/* Header */}
      <div className="flex items-center gap-2">
        <div className="w-2 h-6 rounded-full" style={{ background: "#D4AF37" }} />
        <h3 className="text-lg font-semibold" style={{ color: "#D4AF37" }}>
          Your Files
        </h3>
        <span
          className="ml-auto text-xs px-2 py-1 rounded"
          style={{ background: "#0d2200", color: "#22c55e", border: "1px solid #166534" }}
        >
          Ready to Download
        </span>
      </div>

      <div className="space-y-3">
        {items.map((item) => (
          <div
            key={item.label}
            className="flex items-center gap-4 rounded-xl p-4"
            style={{ background: "#0d0d0d", border: "1px solid #1e1e1e" }}
          >
            {/* Badge */}
            <div
              className="w-12 h-12 rounded-lg flex items-center justify-center flex-shrink-0 text-xs font-bold"
              style={{ background: "#1a1a1a", color: "#D4AF37", border: "1px solid #2a2a2a" }}
            >
              {item.badge}
            </div>

            {/* Info */}
            <div className="flex-1 min-w-0">
              <p className="text-sm font-medium" style={{ color: "#E8E8E8" }}>
                {item.label}
              </p>
              <p className="text-xs mt-0.5 truncate" style={{ color: "#666" }}>
                {item.description}
              </p>
            </div>

            {/* Download button */}
            {item.url ? (
              <a
                href={item.url}
                download={item.filename}
                className="gold-btn px-4 py-2 rounded-lg text-xs flex-shrink-0 inline-flex items-center gap-1.5 no-underline"
              >
                <svg width="12" height="12" viewBox="0 0 16 16" fill="currentColor">
                  <path d="M8 12L3 7l1.4-1.4L7 8.2V1h2v7.2L11.6 5.6 13 7l-5 5zM2 14h12v2H2v-2z" />
                </svg>
                Download
              </a>
            ) : (
              <span className="text-xs px-4 py-2" style={{ color: "#555" }}>
                Not available
              </span>
            )}
          </div>
        ))}
      </div>

      <p className="text-xs" style={{ color: "#555" }}>
        Download links expire in 24 hours. Re-generate to get new signed URLs.
      </p>
    </div>
  );
}

"use client";
import { motion, AnimatePresence } from "framer-motion";

export default function NewsPanel({
  open, news, place, onClose,
}: {
  open: boolean;
  news: any[];
  place: string;
  onClose: () => void;
}) {
  return (
    <AnimatePresence>
      {open && (
        <motion.div
          className="glass scroll-thin"
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          exit={{ opacity: 0, y: 20 }}
          style={{
            position: "absolute", bottom: 120, left: "50%", transform: "translateX(-50%)",
            width: "min(460px, 92vw)", maxHeight: "52vh", overflowY: "auto",
            borderRadius: 14, padding: 16, zIndex: 22,
          }}
        >
          <div style={{ display: "flex", alignItems: "center", marginBottom: 8 }}>
            <span className="display" style={{ color: "var(--gold)", fontSize: 16 }}>
              News {place ? `· ${place}` : ""}
            </span>
            <button
              onClick={onClose}
              style={{ marginLeft: "auto", background: "none", border: "none", color: "var(--text)", fontSize: 20, cursor: "pointer" }}
            >
              &times;
            </button>
          </div>
          {news.length === 0 ? (
            <div style={{ color: "var(--muted)", fontSize: 13 }}>no recent local news right now</div>
          ) : (
            news.map((a, i) => (
              <a
                key={i}
                href={a.url || a.link || "#"}
                target="_blank"
                rel="noreferrer"
                style={{ display: "block", padding: "8px 0", borderTop: "1px solid var(--line)", color: "var(--text)", fontSize: 13, textDecoration: "none" }}
              >
                {a.title || a.name || "(untitled)"}
                {(a.source || a.domain) && (
                  <div style={{ color: "var(--muted)", fontSize: 11, marginTop: 2 }}>{a.source || a.domain}</div>
                )}
              </a>
            ))
          )}
        </motion.div>
      )}
    </AnimatePresence>
  );
}

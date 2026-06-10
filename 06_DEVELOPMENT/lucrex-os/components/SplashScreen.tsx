"use client";
import { useEffect, useRef, useState } from "react";

const STORAGE_KEY = "lucrex_splash_seen";
const HARD_TIMEOUT_MS = 6000;
const FADE_MS = 400;

function basePath(): string {
  const bp = process.env.NEXT_PUBLIC_BASE_PATH ?? "";
  return bp.endsWith("/") ? bp.slice(0, -1) : bp;
}

export function SplashScreen() {
  const [phase, setPhase] = useState<"hidden" | "playing" | "fading">("hidden");
  const videoRef = useRef<HTMLVideoElement>(null);

  useEffect(() => {
    let alreadySeen = false;
    let respectReducedMotion = false;
    try {
      alreadySeen = window.sessionStorage.getItem(STORAGE_KEY) === "1";
      respectReducedMotion =
        window.matchMedia?.("(prefers-reduced-motion: reduce)").matches ?? false;
    } catch {
      // sessionStorage unavailable, treat as not seen
    }
    // Respect user setting from /settings page (defaults true).
    let userEnabled = true;
    try {
      const raw = window.localStorage.getItem("lucrex.settings.v1");
      if (raw) {
        const parsed = JSON.parse(raw);
        if (parsed.splashEnabled === false) userEnabled = false;
      }
    } catch {
      // ignore parse errors
    }
    if (alreadySeen || respectReducedMotion || !userEnabled) {
      setPhase("hidden");
      return;
    }
    setPhase("playing");
  }, []);

  useEffect(() => {
    if (phase !== "playing") return;
    const t = setTimeout(() => beginFade(), HARD_TIMEOUT_MS);
    return () => clearTimeout(t);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [phase]);

  function beginFade() {
    if (phase !== "playing") return;
    setPhase("fading");
    try {
      window.sessionStorage.setItem(STORAGE_KEY, "1");
    } catch {
      // ignore
    }
    setTimeout(() => setPhase("hidden"), FADE_MS);
  }

  if (phase === "hidden") return null;

  const videoSrc = `${basePath()}/lucrex_logo.mp4`;

  return (
    <div
      onClick={beginFade}
      role="button"
      aria-label="Skip intro"
      tabIndex={0}
      onKeyDown={(e) => {
        if (e.key === "Escape" || e.key === "Enter" || e.key === " ") beginFade();
      }}
      className="fixed inset-0 z-[100] bg-black flex items-center justify-center cursor-pointer transition-opacity"
      style={{ opacity: phase === "fading" ? 0 : 1, transitionDuration: `${FADE_MS}ms` }}
    >
      <video
        ref={videoRef}
        src={videoSrc}
        autoPlay
        muted
        playsInline
        preload="auto"
        onEnded={beginFade}
        onError={beginFade}
        className="max-w-[80vw] max-h-[80vh] object-contain"
      />
      <div className="absolute bottom-6 right-6 text-[9px] tracking-[0.3em] text-gray-600 font-mono">
        click to skip
      </div>
    </div>
  );
}

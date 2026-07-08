"use client";
import { useEffect, useRef } from "react";

// Plays a Caltrans HLS stream inline. Loads hls.js lazily (Safari plays native).
export default function LiveVideo({ src, style }: { src: string; style?: React.CSSProperties }) {
  const ref = useRef<HTMLVideoElement>(null);
  useEffect(() => {
    const v = ref.current;
    if (!v) return;
    let hls: any;
    (async () => {
      if (v.canPlayType("application/vnd.apple.mpegurl")) {
        v.src = src;
      } else {
        const Hls = (await import("hls.js")).default;
        if (Hls.isSupported()) {
          hls = new Hls({ liveDurationInfinity: true });
          hls.loadSource(src);
          hls.attachMedia(v);
        } else {
          v.src = src;
        }
      }
    })();
    return () => hls && hls.destroy();
  }, [src]);
  return (
    <video
      ref={ref}
      controls
      muted
      playsInline
      autoPlay
      style={{ width: "100%", borderRadius: 8, background: "#000", ...style }}
    />
  );
}

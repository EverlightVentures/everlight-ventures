"use client";
import { useEffect } from "react";

// Any service worker controlling this origin (from the old PWA) can serve stale
// /console/ files. Unregister everything + purge caches on load so the console
// is always the freshly deployed build.
export default function KillSW() {
  useEffect(() => {
    if ("serviceWorker" in navigator) {
      navigator.serviceWorker.getRegistrations().then((rs) => rs.forEach((r) => r.unregister()));
    }
    if ("caches" in window) {
      caches.keys().then((ks) => ks.forEach((k) => caches.delete(k)));
    }
  }, []);
  return null;
}

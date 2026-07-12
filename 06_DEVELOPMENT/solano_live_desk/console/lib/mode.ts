// Build-time product mode. The private console (Rich's own tool) ships every
// feature. The PUBLIC consumer app (AroundMe on the stores) must NOT ship the
// features counsel flagged as a national legal risk: per-area/reputation risk
// scoring and person/plate entity extraction from scanner audio (FHA / redlining
// / defamation). Next inlines NEXT_PUBLIC_* at build and dead-code-eliminates the
// hidden branches, so the public build does not merely hide that code, it omits it.
//
//   private build (default):  npm run build
//   public app build:         NEXT_PUBLIC_AROUNDME_MODE=public npm run build
export const PUBLIC_BUILD = process.env.NEXT_PUBLIC_AROUNDME_MODE === "public";

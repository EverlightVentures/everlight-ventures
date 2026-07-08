#!/usr/bin/env bash
# Deploy the Survival console (Next.js -> static -> FastAPI /console).
# ALWAYS clears .next: its incremental cache silently ships stale components,
# which cost us hours of "the update isn't showing". Never skip the rm.
set -euo pipefail
HERE="$(cd "$(dirname "$0")/.." && pwd)"
echo "[1/3] sync source -> e5"
rsync -az --exclude node_modules --exclude .next --exclude out "$HERE/console/" e5:~/psim/
echo "[2/3] clean build on e5"
ssh e5 'cd ~/psim && rm -rf .next out && npm run build'
echo "[3/3] publish + restart"
ssh e5 'rm -rf ~/solano_live_desk/web/console && cp -r ~/psim/out ~/solano_live_desk/web/console && systemctl --user restart solano-desk.service && echo "  live: $(stat -c %y ~/solano_live_desk/web/console/index.html | cut -d. -f1)"'

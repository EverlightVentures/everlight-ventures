export type StatusFn = (
  jobId: string
) => Promise<{ status: string; outputs: Record<string, unknown>; signed: Record<string, unknown> }>;

export interface PollOptions {
  intervalMs?: number;
  maxTries?: number;
}

export async function pollJob(
  jobId: string,
  getStatus: StatusFn,
  opts: PollOptions = {}
) {
  const { intervalMs = 1500, maxTries = 60 } = opts;
  for (let i = 0; i < maxTries; i++) {
    const s = await getStatus(jobId);
    if (s.status === "done") return s;
    if (s.status === "failed") throw new Error("render failed");
    if (intervalMs > 0) {
      await new Promise((r) => setTimeout(r, intervalMs));
    }
  }
  throw new Error("poll timeout");
}

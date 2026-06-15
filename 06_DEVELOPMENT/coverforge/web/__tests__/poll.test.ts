import { describe, it, expect, vi } from "vitest";
import { pollJob } from "../lib/poll";

function fakeStatus(seq: string[]) {
  let i = 0;
  return vi.fn(async () => ({
    status: seq[Math.min(i++, seq.length - 1)],
    outputs: {},
    signed: {},
  }));
}

describe("pollJob", () => {
  it("resolves when status becomes done", async () => {
    const r = await pollJob("j1", fakeStatus(["queued", "running", "done"]), {
      intervalMs: 0,
      maxTries: 5,
    });
    expect(r.status).toBe("done");
  });

  it("rejects on failed", async () => {
    await expect(
      pollJob("j2", fakeStatus(["running", "failed"]), {
        intervalMs: 0,
        maxTries: 5,
      })
    ).rejects.toThrow(/failed/);
  });

  it("times out after maxTries", async () => {
    await expect(
      pollJob("j3", fakeStatus(["queued"]), { intervalMs: 0, maxTries: 3 })
    ).rejects.toThrow(/timeout/);
  });

  it("returns immediately when already done", async () => {
    const r = await pollJob("j4", fakeStatus(["done"]), {
      intervalMs: 0,
      maxTries: 1,
    });
    expect(r.status).toBe("done");
  });
});

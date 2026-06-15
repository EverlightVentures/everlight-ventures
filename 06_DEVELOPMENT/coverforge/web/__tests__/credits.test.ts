import { describe, it, expect } from "vitest";
import { uiState } from "../lib/credits";

describe("uiState", () => {
  it("new user with no free use -> can generate free preview", () => {
    expect(uiState({ balance: 0, usedFree: false }).action).toBe("free_generate");
  });

  it("used free, no credits -> must buy", () => {
    expect(uiState({ balance: 0, usedFree: true }).action).toBe("buy");
  });

  it("has credits -> can paid generate", () => {
    expect(uiState({ balance: 3, usedFree: true }).action).toBe("paid_generate");
  });

  it("free_generate cannot download", () => {
    expect(uiState({ balance: 0, usedFree: false }).canDownload).toBe(false);
  });

  it("paid_generate can download", () => {
    expect(uiState({ balance: 1, usedFree: true }).canDownload).toBe(true);
  });

  it("buy cannot download", () => {
    expect(uiState({ balance: 0, usedFree: true }).canDownload).toBe(false);
  });
});

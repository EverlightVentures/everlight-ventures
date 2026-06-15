import { describe, it, expect } from "vitest";
import { validateBookInput } from "../lib/validation";

const ok = {
  title: "Midnight",
  author: "A. Author",
  genre: "thriller",
  vibe: "rainy rooftop",
  trim: "6x9",
  pageCount: 200,
  paper: "white",
};

describe("validateBookInput", () => {
  it("accepts a complete valid input", () => {
    expect(validateBookInput(ok).valid).toBe(true);
  });

  it("rejects empty title", () => {
    const r = validateBookInput({ ...ok, title: "" });
    expect(r.valid).toBe(false);
    expect(r.errors.title).toBeDefined();
  });

  it("rejects page count below KDP minimum (24)", () => {
    expect(validateBookInput({ ...ok, pageCount: 10 }).valid).toBe(false);
  });

  it("rejects an unsupported genre", () => {
    expect(validateBookInput({ ...ok, genre: "western" }).valid).toBe(false);
  });

  it("rejects empty author", () => {
    const r = validateBookInput({ ...ok, author: "" });
    expect(r.valid).toBe(false);
    expect(r.errors.author).toBeDefined();
  });

  it("rejects page count above KDP max (828)", () => {
    expect(validateBookInput({ ...ok, pageCount: 900 }).valid).toBe(false);
  });
});

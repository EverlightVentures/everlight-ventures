"use client";

import { useState } from "react";
import { GENRES, type BookInput } from "../../lib/types";
import { validateBookInput } from "../../lib/validation";

interface CoverFormProps {
  onSubmit: (input: BookInput) => void;
  disabled?: boolean;
  submitLabel?: string;
}

const TRIM_OPTIONS = [
  { value: "5x8", label: '5" x 8" (Digest)' },
  { value: "5.5x8.5", label: '5.5" x 8.5" (Trade)' },
  { value: "6x9", label: '6" x 9" (Standard - most popular)' },
];

const PAPER_OPTIONS = [
  { value: "white", label: "White" },
  { value: "cream", label: "Cream (warmer tone)" },
];

const DEFAULT_INPUT: BookInput = {
  title: "",
  author: "",
  genre: "",
  vibe: "",
  trim: "6x9",
  pageCount: 250,
  paper: "white",
};

export default function CoverForm({
  onSubmit,
  disabled = false,
  submitLabel = "Generate Free Preview",
}: CoverFormProps) {
  const [input, setInput] = useState<BookInput>(DEFAULT_INPUT);
  const [errors, setErrors] = useState<Record<string, string>>({});
  const [touched, setTouched] = useState<Record<string, boolean>>({});

  function handleChange(field: keyof BookInput, value: string | number) {
    setInput((prev) => ({ ...prev, [field]: value }));
    if (touched[field]) {
      const result = validateBookInput({ ...input, [field]: value });
      setErrors(result.errors);
    }
  }

  function handleBlur(field: string) {
    setTouched((prev) => ({ ...prev, [field]: true }));
    const result = validateBookInput(input);
    setErrors(result.errors);
  }

  function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    const allTouched = Object.fromEntries(
      Object.keys(DEFAULT_INPUT).map((k) => [k, true])
    );
    setTouched(allTouched);
    const result = validateBookInput(input);
    setErrors(result.errors);
    if (result.valid) {
      onSubmit(input);
    }
  }

  const isValid = validateBookInput(input).valid;

  return (
    <form onSubmit={handleSubmit} className="space-y-5">
      {/* Title + Author row */}
      <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
        <div>
          <label className="input-label">Book Title *</label>
          <input
            className={`input-field${errors.title && touched.title ? " error" : ""}`}
            type="text"
            placeholder="e.g. Midnight Reckoning"
            value={input.title}
            onChange={(e) => handleChange("title", e.target.value)}
            onBlur={() => handleBlur("title")}
            disabled={disabled}
            maxLength={120}
          />
          {errors.title && touched.title && (
            <p className="mt-1 text-xs text-red-400">{errors.title}</p>
          )}
        </div>
        <div>
          <label className="input-label">Author Name *</label>
          <input
            className={`input-field${errors.author && touched.author ? " error" : ""}`}
            type="text"
            placeholder="e.g. Jordan Rivers"
            value={input.author}
            onChange={(e) => handleChange("author", e.target.value)}
            onBlur={() => handleBlur("author")}
            disabled={disabled}
            maxLength={80}
          />
          {errors.author && touched.author && (
            <p className="mt-1 text-xs text-red-400">{errors.author}</p>
          )}
        </div>
      </div>

      {/* Genre */}
      <div>
        <label className="input-label">Genre *</label>
        <select
          className={`input-field${errors.genre && touched.genre ? " error" : ""}`}
          value={input.genre}
          onChange={(e) => handleChange("genre", e.target.value)}
          onBlur={() => handleBlur("genre")}
          disabled={disabled}
        >
          <option value="">Select a genre...</option>
          {GENRES.map((g) => (
            <option key={g} value={g}>
              {g.charAt(0).toUpperCase() + g.slice(1)}
            </option>
          ))}
        </select>
        {errors.genre && touched.genre && (
          <p className="mt-1 text-xs text-red-400">{errors.genre}</p>
        )}
      </div>

      {/* Vibe */}
      <div>
        <label className="input-label">Mood / Visual Vibe *</label>
        <input
          className={`input-field${errors.vibe && touched.vibe ? " error" : ""}`}
          type="text"
          placeholder="e.g. dark rainy rooftop, glowing city, moody forest at dusk"
          value={input.vibe}
          onChange={(e) => handleChange("vibe", e.target.value)}
          onBlur={() => handleBlur("vibe")}
          disabled={disabled}
          maxLength={200}
        />
        {errors.vibe && touched.vibe && (
          <p className="mt-1 text-xs text-red-400">{errors.vibe}</p>
        )}
        <p className="mt-1 text-xs" style={{ color: "#666" }}>
          Describe the visual mood - this drives the AI image generation.
        </p>
      </div>

      {/* Trim + Paper row */}
      <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
        <div>
          <label className="input-label">Trim Size</label>
          <select
            className="input-field"
            value={input.trim}
            onChange={(e) => handleChange("trim", e.target.value)}
            disabled={disabled}
          >
            {TRIM_OPTIONS.map((t) => (
              <option key={t.value} value={t.value}>
                {t.label}
              </option>
            ))}
          </select>
        </div>
        <div>
          <label className="input-label">Interior Paper</label>
          <select
            className="input-field"
            value={input.paper}
            onChange={(e) => handleChange("paper", e.target.value)}
            disabled={disabled}
          >
            {PAPER_OPTIONS.map((p) => (
              <option key={p.value} value={p.value}>
                {p.label}
              </option>
            ))}
          </select>
        </div>
      </div>

      {/* Page Count */}
      <div>
        <label className="input-label">Page Count *</label>
        <input
          className={`input-field${errors.pageCount && touched.pageCount ? " error" : ""}`}
          type="number"
          min={24}
          max={828}
          value={input.pageCount}
          onChange={(e) =>
            handleChange("pageCount", parseInt(e.target.value, 10) || 0)
          }
          onBlur={() => handleBlur("pageCount")}
          disabled={disabled}
        />
        {errors.pageCount && touched.pageCount ? (
          <p className="mt-1 text-xs text-red-400">{errors.pageCount}</p>
        ) : (
          <p className="mt-1 text-xs" style={{ color: "#666" }}>
            KDP range: 24-828 pages. This determines the spine width.
          </p>
        )}
      </div>

      {/* Submit */}
      <button
        type="submit"
        className="gold-btn w-full py-3 px-6 rounded-lg text-sm tracking-wide"
        disabled={disabled || !isValid}
      >
        {disabled ? (
          <span className="flex items-center justify-center gap-2">
            <svg
              className="animate-spin h-4 w-4"
              viewBox="0 0 24 24"
              fill="none"
            >
              <circle
                className="opacity-25"
                cx="12"
                cy="12"
                r="10"
                stroke="currentColor"
                strokeWidth="4"
              />
              <path
                className="opacity-75"
                fill="currentColor"
                d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z"
              />
            </svg>
            Generating...
          </span>
        ) : (
          submitLabel
        )}
      </button>
    </form>
  );
}

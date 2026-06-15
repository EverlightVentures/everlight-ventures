import { BookInput, GENRES } from "./types";

export interface ValidationResult {
  valid: boolean;
  errors: Record<string, string>;
}

export function validateBookInput(i: BookInput): ValidationResult {
  const errors: Record<string, string> = {};

  if (!i.title?.trim()) errors.title = "Title is required";
  if (!i.author?.trim()) errors.author = "Author is required";
  if (!GENRES.includes(i.genre as typeof GENRES[number])) {
    errors.genre = "Pick a supported genre";
  }
  if (!i.vibe?.trim()) errors.vibe = "Vibe / mood is required";
  if (!i.pageCount || i.pageCount < 24) {
    errors.pageCount = "KDP minimum is 24 pages";
  }
  if (i.pageCount > 828) {
    errors.pageCount = "Max 828 pages";
  }

  return { valid: Object.keys(errors).length === 0, errors };
}

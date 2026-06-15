export type Trim = "5x8" | "6x9" | "5.5x8.5";
export type Paper = "white" | "cream";

export interface BookInput {
  title: string;
  author: string;
  genre: string;
  vibe: string;
  trim: Trim | string;
  pageCount: number;
  paper: Paper | string;
}

export const GENRES = ["romance", "thriller", "fantasy"] as const;
export type Genre = (typeof GENRES)[number];

export interface JobResult {
  job_id: string;
  status: "queued" | "running" | "done" | "failed";
  outputs: {
    preview_url?: string;
    ebook_url?: string;
    wrap_url?: string;
    keywords?: string[];
    categories?: string[];
    blurb?: string;
    ad_headlines?: string[];
  };
  signed: {
    ebook_cover?: string;
    full_wrap_pdf?: string;
  };
}

export interface Bundle {
  keywords: string[];
  categories: string[];
  blurb: string;
  ad_headlines: string[];
}

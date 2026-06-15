import { createClient } from "@supabase/supabase-js";

const supabaseUrl = process.env.NEXT_PUBLIC_SUPABASE_URL!;
const supabaseAnonKey = process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY!;

// COVERFORGE uses its own auth storageKey ("cf-auth") so the session is
// never shared with Alley Kingz / casino (domain-locked logins doctrine).
export const supabase = createClient(supabaseUrl, supabaseAnonKey, {
  auth: {
    storageKey: "cf-auth",
    autoRefreshToken: true,
    persistSession: true,
  },
});

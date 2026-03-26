const ELEVENLABS_API_KEY = Deno.env.get("ELEVENLABS_API_KEY") ?? "";
// Default: Sarah (female, warm) -- matches female dealer avatars (Aria, Kanisha, etc.)
const DEALER_VOICE_ID = Deno.env.get("EL_DEALER_VOICE") ?? "EXAVITQu4vr4xnSDxMaL";

const corsHeaders = {
  "Access-Control-Allow-Origin": "*",
  "Access-Control-Allow-Headers": "authorization, x-client-info, apikey, content-type",
  "Access-Control-Allow-Methods": "POST, OPTIONS",
};

Deno.serve(async (req) => {
  if (req.method === "OPTIONS") {
    return new Response("ok", { headers: corsHeaders });
  }

  if (req.method !== "POST") {
    return new Response("Method not allowed", { status: 405, headers: corsHeaders });
  }

  try {
    const { text, voice_id } = await req.json();
    if (!text) return new Response("Missing text", { status: 400, headers: corsHeaders });

    if (!ELEVENLABS_API_KEY) {
      return new Response("ElevenLabs API key not configured", { status: 503, headers: corsHeaders });
    }

    // Cap text length to prevent abuse (max 500 chars)
    const safeText = text.slice(0, 500);

    // Allow per-dealer voice override (validated against allowlist)
    const ALLOWED_VOICES = [
      "EXAVITQu4vr4xnSDxMaL", // Sarah (Aria)
      "onwK4e9ZLuTAKqWW03F9", // Marcus
      "XrExE9yKIg1WjnnlVkGX", // Kanisha
      "pNInz6obpgDQGcFmaJgB", // James
    ];
    const voiceId = (voice_id && ALLOWED_VOICES.includes(voice_id))
      ? voice_id
      : DEALER_VOICE_ID;

    const res = await fetch(
      `https://api.elevenlabs.io/v1/text-to-speech/${voiceId}`,
      {
        method: "POST",
        headers: {
          "xi-api-key": ELEVENLABS_API_KEY,
          "Content-Type": "application/json",
        },
        body: JSON.stringify({
          text: safeText,
          model_id: "eleven_flash_v2",
          voice_settings: {
            stability: 0.60,
            similarity_boost: 0.85,
            style: 0.20,
            use_speaker_boost: true,
          },
        }),
      }
    );

    if (!res.ok) {
      const err = await res.text();
      console.error("ElevenLabs error:", err);
      return new Response("ElevenLabs error", { status: 502, headers: corsHeaders });
    }

    const audio = await res.arrayBuffer();
    return new Response(audio, {
      headers: {
        ...corsHeaders,
        "Content-Type": "audio/mpeg",
        "Cache-Control": "public, max-age=86400",
      },
    });
  } catch (err) {
    console.error("dealer-speak error:", err);
    return new Response("Internal error", { status: 500, headers: corsHeaders });
  }
});

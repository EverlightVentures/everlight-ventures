import { ComingSoon } from "@/components/ComingSoon";

export default function ArcadePage() {
  return (
    <ComingSoon
      title="Arcade"
      domain="Arcade"
      accent="#F472B6"
      themeClass="theme-arcade"
      blurb="Vantaris casino, Alley Kingz, Blackjack. Playful neon variant, opt-in."
      willInclude={[
        "Vantaris consolidated game launcher (6 games built)",
        "Alley Kingz IAP + VIP + NFT marketplace stats",
        "Blackjack dealer roster (Aria, Marcus, Kanisha, Bacardi Ice)",
        "ElevenLabs TTS minutes consumed",
        "Daily wagered + house edge realized",
      ]}
    />
  );
}

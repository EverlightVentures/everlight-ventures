import { useEffect, useState } from "react";
import { Sheet, SheetContent, SheetHeader, SheetTitle } from "@/components/ui/sheet";
import { bjApi } from "@/lib/blackjack-api";
import AvatarRenderer, { type AvatarConfig, DEFAULT_AVATAR } from "./AvatarRenderer";
import AvatarBuilder from "./AvatarBuilder";
import PresenceBadge, { getVipTier, getNextVipTier } from "./PresenceBadge";
import type { GameSettings } from "./SettingsPanel";
import { getAchievementProgress, getStoredStats } from "@/lib/achievements-system";

interface Props {
  open: boolean;
  onClose: () => void;
  playerId: string;
  displayName: string;
  onDisplayNameChange: (name: string) => void;
  emoji: string;
  onEmojiChange: (emoji: string) => void;
  avatarConfig: AvatarConfig;
  onAvatarChange: (config: AvatarConfig) => void;
  avatarUrl?: string | null;
  onAvatarUrlChange?: (url: string | null) => void;
  settings: GameSettings;
  onSettingsChange: (s: GameSettings) => void;
  onLogout: () => void;
}

interface ProfileStats {
  hands_played: number;
  hands_won: number;
  win_rate: number;
  total_winnings: number;
  total_wagered: number;
  blackjacks_hit: number;
  current_streak: number;
  biggest_win: number;
  rank: number;
  level: number;
  xp: number;
  xp_to_next: number;
  member_since: string;
  total_spent_cents: number;
}

interface HandRecord {
  id: string;
  created_at: string;
  bet_amount: number;
  result: string;
  payout: number;
  player_cards: string;
  dealer_cards: string;
}

export default function PlayerProfile({
  open, onClose, playerId, displayName, onDisplayNameChange,
  emoji, onEmojiChange, avatarConfig, onAvatarChange, avatarUrl, onAvatarUrlChange, settings, onSettingsChange, onLogout,
}: Props) {
  const [stats, setStats] = useState<ProfileStats | null>(null);
  const [history, setHistory] = useState<HandRecord[]>([]);
  const [editingName, setEditingName] = useState(false);
  const [newName, setNewName] = useState(displayName);
  const [activeTab, setActiveTab] = useState<"stats" | "history" | "achievements" | "settings">("stats");
  const [showAvatarBuilder, setShowAvatarBuilder] = useState(false);

  useEffect(() => {
    if (!open || !playerId) return;
    // Merge server stats with local stored stats (local takes precedence if higher)
    const localStats = getStoredStats();
    bjApi.getProfile(playerId).then(data => {
      if (data && !data.error) {
        const serverHands = data.hands_played ?? 0;
        const localHands = localStats.handsPlayed ?? 0;
        const useLocal = localHands > serverHands;
        setStats({
          hands_played: Math.max(serverHands, localHands),
          hands_won: useLocal ? (localStats.handsWon ?? 0) : (data.hands_won ?? 0),
          win_rate: useLocal && localHands > 0
            ? ((localStats.handsWon ?? 0) / localHands) * 100
            : (data.win_rate ?? 0),
          total_winnings: Math.max(data.total_winnings ?? 0, localStats.sessionWinnings ?? 0),
          total_wagered: data.total_wagered ?? 0,
          blackjacks_hit: Math.max(data.blackjacks_hit ?? 0, localStats.blackjacks ?? 0),
          current_streak: Math.max(data.current_streak ?? 0, localStats.winStreak ?? 0),
          biggest_win: Math.max(data.biggest_win ?? 0, localStats.biggestWin ?? 0),
          rank: data.rank ?? 0,
          level: Math.max(data.level ?? 1, Math.floor(Math.max(serverHands, localHands) / 10) + 1),
          xp: data.xp ?? 0,
          xp_to_next: data.xp_to_next ?? 500,
          member_since: data.member_since ?? data.created_at ?? "",
          total_spent_cents: data.total_spent_cents ?? 0,
        });
      } else {
        // Server failed -- use local stats only
        setStats({
          hands_played: localStats.handsPlayed ?? 0,
          hands_won: localStats.handsWon ?? 0,
          win_rate: localStats.handsPlayed ? ((localStats.handsWon ?? 0) / localStats.handsPlayed) * 100 : 0,
          total_winnings: localStats.sessionWinnings ?? 0,
          total_wagered: 0,
          blackjacks_hit: localStats.blackjacks ?? 0,
          current_streak: localStats.winStreak ?? 0,
          biggest_win: localStats.biggestWin ?? 0,
          rank: 0,
          level: Math.floor((localStats.handsPlayed ?? 0) / 10) + 1,
          xp: 0,
          xp_to_next: 500,
          member_since: "",
          total_spent_cents: 0,
        });
      }
    }).catch(() => {
      // Fallback to local stats on network error
      setStats({
        hands_played: localStats.handsPlayed ?? 0,
        hands_won: localStats.handsWon ?? 0,
        win_rate: localStats.handsPlayed ? ((localStats.handsWon ?? 0) / localStats.handsPlayed) * 100 : 0,
        total_winnings: localStats.sessionWinnings ?? 0,
        total_wagered: 0,
        blackjacks_hit: localStats.blackjacks ?? 0,
        current_streak: localStats.winStreak ?? 0,
        biggest_win: localStats.biggestWin ?? 0,
        rank: 0,
        level: Math.floor((localStats.handsPlayed ?? 0) / 10) + 1,
        xp: 0,
        xp_to_next: 500,
        member_since: "",
        total_spent_cents: 0,
      });
    });
    bjApi.getHistory(playerId).then(data => {
      if (data && Array.isArray(data.hands)) setHistory(data.hands.slice(0, 50));
      else if (data && Array.isArray(data.history)) setHistory(data.history.slice(0, 50));
    });
  }, [open, playerId]);

  const saveName = async () => {
    if (newName.length < 3 || newName.length > 20) return;
    const res = await bjApi.updateProfile(playerId, { display_name: newName });
    if (res?.error) {
      alert(res.error);
      return;
    }
    onDisplayNameChange(newName);
    localStorage.setItem("ev_bj_display_name", newName);
    // Sync all cached profile stores so name persists across sessions
    try {
      const cached = JSON.parse(localStorage.getItem("blackjack_player") || "{}");
      cached.display_name = newName;
      cached.name = newName;
      localStorage.setItem("blackjack_player", JSON.stringify(cached));
    } catch {}
    try {
      const profile = JSON.parse(localStorage.getItem("ev_bj_player_profile") || "{}");
      profile.name = newName;
      localStorage.setItem("ev_bj_player_profile", JSON.stringify(profile));
    } catch {}
    setEditingName(false);
  };

  const resultColor = (r: string) => {
    const rl = (r ?? "").toLowerCase();
    if (rl === "blackjack") return "#D4AF37";
    if (rl === "win") return "#22C55E";
    if (rl === "push") return "#888";
    return "#EF4444";
  };

  const level = stats?.level ?? 1;
  const xpPct = stats ? Math.min(100, (stats.xp / Math.max(1, stats.xp_to_next)) * 100) : 0;
  const vipTier = getVipTier(stats?.total_spent_cents ?? 0);
  const nextVip = getNextVipTier(stats?.total_spent_cents ?? 0);

  // Count accessories for presence badge
  const accessoryCount = [avatarConfig.hat, avatarConfig.glasses, avatarConfig.jewelry, avatarConfig.special]
    .filter(a => a && a !== "none").length;

  const Toggle = ({ label, value, onToggle }: { label: string; value: boolean; onToggle: () => void }) => (
    <div className="flex items-center justify-between py-3 border-b" style={{ borderColor: "#222" }}>
      <span className="text-sm" style={{ color: "#CCC" }}>{label}</span>
      <button onClick={onToggle} className="w-11 h-6 rounded-full transition-all relative" style={{ background: value ? "#D4AF37" : "#333" }}>
        <div className="rounded-full absolute top-[3px] transition-all" style={{ background: "#FFF", left: value ? 22 : 3, width: 18, height: 18 }} />
      </button>
    </div>
  );

  return (
    <>
      <Sheet open={open} onOpenChange={onClose}>
        <SheetContent side="left" className="luxury-modal w-[340px] overflow-y-auto">
          <SheetHeader>
            <SheetTitle className="casino-heading text-xl tracking-wider">PLAYER PROFILE</SheetTitle>
            <div className="gold-accent-line" />
          </SheetHeader>

          {/* Avatar + Name */}
          <div className="flex flex-col items-center mt-4 mb-4">
            <div className="relative group">
              {avatarUrl ? (
                <div className="w-[72px] h-[72px] rounded-full overflow-hidden" style={{ border: "3px solid #D4AF37" }}>
                  <img src={avatarUrl} alt="" className="w-full h-full object-cover rounded-full" referrerPolicy="no-referrer" />
                </div>
              ) : (
                <button onClick={() => setShowAvatarBuilder(true)}>
                  <AvatarRenderer config={avatarConfig} size={72} />
                </button>
              )}
              <div className="absolute inset-0 rounded-full flex items-center justify-center opacity-0 group-hover:opacity-100 transition-all cursor-pointer" style={{ background: "rgba(0,0,0,0.5)" }}
                onClick={() => setShowAvatarBuilder(true)}
              >
                <span className="text-[10px] font-bold tracking-wider" style={{ color: "#D4AF37" }}>EDIT</span>
              </div>
            </div>
            {/* Photo upload / remove */}
            <div className="flex gap-2 mt-2">
              <label className="text-[9px] font-bold tracking-wider px-2 py-1 rounded cursor-pointer hover:bg-white/5 transition-all"
                style={{ color: "#D4AF37", border: "1px solid #D4AF3740" }}
              >
                UPLOAD PHOTO
                <input type="file" accept="image/*" className="hidden" onChange={(e) => {
                  const file = e.target.files?.[0];
                  if (!file) return;
                  const reader = new FileReader();
                  reader.onload = (ev) => {
                    const dataUrl = ev.target?.result as string;
                    if (dataUrl && onAvatarUrlChange) {
                      onAvatarUrlChange(dataUrl);
                      localStorage.setItem("ev_bj_avatar_url", dataUrl);
                      try {
                        const cached = JSON.parse(localStorage.getItem("blackjack_player") || "{}");
                        cached.avatar_url = dataUrl;
                        localStorage.setItem("blackjack_player", JSON.stringify(cached));
                      } catch {}
                    }
                  };
                  reader.readAsDataURL(file);
                }} />
              </label>
              {avatarUrl && onAvatarUrlChange && (
                <button onClick={() => {
                  onAvatarUrlChange(null);
                  localStorage.removeItem("ev_bj_avatar_url");
                  try {
                    const cached = JSON.parse(localStorage.getItem("blackjack_player") || "{}");
                    delete cached.avatar_url;
                    localStorage.setItem("blackjack_player", JSON.stringify(cached));
                  } catch {}
                }}
                  className="text-[9px] font-bold tracking-wider px-2 py-1 rounded hover:bg-white/5 transition-all"
                  style={{ color: "#888", border: "1px solid #33340" }}
                >
                  USE AVATAR
                </button>
              )}
            </div>

            {editingName ? (
              <div className="flex items-center gap-2 mt-2">
                <input value={newName} onChange={e => setNewName(e.target.value)} maxLength={20}
                  className="px-2 py-1 rounded text-sm text-center w-32"
                  style={{ background: "#1a1a1a", border: "1px solid #D4AF37", color: "#E0E0E0" }}
                  autoFocus onKeyDown={e => e.key === "Enter" && saveName()}
                />
                <button onClick={saveName} className="text-xs px-2 py-1 rounded" style={{ background: "#D4AF37", color: "#0A0A0A" }}>Save</button>
              </div>
            ) : (
              <button onClick={() => { setNewName(displayName); setEditingName(true); }} className="text-lg font-bold hover:underline mt-2" style={{ color: "#E0E0E0" }}>
                {displayName}
              </button>
            )}

            {/* Level + Presence badges */}
            <div className="flex items-center gap-2 mt-2 flex-wrap justify-center">
              <span className="text-xs font-bold px-2 py-0.5 rounded" style={{ background: "#D4AF37", color: "#0A0A0A" }}>LVL {level}</span>
              <PresenceBadge
                accessories={accessoryCount}
                winStreak={stats?.current_streak ?? 0}
                level={level}
                handsPlayed={stats?.hands_played ?? 0}
                totalSpentCents={stats?.total_spent_cents ?? 0}
              />
            </div>

            {/* XP bar */}
            <div className="w-full mt-2 h-2 rounded-full overflow-hidden" style={{ background: "#222" }}>
              <div className="h-full rounded-full transition-all" style={{ width: `${xpPct}%`, background: "linear-gradient(90deg, #D4AF37, #B8960C)" }} />
            </div>
            <span className="text-[10px] mt-1" style={{ color: "#666" }}>{stats?.xp ?? 0} / {stats?.xp_to_next ?? 500} XP</span>

            {/* VIP progress */}
            {vipTier.icon && (
              <div className="mt-2 text-center">
                <span className="text-xs" style={{ color: vipTier.color }}>{vipTier.icon} {vipTier.name} VIP</span>
                {nextVip && (
                  <p className="text-[9px] mt-0.5" style={{ color: "#555" }}>
                    ${((nextVip.min - (stats?.total_spent_cents ?? 0)) / 100).toFixed(2)} to {nextVip.name}
                  </p>
                )}
              </div>
            )}
          </div>

          {/* Tabs */}
          <div className="flex border-b mb-4" style={{ borderColor: "#333" }}>
            {(["stats", "achievements", "history", "settings"] as const).map(t => (
              <button key={t} onClick={() => setActiveTab(t)}
                className="flex-1 py-2 text-[10px] font-bold tracking-wider transition-all"
                style={{ color: activeTab === t ? "#D4AF37" : "#666", borderBottom: activeTab === t ? "2px solid #D4AF37" : "none" }}
              >{t === "achievements" ? "ACHIEVE" : t.toUpperCase()}</button>
            ))}
          </div>

          {activeTab === "achievements" && (
            <div className="space-y-2 max-h-[400px] overflow-y-auto">
              {getAchievementProgress(getStoredStats()).map(a => (
                <div key={a.id} className="flex items-center gap-3 p-3 rounded-lg" style={{ background: "#1a1a1a", opacity: a.earned ? 1 : 0.6 }}>
                  <span className="text-2xl">{a.icon}</span>
                  <div className="flex-1 min-w-0">
                    <p className="text-xs font-bold" style={{ color: a.earned ? "#D4AF37" : "#888" }}>{a.title}</p>
                    <p className="text-[10px]" style={{ color: "#666" }}>{a.description}</p>
                    {!a.earned && (
                      <div className="mt-1 h-1.5 rounded-full overflow-hidden" style={{ background: "#222" }}>
                        <div className="h-full rounded-full" style={{ width: `${Math.min(100, (a.progressInfo.current / Math.max(1, a.progressInfo.target)) * 100)}%`, background: "#D4AF37" }} />
                      </div>
                    )}
                    {!a.earned && <p className="text-[9px] mt-0.5" style={{ color: "#555" }}>{a.progressInfo.current}/{a.progressInfo.target}</p>}
                  </div>
                  <span className="text-[10px] font-bold" style={{ color: a.earned ? "#22C55E" : "#555" }}>
                    {a.earned ? "✓" : `+${a.reward}`}
                  </span>
                </div>
              ))}
            </div>
          )}

          {activeTab === "stats" && (
            <div className="grid grid-cols-2 gap-2">
              {[
                { label: "Hands Played", value: (stats?.hands_played ?? 0).toLocaleString() },
                { label: "Win Rate", value: `${(stats?.win_rate ?? 0).toFixed(1)}%` },
                { label: "Total Winnings", value: (stats?.total_winnings ?? 0).toLocaleString() },
                { label: "Total Wagered", value: (stats?.total_wagered ?? 0).toLocaleString() },
                { label: "Blackjacks", value: (stats?.blackjacks_hit ?? 0).toLocaleString() },
                { label: "Streak", value: (stats?.current_streak ?? 0).toLocaleString() },
                { label: "Biggest Win", value: (stats?.biggest_win ?? 0).toLocaleString() },
                { label: "Rank", value: stats?.rank ? `#${stats.rank}` : "—" },
              ].map(s => (
                <div key={s.label} className="p-3 rounded-lg text-center" style={{ background: "#1a1a1a" }}>
                  <p className="text-[10px] tracking-wider mb-1" style={{ color: "#888" }}>{s.label.toUpperCase()}</p>
                  <p className="text-sm font-bold" style={{ color: "#D4AF37" }}>{s.value}</p>
                </div>
              ))}
            </div>
          )}

          {activeTab === "history" && (
            <div className="space-y-1 max-h-[400px] overflow-y-auto">
              {history.length === 0 ? (
                <p className="text-sm text-center py-8" style={{ color: "#666" }}>No hands yet. Play a round!</p>
              ) : history.map((h, i) => (
                <div key={h.id ?? i} className="flex items-center justify-between px-3 py-2 rounded-lg" style={{ background: "#1a1a1a" }}>
                  <div className="flex-1">
                    <span className="text-xs font-bold mr-2" style={{ color: resultColor(h.result) }}>
                      {(h.result ?? "").toUpperCase()}
                    </span>
                    <span className="text-[10px]" style={{ color: "#888" }}>Bet: {(h.bet_amount ?? 0).toLocaleString()}</span>
                  </div>
                  <span className="text-xs font-bold" style={{ color: (h.payout ?? 0) > 0 ? "#22C55E" : "#EF4444" }}>
                    {(h.payout ?? 0) > 0 ? "+" : ""}{(h.payout ?? 0).toLocaleString()}
                  </span>
                </div>
              ))}
            </div>
          )}

          {activeTab === "settings" && (
            <div>
              <Toggle label="Sound Effects" value={settings.soundOn} onToggle={() => onSettingsChange({ ...settings, soundOn: !settings.soundOn })} />
              <Toggle label="Music" value={settings.musicOn} onToggle={() => onSettingsChange({ ...settings, musicOn: !settings.musicOn })} />
              <Toggle label="Auto-Rebet" value={settings.autoRebet} onToggle={() => onSettingsChange({ ...settings, autoRebet: !settings.autoRebet })} />
              <div className="flex items-center justify-between py-3 border-b" style={{ borderColor: "#222" }}>
                <span className="text-sm" style={{ color: "#CCC" }}>Card Speed</span>
                <div className="flex gap-1">
                  {(["normal", "fast"] as const).map(s => (
                    <button key={s} onClick={() => onSettingsChange({ ...settings, cardSpeed: s })}
                      className="px-3 py-1 rounded text-xs font-bold tracking-wider"
                      style={{ background: settings.cardSpeed === s ? "#D4AF37" : "#222", color: settings.cardSpeed === s ? "#0A0A0A" : "#888" }}
                    >{s.toUpperCase()}</button>
                  ))}
                </div>
              </div>
              <button onClick={onLogout} className="w-full mt-6 py-3 rounded-lg text-sm font-bold tracking-wider" style={{ background: "#EF4444", color: "#FFF" }}>
                LOG OUT
              </button>
            </div>
          )}

          {stats?.member_since && (
            <p className="text-[10px] text-center mt-6" style={{ color: "#555" }}>
              Member since {new Date(stats.member_since).toLocaleDateString()}
            </p>
          )}
        </SheetContent>
      </Sheet>

      <AvatarBuilder
        open={showAvatarBuilder}
        onClose={() => setShowAvatarBuilder(false)}
        config={avatarConfig}
        onSave={onAvatarChange}
      />
    </>
  );
}

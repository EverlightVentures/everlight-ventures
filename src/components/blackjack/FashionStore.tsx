import { useState } from "react";
import { Dialog, DialogContent, DialogHeader, DialogTitle } from "@/components/ui/dialog";
import { getEarnedAchievements } from "@/lib/achievements-system";

interface Props {
  open: boolean;
  onClose: () => void;
  balance: number;
  onPurchase: (item: FashionItem) => void;
  ownedItems: string[];
  playerLevel?: number;
  isMasterPass?: boolean;
}

export interface FashionItem {
  id: string;
  name: string;
  type: "hat" | "glasses" | "jewelry" | "special" | "outfit" | "card_back" | "table_theme" | "emote" | "avatar_frame" | "dealer_skin";
  emoji: string;
  price: number;
  rarity: "common" | "rare" | "epic" | "legendary";
  unlockMethod?: "free" | "achievement" | "gems" | "level" | "master_pass";
  unlockCondition?: string; // e.g. "Win 10 blackjacks" or "Level 10"
  unlockLevel?: number;
  unlockAchievement?: string;
}

const STORE_ITEMS: FashionItem[] = [
  // Card Backs - 2 free, 3 achievement, 5 gem, 3 master pass
  { id: "cb-classic-red", name: "Classic Red", type: "card_back", emoji: "🟥", price: 0, rarity: "common", unlockMethod: "free" },
  { id: "cb-midnight-blue", name: "Midnight Blue", type: "card_back", emoji: "🟦", price: 0, rarity: "common", unlockMethod: "free" },
  { id: "cb-gold-foil", name: "Gold Foil", type: "card_back", emoji: "🟨", price: 0, rarity: "rare", unlockMethod: "achievement", unlockAchievement: "card-shark", unlockCondition: "Play 100 hands" },
  { id: "cb-neon-green", name: "Neon Green", type: "card_back", emoji: "🟩", price: 0, rarity: "rare", unlockMethod: "achievement", unlockAchievement: "hot-streak", unlockCondition: "Win 5 in a row" },
  { id: "cb-everlight-purple", name: "Everlight Purple", type: "card_back", emoji: "🟪", price: 0, rarity: "epic", unlockMethod: "achievement", unlockAchievement: "bj-master", unlockCondition: "Get 10 blackjacks" },
  { id: "cb-diamond", name: "Diamond Pattern", type: "card_back", emoji: "💎", price: 50, rarity: "rare", unlockMethod: "gems" },
  { id: "cb-fire", name: "Flame Card", type: "card_back", emoji: "🔥", price: 100, rarity: "epic", unlockMethod: "gems" },
  { id: "cb-royal", name: "Royal Crest", type: "card_back", emoji: "👑", price: 200, rarity: "legendary", unlockMethod: "gems" },
  { id: "cb-master-1", name: "Master Gold", type: "card_back", emoji: "✨", price: 0, rarity: "legendary", unlockMethod: "master_pass", unlockCondition: "Master Pass Exclusive" },
  { id: "cb-master-2", name: "Master Obsidian", type: "card_back", emoji: "🖤", price: 0, rarity: "legendary", unlockMethod: "master_pass", unlockCondition: "Master Pass Exclusive" },

  // Table Themes - 1 free, 2 level, 3 gem, 2 master pass
  { id: "tt-default", name: "Classic Green", type: "table_theme", emoji: "🟢", price: 0, rarity: "common", unlockMethod: "free" },
  { id: "tt-blue", name: "Ocean Blue", type: "table_theme", emoji: "🌊", price: 0, rarity: "rare", unlockMethod: "level", unlockLevel: 5, unlockCondition: "Reach Level 5" },
  { id: "tt-red", name: "Ruby Red", type: "table_theme", emoji: "❤️", price: 0, rarity: "rare", unlockMethod: "level", unlockLevel: 10, unlockCondition: "Reach Level 10" },
  { id: "tt-midnight", name: "Midnight", type: "table_theme", emoji: "🌙", price: 100, rarity: "rare", unlockMethod: "gems" },
  { id: "tt-sunset", name: "Sunset", type: "table_theme", emoji: "🌅", price: 200, rarity: "epic", unlockMethod: "gems" },
  { id: "tt-neon", name: "Neon Vegas", type: "table_theme", emoji: "🌃", price: 300, rarity: "epic", unlockMethod: "gems" },
  { id: "tt-master-1", name: "Master Gold Felt", type: "table_theme", emoji: "🏆", price: 0, rarity: "legendary", unlockMethod: "master_pass", unlockCondition: "Master Pass Exclusive" },

  // Emotes - 5 free, 5 achievement, 10 gem, 5 master pass
  { id: "em-thumbsup", name: "Thumbs Up", type: "emote", emoji: "👍", price: 0, rarity: "common", unlockMethod: "free" },
  { id: "em-fire", name: "Fire", type: "emote", emoji: "🔥", price: 0, rarity: "common", unlockMethod: "free" },
  { id: "em-clap", name: "Clap", type: "emote", emoji: "👏", price: 0, rarity: "common", unlockMethod: "free" },
  { id: "em-heart", name: "Heart", type: "emote", emoji: "❤️", price: 0, rarity: "common", unlockMethod: "free" },
  { id: "em-laugh", name: "Laugh", type: "emote", emoji: "😂", price: 0, rarity: "common", unlockMethod: "free" },
  { id: "em-crown", name: "Crown", type: "emote", emoji: "👑", price: 0, rarity: "rare", unlockMethod: "achievement", unlockAchievement: "on-fire", unlockCondition: "Win 10 in a row" },
  { id: "em-money", name: "Money", type: "emote", emoji: "💰", price: 25, rarity: "rare", unlockMethod: "gems" },
  { id: "em-dice", name: "Dice", type: "emote", emoji: "🎲", price: 50, rarity: "rare", unlockMethod: "gems" },
  { id: "em-rocket", name: "Rocket", type: "emote", emoji: "🚀", price: 100, rarity: "epic", unlockMethod: "gems" },

  // Avatar Frames
  { id: "af-default", name: "Default", type: "avatar_frame", emoji: "⚪", price: 0, rarity: "common", unlockMethod: "free" },
  { id: "af-blue", name: "Blue Ring", type: "avatar_frame", emoji: "🔵", price: 0, rarity: "rare", unlockMethod: "level", unlockLevel: 5, unlockCondition: "Reach Level 5" },
  { id: "af-purple", name: "Purple Ring", type: "avatar_frame", emoji: "🟣", price: 0, rarity: "epic", unlockMethod: "level", unlockLevel: 10, unlockCondition: "Reach Level 10" },
  { id: "af-gold", name: "Gold Ring", type: "avatar_frame", emoji: "🟡", price: 0, rarity: "legendary", unlockMethod: "level", unlockLevel: 20, unlockCondition: "Reach Level 20" },
  { id: "af-master", name: "Master Ring", type: "avatar_frame", emoji: "✨", price: 0, rarity: "legendary", unlockMethod: "master_pass", unlockCondition: "Master Pass Exclusive" },

  // Dealer Skins
  { id: "ds-default", name: "House Dealer", type: "dealer_skin", emoji: "🤵", price: 0, rarity: "common", unlockMethod: "free" },
  { id: "ds-vegas", name: "Vegas Pro", type: "dealer_skin", emoji: "🎰", price: 500, rarity: "epic", unlockMethod: "gems" },
  { id: "ds-master", name: "Gold Dealer", type: "dealer_skin", emoji: "👔", price: 0, rarity: "legendary", unlockMethod: "master_pass", unlockCondition: "Master Pass Exclusive" },
];

const RARITY_COLORS: Record<string, string> = {
  common: "#888",
  rare: "#1E90FF",
  epic: "#7C3AED",
  legendary: "#D4AF37",
  gold: "#D4AF37",
};

type FilterTab = "all" | "card_back" | "table_theme" | "emote" | "avatar_frame" | "dealer_skin";
const FILTER_LABELS: Record<FilterTab, string> = {
  all: "ALL",
  card_back: "CARDS",
  table_theme: "TABLES",
  emote: "EMOTES",
  avatar_frame: "FRAMES",
  dealer_skin: "DEALERS",
};

function isItemUnlocked(item: FashionItem, ownedItems: string[], playerLevel: number, isMasterPass: boolean): boolean {
  if (ownedItems.includes(item.id)) return true;
  if (item.unlockMethod === "free") return true;
  if (item.unlockMethod === "level" && item.unlockLevel && playerLevel >= item.unlockLevel) return true;
  if (item.unlockMethod === "master_pass" && isMasterPass) return true;
  if (item.unlockMethod === "achievement" && item.unlockAchievement) {
    const earned = getEarnedAchievements();
    return !!earned[item.unlockAchievement];
  }
  if (item.unlockMethod === "gems") return ownedItems.includes(item.id); // Must be purchased
  return false;
}

export default function FashionStore({ open, onClose, balance, onPurchase, ownedItems, playerLevel = 1, isMasterPass = false }: Props) {
  const [filter, setFilter] = useState<FilterTab>("all");
  const [confirmId, setConfirmId] = useState<string | null>(null);

  const filtered = filter === "all" ? STORE_ITEMS : STORE_ITEMS.filter(i => i.type === filter);

  return (
    <Dialog open={open} onOpenChange={onClose}>
      <DialogContent className="luxury-modal max-w-md max-h-[80vh] overflow-hidden flex flex-col">
        <DialogHeader>
          <DialogTitle className="casino-heading text-xl tracking-wider">EVERLIGHT BOUTIQUE</DialogTitle>
          <p className="text-xs" style={{ color: "#888" }}>Earn, unlock, or purchase cosmetic items</p>
          <div className="gold-accent-line" />
        </DialogHeader>

        <div className="flex justify-center mb-2">
          <div className="px-4 py-1.5 rounded-lg text-xs font-bold" style={{ background: "#1a1a1a", border: "1px solid #D4AF37", color: "#D4AF37" }}>
            CHIPS: {balance.toLocaleString()}
          </div>
        </div>

        <div className="flex gap-1 overflow-x-auto pb-2">
          {(Object.keys(FILTER_LABELS) as FilterTab[]).map(t => (
            <button key={t} onClick={() => setFilter(t)}
              className="px-3 py-1.5 rounded-lg text-[10px] font-bold tracking-wider whitespace-nowrap transition-all"
              style={{
                background: filter === t ? "#D4AF3720" : "#1a1a1a",
                border: filter === t ? "1px solid #D4AF37" : "1px solid #333",
                color: filter === t ? "#D4AF37" : "#888",
              }}
            >{FILTER_LABELS[t]}</button>
          ))}
        </div>

        <div className="flex-1 overflow-y-auto grid grid-cols-2 gap-2">
          {filtered.map(item => {
            const unlocked = isItemUnlocked(item, ownedItems, playerLevel, isMasterPass);
            const owned = ownedItems.includes(item.id);
            const canBuy = item.unlockMethod === "gems" && !owned && balance >= item.price;
            const isConfirming = confirmId === item.id;

            return (
              <div key={item.id} className="p-3 rounded-xl transition-all relative" style={{
                background: "#1a1a1a",
                border: `1px solid ${RARITY_COLORS[item.rarity] || "#888"}30`,
                opacity: unlocked || item.unlockMethod === "gems" ? 1 : 0.6,
              }}>
                {/* Lock overlay */}
                {!unlocked && item.unlockMethod !== "gems" && (
                  <div className="absolute inset-0 rounded-xl flex items-center justify-center z-10" style={{ background: "rgba(0,0,0,0.5)" }}>
                    <span className="text-2xl">🔒</span>
                  </div>
                )}

                <div className="flex items-center justify-between mb-2">
                  <span className="text-2xl">{item.emoji}</span>
                  <span className="text-[8px] font-bold px-1.5 py-0.5 rounded-full tracking-wider" style={{
                    background: `${RARITY_COLORS[item.rarity] || "#888"}20`,
                    color: RARITY_COLORS[item.rarity] || "#888",
                    border: `1px solid ${RARITY_COLORS[item.rarity] || "#888"}40`,
                  }}>
                    {item.rarity.toUpperCase()}
                  </span>
                </div>
                <p className="text-xs font-bold mb-1" style={{ color: "#E0E0E0" }}>{item.name}</p>

                {/* Unlock condition */}
                {!unlocked && item.unlockCondition && item.unlockMethod !== "gems" && (
                  <p className="text-[9px] mb-1" style={{ color: "#666" }}>{item.unlockCondition}</p>
                )}

                {/* Action button */}
                {owned || (unlocked && item.unlockMethod === "free") ? (
                  <button disabled className="w-full py-1.5 rounded-lg text-[10px] font-bold tracking-wider" style={{ background: "#333", color: "#888" }}>
                    {owned ? "OWNED" : "EQUIPPED"}
                  </button>
                ) : item.unlockMethod === "gems" ? (
                  isConfirming ? (
                    <div className="flex gap-1">
                      <button
                        onClick={() => { onPurchase(item); setConfirmId(null); }}
                        disabled={!canBuy}
                        className="flex-1 py-1.5 rounded-lg text-[10px] font-bold"
                        style={{ background: canBuy ? "#22C55E" : "#333", color: canBuy ? "#FFF" : "#666" }}
                      >CONFIRM</button>
                      <button onClick={() => setConfirmId(null)} className="px-2 py-1.5 rounded-lg text-[10px]" style={{ background: "#333", color: "#888" }}>✕</button>
                    </div>
                  ) : (
                    <button
                      onClick={() => canBuy && setConfirmId(item.id)}
                      disabled={!canBuy}
                      className="w-full py-1.5 rounded-lg text-[10px] font-bold tracking-wider"
                      style={{
                        background: canBuy ? (RARITY_COLORS[item.rarity] || "#888") : "#222",
                        color: canBuy ? "#0A0A0A" : "#555",
                      }}
                    >
                      {canBuy ? `${item.price.toLocaleString()} CHIPS` : "CAN'T AFFORD"}
                    </button>
                  )
                ) : unlocked ? (
                  <button disabled className="w-full py-1.5 rounded-lg text-[10px] font-bold tracking-wider" style={{ background: "#22C55E20", color: "#22C55E" }}>
                    UNLOCKED
                  </button>
                ) : (
                  <button disabled className="w-full py-1.5 rounded-lg text-[10px] font-bold tracking-wider" style={{ background: "#222", color: "#555" }}>
                    LOCKED
                  </button>
                )}

                {/* Master Pass badge */}
                {item.unlockMethod === "master_pass" && (
                  <span className="absolute top-1 right-1 text-[7px] font-bold px-1 rounded" style={{ background: "#D4AF37", color: "#0A0A0A" }}>
                    PASS
                  </span>
                )}
              </div>
            );
          })}
        </div>
      </DialogContent>
    </Dialog>
  );
}

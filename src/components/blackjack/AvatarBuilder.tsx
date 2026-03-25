import { useState } from "react";
import { Dialog, DialogContent, DialogHeader, DialogTitle } from "@/components/ui/dialog";
import AvatarRenderer, {
  type AvatarConfig, DEFAULT_AVATAR,
  SKIN_TONES, HAIR_COLORS, EYE_COLORS, OUTFIT_COLORS,
  HATS, GLASSES_LIST, JEWELRY_LIST, SPECIAL_LIST,
} from "./AvatarRenderer";

interface Props {
  open: boolean;
  onClose: () => void;
  config: AvatarConfig;
  onSave: (config: AvatarConfig) => void;
}

type Tab = "face" | "hair" | "outfit" | "accessories";

export default function AvatarBuilder({ open, onClose, config, onSave }: Props) {
  const [draft, setDraft] = useState<AvatarConfig>({ ...config });
  const [tab, setTab] = useState<Tab>("face");

  const update = (key: keyof AvatarConfig, val: any) => setDraft(prev => ({ ...prev, [key]: val }));

  const handleSave = () => {
    onSave(draft);
    onClose();
  };

  const ColorRow = ({ label, colors, value, onChange }: { label: string; colors: string[]; value: number; onChange: (v: number) => void }) => (
    <div className="mb-3">
      <p className="text-[10px] tracking-wider mb-1.5" style={{ color: "#888" }}>{label}</p>
      <div className="flex flex-wrap gap-1.5">
        {colors.map((c, i) => (
          <button key={i} onClick={() => onChange(i)}
            className="w-7 h-7 rounded-full transition-all hover:scale-110"
            style={{ background: c, border: value === i ? "2px solid #D4AF37" : "2px solid #333", boxShadow: value === i ? "0 0 8px #D4AF3760" : "none" }}
          />
        ))}
      </div>
    </div>
  );

  const EmojiRow = ({ label, items, value, onChange }: { label: string; items: string[]; value: string | null; onChange: (v: string) => void }) => (
    <div className="mb-3">
      <p className="text-[10px] tracking-wider mb-1.5" style={{ color: "#888" }}>{label}</p>
      <div className="flex flex-wrap gap-1.5">
        {items.map((item) => (
          <button key={item} onClick={() => onChange(item)}
            className="w-9 h-9 rounded-lg flex items-center justify-center text-lg transition-all hover:scale-110"
            style={{
              background: (value ?? "none") === item ? "#D4AF3730" : "#1a1a1a",
              border: (value ?? "none") === item ? "2px solid #D4AF37" : "1px solid #333",
            }}
          >
            {item === "none" ? "✕" : item}
          </button>
        ))}
      </div>
    </div>
  );

  const NumberRow = ({ label, count, value, onChange }: { label: string; count: number; value: number; onChange: (v: number) => void }) => (
    <div className="mb-3">
      <p className="text-[10px] tracking-wider mb-1.5" style={{ color: "#888" }}>{label}</p>
      <div className="flex flex-wrap gap-1.5">
        {Array.from({ length: count }).map((_, i) => (
          <button key={i} onClick={() => onChange(i)}
            className="w-9 h-9 rounded-lg flex items-center justify-center text-xs font-bold transition-all hover:scale-110"
            style={{
              background: value === i ? "#D4AF3730" : "#1a1a1a",
              border: value === i ? "2px solid #D4AF37" : "1px solid #333",
              color: value === i ? "#D4AF37" : "#888",
            }}
          >
            {i + 1}
          </button>
        ))}
      </div>
    </div>
  );

  return (
    <Dialog open={open} onOpenChange={onClose}>
      <DialogContent className="luxury-modal max-w-md max-h-[85vh] overflow-hidden flex flex-col">
        <DialogHeader>
          <DialogTitle className="casino-heading text-xl tracking-wider">AVATAR STUDIO</DialogTitle>
          <div className="gold-accent-line" />
        </DialogHeader>

        {/* Live preview */}
        <div className="flex justify-center py-4">
          <AvatarRenderer config={draft} size={120} />
        </div>

        {/* Tabs */}
        <div className="flex border-b mb-3" style={{ borderColor: "#333" }}>
          {(["face", "hair", "outfit", "accessories"] as Tab[]).map(t => (
            <button key={t} onClick={() => setTab(t)}
              className="flex-1 py-2 text-xs font-bold tracking-wider transition-all"
              style={{ color: tab === t ? "#D4AF37" : "#666", borderBottom: tab === t ? "2px solid #D4AF37" : "none" }}
            >{t.toUpperCase()}</button>
          ))}
        </div>

        {/* Tab content */}
        <div className="flex-1 overflow-y-auto pr-1" style={{ maxHeight: "300px" }}>
          {tab === "face" && (
            <>
              <ColorRow label="SKIN TONE" colors={SKIN_TONES} value={draft.skinTone} onChange={v => update("skinTone", v)} />
              <NumberRow label="EYE SHAPE" count={6} value={draft.eyeShape} onChange={v => update("eyeShape", v)} />
              <ColorRow label="EYE COLOR" colors={EYE_COLORS} value={draft.eyeColor} onChange={v => update("eyeColor", v)} />
              <NumberRow label="EXPRESSION" count={4} value={draft.expression} onChange={v => update("expression", v)} />
            </>
          )}
          {tab === "hair" && (
            <>
              <NumberRow label="HAIR STYLE" count={12} value={draft.hairStyle} onChange={v => update("hairStyle", v)} />
              <ColorRow label="HAIR COLOR" colors={HAIR_COLORS} value={draft.hairColor} onChange={v => update("hairColor", v)} />
            </>
          )}
          {tab === "outfit" && (
            <>
              <NumberRow label="OUTFIT STYLE" count={8} value={draft.outfit} onChange={v => update("outfit", v)} />
              <ColorRow label="OUTFIT COLOR" colors={OUTFIT_COLORS} value={draft.outfitColor} onChange={v => update("outfitColor", v)} />
            </>
          )}
          {tab === "accessories" && (
            <>
              <EmojiRow label="HAT" items={HATS} value={draft.hat} onChange={v => update("hat", v)} />
              <EmojiRow label="GLASSES" items={GLASSES_LIST} value={draft.glasses} onChange={v => update("glasses", v)} />
              <EmojiRow label="JEWELRY" items={JEWELRY_LIST} value={draft.jewelry} onChange={v => update("jewelry", v)} />
              <EmojiRow label="SPECIAL EFFECT" items={SPECIAL_LIST} value={draft.special} onChange={v => update("special", v)} />
            </>
          )}
        </div>

        {/* Actions */}
        <div className="flex gap-2 pt-3 border-t" style={{ borderColor: "#333" }}>
          <button onClick={() => setDraft({ ...DEFAULT_AVATAR })}
            className="flex-1 py-2.5 rounded-lg text-xs font-bold tracking-wider" style={{ background: "#222", color: "#888" }}>
            RESET
          </button>
          <button onClick={handleSave}
            className="flex-[2] py-2.5 rounded-lg text-sm font-bold tracking-wider transition-all hover:scale-[1.02]"
            style={{ background: "linear-gradient(135deg, #D4AF37, #B8960C)", color: "#0A0A0A" }}>
            SAVE AVATAR
          </button>
        </div>
      </DialogContent>
    </Dialog>
  );
}

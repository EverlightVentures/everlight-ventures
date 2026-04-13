'use client'

import { motion, AnimatePresence } from 'framer-motion'
import { useState } from 'react'

/**
 * Avatar Builder / Studio
 *
 * Full avatar customization: face, hair, outfit, accessories.
 * Live preview with presence score calculation.
 * Migrated from the Everlight AvatarBuilder.tsx + Django avatar fields.
 */

const SKIN_TONES = ['#f5d0a9', '#e8b88a', '#c68642', '#8d5524', '#5c3317', '#3b1f0b']
const EYE_COLORS = ['#4a90d9', '#2ecc71', '#8b4513', '#2c3e50', '#9b59b6', '#e74c3c']
const HAIR_COLORS = ['#1a1a1a', '#3d2314', '#8b4513', '#d4a574', '#c0392b', '#ecf0f1', '#9b59b6', '#3498db']
const OUTFIT_COLORS = ['#c9a84c', '#e74c3c', '#3498db', '#27ae60', '#9b59b6', '#e67e22', '#1abc9c', '#e91e63', '#fff', '#2c2c2c']

const EYE_SHAPES = [
  { id: 'round', label: 'Round' },
  { id: 'almond', label: 'Almond' },
  { id: 'narrow', label: 'Narrow' },
  { id: 'wide', label: 'Wide' },
  { id: 'cat', label: 'Cat' },
  { id: 'deep', label: 'Deep Set' },
]

const EXPRESSIONS = [
  { id: 'neutral', label: 'Neutral', emoji: '\uD83D\uDE10' },
  { id: 'confident', label: 'Confident', emoji: '\uD83D\uDE0F' },
  { id: 'focused', label: 'Focused', emoji: '\uD83E\uDDD0' },
  { id: 'playful', label: 'Playful', emoji: '\uD83D\uDE0E' },
]

const HAIR_STYLES = [
  { id: 'short_clean', label: 'Short Clean' },
  { id: 'slick_back', label: 'Slicked Back' },
  { id: 'curly', label: 'Curly' },
  { id: 'afro', label: 'Afro' },
  { id: 'long_straight', label: 'Long Straight' },
  { id: 'braids', label: 'Braids' },
  { id: 'mohawk', label: 'Mohawk' },
  { id: 'buzz', label: 'Buzz Cut' },
  { id: 'ponytail', label: 'Ponytail' },
  { id: 'bob', label: 'Bob' },
  { id: 'waves', label: 'Waves' },
  { id: 'bald', label: 'Bald' },
]

const OUTFIT_STYLES = [
  { id: 'default_suit', label: 'Classic Suit', score: 1.0 },
  { id: 'gold_tux', label: 'Gold Tuxedo', score: 1.15 },
  { id: 'diamond_blazer', label: 'Diamond Blazer', score: 1.25 },
  { id: 'neon_suit', label: 'Neon Synthwave', score: 1.20 },
  { id: 'royal_robe', label: 'Royal Robe', score: 1.35 },
  { id: 'legendary_drip', label: 'Legend Drip', score: 1.50 },
  { id: 'streetwear', label: 'Streetwear' , score: 1.0 },
  { id: 'evening_gown', label: 'Evening Gown', score: 1.10 },
]

const HATS = ['none', '\uD83E\uDDE2 Cap', '\uD83C\uDFA9 Top Hat', '\uD83D\uDC51 Crown', '\u26D1 Helmet', '\uD83E\uDD20 Cowboy']
const GLASSES = ['none', '\uD83D\uDD76 Aviators', '\uD83E\uDDD0 Monocle', '\uD83D\uDC53 Round', '\uD83E\uDE7C Square']
const JEWELRY = ['none', '\u26D3 Chain', '\uD83D\uDC8D Ring', '\u231A Watch', '\uD83D\uDC8E Pendant']
const SPECIALS = ['none', '\u2728 Sparkle', '\uD83D\uDD25 Flames', '\uD83C\uDF0C Galaxy', '\u26A1 Lightning', '\u2744 Frost']

interface AvatarConfig {
  skinTone: string
  eyeShape: string
  eyeColor: string
  expression: string
  hairStyle: string
  hairColor: string
  outfitStyle: string
  outfitColor: string
  hat: string
  glasses: string
  jewelry: string
  special: string
  name: string
}

const DEFAULT_AVATAR: AvatarConfig = {
  skinTone: '#c68642',
  eyeShape: 'round',
  eyeColor: '#4a90d9',
  expression: 'confident',
  hairStyle: 'slick_back',
  hairColor: '#1a1a1a',
  outfitStyle: 'default_suit',
  outfitColor: '#c9a84c',
  hat: 'none',
  glasses: 'none',
  jewelry: 'none',
  special: 'none',
  name: 'Player',
}

// Simple avatar preview renderer
function AvatarPreview({ config }: { config: AvatarConfig }) {
  const outfit = OUTFIT_STYLES.find(o => o.id === config.outfitStyle)

  return (
    <div className="w-32 h-40 mx-auto relative flex flex-col items-center justify-end">
      {/* Special effect background */}
      {config.special !== 'none' && (
        <motion.div
          className="absolute inset-0 rounded-xl opacity-30"
          animate={{ opacity: [0.2, 0.4, 0.2] }}
          transition={{ duration: 2, repeat: Infinity }}
          style={{
            background: config.special.includes('Flames') ? 'radial-gradient(circle, #ff6b3540, transparent)'
              : config.special.includes('Galaxy') ? 'radial-gradient(circle, #6a5acd40, transparent)'
              : config.special.includes('Lightning') ? 'radial-gradient(circle, #58a6ff40, transparent)'
              : config.special.includes('Frost') ? 'radial-gradient(circle, #00bcd440, transparent)'
              : 'radial-gradient(circle, #c9a84c30, transparent)',
          }}
        />
      )}

      {/* Hat */}
      {config.hat !== 'none' && (
        <div className="text-2xl mb-[-8px] relative z-10">{config.hat.split(' ')[0]}</div>
      )}

      {/* Head */}
      <div
        className="w-16 h-16 rounded-full relative flex items-center justify-center"
        style={{ background: config.skinTone }}
      >
        {/* Eyes */}
        <div className="flex gap-2 mb-1">
          <div className="w-2.5 h-2 rounded-full" style={{ background: config.eyeColor }} />
          <div className="w-2.5 h-2 rounded-full" style={{ background: config.eyeColor }} />
        </div>
        {/* Glasses */}
        {config.glasses !== 'none' && (
          <div className="absolute top-5 text-sm">{config.glasses.split(' ')[0]}</div>
        )}
        {/* Hair color indicator */}
        <div
          className="absolute top-0 left-2 right-2 h-4 rounded-t-full"
          style={{ background: config.hairColor, opacity: config.hairStyle === 'bald' ? 0 : 0.8 }}
        />
      </div>

      {/* Body / Outfit */}
      <div
        className="w-20 h-14 rounded-t-xl mt-[-4px] flex items-center justify-center"
        style={{ background: config.outfitColor + '80', border: `1px solid ${config.outfitColor}40` }}
      >
        {config.jewelry !== 'none' && (
          <span className="text-sm">{config.jewelry.split(' ')[0]}</span>
        )}
      </div>

      {/* Presence score */}
      {outfit && outfit.score > 1.0 && (
        <div className="absolute bottom-[-20px] text-[9px] font-mono" style={{ color: 'var(--gold)' }}>
          {outfit.score.toFixed(2)}x presence
        </div>
      )}
    </div>
  )
}

function ColorPicker({ colors, selected, onChange, label }: {
  colors: string[]; selected: string; onChange: (c: string) => void; label: string
}) {
  return (
    <div>
      <p className="text-[10px] uppercase tracking-wider mb-1.5" style={{ color: 'var(--text-tertiary)' }}>{label}</p>
      <div className="flex gap-1.5 flex-wrap">
        {colors.map(c => (
          <button
            key={c}
            onClick={() => onChange(c)}
            className="w-6 h-6 rounded-full transition-transform"
            style={{
              background: c,
              border: selected === c ? '2px solid var(--gold)' : '2px solid transparent',
              boxShadow: selected === c ? '0 0 8px rgba(201,168,76,0.3)' : 'none',
              transform: selected === c ? 'scale(1.2)' : 'scale(1)',
            }}
          />
        ))}
      </div>
    </div>
  )
}

function OptionGrid({ options, selected, onChange, label }: {
  options: { id: string; label: string; emoji?: string; score?: number }[]
  selected: string; onChange: (id: string) => void; label: string
}) {
  return (
    <div>
      <p className="text-[10px] uppercase tracking-wider mb-1.5" style={{ color: 'var(--text-tertiary)' }}>{label}</p>
      <div className="grid grid-cols-3 gap-1.5">
        {options.map(opt => (
          <button
            key={opt.id}
            onClick={() => onChange(opt.id)}
            className="text-xs px-2 py-1.5 rounded-lg transition-all text-center"
            style={{
              background: selected === opt.id ? 'var(--gold-glow)' : 'var(--vanta-surface)',
              color: selected === opt.id ? 'var(--gold)' : 'var(--text-secondary)',
              border: `1px solid ${selected === opt.id ? 'var(--gold)' : 'var(--vanta-border)'}`,
            }}
          >
            {opt.emoji ? `${opt.emoji} ` : ''}{opt.label}
          </button>
        ))}
      </div>
    </div>
  )
}

function StringPicker({ options, selected, onChange, label }: {
  options: string[]; selected: string; onChange: (s: string) => void; label: string
}) {
  return (
    <div>
      <p className="text-[10px] uppercase tracking-wider mb-1.5" style={{ color: 'var(--text-tertiary)' }}>{label}</p>
      <div className="flex gap-1.5 flex-wrap">
        {options.map(opt => {
          const display = opt === 'none' ? 'None' : opt
          return (
            <button
              key={opt}
              onClick={() => onChange(opt)}
              className="text-xs px-2 py-1 rounded-lg transition-all"
              style={{
                background: selected === opt ? 'var(--gold-glow)' : 'var(--vanta-surface)',
                color: selected === opt ? 'var(--gold)' : 'var(--text-secondary)',
                border: `1px solid ${selected === opt ? 'var(--gold)' : 'var(--vanta-border)'}`,
              }}
            >
              {display}
            </button>
          )
        })}
      </div>
    </div>
  )
}

export function AvatarBuilder({
  isOpen,
  onClose,
  currentAvatar,
  onSave,
}: {
  isOpen: boolean
  onClose: () => void
  currentAvatar: AvatarConfig
  onSave: (avatar: AvatarConfig) => void
}) {
  const [avatar, setAvatar] = useState<AvatarConfig>(currentAvatar)
  const [tab, setTab] = useState<'face' | 'hair' | 'outfit' | 'accessories'>('face')

  const update = (field: keyof AvatarConfig, value: string) => {
    setAvatar(prev => ({ ...prev, [field]: value }))
  }

  return (
    <AnimatePresence>
      {isOpen && (
        <motion.div
          initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }}
          className="fixed inset-0 z-50 flex items-center justify-center p-4"
          style={{ background: 'rgba(0,0,0,0.85)', backdropFilter: 'blur(16px)' }}
          onClick={(e) => { if (e.target === e.currentTarget) onClose() }}
        >
          <motion.div
            initial={{ scale: 0.95, y: 20 }} animate={{ scale: 1, y: 0 }} exit={{ scale: 0.95, y: 20 }}
            className="w-full max-w-md max-h-[85vh] rounded-2xl overflow-hidden flex flex-col"
            style={{ background: 'var(--vanta-abyss)', border: '1px solid var(--vanta-border)' }}
          >
            {/* Header */}
            <div className="px-5 py-3 border-b flex items-center justify-between" style={{ borderColor: 'var(--vanta-border)' }}>
              <h2 className="font-display text-lg font-bold" style={{ color: 'var(--gold)' }}>Avatar Studio</h2>
              <button onClick={onClose} className="text-lg" style={{ color: 'var(--text-tertiary)' }}>&times;</button>
            </div>

            {/* Preview */}
            <div className="py-6 px-4" style={{ background: 'var(--vanta-surface)' }}>
              <AvatarPreview config={avatar} />
              {/* Name edit */}
              <div className="mt-6 text-center">
                <input
                  value={avatar.name}
                  onChange={(e) => update('name', e.target.value.slice(0, 20))}
                  className="bg-transparent text-center text-sm font-semibold outline-none border-b"
                  style={{ borderColor: 'var(--vanta-border)', color: 'var(--text-primary)', width: '140px' }}
                  placeholder="Your Name"
                  maxLength={20}
                />
              </div>
            </div>

            {/* Tabs */}
            <div className="flex border-b" style={{ borderColor: 'var(--vanta-border)' }}>
              {(['face', 'hair', 'outfit', 'accessories'] as const).map(t => (
                <button
                  key={t}
                  onClick={() => setTab(t)}
                  className="flex-1 py-2 text-xs uppercase tracking-wider transition-colors"
                  style={{
                    color: tab === t ? 'var(--gold)' : 'var(--text-tertiary)',
                    borderBottom: tab === t ? '2px solid var(--gold)' : '2px solid transparent',
                  }}
                >
                  {t}
                </button>
              ))}
            </div>

            {/* Tab content */}
            <div className="flex-1 overflow-y-auto p-4 space-y-4">
              {tab === 'face' && (
                <>
                  <ColorPicker colors={SKIN_TONES} selected={avatar.skinTone} onChange={(c) => update('skinTone', c)} label="Skin Tone" />
                  <OptionGrid options={EYE_SHAPES} selected={avatar.eyeShape} onChange={(id) => update('eyeShape', id)} label="Eye Shape" />
                  <ColorPicker colors={EYE_COLORS} selected={avatar.eyeColor} onChange={(c) => update('eyeColor', c)} label="Eye Color" />
                  <OptionGrid options={EXPRESSIONS} selected={avatar.expression} onChange={(id) => update('expression', id)} label="Expression" />
                </>
              )}
              {tab === 'hair' && (
                <>
                  <OptionGrid options={HAIR_STYLES} selected={avatar.hairStyle} onChange={(id) => update('hairStyle', id)} label="Hair Style" />
                  <ColorPicker colors={HAIR_COLORS} selected={avatar.hairColor} onChange={(c) => update('hairColor', c)} label="Hair Color" />
                </>
              )}
              {tab === 'outfit' && (
                <>
                  <OptionGrid options={OUTFIT_STYLES} selected={avatar.outfitStyle} onChange={(id) => update('outfitStyle', id)} label="Outfit" />
                  <ColorPicker colors={OUTFIT_COLORS} selected={avatar.outfitColor} onChange={(c) => update('outfitColor', c)} label="Outfit Color" />
                </>
              )}
              {tab === 'accessories' && (
                <>
                  <StringPicker options={HATS} selected={avatar.hat} onChange={(s) => update('hat', s)} label="Hat" />
                  <StringPicker options={GLASSES} selected={avatar.glasses} onChange={(s) => update('glasses', s)} label="Glasses" />
                  <StringPicker options={JEWELRY} selected={avatar.jewelry} onChange={(s) => update('jewelry', s)} label="Jewelry" />
                  <StringPicker options={SPECIALS} selected={avatar.special} onChange={(s) => update('special', s)} label="Special Effect" />
                </>
              )}
            </div>

            {/* Actions */}
            <div className="px-4 py-3 border-t flex gap-2" style={{ borderColor: 'var(--vanta-border)' }}>
              <button
                onClick={() => setAvatar(DEFAULT_AVATAR)}
                className="btn-ghost flex-1 py-2 text-xs"
              >
                RESET
              </button>
              <button
                onClick={() => { onSave(avatar); onClose() }}
                className="btn-primary flex-1 py-2 text-xs"
              >
                SAVE AVATAR
              </button>
            </div>
          </motion.div>
        </motion.div>
      )}
    </AnimatePresence>
  )
}

export type { AvatarConfig }
export { DEFAULT_AVATAR }

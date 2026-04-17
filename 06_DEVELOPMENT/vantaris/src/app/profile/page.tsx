'use client'

import { motion } from 'framer-motion'
import { useState, useEffect } from 'react'
import Link from 'next/link'
import { useBlackjackStore } from '@/lib/blackjack-store'

/**
 * Vantaris Character Customization
 *
 * Full avatar builder: skin tone, hairstyle, outfit, accessories, aura.
 * Live preview. Presence multiplier visible. Save to localStorage.
 */

const SKIN_TONES = [
  { id: 'fair', color: '#F5CBA7', label: 'Fair' },
  { id: 'light', color: '#E59866', label: 'Light' },
  { id: 'medium', color: '#CA8A5B', label: 'Medium' },
  { id: 'tan', color: '#A0522D', label: 'Tan' },
  { id: 'dark', color: '#6B3A2A', label: 'Dark' },
  { id: 'deep', color: '#3D1C02', label: 'Deep' },
]

const HAIRSTYLES = [
  { id: 'short', label: 'Short', icon: '\uD83D\uDC64' },
  { id: 'fade', label: 'Fade', icon: '\uD83D\uDC71' },
  { id: 'locs', label: 'Locs', icon: '\uD83E\uDDD4' },
  { id: 'braids', label: 'Braids', icon: '\uD83D\uDC69' },
  { id: 'afro', label: 'Afro', icon: '\uD83E\uDDD1' },
  { id: 'bald', label: 'Bald', icon: '\uD83E\uDDD1' },
]

const OUTFITS = [
  { id: 'default_suit', label: 'Classic Suit', presence: 1.0, price: 0, icon: '\uD83D\uDC54' },
  { id: 'gold_tux', label: 'Gold Tuxedo', presence: 1.15, price: 5000, icon: '\uD83E\uDD35' },
  { id: 'diamond_blazer', label: 'Diamond Blazer', presence: 1.25, price: 15000, icon: '\uD83D\uDC8E' },
  { id: 'neon_suit', label: 'Neon Synthwave', presence: 1.20, price: 50, currency: 'gems', icon: '\uD83C\uDF1F' },
  { id: 'royal_robe', label: 'Royal Robe', presence: 1.35, price: 120, currency: 'gems', icon: '\uD83D\uDC51' },
  { id: 'legendary_drip', label: 'Legend Drip', presence: 1.50, price: 300, currency: 'gems', icon: '\uD83D\uDD25' },
]

const AURAS = [
  { id: 'none', label: 'No Aura', presence: 1.0, price: 0 },
  { id: 'golden_glow', label: 'Golden Glow', presence: 1.05, price: 2000, color: '#c9a84c' },
  { id: 'hologram_blue', label: 'Hologram', presence: 1.10, price: 40, currency: 'gems', color: '#58a6ff' },
  { id: 'fire_aura', label: 'Fire Aura', presence: 1.15, price: 80, currency: 'gems', color: '#ff6b35' },
  { id: 'legend_aura', label: 'Legend Aura', presence: 1.25, price: 200, currency: 'gems', color: '#9b59b6' },
]

const ACCESSORIES = [
  { id: 'none', label: 'None' },
  { id: 'gold_chain', label: 'Gold Chain', icon: '\uD83D\uDCFF' },
  { id: 'shades', label: 'Shades', icon: '\uD83D\uDD76\uFE0F' },
  { id: 'earring', label: 'Diamond Earring', icon: '\uD83D\uDC8D' },
  { id: 'watch', label: 'Luxury Watch', icon: '\u231A' },
  { id: 'crown', label: 'Crown', icon: '\uD83D\uDC51' },
]

interface ProfileAvatarConfig {
  skinTone: string
  hairstyle: string
  outfit: string
  aura: string
  accessory: string
  name: string
}

export default function ProfilePage() {
  const [avatar, setAvatar] = useState<ProfileAvatarConfig>({
    skinTone: 'medium', hairstyle: 'short', outfit: 'default_suit',
    aura: 'none', accessory: 'none', name: '',
  })
  const [tab, setTab] = useState<'skin' | 'hair' | 'outfit' | 'aura' | 'accessory'>('skin')

  useEffect(() => {
    try {
      const saved = JSON.parse(localStorage.getItem('vantaris_avatar') || '{}')
      if (saved.skinTone) setAvatar(prev => ({ ...prev, ...saved }))
      const name = localStorage.getItem('vantaris_player_name') || ''
      setAvatar(prev => ({ ...prev, name }))
    } catch (err) {
      console.warn('[profile] Failed to load saved avatar:', err)
    }
  }, [])

  const handleSave = () => {
    localStorage.setItem('vantaris_avatar', JSON.stringify(avatar))
    // Also update Zustand store so equipped items persist and affect gameplay
    const player = useBlackjackStore.getState().player
    useBlackjackStore.setState({
      player: {
        ...player,
        equippedOutfit: avatar.outfit,
        equippedAura: avatar.aura,
      },
    })
    if (avatar.name) localStorage.setItem('vantaris_player_name', avatar.name)
  }

  const selectedOutfit = OUTFITS.find(o => o.id === avatar.outfit) || OUTFITS[0]
  const selectedAura = AURAS.find(a => a.id === avatar.aura) || AURAS[0]
  const presence = Math.round(selectedOutfit.presence * selectedAura.presence * 100) / 100
  const skinColor = SKIN_TONES.find(s => s.id === avatar.skinTone)?.color || '#CA8A5B'

  return (
    <div className="min-h-screen" style={{ background: 'var(--vanta-void)' }}>
      {/* Header */}
      <div className="px-6 py-4 border-b flex items-center justify-between" style={{ borderColor: 'var(--vanta-border)' }}>
        <div className="flex items-center gap-4">
          <Link href="/lobby"><button className="text-sm" style={{ color: 'var(--text-tertiary)' }}>{'\u2190'} Back</button></Link>
          <h1 className="text-xl font-bold tracking-widest" style={{
            fontFamily: "'Cinzel', serif",
            background: 'linear-gradient(135deg, #c9a84c, #e8c55a)',
            WebkitBackgroundClip: 'text', WebkitTextFillColor: 'transparent',
          }}>CHARACTER</h1>
        </div>
        <motion.button onClick={handleSave}
          className="px-6 py-2 rounded-xl text-sm font-bold"
          style={{ background: 'linear-gradient(135deg, #c9a84c, #f0d080)', color: '#000', fontFamily: "'Cinzel', serif" }}
          whileTap={{ scale: 0.95 }}>
          SAVE
        </motion.button>
      </div>

      <div className="flex flex-col md:flex-row gap-8 p-6 max-w-5xl mx-auto">
        {/* Avatar Preview */}
        <div className="md:w-1/3 flex flex-col items-center">
          <div className="w-40 h-40 rounded-full mb-4 flex items-center justify-center text-5xl relative"
            style={{
              background: `radial-gradient(circle, ${skinColor}, ${skinColor}dd)`,
              border: '3px solid #c9a84c',
              boxShadow: selectedAura.color ? `0 0 30px ${selectedAura.color}40` : '0 0 15px rgba(201,168,76,0.2)',
            }}>
            {HAIRSTYLES.find(h => h.id === avatar.hairstyle)?.icon || '\uD83D\uDC64'}
            {avatar.accessory !== 'none' && (
              <span className="absolute -top-2 -right-2 text-2xl">
                {ACCESSORIES.find(a => a.id === avatar.accessory)?.icon}
              </span>
            )}
          </div>

          {/* Name input */}
          <input type="text" value={avatar.name}
            onChange={e => setAvatar(prev => ({ ...prev, name: e.target.value.slice(0, 20) }))}
            placeholder="Your name..."
            className="w-full max-w-[200px] bg-transparent border-b text-center text-lg py-1 mb-4 outline-none"
            style={{ borderColor: 'rgba(201,168,76,0.3)', color: '#fff', fontFamily: "'Cinzel', serif" }} />

          {/* Presence display */}
          <div className="glass px-4 py-2 rounded-xl text-center">
            <p className="text-[9px] uppercase tracking-wider" style={{ color: 'var(--text-tertiary)' }}>TABLE PRESENCE</p>
            <p className="text-xl font-bold font-mono" style={{ color: 'var(--gold)' }}>{presence}x</p>
          </div>

          {/* Current loadout */}
          <div className="mt-4 space-y-1 text-xs w-full">
            <div className="flex justify-between" style={{ color: 'var(--text-tertiary)' }}>
              <span>Outfit</span><span style={{ color: 'var(--gold)' }}>{selectedOutfit.label} ({selectedOutfit.presence}x)</span>
            </div>
            <div className="flex justify-between" style={{ color: 'var(--text-tertiary)' }}>
              <span>Aura</span><span style={{ color: selectedAura.color || '#888' }}>{selectedAura.label} ({selectedAura.presence}x)</span>
            </div>
          </div>
        </div>

        {/* Customization Panel */}
        <div className="md:w-2/3">
          {/* Category tabs */}
          <div className="flex gap-1 mb-6 flex-wrap">
            {(['skin', 'hair', 'outfit', 'aura', 'accessory'] as const).map(t => (
              <button key={t} onClick={() => setTab(t)}
                className="px-4 py-2 text-xs uppercase tracking-wider rounded-lg"
                style={{
                  background: tab === t ? 'rgba(201,168,76,0.15)' : 'transparent',
                  color: tab === t ? 'var(--gold)' : 'var(--text-tertiary)',
                  border: `1px solid ${tab === t ? 'rgba(201,168,76,0.3)' : 'var(--vanta-border)'}`,
                  fontFamily: "'Cinzel', serif",
                }}>
                {t}
              </button>
            ))}
          </div>

          {/* Skin tones */}
          {tab === 'skin' && (
            <div className="grid grid-cols-3 md:grid-cols-6 gap-3">
              {SKIN_TONES.map(s => (
                <motion.button key={s.id} onClick={() => setAvatar(prev => ({ ...prev, skinTone: s.id }))}
                  className="p-4 rounded-xl flex flex-col items-center gap-2"
                  style={{
                    border: avatar.skinTone === s.id ? '2px solid #c9a84c' : '2px solid transparent',
                    background: avatar.skinTone === s.id ? 'rgba(201,168,76,0.08)' : 'var(--vanta-surface)',
                  }}
                  whileTap={{ scale: 0.95 }}>
                  <div className="w-10 h-10 rounded-full" style={{ background: s.color }} />
                  <span className="text-[10px]" style={{ color: 'var(--text-tertiary)' }}>{s.label}</span>
                </motion.button>
              ))}
            </div>
          )}

          {/* Hairstyles */}
          {tab === 'hair' && (
            <div className="grid grid-cols-3 md:grid-cols-6 gap-3">
              {HAIRSTYLES.map(h => (
                <motion.button key={h.id} onClick={() => setAvatar(prev => ({ ...prev, hairstyle: h.id }))}
                  className="p-4 rounded-xl flex flex-col items-center gap-2"
                  style={{
                    border: avatar.hairstyle === h.id ? '2px solid #c9a84c' : '2px solid transparent',
                    background: avatar.hairstyle === h.id ? 'rgba(201,168,76,0.08)' : 'var(--vanta-surface)',
                  }}
                  whileTap={{ scale: 0.95 }}>
                  <span className="text-2xl">{h.icon}</span>
                  <span className="text-[10px]" style={{ color: 'var(--text-tertiary)' }}>{h.label}</span>
                </motion.button>
              ))}
            </div>
          )}

          {/* Outfits */}
          {tab === 'outfit' && (
            <div className="grid grid-cols-2 md:grid-cols-3 gap-3">
              {OUTFITS.map(o => (
                <motion.button key={o.id} onClick={() => setAvatar(prev => ({ ...prev, outfit: o.id }))}
                  className="p-4 rounded-xl text-center"
                  style={{
                    border: avatar.outfit === o.id ? '2px solid #c9a84c' : '2px solid transparent',
                    background: avatar.outfit === o.id ? 'rgba(201,168,76,0.08)' : 'var(--vanta-surface)',
                  }}
                  whileTap={{ scale: 0.95 }}>
                  <span className="text-3xl block mb-2">{o.icon}</span>
                  <p className="text-xs font-semibold">{o.label}</p>
                  <p className="text-[9px]" style={{ color: 'var(--gold)' }}>{o.presence}x presence</p>
                  {o.price > 0 && (
                    <p className="text-[9px] mt-1" style={{ color: 'var(--text-tertiary)' }}>
                      {o.price} {o.currency || 'GC'}
                    </p>
                  )}
                </motion.button>
              ))}
            </div>
          )}

          {/* Auras */}
          {tab === 'aura' && (
            <div className="grid grid-cols-2 md:grid-cols-3 gap-3">
              {AURAS.map(a => (
                <motion.button key={a.id} onClick={() => setAvatar(prev => ({ ...prev, aura: a.id }))}
                  className="p-4 rounded-xl text-center"
                  style={{
                    border: avatar.aura === a.id ? `2px solid ${a.color || '#c9a84c'}` : '2px solid transparent',
                    background: avatar.aura === a.id ? `${a.color || '#c9a84c'}10` : 'var(--vanta-surface)',
                    boxShadow: avatar.aura === a.id && a.color ? `0 0 15px ${a.color}20` : 'none',
                  }}
                  whileTap={{ scale: 0.95 }}>
                  <p className="text-sm font-semibold" style={{ color: a.color || '#888' }}>{a.label}</p>
                  <p className="text-[9px]" style={{ color: 'var(--gold)' }}>{a.presence}x</p>
                  {a.price > 0 && (
                    <p className="text-[9px] mt-1" style={{ color: 'var(--text-tertiary)' }}>
                      {a.price} {a.currency || 'GC'}
                    </p>
                  )}
                </motion.button>
              ))}
            </div>
          )}

          {/* Accessories */}
          {tab === 'accessory' && (
            <div className="grid grid-cols-3 md:grid-cols-6 gap-3">
              {ACCESSORIES.map(a => (
                <motion.button key={a.id} onClick={() => setAvatar(prev => ({ ...prev, accessory: a.id }))}
                  className="p-4 rounded-xl flex flex-col items-center gap-2"
                  style={{
                    border: avatar.accessory === a.id ? '2px solid #c9a84c' : '2px solid transparent',
                    background: avatar.accessory === a.id ? 'rgba(201,168,76,0.08)' : 'var(--vanta-surface)',
                  }}
                  whileTap={{ scale: 0.95 }}>
                  <span className="text-2xl">{a.icon || '\u2716'}</span>
                  <span className="text-[10px]" style={{ color: 'var(--text-tertiary)' }}>{a.label}</span>
                </motion.button>
              ))}
            </div>
          )}
        </div>
      </div>
    </div>
  )
}

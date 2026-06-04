'use client'

import { useRef, useMemo, useCallback } from 'react'
import { Canvas, useFrame, useThree } from '@react-three/fiber'
import {
  Environment, Float, MeshReflectorMaterial,
  Sparkles, ContactShadows, Text,
} from '@react-three/drei'
import {
  EffectComposer, Bloom, Vignette, ChromaticAberration,
} from '@react-three/postprocessing'
import * as THREE from 'three'
import type { SeatPosition } from './BotPlayers'

/**
 * Vantaris Casino 3D Scene
 *
 * Full immersive casino environment rendered with React Three Fiber.
 * Oval table with dark purple/gold/black felt.
 * Chip tray, chandelier, neon rim lights, gold dust particles.
 * Postprocessing: bloom (gold glow bleeds), vignette (cinematic edges),
 * chromatic aberration (luxury lens effect).
 *
 * This renders BEHIND the card HUD (cards are still DOM elements on top).
 */

// ============================================================
// OVAL CASINO TABLE
// ============================================================

// Module-level felt color (set by parent CasinoScene3D)
let _feltColor = '#0d5c2e'

function CasinoTable() {
  const feltRef = useRef<THREE.Mesh>(null)

  useFrame((state) => {
    if (feltRef.current) {
      const mat = feltRef.current.material as THREE.MeshStandardMaterial
      mat.emissiveIntensity = 0.02 + Math.sin(state.clock.elapsedTime * 0.5) * 0.008
    }
  })

  // 5 betting circle positions (matches seat positions)
  const bettingSpots = [
    { x: -2.4, z: 1.8 },  // Seat 1
    { x: -1.2, z: 2.3 },  // Seat 2
    { x: 0.0,  z: 2.5 },  // Seat 3 (player)
    { x: 1.2,  z: 2.3 },  // Seat 4
    { x: 2.4,  z: 1.8 },  // Seat 5
  ]

  return (
    <group>
      {/* ENTIRE TABLE in oval scale group (1.3x width = luxury oval) */}
      <group scale={[1.3, 1, 1]}>
        {/* Table base -- dark wood */}
        <mesh position={[0, -0.8, 0]} castShadow receiveShadow>
          <cylinderGeometry args={[4.2, 4.0, 0.5, 64]} />
          <meshStandardMaterial
            color="#1a0d08"
            roughness={0.35}
            metalness={0.25}
          />
        </mesh>

        {/* Padded rail (leather cushion around edge) */}
        <mesh position={[0, -0.5, 0]} rotation={[Math.PI / 2, 0, 0]}>
          <torusGeometry args={[4.05, 0.12, 12, 128]} />
          <meshStandardMaterial
            color="#1a0d08"
            roughness={0.6}
            metalness={0.1}
          />
        </mesh>

        {/* Felt surface -- CASINO GREEN */}
        <mesh ref={feltRef} position={[0, -0.46, 0]} receiveShadow>
          <cylinderGeometry args={[3.9, 3.9, 0.06, 64]} />
          <meshStandardMaterial
            color={_feltColor}
            roughness={0.92}
            metalness={0.02}
            emissive="#0a4a24"
            emissiveIntensity={0.03}
          />
        </mesh>

        {/* Inner gold stitch line */}
        <mesh position={[0, -0.42, 0]} rotation={[Math.PI / 2, 0, 0]}>
          <torusGeometry args={[3.5, 0.012, 8, 128]} />
          <meshStandardMaterial
            color="#c9a84c"
            roughness={0.2}
            metalness={0.8}
            emissive="#c9a84c"
            emissiveIntensity={0.25}
          />
        </mesh>

        {/* Outer gold trim ring */}
        <mesh position={[0, -0.43, 0]} rotation={[Math.PI / 2, 0, 0]}>
          <torusGeometry args={[3.95, 0.05, 12, 128]} />
          <meshStandardMaterial
            color="#c9a84c"
            roughness={0.15}
            metalness={0.95}
            emissive="#c9a84c"
            emissiveIntensity={0.15}
          />
        </mesh>
      </group>
      {/* End oval scale group -- EVERYTHING above is oval */}

      {/* Insurance arc (semi-circle in front of dealer) */}
      <mesh rotation={[-Math.PI / 2, 0, 0]} position={[0, -0.415, -0.5]}>
        <torusGeometry args={[2.2, 0.012, 8, 64, Math.PI]} />
        <meshStandardMaterial
          color="#c9a84c"
          emissive="#c9a84c"
          emissiveIntensity={0.15}
          side={THREE.DoubleSide}
          transparent
          opacity={0.35}
        />
      </mesh>

      {/* Dealer nameplate (gold placard) */}
      <mesh position={[0, -0.38, -2.8]}>
        <boxGeometry args={[1.5, 0.04, 0.3]} />
        <meshStandardMaterial
          color="#c9a84c"
          emissive="#c9a84c"
          emissiveIntensity={0.2}
          metalness={0.9}
          roughness={0.1}
        />
      </mesh>

      {/* Table legs (4 for oval) */}
      {[[-2.5, -2], [2.5, -2], [-2.5, 2], [2.5, 2]].map(([x, z], i) => (
        <mesh key={`leg-${i}`} position={[x, -1.3, z]} castShadow>
          <cylinderGeometry args={[0.12, 0.16, 0.9, 12]} />
          <meshStandardMaterial color="#1a0d08" roughness={0.3} metalness={0.3} />
        </mesh>
      ))}

      {/* VANTARIS CASINO branding on felt */}
      <Text
        position={[0, -0.41, 0.1]}
        rotation={[-Math.PI / 2, 0, 0]}
        fontSize={0.35}
        color="#c9a84c"
        anchorX="center"
        anchorY="middle"
        fillOpacity={0.15}
        letterSpacing={0.15}
      >
        VANTARIS CASINO
      </Text>
      <Text
        position={[0, -0.41, 0.55]}
        rotation={[-Math.PI / 2, 0, 0]}
        fontSize={0.12}
        color="#c9a84c"
        anchorX="center"
        anchorY="middle"
        fillOpacity={0.1}
        letterSpacing={0.2}
      >
        BY EVERLIGHT VENTURES
      </Text>
      {/* RG initials (owner branding) */}
      <Text
        position={[0, -0.41, -0.4]}
        rotation={[-Math.PI / 2, 0, 0]}
        fontSize={0.5}
        color="#c9a84c"
        anchorX="center"
        anchorY="middle"
        fillOpacity={0.08}
        letterSpacing={0.3}
      >
        RG
      </Text>
      {/* INSURANCE PAYS 2 TO 1 arc text */}
      <Text
        position={[0, -0.41, -1.0]}
        rotation={[-Math.PI / 2, 0, 0]}
        fontSize={0.1}
        color="#c9a84c"
        anchorX="center"
        anchorY="middle"
        fillOpacity={0.2}
        letterSpacing={0.08}
      >
        INSURANCE PAYS 2 TO 1
      </Text>
      {/* DEALER MUST HIT SOFT 17 */}
      <Text
        position={[0, -0.41, -1.5]}
        rotation={[-Math.PI / 2, 0, 0]}
        fontSize={0.08}
        color="#c9a84c"
        anchorX="center"
        anchorY="middle"
        fillOpacity={0.15}
        letterSpacing={0.05}
      >
        DEALER MUST HIT SOFT 17
      </Text>
      {/* BLACKJACK PAYS 3 TO 2 */}
      <Text
        position={[0, -0.41, -2.0]}
        rotation={[-Math.PI / 2, 0, 0]}
        fontSize={0.08}
        color="#c9a84c"
        anchorX="center"
        anchorY="middle"
        fillOpacity={0.15}
        letterSpacing={0.05}
      >
        BLACKJACK PAYS 3 TO 2
      </Text>
    </group>
  )
}

// ============================================================
// CHIP TRAY (dealer side)
// ============================================================

function ChipTray() {
  const chipColors = [
    '#e74c3c',  // red
    '#27ae60',  // green
    '#2980b9',  // blue
    '#8e44ad',  // purple
    '#c9a84c',  // gold
  ]
  const stackHeights = [8, 6, 10, 5, 7]

  return (
    <group position={[0, -0.41, -1.8]}>
      {/* Tray body */}
      <mesh>
        <boxGeometry args={[3.2, 0.12, 0.6]} />
        <meshStandardMaterial
          color="#111111"
          roughness={0.2}
          metalness={0.7}
          emissive="#0a0a0a"
          emissiveIntensity={0.1}
        />
      </mesh>

      {/* Gold lip */}
      <mesh position={[0, 0.04, 0.25]}>
        <boxGeometry args={[3.5, 0.04, 0.03]} />
        <meshStandardMaterial
          color="#c9a84c"
          roughness={0.1}
          metalness={0.95}
          emissive="#c9a84c"
          emissiveIntensity={0.15}
        />
      </mesh>

      {/* Chip stacks */}
      {chipColors.map((color, ci) => (
        <group key={ci}>
          {Array.from({ length: stackHeights[ci] }).map((_, si) => (
            <mesh
              key={si}
              position={[
                -1.3 + ci * 0.65 + (Math.random() - 0.5) * 0.02,
                0.06 + si * 0.024,
                (Math.random() - 0.5) * 0.02,
              ]}
            >
              <cylinderGeometry args={[0.11, 0.11, 0.02, 16]} />
              <meshStandardMaterial
                color={color}
                roughness={0.25}
                metalness={0.6}
                emissive={color}
                emissiveIntensity={0.08}
              />
            </mesh>
          ))}
        </group>
      ))}
    </group>
  )
}

// ============================================================
// CHANDELIER
// ============================================================

function Chandelier() {
  const glowRef = useRef<THREE.PointLight>(null)

  useFrame((state) => {
    if (glowRef.current) {
      glowRef.current.intensity = 1.5 + Math.sin(state.clock.elapsedTime * 0.8) * 0.3
    }
  })

  return (
    <group position={[0, 8, -1]}>
      {/* Chain */}
      <mesh>
        <cylinderGeometry args={[0.015, 0.015, 4, 8]} />
        <meshStandardMaterial color="#c9a84c" metalness={0.95} roughness={0.1} />
      </mesh>

      {/* Base */}
      <mesh position={[0, -2, 0]}>
        <cylinderGeometry args={[0.7, 0.5, 0.15, 16]} />
        <meshStandardMaterial
          color="#c9a84c"
          metalness={0.9}
          roughness={0.1}
          emissive="#c9a84c"
          emissiveIntensity={0.4}
        />
      </mesh>

      {/* Warm glow light */}
      <pointLight
        ref={glowRef}
        position={[0, -2.5, 0]}
        color="#fff5e0"
        intensity={2}
        distance={20}
        decay={2}
        castShadow
        shadow-mapSize={[1024, 1024]}
      />
    </group>
  )
}

// ============================================================
// NEON RIM LIGHTS
// ============================================================

function NeonLights() {
  return (
    <>
      {/* Left neon -- blue-violet */}
      <pointLight position={[-8, 3, 0]} color="#4400ff" intensity={0.8} distance={15} />
      <mesh position={[-8, 3, 0]}>
        <sphereGeometry args={[0.15, 8, 8]} />
        <meshBasicMaterial color="#4400ff" />
      </mesh>

      {/* Right neon -- red/magenta */}
      <pointLight position={[8, 3, 0]} color="#ff2200" intensity={0.6} distance={15} />
      <mesh position={[8, 3, 0]}>
        <sphereGeometry args={[0.15, 8, 8]} />
        <meshBasicMaterial color="#ff2200" />
      </mesh>

      {/* Back neon -- cyan */}
      <pointLight position={[0, 4, -12]} color="#00aaff" intensity={0.5} distance={18} />
      <mesh position={[0, 4, -12]}>
        <sphereGeometry args={[0.2, 8, 8]} />
        <meshBasicMaterial color="#00aaff" />
      </mesh>

      {/* Table gold underglow */}
      <pointLight position={[0, -0.2, 0]} color="#c9a84c" intensity={0.3} distance={6} />
    </>
  )
}

// ============================================================
// GOLD DUST PARTICLES
// ============================================================

function GoldDust() {
  return (
    <Sparkles
      count={300}
      size={2}
      scale={[20, 10, 20]}
      speed={0.2}
      color="#c9a84c"
      opacity={0.3}
    />
  )
}

// ============================================================
// CASINO SIGNS (background atmosphere)
// ============================================================

function BackgroundAtmosphere() {
  return (
    <>
      {/* Floor */}
      <mesh rotation={[-Math.PI / 2, 0, 0]} position={[0, -1.1, 0]} receiveShadow>
        <planeGeometry args={[60, 60]} />
        <MeshReflectorMaterial
          blur={[300, 100]}
          resolution={512}
          mixBlur={0.8}
          mixStrength={0.3}
          roughness={1}
          depthScale={0.5}
          minDepthThreshold={0.4}
          maxDepthThreshold={1.4}
          color="#0a0508"
          metalness={0.4}
          mirror={0.3}
        />
      </mesh>

      {/* Back wall */}
      <mesh position={[0, 4, -18]}>
        <planeGeometry args={[40, 12]} />
        <meshStandardMaterial color="#060310" roughness={0.95} />
      </mesh>

      {/* Distant casino signs (gold glowing boxes) */}
      {[[-12, 6, -16], [12, 5, -14], [-8, 4, -17], [10, 7, -15]].map(([x, y, z], i) => (
        <mesh key={i} position={[x, y, z]}>
          <boxGeometry args={[2, 0.6, 0.1]} />
          <meshStandardMaterial
            color="#c9a84c"
            emissive="#c9a84c"
            emissiveIntensity={0.6}
            roughness={0.1}
            metalness={0.8}
          />
        </mesh>
      ))}
    </>
  )
}

// ============================================================
// CAMERA RIG (subtle breathing motion)
// ============================================================

function CameraRig() {
  useFrame((state) => {
    const t = state.clock.elapsedTime
    // Gentle sway
    state.camera.position.x = Math.sin(t * 0.12) * 0.25
    state.camera.position.y = 5.5 + Math.sin(t * 0.08) * 0.08
    state.camera.lookAt(0, -0.3, -0.5)
  })
  return null
}

// ============================================================
// HOLOGRAM PLAYER SEATS
// ============================================================

function SeatMarkers() {
  const seats = [
    { x: -3.5, z: 2.8 },  // Seat 1 far left
    { x: -1.8, z: 3.4 },  // Seat 2
    { x: 0.0,  z: 3.6 },  // Seat 3 center (player)
    { x: 1.8,  z: 3.4 },  // Seat 4
    { x: 3.5,  z: 2.8 },  // Seat 5 far right
  ]

  return (
    <>
      {seats.map((seat, i) => (
        <group key={i} position={[seat.x, 0, seat.z]}>
          {/* Seat disc -- flat marker on felt (no cones) */}
          <mesh position={[0, -0.42, 0]} rotation={[-Math.PI / 2, 0, 0]}>
            <circleGeometry args={[0.4, 32]} />
            <meshStandardMaterial
              color={i === 2 ? '#c9a84c' : '#0d7a3e'}
              emissive={i === 2 ? '#c9a84c' : '#0a5a2e'}
              emissiveIntensity={i === 2 ? 0.2 : 0.05}
              transparent
              opacity={i === 2 ? 0.4 : 0.2}
              side={THREE.DoubleSide}
            />
          </mesh>

          {/* Gold ring around seat */}
          <mesh rotation={[-Math.PI / 2, 0, 0]} position={[0, -0.415, 0]}>
            <ringGeometry args={[0.38, 0.42, 32]} />
            <meshStandardMaterial
              color="#c9a84c"
              emissive="#c9a84c"
              emissiveIntensity={i === 2 ? 0.3 : 0.12}
              side={THREE.DoubleSide}
              transparent
              opacity={i === 2 ? 0.7 : 0.35}
            />
          </mesh>

          {/* Chip area marker ring (in front of seat) */}
          <mesh rotation={[-Math.PI / 2, 0, 0]} position={[0, -0.43, 0.55]}>
            <ringGeometry args={[0.22, 0.28, 32]} />
            <meshStandardMaterial
              color="#c9a84c"
              emissive="#c9a84c"
              emissiveIntensity={0.2}
              side={THREE.DoubleSide}
              transparent
              opacity={0.4}
            />
          </mesh>
        </group>
      ))}
    </>
  )
}

// ============================================================
// SEAT PROJECTOR (3D -> 2D screen coords every frame)
// ============================================================

// Seat positions ON the table surface (lower Y = on the felt, not floating above)
const SEAT_WORLD_POSITIONS = [
  new THREE.Vector3(-3.5, 0.2, 2.8),   // Seat 1 -- just above felt
  new THREE.Vector3(-1.8, 0.2, 3.4),   // Seat 2
  new THREE.Vector3( 0.0, 0.2, 3.6),   // Seat 3 (player)
  new THREE.Vector3( 1.8, 0.2, 3.4),   // Seat 4
  new THREE.Vector3( 3.5, 0.2, 2.8),   // Seat 5
]

function SeatProjector({ onProject }: { onProject: (positions: SeatPosition[]) => void }) {
  const { camera, size } = useThree()
  const lastRef = useRef<string>('')

  useFrame(() => {
    const positions: SeatPosition[] = SEAT_WORLD_POSITIONS.map(worldPos => {
      const pos = worldPos.clone().project(camera)
      return {
        x: (pos.x * 0.5 + 0.5) * size.width,
        y: (-pos.y * 0.5 + 0.5) * size.height,
        visible: pos.z > 0 && pos.z < 1,
      }
    })

    // Only call back when positions actually change (avoid re-render thrash)
    const key = positions.map(p => `${Math.round(p.x)},${Math.round(p.y)}`).join('|')
    if (key !== lastRef.current) {
      lastRef.current = key
      onProject(positions)
    }
  })

  return null
}

// ============================================================
// MAIN SCENE EXPORT
// ============================================================

export function CasinoScene3D({ onSeatPositions, feltColor = '#0d5c2e' }: { onSeatPositions?: (positions: SeatPosition[]) => void; feltColor?: string }) {
  _feltColor = feltColor // pass to CasinoTable via module scope
  const handleProject = useCallback((positions: SeatPosition[]) => {
    onSeatPositions?.(positions)
  }, [onSeatPositions])

  return (
    <div className="absolute inset-0" style={{ zIndex: 1 }}>
      <Canvas
        shadows
        dpr={[1, 1.5]}
        gl={{
          antialias: true,
          alpha: true,
          toneMapping: THREE.ACESFilmicToneMapping,
          toneMappingExposure: 1.1,
        }}
        camera={{
          fov: 50,
          near: 0.1,
          far: 200,
          // Seated-player POV: lower the camera so you look ACROSS the felt and out
          // the window, instead of down at the table. Tune y (height) / z (distance).
          position: [0, 3.6, 8.2],
        }}
        style={{ background: 'transparent' }}
      >
        {/* Fog -- lighter so environment shows through */}
        <fog attach="fog" args={['#04040a', 8, 35]} />

        {/* NO background color -- transparent canvas so video shows through */}

        {/* Ambient light -- very dim purple-dark */}
        <ambientLight color="#110a18" intensity={0.6} />

        {/* Key spotlight -- warm chandelier */}
        <spotLight
          position={[0, 12, 2]}
          angle={0.5}
          penumbra={0.8}
          intensity={3}
          color="#fff5e0"
          castShadow
          shadow-mapSize={[2048, 2048]}
          shadow-bias={-0.0001}
        />

        {/* Scene objects */}
        <CasinoTable />
        <ChipTray />
        <Chandelier />
        <NeonLights />
        <GoldDust />
        <BackgroundAtmosphere />
        {/* Hologram seat stands */}
        <SeatMarkers />

        {/* Projects 3D seat positions to 2D for bot labels */}
        <SeatProjector onProject={handleProject} />

        <CameraRig />

        {/* Contact shadows under table */}
        <ContactShadows
          position={[0, -1.09, 0]}
          opacity={0.6}
          scale={20}
          blur={2}
          far={4}
        />

        {/* Postprocessing -- the cinematic layer */}
        <EffectComposer>
          {/* Bloom: gold glow bleeds light */}
          <Bloom
            luminanceThreshold={0.6}
            luminanceSmoothing={0.9}
            intensity={0.4}
            mipmapBlur
          />
          {/* Vignette: darkens edges like a film camera */}
          <Vignette eskil={false} offset={0.2} darkness={0.8} />
          {/* Chromatic aberration: subtle luxury lens effect */}
          <ChromaticAberration
            offset={new THREE.Vector2(0.0005, 0.0005)}
            radialModulation={true}
            modulationOffset={0.5}
          />
        </EffectComposer>
      </Canvas>
    </div>
  )
}

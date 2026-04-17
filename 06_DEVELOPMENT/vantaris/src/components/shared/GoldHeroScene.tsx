'use client'

import { useRef, useMemo } from 'react'
import { Canvas, useFrame } from '@react-three/fiber'
import { Float, Sparkles } from '@react-three/drei'
import * as THREE from 'three'

/* ================================================================
   3D Hero Scene -- Luminous platinum/champagne crystal with
   iridescent lighting, bloom-like glow, orbiting rings, sparkles.
   NOT brown gold. Think: diamond in a luxury display case.
   ================================================================ */

function Crystal() {
  const meshRef = useRef<THREE.Mesh>(null)
  const glowRef = useRef<THREE.Mesh>(null)

  useFrame((state) => {
    if (!meshRef.current) return
    const t = state.clock.elapsedTime
    meshRef.current.rotation.x = t * 0.1
    meshRef.current.rotation.y = t * 0.15
    meshRef.current.rotation.z = Math.sin(t * 0.3) * 0.1
    if (glowRef.current) {
      glowRef.current.rotation.x = t * 0.1
      glowRef.current.rotation.y = t * 0.15
      // Pulsing scale
      const pulse = 1 + Math.sin(t * 1.5) * 0.03
      glowRef.current.scale.setScalar(1.6 * pulse)
    }
  })

  return (
    <Float speed={1.2} rotationIntensity={0.2} floatIntensity={0.6}>
      <group>
        {/* Main crystal -- bright champagne/platinum */}
        <mesh ref={meshRef}>
          <octahedronGeometry args={[1.6, 0]} />
          <meshPhysicalMaterial
            color="#F0E6D0"
            metalness={1}
            roughness={0.05}
            emissive="#E8D48B"
            emissiveIntensity={0.3}
            clearcoat={1}
            clearcoatRoughness={0.1}
            reflectivity={1}
            envMapIntensity={2}
          />
        </mesh>

        {/* Outer glow shell */}
        <mesh ref={glowRef} scale={1.6}>
          <octahedronGeometry args={[1.6, 0]} />
          <meshBasicMaterial
            color="#E8D48B"
            transparent
            opacity={0.03}
            side={THREE.BackSide}
          />
        </mesh>

        {/* Inner wireframe */}
        <mesh rotation={[Math.PI / 4, 0, Math.PI / 4]}>
          <octahedronGeometry args={[1.2, 0]} />
          <meshBasicMaterial color="#F5EED5" wireframe transparent opacity={0.1} />
        </mesh>
      </group>
    </Float>
  )
}

function OrbitRing({ radius, speed, tilt, color, opacity }: { radius: number; speed: number; tilt: number; color: string; opacity: number }) {
  const ref = useRef<THREE.Mesh>(null)

  useFrame((state) => {
    if (!ref.current) return
    const t = state.clock.elapsedTime * speed
    ref.current.rotation.z = t
    ref.current.rotation.x = tilt
  })

  return (
    <mesh ref={ref}>
      <torusGeometry args={[radius, 0.005, 16, 128]} />
      <meshBasicMaterial color={color} transparent opacity={opacity} />
    </mesh>
  )
}

function FloatingDiamonds({ count = 12 }: { count?: number }) {
  const groupRef = useRef<THREE.Group>(null)

  const diamonds = useMemo(() =>
    Array.from({ length: count }, (_, i) => ({
      position: [
        (Math.random() - 0.5) * 14,
        (Math.random() - 0.5) * 8,
        (Math.random() - 0.5) * 6,
      ] as [number, number, number],
      scale: Math.random() * 0.08 + 0.03,
      speed: Math.random() * 0.5 + 0.2,
      offset: Math.random() * Math.PI * 2,
    })),
    [count]
  )

  useFrame((state) => {
    if (!groupRef.current) return
    groupRef.current.rotation.y = state.clock.elapsedTime * 0.01
  })

  return (
    <group ref={groupRef}>
      {diamonds.map((d, i) => (
        <Float key={i} speed={d.speed} floatIntensity={0.3}>
          <mesh position={d.position} scale={d.scale}>
            <octahedronGeometry args={[1, 0]} />
            <meshPhysicalMaterial
              color="#F0E6D0"
              metalness={0.9}
              roughness={0.1}
              emissive="#D4AF37"
              emissiveIntensity={0.5}
            />
          </mesh>
        </Float>
      ))}
    </group>
  )
}

function Particles({ count = 100 }: { count?: number }) {
  const ref = useRef<THREE.Points>(null)

  const positions = useMemo(() => {
    const arr = new Float32Array(count * 3)
    for (let i = 0; i < count; i++) {
      arr[i * 3] = (Math.random() - 0.5) * 20
      arr[i * 3 + 1] = (Math.random() - 0.5) * 12
      arr[i * 3 + 2] = (Math.random() - 0.5) * 8
    }
    return arr
  }, [count])

  useFrame((state) => {
    if (!ref.current) return
    ref.current.rotation.y = state.clock.elapsedTime * 0.012
  })

  return (
    <points ref={ref}>
      <bufferGeometry>
        <bufferAttribute attach="attributes-position" args={[positions, 3]} />
      </bufferGeometry>
      <pointsMaterial size={0.02} color="#E8D48B" transparent opacity={0.5} sizeAttenuation blending={THREE.AdditiveBlending} depthWrite={false} />
    </points>
  )
}

export function GoldHeroScene() {
  return (
    <div className="absolute inset-0 pointer-events-none" style={{ zIndex: 0 }}>
      <Canvas
        camera={{ position: [0, 0, 7], fov: 45 }}
        style={{ background: 'transparent' }}
        gl={{ alpha: true, antialias: true, powerPreference: 'high-performance' }}
        dpr={[1, 2]}>

        {/* Lighting rig -- bright, multi-colored for iridescence */}
        <ambientLight intensity={0.4} color="#F0E6D0" />
        <directionalLight position={[5, 5, 5]} intensity={1.2} color="#FFFAF0" />
        <directionalLight position={[-5, 3, 3]} intensity={0.6} color="#C8A2E8" />
        <directionalLight position={[0, -3, 5]} intensity={0.4} color="#87CEEB" />
        <pointLight position={[0, 0, 4]} intensity={0.8} color="#E8D48B" distance={10} />
        <pointLight position={[3, 2, 2]} intensity={0.3} color="#FF69B4" distance={8} />

        <Crystal />

        {/* Orbit rings -- different colors for prismatic effect */}
        <OrbitRing radius={3} speed={0.15} tilt={1.2} color="#E8D48B" opacity={0.08} />
        <OrbitRing radius={3.8} speed={-0.1} tilt={0.8} color="#C8A2E8" opacity={0.05} />
        <OrbitRing radius={4.5} speed={0.08} tilt={1.5} color="#87CEEB" opacity={0.04} />

        {/* Floating mini diamonds */}
        <FloatingDiamonds count={15} />

        {/* Sparkle particles */}
        <Sparkles count={40} scale={12} size={1.5} speed={0.3} color="#E8D48B" opacity={0.3} />

        {/* Dust particles */}
        <Particles count={80} />
      </Canvas>
    </div>
  )
}

// Re-export for backward compat
export { GoldHeroScene as GoldParticles }

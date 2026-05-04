"use client";
import * as React from "react";
import { Canvas, useFrame } from "@react-three/fiber";
import { OrbitControls, Stars } from "@react-three/drei";
import * as THREE from "three";
import { useT } from "@/lib/i18n";

/**
 * Stylised constituency scene. Real AC boundaries aren't shipped (would
 * blow the 10 MB repo cap). Instead we draw:
 *   - a centroid pin (glowing dot)
 *   - a halo ring sized roughly by elector count
 *   - an animated "your vote" particle orbiting in
 * Caption discloses the abstraction.
 */
export interface StoryCanvasProps {
  acCode: string;
  acName: string;
  electors: number;
  className?: string;
}

function Pin() {
  return (
    <mesh>
      <sphereGeometry args={[0.12, 32, 32]} />
      <meshStandardMaterial color="#facc15" emissive="#facc15" emissiveIntensity={1.6} />
    </mesh>
  );
}

function Halo({ radius }: { radius: number }) {
  const ref = React.useRef<THREE.Mesh>(null);
  useFrame((_, dt) => {
    if (ref.current) ref.current.rotation.z += dt * 0.25;
  });
  return (
    <mesh ref={ref} rotation={[Math.PI / 2, 0, 0]}>
      <ringGeometry args={[radius, radius + 0.04, 96]} />
      <meshBasicMaterial color="#60a5fa" side={THREE.DoubleSide} transparent opacity={0.7} />
    </mesh>
  );
}

function VoteParticle({ radius }: { radius: number }) {
  const ref = React.useRef<THREE.Mesh>(null);
  // Bezier-ish path: start outside the halo, spiral in toward the pin.
  useFrame(({ clock }) => {
    if (!ref.current) return;
    const t = (clock.getElapsedTime() % 4) / 4; // 0..1 over 4s
    const angle = t * Math.PI * 2;
    const r = radius * (1 - t * 0.92);
    ref.current.position.set(Math.cos(angle) * r, 0.05, Math.sin(angle) * r);
    const scale = 0.05 + (1 - t) * 0.05;
    ref.current.scale.setScalar(scale);
  });
  return (
    <mesh ref={ref}>
      <sphereGeometry args={[1, 16, 16]} />
      <meshBasicMaterial color="#22d3ee" />
    </mesh>
  );
}

export function StoryCanvas({ acCode, acName, electors, className }: StoryCanvasProps) {
  const t = useT();
  // Halo radius: roughly proportional to log10(electors) so it scales nicely
  // across rural (~50k) and urban (~500k) constituencies.
  const haloRadius = Math.min(2.5, 0.6 + Math.log10(Math.max(1000, electors)) * 0.3);

  return (
    <figure className={className}>
      <div className="aspect-video w-full overflow-hidden rounded-md border bg-black">
        <Canvas camera={{ position: [0, 1.6, 3.5], fov: 45 }}>
          <ambientLight intensity={0.4} />
          <pointLight position={[2, 3, 2]} intensity={1.2} />
          <Stars radius={50} depth={30} count={800} factor={3} fade speed={0.4} />
          <group>
            <Pin />
            <Halo radius={haloRadius} />
            <VoteParticle radius={haloRadius} />
          </group>
          <OrbitControls enablePan={false} enableZoom={false} autoRotate autoRotateSpeed={0.6} />
        </Canvas>
      </div>
      <figcaption className="mt-1 text-xs text-muted-foreground">
        {acName} ({acCode}) · {electors.toLocaleString()} electors · stylised representation, not to scale
      </figcaption>
    </figure>
  );
}

export default StoryCanvas;

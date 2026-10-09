import React, { useEffect, useRef } from 'react';

interface CelestialCoreProps {
  pipelineState: string;
  isRecording: boolean;
  audioLevel: number;
  onToggleRecording: () => void;
}

export const CelestialCore: React.FC<CelestialCoreProps> = ({
  pipelineState,
  isRecording,
  audioLevel,
  onToggleRecording
}) => {
  const canvasRef = useRef<HTMLCanvasElement | null>(null);

  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas) return;

    const ctx = canvas.getContext('2d');
    if (!ctx) return;

    let animId: number;
    const dpr = window.devicePixelRatio || 1;
    const size = 260;
    canvas.width = size * dpr;
    canvas.height = size * dpr;
    ctx.scale(dpr, dpr);

    const centerX = size / 2;
    const centerY = size / 2;

    // Keplerian particles for accretion disc
    const particleCount = 80;
    const particles = Array.from({ length: particleCount }, () => ({
      angle: Math.random() * Math.PI * 2,
      distance: 55 + Math.random() * 55,
      speed: (0.006 + Math.random() * 0.012) * (Math.random() < 0.5 ? 1 : -1),
      size: Math.random() * 1.8 + 0.6,
      opacity: Math.random() * 0.6 + 0.2,
      hueOffset: (Math.random() - 0.5) * 30
    }));

    // Expanding shockwaves
    const shockwaves: { radius: number; maxRadius: number; alpha: number; speed: number }[] = [];

    let time = 0;
    let smoothedLevel = 0;

    const render = () => {
      time += 0.016;
      ctx.clearRect(0, 0, size, size);

      // Smooth audio level
      smoothedLevel += (audioLevel - smoothedLevel) * 0.25;

      const isListening = isRecording && pipelineState === 'Listening...';
      const isSpeaking = pipelineState === 'Speaking...';
      const isThinking = pipelineState === 'Thinking...';

      // Spawn shockwaves during voice activity
      if (isListening && smoothedLevel > 0.15 && Math.random() < 0.25) {
        shockwaves.push({
          radius: 45,
          maxRadius: 110 + smoothedLevel * 30,
          alpha: 0.6,
          speed: 1.2 + smoothedLevel * 2
        });
      }
      if (isSpeaking && Math.random() < 0.15) {
        shockwaves.push({
          radius: 45,
          maxRadius: 105,
          alpha: 0.5,
          speed: 1.0
        });
      }

      // 1. Draw Expanding Gravitational Wave Rings
      for (let i = shockwaves.length - 1; i >= 0; i--) {
        const sw = shockwaves[i];
        sw.radius += sw.speed;
        sw.alpha *= 0.96;

        ctx.beginPath();
        ctx.arc(centerX, centerY, sw.radius, 0, Math.PI * 2);
        const ringColor = isListening
          ? `rgba(0, 245, 212, ${sw.alpha})`
          : `rgba(96, 165, 250, ${sw.alpha})`;
        ctx.strokeStyle = ringColor;
        ctx.lineWidth = 1.2;
        ctx.stroke();

        if (sw.alpha < 0.02 || sw.radius >= sw.maxRadius) {
          shockwaves.splice(i, 1);
        }
      }

      // Base radius calculation
      let targetRadius = 42;
      if (isListening) {
        targetRadius = 45 + smoothedLevel * 35;
      } else if (isSpeaking) {
        targetRadius = 46 + Math.sin(time * 5) * 6;
      } else if (isThinking) {
        targetRadius = 38 + Math.sin(time * 8) * 3;
      } else {
        targetRadius = 42 + Math.sin(time * 1.8) * 2;
      }

      // 2. Ambient Deep Corona Glow
      const glowGrad = ctx.createRadialGradient(
        centerX, centerY, targetRadius * 0.5,
        centerX, centerY, targetRadius * 2.4
      );

      if (isListening) {
        glowGrad.addColorStop(0, 'rgba(0, 245, 212, 0.45)');
        glowGrad.addColorStop(0.5, 'rgba(16, 185, 129, 0.18)');
        glowGrad.addColorStop(1, 'rgba(0, 0, 0, 0)');
      } else if (isSpeaking) {
        glowGrad.addColorStop(0, 'rgba(56, 189, 248, 0.5)');
        glowGrad.addColorStop(0.5, 'rgba(99, 102, 241, 0.2)');
        glowGrad.addColorStop(1, 'rgba(0, 0, 0, 0)');
      } else if (isThinking) {
        glowGrad.addColorStop(0, 'rgba(217, 70, 239, 0.45)');
        glowGrad.addColorStop(0.5, 'rgba(168, 85, 247, 0.18)');
        glowGrad.addColorStop(1, 'rgba(0, 0, 0, 0)');
      } else {
        glowGrad.addColorStop(0, 'rgba(99, 102, 241, 0.25)');
        glowGrad.addColorStop(0.6, 'rgba(59, 130, 246, 0.08)');
        glowGrad.addColorStop(1, 'rgba(0, 0, 0, 0)');
      }

      ctx.fillStyle = glowGrad;
      ctx.beginPath();
      ctx.arc(centerX, centerY, targetRadius * 2.4, 0, Math.PI * 2);
      ctx.fill();

      // 3. Orbiting Accretion Dust Particles
      ctx.save();
      for (const p of particles) {
        const speedMult = isThinking ? 3.0 : isListening ? 1.5 : 1.0;
        p.angle += p.speed * speedMult;

        const px = centerX + Math.cos(p.angle) * p.distance;
        const py = centerY + Math.sin(p.angle) * (p.distance * 0.45); // Elliptical projection

        ctx.beginPath();
        ctx.arc(px, py, p.size, 0, Math.PI * 2);

        let pColor = `rgba(226, 232, 240, ${p.opacity})`;
        if (isListening) pColor = `rgba(167, 243, 208, ${p.opacity})`;
        if (isSpeaking) pColor = `rgba(186, 230, 253, ${p.opacity})`;
        if (isThinking) pColor = `rgba(245, 208, 254, ${p.opacity})`;

        ctx.fillStyle = pColor;
        ctx.fill();
      }
      ctx.restore();

      // 4. Primary Stellar Photosphere
      const coreGrad = ctx.createRadialGradient(
        centerX - targetRadius * 0.25, centerY - targetRadius * 0.25, targetRadius * 0.1,
        centerX, centerY, targetRadius
      );

      if (isListening) {
        coreGrad.addColorStop(0, '#ffffff');
        coreGrad.addColorStop(0.3, '#5eead4');
        coreGrad.addColorStop(0.7, '#0d9488');
        coreGrad.addColorStop(1, '#042f2e');
      } else if (isSpeaking) {
        coreGrad.addColorStop(0, '#ffffff');
        coreGrad.addColorStop(0.3, '#7dd3fc');
        coreGrad.addColorStop(0.7, '#2563eb');
        coreGrad.addColorStop(1, '#0f172a');
      } else if (isThinking) {
        coreGrad.addColorStop(0, '#fdf4ff');
        coreGrad.addColorStop(0.3, '#f472b6');
        coreGrad.addColorStop(0.7, '#9333ea');
        coreGrad.addColorStop(1, '#3b0764');
      } else {
        coreGrad.addColorStop(0, '#ffffff');
        coreGrad.addColorStop(0.35, '#93c5fd');
        coreGrad.addColorStop(0.75, '#3b82f6');
        coreGrad.addColorStop(1, '#090d16');
      }

      ctx.beginPath();
      ctx.arc(centerX, centerY, targetRadius, 0, Math.PI * 2);
      ctx.fillStyle = coreGrad;
      ctx.fill();

      // 5. Equatorial Relativistic Lensing Ring
      ctx.save();
      ctx.beginPath();
      ctx.ellipse(
        centerX, centerY,
        targetRadius * 1.55,
        targetRadius * 0.42,
        Math.PI / 12,
        0, Math.PI * 2
      );
      ctx.strokeStyle = isListening
        ? 'rgba(94, 234, 212, 0.45)'
        : isSpeaking
        ? 'rgba(147, 197, 253, 0.5)'
        : isThinking
        ? 'rgba(244, 114, 182, 0.5)'
        : 'rgba(255, 255, 255, 0.18)';
      ctx.lineWidth = 1.5;
      ctx.stroke();
      ctx.restore();

      animId = requestAnimationFrame(render);
    };

    render();

    return () => {
      cancelAnimationFrame(animId);
    };
  }, [pipelineState, isRecording, audioLevel]);

  return (
    <div className="relative flex flex-col items-center justify-center my-2 select-none group">
      {/* Interactive Core Trigger */}
      <button
        onClick={onToggleRecording}
        className="relative focus:outline-none focus-visible:ring-2 focus-visible:ring-cyan-400 rounded-full cursor-pointer transition-transform duration-300 hover:scale-105 active:scale-95"
        aria-label={isRecording ? "Stop voice listening" : "Start voice listening"}
        title={isRecording ? "Click to stop listening" : "Click to speak with the observatory"}
      >
        <canvas
          ref={canvasRef}
          style={{ width: 260, height: 260 }}
          className="filter drop-shadow-[0_0_35px_rgba(59,130,246,0.3)] transition-all"
        />

        {/* Floating Reticle Badge Over Core */}
        <div className="absolute inset-0 flex items-center justify-center pointer-events-none">
          <div className="opacity-0 group-hover:opacity-100 transition-opacity duration-300 px-3 py-1 rounded-full bg-black/60 backdrop-blur-md border border-white/20 text-[11px] font-mono tracking-widest text-white uppercase shadow-lg">
            {isRecording ? "Active Intercom" : "Tap to Speak"}
          </div>
        </div>
      </button>

      {/* State Metadata Pill Below Core */}
      <div className="mt-1 flex items-center space-x-2 px-3 py-1 rounded-full bg-white/[0.04] border border-white/[0.08] backdrop-blur-md text-xs font-mono tracking-wider">
        <span
          className={`w-2 h-2 rounded-full ${
            pipelineState === 'Speaking...'
              ? 'bg-sky-400 animate-ping'
              : pipelineState === 'Listening...'
              ? 'bg-emerald-400 animate-pulse'
              : pipelineState === 'Thinking...'
              ? 'bg-pink-400 animate-spin'
              : 'bg-zinc-500'
          }`}
        />
        <span className="text-zinc-300 uppercase text-[11px]">
          {pipelineState === 'Speaking...'
            ? 'Observatory Synthesizing Audio'
            : pipelineState === 'Listening...'
            ? 'Acoustic Core Listening'
            : pipelineState === 'Thinking...'
            ? 'Relativistic Vector Retrieval'
            : 'Observatory Core Standby'}
        </span>
      </div>
    </div>
  );
};

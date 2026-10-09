import React, { useEffect, useRef } from 'react';

interface Star {
  x: number;
  y: number;
  radius: number;
  baseAlpha: number;
  alpha: number;
  speed: number;
  phase: number;
  color: string;
  depth: number;
}

interface Meteor {
  x: number;
  y: number;
  length: number;
  speed: number;
  angle: number;
  alpha: number;
  active: boolean;
}

export const CosmicBackground: React.FC = () => {
  const canvasRef = useRef<HTMLCanvasElement | null>(null);

  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas) return;

    const ctx = canvas.getContext('2d', { alpha: false });
    if (!ctx) return;

    let animId: number;
    let width = (canvas.width = window.innerWidth);
    let height = (canvas.height = window.innerHeight);

    let mouseX = width / 2;
    let mouseY = height / 2;
    let targetMouseX = mouseX;
    let targetMouseY = mouseY;

    const handleMouseMove = (e: MouseEvent) => {
      targetMouseX = e.clientX;
      targetMouseY = e.clientY;
    };
    window.addEventListener('mousemove', handleMouseMove);

    const spectralColors = [
      '#ffffff',
      '#f8fafc',
      '#e2e8f0',
      '#bfdbfe',
      '#dbeafe',
      '#fef3c7',
      '#a5b4fc'
    ];

    let stars: Star[] = [];
    const meteors: Meteor[] = [];

    const init = () => {
      width = canvas.width = window.innerWidth;
      height = canvas.height = window.innerHeight;
      stars = [];

      const count = Math.min(320, Math.floor((width * height) / 3800));
      for (let i = 0; i < count; i++) {
        const isBright = Math.random() < 0.08;
        stars.push({
          x: Math.random() * width,
          y: Math.random() * height,
          radius: isBright ? Math.random() * 0.9 + 0.6 : Math.random() * 0.5 + 0.25,
          baseAlpha: isBright ? Math.random() * 0.5 + 0.4 : Math.random() * 0.35 + 0.15,
          alpha: 0.5,
          speed: Math.random() * 0.008 + 0.002,
          phase: Math.random() * Math.PI * 2,
          color: spectralColors[Math.floor(Math.random() * spectralColors.length)],
          depth: Math.random() * 0.8 + 0.2
        });
      }
    };

    init();
    window.addEventListener('resize', init);

    let time = 0;
    const render = () => {
      time += 0.016;

      // Smooth mouse parallax
      mouseX += (targetMouseX - mouseX) * 0.04;
      mouseY += (targetMouseY - mouseY) * 0.04;
      const offsetX = (mouseX - width / 2) * 0.025;
      const offsetY = (mouseY - height / 2) * 0.025;

      // 1. Interstellar Void Base
      ctx.fillStyle = '#030408';
      ctx.fillRect(0, 0, width, height);

      // 2. Cosmic Nebulae Dust Clouds (Soft deep purples & cyans)
      const neb1 = ctx.createRadialGradient(
        width * 0.3 + offsetX * 0.5, height * 0.35 + offsetY * 0.5, 0,
        width * 0.3, height * 0.35, Math.max(width, height) * 0.55
      );
      neb1.addColorStop(0, 'rgba(49, 46, 129, 0.16)');
      neb1.addColorStop(0.5, 'rgba(30, 27, 75, 0.08)');
      neb1.addColorStop(1, 'rgba(0, 0, 0, 0)');
      ctx.fillStyle = neb1;
      ctx.fillRect(0, 0, width, height);

      const neb2 = ctx.createRadialGradient(
        width * 0.75 - offsetX * 0.5, height * 0.65 - offsetY * 0.5, 0,
        width * 0.75, height * 0.65, Math.max(width, height) * 0.5
      );
      neb2.addColorStop(0, 'rgba(15, 23, 42, 0.22)');
      neb2.addColorStop(0.5, 'rgba(14, 116, 144, 0.06)');
      neb2.addColorStop(1, 'rgba(0, 0, 0, 0)');
      ctx.fillStyle = neb2;
      ctx.fillRect(0, 0, width, height);

      // 3. Render Stars with Depth Parallax
      for (let i = 0; i < stars.length; i++) {
        const s = stars[i];
        const twinkle = Math.sin(time * s.speed * 60 + s.phase);
        const currentAlpha = Math.max(0.08, Math.min(1.0, s.baseAlpha + twinkle * 0.25));

        const px = (s.x + offsetX * s.depth + width) % width;
        const py = (s.y + offsetY * s.depth + height) % height;

        ctx.fillStyle = s.color;
        ctx.globalAlpha = currentAlpha;
        ctx.beginPath();
        ctx.arc(px, py, s.radius, 0, Math.PI * 2);
        ctx.fill();

        // Cross diffraction spikes on bright specimen stars
        if (s.radius > 1.1 && currentAlpha > 0.6) {
          ctx.strokeStyle = s.color;
          ctx.globalAlpha = currentAlpha * 0.25;
          ctx.lineWidth = 0.5;

          ctx.beginPath();
          ctx.moveTo(px - 3.5, py);
          ctx.lineTo(px + 3.5, py);
          ctx.moveTo(px, py - 3.5);
          ctx.lineTo(px, py + 3.5);
          ctx.stroke();
        }
      }

      // 4. Occasional Shooting Star (Meteor Streak)
      if (Math.random() < 0.008 && meteors.length < 2) {
        meteors.push({
          x: Math.random() * width,
          y: Math.random() * (height * 0.4),
          length: Math.random() * 80 + 50,
          speed: Math.random() * 9 + 11,
          angle: Math.PI / 4 + (Math.random() - 0.5) * 0.2,
          alpha: 1.0,
          active: true
        });
      }

      for (let i = meteors.length - 1; i >= 0; i--) {
        const m = meteors[i];
        m.x += Math.cos(m.angle) * m.speed;
        m.y += Math.sin(m.angle) * m.speed;
        m.alpha -= 0.02;

        if (m.alpha <= 0) {
          meteors.splice(i, 1);
          continue;
        }

        const tailX = m.x - Math.cos(m.angle) * m.length;
        const tailY = m.y - Math.sin(m.angle) * m.length;

        const meteorGrad = ctx.createLinearGradient(tailX, tailY, m.x, m.y);
        meteorGrad.addColorStop(0, 'rgba(255, 255, 255, 0)');
        meteorGrad.addColorStop(1, `rgba(255, 255, 255, ${m.alpha * 0.8})`);

        ctx.strokeStyle = meteorGrad;
        ctx.lineWidth = 1.2;
        ctx.beginPath();
        ctx.moveTo(tailX, tailY);
        ctx.lineTo(m.x, m.y);
        ctx.stroke();
      }

      ctx.globalAlpha = 1.0;
      animId = requestAnimationFrame(render);
    };

    render();

    return () => {
      window.removeEventListener('mousemove', handleMouseMove);
      window.removeEventListener('resize', init);
      cancelAnimationFrame(animId);
    };
  }, []);

  return (
    <canvas
      ref={canvasRef}
      className="fixed inset-0 pointer-events-none z-0"
      style={{ background: '#030408' }}
      aria-hidden="true"
    />
  );
};

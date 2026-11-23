/* Living fluorescence field: illustrative nuclei that drift and breathe, with
 * instance outlines. Used as a "microscope eyepiece" in page headers.
 * Cheap: capped at ~30 fps, pauses off-screen and in hidden tabs, static for
 * prefers-reduced-motion. Not model output; callers label it as illustrative. */
(() => {
  'use strict';
  const reduced = window.matchMedia('(prefers-reduced-motion: reduce)').matches;
  function rng(seed) { return () => { seed |= 0; seed = seed + 0x6D2B79F5 | 0; let t = Math.imul(seed ^ seed >>> 15, 1 | seed); t = t + Math.imul(t ^ t >>> 7, 61 | t) ^ t; return ((t ^ t >>> 14) >>> 0) / 4294967296; }; }

  function create(canvas, opts = {}) {
    const ctx = canvas.getContext('2d');
    const outline = opts.outline !== false;
    const sweepOn = opts.sweep !== false;
    const dim = Number(opts.dim || 1);
    let w = 0, h = 0, dpr = 1, nuclei = [], visible = true, raf = 0, last = 0;
    const seed = Number(opts.seed || 7);
    function layout() {
      const r = canvas.getBoundingClientRect();
      dpr = Math.min(2, window.devicePixelRatio || 1);
      w = Math.max(1, Math.round(r.width * dpr)); h = Math.max(1, Math.round(r.height * dpr));
      canvas.width = w; canvas.height = h;
      const rand = rng(seed), unit = Math.min(w, h) / 300, target = Math.round((w * h) / (unit * unit * 2600));
      nuclei = [];
      let guard = 0;
      while (nuclei.length < target && guard++ < target * 50) {
        const rad = unit * (9 + rand() * 8);
        const n = { x: rad + rand() * (w - 2 * rad), y: rad + rand() * (h - 2 * rad), rx: rad * (0.9 + rand() * 0.35), ry: rad * (0.72 + rand() * 0.3), a: rand() * Math.PI,
          b: 0.55 + rand() * 0.45, hue: rand(), p: rand() * Math.PI * 2, s: 0.25 + rand() * 0.5, vx: (rand() - 0.5) * unit * 2.2, vy: (rand() - 0.5) * unit * 2.2 };
        if (nuclei.every(o => Math.hypot(o.x - n.x, o.y - n.y) > (o.rx + n.rx) * 1.05)) nuclei.push(n);
      }
      draw(performance.now());
    }
    function draw(t) {
      const time = t / 1000;
      ctx.globalCompositeOperation = 'source-over';
      ctx.fillStyle = '#04060a'; ctx.fillRect(0, 0, w, h);
      const bg = ctx.createRadialGradient(w * 0.55, h * 0.45, 0, w * 0.55, h * 0.45, Math.max(w, h) * 0.7);
      bg.addColorStop(0, 'rgba(46,66,110,.35)'); bg.addColorStop(1, 'rgba(0,0,0,0)');
      ctx.fillStyle = bg; ctx.fillRect(0, 0, w, h);
      ctx.globalCompositeOperation = 'lighter';
      const sweep = (time * 0.12) % 1.4 - 0.2; // outline reveal sweeps slowly across the field
      nuclei.forEach(n => {
        const dx = reduced ? 0 : Math.sin(time * n.s + n.p) * n.vx * 3;
        const dy = reduced ? 0 : Math.cos(time * n.s * 0.8 + n.p) * n.vy * 3;
        const breathe = reduced ? 1 : 0.85 + 0.15 * Math.sin(time * n.s * 1.6 + n.p);
        n.cx = n.x + dx; n.cy = n.y + dy;
        ctx.save(); ctx.translate(n.cx, n.cy); ctx.rotate(n.a); ctx.scale(1, n.ry / n.rx);
        const g = ctx.createRadialGradient(0, 0, 0, 0, 0, n.rx * 1.3);
        const c = `${80 + n.hue * 50},${140 + n.hue * 60},255`;
        g.addColorStop(0, `rgba(${c},${n.b * breathe * dim})`); g.addColorStop(0.6, `rgba(${c},${0.55 * n.b * breathe * dim})`); g.addColorStop(1, 'rgba(20,40,90,0)');
        ctx.fillStyle = g; ctx.beginPath(); ctx.arc(0, 0, n.rx * 1.3, 0, Math.PI * 2); ctx.fill(); ctx.restore();
      });
      if (outline) {
        ctx.globalCompositeOperation = 'source-over';
        nuclei.forEach((n, i) => {
          const reveal = reduced || !sweepOn ? 1 : Math.max(0, Math.min(1, (sweep - n.cx / w) * 6 + 1));
          if (reveal <= 0) return;
          const hue = 320 + (i * 37) % 60;
          ctx.save(); ctx.translate(n.cx, n.cy); ctx.rotate(n.a);
          ctx.beginPath(); ctx.ellipse(0, 0, n.rx, n.ry, 0, 0, Math.PI * 2 * reveal);
          if (opts.fill) { ctx.fillStyle = `hsla(${hue},70%,55%,.2)`; ctx.fill(); }
          ctx.lineWidth = 1.8 * dpr; ctx.strokeStyle = `hsla(${hue},85%,72%,${0.95 * reveal})`; ctx.stroke();
          ctx.restore();
        });
      }
    }
    function loop(t) {
      raf = 0;
      if (!visible || document.hidden) return;
      if (t - last > 33) { draw(t); last = t; }
      raf = requestAnimationFrame(loop);
    }
    function start() { if (!reduced && !raf) raf = requestAnimationFrame(loop); }
    layout();
    let timer = 0;
    window.addEventListener('resize', () => { clearTimeout(timer); timer = setTimeout(layout, 150); });
    if ('IntersectionObserver' in window) new IntersectionObserver(es => { visible = es[0].isIntersecting; if (visible) start(); }, { threshold: 0.01 }).observe(canvas);
    document.addEventListener('visibilitychange', () => { if (!document.hidden) start(); });
    start();
    return { count: () => nuclei.length };
  }

  function boot() {
    document.querySelectorAll('canvas[data-micro-field]').forEach(c => { if (!c.__field) c.__field = create(c, { outline: c.dataset.outline !== 'false', seed: c.dataset.seed }); });
  }
  window.BioNucleiField = { create, boot };
  if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', boot, { once: true }); else boot();
})();

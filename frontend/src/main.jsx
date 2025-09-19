import React, { useEffect } from 'react';
import { createRoot } from 'react-dom/client';
import SparkleFall from 'sparklefall';

function Sparkles() {
  useEffect(() => {
    const container = document.getElementById('sparkleContainer');
    if (!container) return;

    let teardown = null;

    try {
      // Use the default class export from sparklefall
      const instance = new SparkleFall({
        container,
        sparkles: ['✨', '⭐', '💫', '🌟'],
        interval: 800,
        maxSparkles: 50,
        injectStyles: true,
      });
      // Instance auto-starts by default; keep a teardown
      teardown = instance && (instance.destroy ? instance.destroy.bind(instance) : null);
    } catch (e) {
      // Fallback: simple sparkles if library init fails
      let active = true;
      function createSparkle() {
        if (!active) return;
        const sparkles = ['✨', '⭐', '💫', '🌟'];
        const el = document.createElement('div');
        el.className = 'sparklefall-sparkle';
        el.textContent = sparkles[Math.floor(Math.random() * sparkles.length)];
        el.style.left = Math.random() * 100 + '%';
        el.style.animationDuration = (Math.random() * 3 + 2) + 's';
        el.style.fontSize = (Math.random() * 20 + 10) + 'px';
        container.appendChild(el);
        setTimeout(() => el.remove(), 5000);
      }
      const interval = setInterval(createSparkle, 800);
      for (let i = 0; i < 5; i++) setTimeout(createSparkle, i * 200);
      teardown = () => { active = false; clearInterval(interval); };
    }

    return () => { if (teardown) teardown(); };
  }, []);

  return null;
}

function FormEnhancer() {
  useEffect(() => {
    const form = document.getElementById('vibeCheckForm');
    const btn = document.getElementById('analyzeBtn');
    if (!form || !btn) return;

    function onSubmit() {
      btn.classList.add('loading');
    }

    form.addEventListener('submit', onSubmit);
    return () => form.removeEventListener('submit', onSubmit);
  }, []);
  return null;
}

function HomeApp() {
  return (
    <>
      <Sparkles />
      <FormEnhancer />
    </>
  );
}

export function mountHomeApp(mountId = 'react-home-root') {
  const mountNode = document.getElementById(mountId);
  if (!mountNode) return;
  const root = createRoot(mountNode);
  root.render(<HomeApp />);
}

// Auto-mount if window is ready and a default mount node exists
if (typeof window !== 'undefined') {
  const doMount = () => {
    const defaultNode = document.getElementById('react-home-root');
    if (defaultNode) {
      mountHomeApp('react-home-root');
    }
  };

  if (document.readyState === 'loading') {
    window.addEventListener('DOMContentLoaded', doMount);
  } else {
    // DOM already parsed
    doMount();
  }
}

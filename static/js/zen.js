document.addEventListener('DOMContentLoaded', () => {
  const body = document.body;
  const header = document.querySelector('header');
  const hotspot = document.getElementById('topEdgeHotspot');
  const zenBtn = document.getElementById('zenModeToggle');
  let zenMode = false;

  const applyZenState = () => {
    if (zenMode) {
      body.classList.add('zen-mode');
      body.classList.add('header-hidden');
      body.classList.remove('header-visible');
      if (hotspot) hotspot.style.pointerEvents = 'none';
      if (zenBtn) zenBtn.textContent = 'Exit Zen';
    } else {
      body.classList.remove('zen-mode');
      if (hotspot) hotspot.style.pointerEvents = 'auto';
      if (zenBtn) zenBtn.textContent = 'Zen Mode';
    }
  };

  if (zenBtn) {
    zenBtn.addEventListener('click', () => {
      zenMode = !zenMode;
      applyZenState();
    });
  }

  // Block top-edge touch reveal while in Zen Mode (capture to intercept before main.js)
  window.addEventListener('touchstart', (e) => {
    if (!zenMode) return;
    const y = e.touches && e.touches[0] ? e.touches[0].clientY : 9999;
    if (y <= 12) {
      e.stopImmediatePropagation();
      body.classList.add('header-hidden');
      body.classList.remove('header-visible');
    }
  }, { capture: true });

  // Exit Zen on Esc key
  window.addEventListener('keydown', (e) => {
    if (e.key === 'Escape' && zenMode) {
      zenMode = false;
      applyZenState();
    }
  });
});

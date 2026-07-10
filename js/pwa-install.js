// PWA Install Prompt - simple inline version
// Banner HTML is hardcoded in index.html, this script just controls show/hide + button behavior

(function() {
  const banner = document.getElementById('pwa-install-banner');
  if (!banner) return;

  const installBtn = document.getElementById('pwa-install-btn');
  const dismissBtn = document.getElementById('pwa-dismiss-btn');
  const DISMISS_KEY = 'px-pwa-dismissed-' + new Date().toISOString().slice(0, 10);

  // Skip if installed (PWA standalone mode)
  if (window.matchMedia('(display-mode: standalone)').matches) {
    banner.classList.add('hidden');
    return;
  }

  // Skip if user dismissed today
  if (localStorage.getItem(DISMISS_KEY)) {
    banner.classList.add('hidden');
    return;
  }

  // Show banner after 2 seconds
  setTimeout(() => {
    banner.classList.remove('hidden');
  }, 2000);

  // Dismiss button
  if (dismissBtn) {
    dismissBtn.addEventListener('click', () => {
      banner.classList.add('hidden');
      localStorage.setItem(DISMISS_KEY, '1');
    });
  }

  // Install button
  if (installBtn) {
    installBtn.addEventListener('click', async () => {
      // Try native install prompt (Android Chrome)
      if (window.deferredPrompt) {
        try {
          window.deferredPrompt.prompt();
          const { outcome } = await window.deferredPrompt.userChoice;
          if (outcome === 'accepted') {
            localStorage.setItem(DISMISS_KEY, '1');
          }
          window.deferredPrompt = null;
        } catch (e) {
          alert('安裝步驟：\n\nChrome Menu (⋮) → 「加到主畫面」或「安裝 App」\n\nSafari：分享掣 → 「加入主畫面」');
        }
      } else {
        // Fallback instructions
        alert('安裝步驟：\n\nChrome Menu (⋮) → 「加到主畫面」或「安裝 App」\n\nSafari：分享掣 → 「加入主畫面」');
      }
      banner.classList.add('hidden');
    });
  }

  // Listen for beforeinstallprompt and store globally
  window.addEventListener('beforeinstallprompt', (e) => {
    e.preventDefault();
    window.deferredPrompt = e;
    // Show banner immediately if user hasn't dismissed
    if (!localStorage.getItem(DISMISS_KEY)) {
      banner.classList.remove('hidden');
    }
  });
})();
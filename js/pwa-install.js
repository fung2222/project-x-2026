// PWA Install Prompt
(function() {
  // iOS detection (iOS 不支援 beforeinstallprompt)
  const isIOS = /iPad|iPhone|iPod/.test(navigator.userAgent) && !window.MSStream;
  const isStandalone = window.matchMedia('(display-mode: standalone)').matches || window.navigator.standalone === true;
  const DISMISS_KEY = 'px-pwa-dismissed-' + new Date().toISOString().slice(0, 10);

  // 已經安裝 / 今日已 dismiss → 唔顯示
  if (isStandalone) return;
  if (localStorage.getItem(DISMISS_KEY)) return;

  // Create banner
  const banner = document.createElement('div');
  banner.className = 'pwa-install-banner';
  banner.innerHTML = `
    <svg class="pwa-install-icon" viewBox="0 0 32 32" xmlns="http://www.w3.org/2000/svg">
      <rect x="0" y="0" width="32" height="32" rx="7" ry="7" fill="#ffffff" stroke="#e2e8f0" stroke-width="0.4"/>
      <text x="16" y="16" text-anchor="middle" dominant-baseline="central" font-family="Arial Black, Arial, Helvetica, sans-serif" font-weight="900" font-size="18" fill="#000000">PX</text>
    </svg>
    <div class="pwa-install-text">
      <strong>安裝 Project X App</strong>
      <small>加入主畫面，離線使用，每日自動更新</small>
    </div>
    <div class="pwa-install-actions">
      <button class="pwa-btn pwa-btn-primary" id="pwa-install-btn">安裝</button>
      <button class="pwa-btn pwa-btn-secondary" id="pwa-dismiss-btn">✕</button>
    </div>
  `;
  document.body.appendChild(banner);

  let deferredPrompt = null;

  document.getElementById('pwa-dismiss-btn').addEventListener('click', () => {
    banner.classList.remove('show');
    localStorage.setItem(DISMISS_KEY, '1');
  });

  // Android / Chrome 用 beforeinstallprompt event
  window.addEventListener('beforeinstallprompt', (e) => {
    e.preventDefault();
    deferredPrompt = e;
    banner.classList.add('show');

    document.getElementById('pwa-install-btn').addEventListener('click', async () => {
      banner.classList.remove('show');
      deferredPrompt.prompt();
      const { outcome } = await deferredPrompt.userChoice;
      if (outcome === 'accepted') {
        localStorage.setItem(DISMISS_KEY, '1');
      }
      deferredPrompt = null;
    });
  });

  // iOS 用 Safari「加入主畫面」指示
  if (isIOS && !isStandalone) {
    setTimeout(() => banner.classList.add('show'), 2000);
    document.getElementById('pwa-install-btn').addEventListener('click', () => {
      const msg = 'iOS 安裝步驟：\n\n1. 撳底部分享掣 ⬆️\n2. 揀「加入主畫面」\n3. 撳「加入」\n\nPX icon 會喺主畫面出現。';
      alert(msg);
    });
  }

  // 桌面 browser fallback
  if (!isIOS && !deferredPrompt && !window.matchMedia('(display-mode: standalone)').matches) {
    // 桌面：30 秒後提示
    setTimeout(() => {
      if (window.innerWidth > 768) banner.classList.add('show');
    }, 30000);
  }
})();
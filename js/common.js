// Project X 2026 - 共用 JS
const API_BASE = './data';

async function loadJSON(path) {
  try {
    const res = await fetch(`${API_BASE}/${path}?t=${Date.now()}`);
    if (!res.ok) throw new Error(`HTTP ${res.status}`);
    return await res.json();
  } catch (e) {
    console.error(`Failed to load ${path}:`, e);
    return null;
  }
}

function formatUSD(v, decimals = 2) {
  if (v == null) return '—';
  return `$${Number(v).toFixed(decimals)}`;
}

function formatHKD(v, decimals = 0) {
  if (v == null) return '—';
  return `HK$${Number(v).toFixed(decimals)}`;
}

function formatPct(v, decimals = 2) {
  if (v == null) return '—';
  const sign = v > 0 ? '+' : '';
  return `${sign}${Number(v).toFixed(decimals)}%`;
}

function signalClass(signal) {
  if (!signal) return 'na';
  if (signal.includes('買入')) return 'buy';
  if (signal.includes('小心') || signal.includes('止盈')) return 'warn';
  if (signal.includes('賣')) return 'sell';
  return 'hold';
}

function signalText(signal) {
  if (!signal) return '—';
  if (signal.includes('買入')) return '🟢 考慮買入';
  if (signal.includes('小心')) return '🟡 需小心';
  if (signal.includes('賣出')) return '🔴 賣出';
  if (signal.includes('止盈')) return '💰 止盈';
  return '⚪ 觀望為主';
}

function trendArrow(v) {
  if (v == null) return '';
  if (v > 0) return '▲';
  if (v < 0) return '▼';
  return '━';
}

function rsiZone(rsi) {
  if (rsi == null) return '—';
  if (rsi < 35) return '超賣';
  if (rsi > 65) return '超買';
  return '中性';
}

function setHeaderDate(d) {
  const el = document.getElementById('update-time');
  if (el && d) el.textContent = `更新：${d}`;
}

function escapeHTML(s) {
  if (s == null) return '';
  return String(s).replace(/[&<>"']/g, c => ({
    '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;'
  }[c]));
}

// Active nav highlight
document.addEventListener('DOMContentLoaded', () => {
  const path = location.pathname.split('/').pop() || 'index.html';
  document.querySelectorAll('.nav-link').forEach(link => {
    const href = link.getAttribute('href');
    if (href === path || (path === '' && href === 'index.html')) {
      link.classList.add('active');
    }
  });
});
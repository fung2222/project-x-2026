/* P&L Chart — lightweight-charts v4 */
let pnlChart = null;

async function initPnlChart(containerId, history) {
  if (!history || history.length === 0) {
    document.getElementById(containerId).innerHTML =
      '<div class="empty">📊 暫無歷史數據（明日收市後開始累積）</div>';
    return;
  }

  const container = document.getElementById(containerId);
  container.innerHTML = '';

  const lib = await import('https://unpkg.com/lightweight-charts@4.1.3/dist/lightweight-charts.standalone.production.js');
  const createChart = lib.createChart;

  pnlChart = createChart(container, {
    width: container.clientWidth,
    height: 280,
    layout: {
      background: { color: '#ffffff' },
      textColor: '#4a5568',
      fontSize: 12
    },
    grid: {
      vertLines: { color: '#f1f4f8' },
      horzLines: { color: '#f1f4f8' }
    },
    timeScale: {
      timeVisible: false,
      borderColor: '#e2e8f0'
    },
    rightPriceScale: {
      borderColor: '#e2e8f0'
    },
    crosshair: {
      mode: 1
    }
  });

  const sorted = history.slice().sort((a, b) => a.date.localeCompare(b.date));

  const valueSeries = pnlChart.addAreaSeries({
    lineColor: '#0f766e',
    topColor: 'rgba(15, 118, 110, 0.4)',
    bottomColor: 'rgba(15, 118, 110, 0.05)',
    lineWidth: 2,
    title: '組合總值 (USD)'
  });

  valueSeries.setData(sorted.map(h => ({
    time: h.date,
    value: h.total_value_usd || 0
  })));

  const pnlSeries = pnlChart.addLineSeries({
    color: '#059669',
    lineWidth: 2,
    title: 'P&L %'
  });

  pnlSeries.setData(sorted.map(h => ({
    time: h.date,
    value: h.total_pnl_pct || 0
  })));

  pnlChart.timeScale().fitContent();

  window.addEventListener('resize', () => {
    if (pnlChart) pnlChart.applyOptions({ width: container.clientWidth });
  });
}

async function loadAndRenderPnlChart(containerId) {
  const data = await loadJSON('pnl_history.json');
  if (!data || data.length === 0) {
    document.getElementById(containerId).innerHTML =
      '<div class="empty">📊 暫無歷史數據（明日收市後開始累積）</div>';
    return;
  }
  await initPnlChart(containerId, data);
}
/* P&L Chart — lightweight-charts v4 (loaded via <script> tag in HTML) */
let pnlChart = null;

function renderPnlChart(containerId, history) {
  const container = document.getElementById(containerId);
  if (!container) return;

  if (!history || history.length === 0) {
    container.innerHTML = '<div class="empty">📊 暫無歷史數據（明日收市後開始累積）</div>';
    return;
  }

  // Wait for library to be available (script load may be async)
  if (typeof LightweightCharts === 'undefined') {
    // Retry after 200ms
    setTimeout(() => renderPnlChart(containerId, history), 200);
    container.innerHTML = '<div class="empty">📊 圖表載入中…</div>';
    return;
  }

  container.innerHTML = '';

  try {
    pnlChart = LightweightCharts.createChart(container, {
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
  } catch (e) {
    console.error('Chart error:', e);
    container.innerHTML = '<div class="empty">⚠️ 圖表載入失敗：' + e.message + '</div>';
  }
}

async function loadAndRenderPnlChart(containerId) {
  const data = await loadJSON('pnl_history.json');
  if (!data || data.length === 0) {
    document.getElementById(containerId).innerHTML = '<div class="empty">📊 暫無歷史數據（明日收市後開始累積）</div>';
    return;
  }

  // Wait for library to load (max 5 sec)
  let waited = 0;
  while (typeof LightweightCharts === 'undefined' && waited < 5000) {
    await new Promise(r => setTimeout(r, 100));
    waited += 100;
  }

  if (typeof LightweightCharts === 'undefined') {
    document.getElementById(containerId).innerHTML = '<div class="empty">⚠️ 圖表 library 載入失敗（網絡問題）。請 reload 試下。</div>';
    return;
  }

  renderPnlChart(containerId, data);
}
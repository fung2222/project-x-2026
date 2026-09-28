"""Mag7 HTML 報表 - 手機優先，廣東話單段摘要，一頁 7 隻易掃。
設計：
- header: 標題 + 生成時間 + 整體氛圍
- 7 張卡片，每隻一卡
- 每卡: 價/變幅/趨勢/score + 圖 + 信號/警示/計劃
"""
import json
from pathlib import Path
from datetime import datetime

ROOT = Path("/opt/data/mag7_observer")
DATA = ROOT / "data" / "mag7_snapshot.json"
OUT = ROOT / "output"

CSS = """
:root { --bg:#0f1216; --card:#1a1f29; --txt:#e8eaf0; --dim:#8a93a6; --up:#10b05a; --down:#ef4146; --warn:#f59e0b; --brand:#5b8def; }
* { box-sizing:border-box; margin:0; padding:0; }
body { background:var(--bg); color:var(--txt); font:14px/1.5 -apple-system,BlinkMacSystemFont,'PingFang HK','Microsoft JhengHei',sans-serif; padding:12px; }
.hdr { padding:14px 12px; border-bottom:1px solid #2a313c; margin-bottom:14px; }
.hdr h1 { font-size:20px; font-weight:700; }
.hdr .meta { color:var(--dim); font-size:12px; margin-top:4px; }
.hdr .mood { margin-top:8px; font-size:13px; }
.hdr .mood span { background:#222a36; padding:3px 8px; border-radius:6px; margin-right:6px; }
.grid { display:grid; grid-template-columns:1fr; gap:12px; }
.card { background:var(--card); border-radius:14px; padding:14px; }
.card .row1 { display:flex; justify-content:space-between; align-items:baseline; }
.card .sym { font-size:22px; font-weight:700; }
.card .price { font-size:22px; font-weight:700; }
.card .chg { font-size:13px; margin-left:6px; }
.up { color:var(--up); } .down { color:var(--down); } .warn { color:var(--warn); } .dim { color:var(--dim); }
.card .sub { color:var(--dim); font-size:12px; margin-top:2px; }
.card .stat-row { display:flex; gap:8px; margin-top:10px; flex-wrap:wrap; }
.card .stat { background:#222a36; padding:4px 10px; border-radius:8px; font-size:12px; }
.card .trend { font-size:14px; font-weight:700; margin-top:10px; padding:6px 10px; border-radius:8px; display:inline-block; }
.t-strong { background:#0d3a26; color:#10b05a; }
.t-up { background:#0d3a26; color:#10b05a; }
.t-mid { background:#2a313c; color:var(--dim); }
.t-down { background:#3a1a1a; color:#ef4146; }
.card img { width:100%; border-radius:8px; margin-top:10px; background:#000; }
.card .sig, .card .warnl, .card .plan { margin-top:10px; font-size:13px; }
.card .sig b, .card .warnl b, .card .plan b { display:block; font-size:12px; margin-bottom:3px; }
.card .plan { background:#0e1a2e; padding:10px; border-radius:8px; border-left:3px solid var(--brand); }
.ftr { color:var(--dim); font-size:11px; text-align:center; margin-top:18px; padding-bottom:20px; }
@media (min-width:900px) { .grid { grid-template-columns:repeat(2,1fr); } }
"""

MOOD_LABEL = {
    "STRONG_UP": "整體強勢", "UP": "偏多", "NEUTRAL": "中性", "DOWN": "偏空", "STRONG_DOWN": "弱勢"
}


def render():
    snap = json.loads(DATA.read_text())
    gen = snap["generated_at"]
    items = [d for d in snap["data"] if "error" not in d]

    # overall mood: 平均 score + 過熱警數
    avg = sum(i["score"] for i in items) / len(items)
    hot = sum(1 for i in items if i["rsi"] > 75)
    cold = sum(1 for i in items if i["rsi"] < 30)
    if avg >= 75: mood = "🔥 板塊強勢"
    elif avg >= 60: mood = "🟢 偏多"
    elif avg >= 45: mood = "⚪ 中性"
    elif avg >= 30: mood = "🟠 偏空"
    else: mood = "🔴 弱勢"
    mood_summary = f"{mood} (均分 {avg:.0f}/100)"
    if hot: mood_summary += f" · {hot}隻過熱"
    if cold: mood_summary += f" · {cold}隻超賣"

    cards = []
    for it in items:
        chg_class = "up" if it["chg_pct"] >= 0 else "down"
        arrow = "▲" if it["chg_pct"] >= 0 else "▼"
        if "過熱" in it["trend"]: tcls = "t-strong"
        elif "強升" in it["trend"]: tcls = "t-up"
        elif "偏多" in it["trend"]: tcls = "t-up"
        elif "中性" in it["trend"]: tcls = "t-mid"
        else: tcls = "t-down"

        sig_html = "<br>".join(it["signals"]) if it["signals"] != ["— 無明確信號 —"] else '<span class="dim">無明確信號</span>'
        warn_html = "<br>".join(it["warnings"]) if it["warnings"] != ["— 暫無風險 —"] else '<span class="dim">暫無</span>'

        chart_png = f"chart_{it['ticker']}_{it['as_of']}.png"

        cards.append(f"""
<div class="card">
  <div class="row1">
    <div><span class="sym">{it['ticker']}</span> <span class="sub">{it['as_of']}</span></div>
    <div><span class="price">${it['last']}</span><span class="chg {chg_class}">{arrow}{abs(it['chg_pct']):.2f}%</span></div>
  </div>
  <div class="sub">前收 ${it['prev_close']} · RSI {it['rsi']} · MA20 ${it['ma20']} · MA50 ${it['ma50']}</div>
  <div class="stat-row">
    <span class="stat">5日 {it['mom5_pct']:+.1f}%</span>
    <span class="stat">20日 {it['mom20_pct']:+.1f}%</span>
    <span class="stat">量比 {it['vol_ratio']:.2f}x</span>
    <span class="stat">支 ${it['support_60d']}</span>
    <span class="stat">阻 ${it['resistance_60d']}</span>
  </div>
  <div><span class="trend {tcls}">{it['trend']} · Score {it['score']}</span></div>
  <img src="{chart_png}" alt="{it['ticker']} chart" loading="lazy"/>
  <div class="sig"><b>📊 Signals</b>{sig_html}</div>
  <div class="warnl"><b>⚠️ Risks</b>{warn_html}</div>
  <div class="plan"><b>🎯 Plan</b>{it['plan']}</div>
</div>""")

    html = f"""<!doctype html><html lang="zh-HK"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>Mag7 觀察報告 {snap['data'][0].get('as_of','-') if items else '-'}</title>
<style>{CSS}</style></head>
<body>
<div class="hdr">
  <h1>🔥 Magnificent 7 觀察報告</h1>
  <div class="meta">生成時間 {gen} · 數據截至 {items[0]['as_of'] if items else '-'}</div>
  <div class="mood"><span>{mood_summary}</span><span>追蹤 {len(items)} 隻</span></div>
</div>
<div class="grid">{''.join(cards)}</div>
<div class="ftr">僅供觀察參考 · 不構成投資建議 · 數據源 yfinance · 策略 score + 信號 rule-based</div>
</body></html>"""

    out = OUT / f"report_{snap['data'][0].get('as_of','-') if items else '-'}.html"
    out.write_text(html)
    print(f"[report] {out}")
    return out


if __name__ == "__main__":
    render()
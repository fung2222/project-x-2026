"""Mag7 數據層 - yfinance 拉硬數，寫 JSON。
職責：拉 6 個月 OHLCV，計 MA/RSI/momentum/score/signal，
落 mag7_snapshot.json。冇 LLM 介入數字。
"""
import yfinance as yf
import json
from pathlib import Path
from datetime import datetime, timezone

TICKERS = ["TSLA", "NVDA", "GOOGL", "MSFT", "INTC", "CRM", "PLTR"]
ROOT = Path("/opt/data/mag7_observer")
DATA = ROOT / "data"
DATA.mkdir(parents=True, exist_ok=True)


def _rsi(close, period=14):
    d = close.diff()
    gain = d.clip(lower=0).rolling(period).mean()
    loss = (-d.clip(upper=0)).rolling(period).mean()
    rs = gain / loss.replace(0, 1e-9)
    return 100 - (100 / (1 + rs))


def _trend_score(last, ma20, ma50, rsi, mom5, mom20, vol_ratio):
    score = 50
    if last > ma20: score += 10
    if last > ma50: score += 10
    if ma20 > ma50: score += 10
    if rsi > 50: score += 5
    if mom5 > 0: score += 5
    if mom20 > 0: score += 5
    if vol_ratio > 1.2: score += 5
    if rsi > 75: score -= 5
    if rsi < 30: score += 3  # oversold bounce candidate
    return max(0, min(100, score))


def _trend_label(score, rsi):
    if rsi >= 75: return "強升(過熱)"
    if score >= 75: return "強升"
    if score >= 60: return "偏多"
    if score >= 45: return "中性"
    if score >= 30: return "偏空"
    return "下降"


def analyze(ticker):
    s = yf.Ticker(ticker)
    h = s.history(period="6mo", auto_adjust=True)
    if h.empty or len(h) < 50:
        return {"ticker": ticker, "error": "no data"}

    close = h["Close"]
    vol = h["Volume"]
    ma20 = close.rolling(20).mean()
    ma50 = close.rolling(50).mean()
    rsi = _rsi(close)
    mom5 = close.pct_change(5) * 100
    mom20 = close.pct_change(20) * 100
    vol_avg = vol.rolling(20).mean()
    vol_ratio = vol / vol_avg.replace(0, 1e-9)

    last = close.iloc[-1]
    prev = close.iloc[-2]
    pct = (last - prev) / prev * 100

    score = _trend_score(last, ma20.iloc[-1], ma50.iloc[-1],
                         rsi.iloc[-1], mom5.iloc[-1], mom20.iloc[-1],
                         vol_ratio.iloc[-1])
    trend = _trend_label(score, rsi.iloc[-1])

    # buy signals (no emoji - PIL can't render emoji reliably)
    signals = []
    if rsi.iloc[-1] < 30:
        signals.append(f"[BUY] RSI 超賣反彈機 ({rsi.iloc[-1]:.0f})")
    if last > ma20.iloc[-1] and mom5.iloc[-1] > 5 and mom20.iloc[-1] > 0:
        signals.append("[BUY] 短中線動能齊升")
    if (close.iloc[-2] <= ma20.iloc[-1] and last > ma20.iloc[-1]
            and vol_ratio.iloc[-1] > 1.5):
        signals.append("[BUY] 突破 MA20 帶量")
    if (ma20.iloc[-2] <= ma50.iloc[-1] and ma20.iloc[-1] > ma50.iloc[-1]):
        signals.append("[BUY] MA20 上穿 MA50 (Golden Cross)")

    # warnings
    warnings = []
    if rsi.iloc[-1] > 75:
        warnings.append(f"[WARN] RSI 極度超買 ({rsi.iloc[-1]:.0f})")
    if last < ma50.iloc[-1] and (last - ma50.iloc[-1]) / ma50.iloc[-1] < -0.05:
        d = (last - ma50.iloc[-1]) / ma50.iloc[-1] * 100
        warnings.append(f"[WARN] 跌破 MA50 {d:.1f}%")
    if mom5.iloc[-1] < -7:
        warnings.append(f"[WARN] 5日急跌 {mom5.iloc[-1]:.1f}%")
    if vol_ratio.iloc[-1] > 2 and pct < 0:
        warnings.append("[WARN] 放量下跌")
    if last < close.iloc[-60:].min() * 1.02:
        warnings.append("[WARN] 接近 60 日新低")

    # buy zone / stop / target
    pl60 = close.iloc[-60:].min()
    ph60 = close.iloc[-60:].max()
    if ma20.iloc[-1] > ma50.iloc[-1] and last > ma20.iloc[-1]:
        buy_zone = round(float(ma20.iloc[-1]) * 0.98, 2)
        stop = round(float(ma50.iloc[-1]) * 0.98, 2)
        target = round(float(last) * 1.10, 2)
        target2 = round(float(last) * 1.20, 2)
        plan = f"拉回 ${buy_zone} 入 / 止損 ${stop} / TP ${target}→${target2}"
    elif last < ma20.iloc[-1] and ma20.iloc[-1] > ma50.iloc[-1]:
        buy_zone = round(float(ma50.iloc[-1]), 2)
        stop = round(float(ma50.iloc[-1]) * 0.95, 2)
        target = round(float(ma20.iloc[-1]), 2)
        plan = f"待回 ${buy_zone} (MA50) / 止損 ${stop} / 反彈 ${target}"
    else:
        buy_zone = round(float(pl60), 2)
        stop = round(float(pl60) * 0.95, 2)
        target = round(float(ma20.iloc[-1]), 2)
        plan = f"待 ${buy_zone} (60日底) / 止損 ${stop} / 反彈 ${target}"

    # last 90 trading days for chart
    chart = []
    for i in range(-90, 0):
        if abs(i) > len(close):
            continue
        chart.append({
            "date": h.index[i].strftime("%Y-%m-%d"),
            "close": round(float(close.iloc[i]), 2),
            "ma20": round(float(ma20.iloc[i]), 2) if i >= -len(ma20.dropna()) else None,
            "ma50": round(float(ma50.iloc[i]), 2) if i >= -len(ma50.dropna()) else None,
        })

    return {
        "ticker": ticker,
        "as_of": h.index[-1].strftime("%Y-%m-%d"),
        "last": round(float(last), 2),
        "prev_close": round(float(prev), 2),
        "chg_pct": round(float(pct), 2),
        "ma20": round(float(ma20.iloc[-1]), 2),
        "ma50": round(float(ma50.iloc[-1]), 2),
        "rsi": round(float(rsi.iloc[-1]), 1),
        "mom5_pct": round(float(mom5.iloc[-1]), 2),
        "mom20_pct": round(float(mom20.iloc[-1]), 2),
        "vol_ratio": round(float(vol_ratio.iloc[-1]), 2),
        "score": int(score),
        "trend": trend,
        "signals": signals if signals else ["— 無明確信號 —"],
        "warnings": warnings if warnings else ["— 暫無風險 —"],
        "plan": plan,
        "support_60d": round(float(pl60), 2),
        "resistance_60d": round(float(ph60), 2),
        "chart_90d": chart,
    }


def run():
    out = {
        "generated_at": datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC"),
        "tickers": TICKERS,
        "data": [],
    }
    for t in TICKERS:
        try:
            out["data"].append(analyze(t))
        except Exception as e:
            out["data"].append({"ticker": t, "error": str(e)})

    snap = DATA / "mag7_snapshot.json"
    snap.write_text(json.dumps(out, ensure_ascii=False, indent=2))
    print(f"[mag7_data] saved -> {snap}")
    return out


if __name__ == "__main__":
    run()
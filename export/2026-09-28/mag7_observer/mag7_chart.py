"""Mag7 圖表 - 用 PIL 自家畫 trend chart PNG。
3-in-1: 主圖 (close + MA20 + MA50), RSI sub-panel, 信號/警示 tag。
"""
from PIL import Image, ImageDraw, ImageFont
from pathlib import Path
from datetime import datetime

ROOT = Path("/opt/data/mag7_observer")
OUT = ROOT / "output"
OUT.mkdir(parents=True, exist_ok=True)

W, H = 1200, 640
PAD_L, PAD_R, PAD_T, PAD_B = 90, 70, 80, 60
PLOT_W = W - PAD_L - PAD_R
PLOT_H = 320
RSI_T = PAD_T + PLOT_H + 40
RSI_H = 70
INFO_T = RSI_T + RSI_H + 25  # signals/warnings/plan 區
LINE_H = 22

# font: wqy-zenhei handles both ASCII (Latin) + CJK with consistent metrics.
# (DejaVu doesn't have CJK glyphs; mixing caused tofu boxes)
CN_FONT = "/usr/share/fonts/truetype/wqy/wqy-zenhei.ttc"


def _font(size):
    return ImageFont.truetype(CN_FONT, size)

F_TITLE = _font(28)
F_LBL = _font(16)
F_S = _font(13)
F_TINY = _font(11)

# colors
BG = (250, 250, 252)
GRID = (220, 220, 225)
TXT = (40, 40, 50)
CLOSE_C = (35, 99, 210)
MA20_C = (245, 158, 11)
MA50_C = (220, 38, 38)
RSI_C = (120, 80, 200)
WARN_C = (220, 38, 38)
SIG_C = (16, 152, 86)


def _resample_y(points, plot_h, ymin, ymax):
    if ymax == ymin:
        return [PAD_T + plot_h / 2] * len(points)
    return [PAD_T + plot_h - (v - ymin) / (ymax - ymin) * plot_h for v in points]


def draw(ticker, snap):
    chart = snap.get("chart_90d") or []
    if len(chart) < 30:
        return None
    closes = [c["close"] for c in chart if c["close"] is not None]
    ma20s = [c["ma20"] for c in chart if c["ma20"] is not None]
    ma50s = [c["ma50"] for c in chart if c["ma50"] is not None]

    # RSI recompute from snapshot data via mom5/mom20 isn't accurate; recompute from close series
    # 為簡化直接用 chart 嘅 close 自家計
    rsi_series = []
    for i in range(len(closes)):
        if i < 14:
            rsi_series.append(None)
            continue
        sub = closes[max(0, i - 14):i + 1]
        deltas = [sub[j + 1] - sub[j] for j in range(len(sub) - 1)]
        gain = sum(max(0, d) for d in deltas) / 14
        loss = sum(max(0, -d) for d in deltas) / 14
        if loss == 0:
            rsi_series.append(100.0)
        else:
            rs = gain / loss
            rsi_series.append(100 - (100 / (1 + rs)))

    ymin = min(min(c for c in closes if c is not None),
               min(c for c in ma20s if c is not None),
               min(c for c in ma50s if c is not None)) * 0.97
    ymax = max(max(c for c in closes if c is not None),
               max(c for c in ma20s if c is not None),
               max(c for c in ma50s if c is not None)) * 1.03

    img = Image.new("RGB", (W, H), BG)
    d = ImageDraw.Draw(img)

    # title
    last = snap["last"]
    chg = snap["chg_pct"]
    arrow = "▲" if chg >= 0 else "▼"
    chg_color = (16, 152, 86) if chg >= 0 else (220, 38, 38)
    title = f"{ticker}  ${last}  {arrow}{abs(chg):.2f}%   |   {snap['trend']}  Score {snap['score']}/100"
    d.text((PAD_L, 18), title, fill=TXT, font=F_TITLE)
    d.text((PAD_L, 52), f"RSI {snap['rsi']}  ·  MA20 ${snap['ma20']}  ·  MA50 ${snap['ma50']}  ·  Mom5 {snap['mom5_pct']:+.1f}%  ·  as_of {snap['as_of']}",
           fill=(100, 100, 110), font=F_S)

    # grid + Y axis labels
    for i in range(5):
        y = PAD_T + i * PLOT_H / 4
        d.line([(PAD_L, y), (W - PAD_R, y)], fill=GRID, width=1)
        val = ymax - i * (ymax - ymin) / 4
        d.line([(PAD_L - 4, y), (PAD_L, y)], fill=TXT, width=1)
        d.text((PAD_L - 70, y - 8), f"${val:.0f}", fill=TXT, font=F_TINY)

    # X axis: 5 ticks
    n = len(closes)
    for i in range(6):
        x = PAD_L + i * PLOT_W / 5
        idx = min(int(i * (n - 1) / 5), n - 1)
        date = chart[idx]["date"][5:]  # MM-DD
        d.line([(x, PAD_T + PLOT_H), (x, PAD_T + PLOT_H + 4)], fill=TXT, width=1)
        d.text((x - 16, PAD_T + PLOT_H + 8), date, fill=(100, 100, 110), font=F_TINY)

    def plot(series, color, width=2):
        pts = [(PAD_L + i * PLOT_W / (n - 1), y)
               for i, y in enumerate(_resample_y(series, PLOT_H, ymin, ymax))
               if series[i] is not None]
        if len(pts) >= 2:
            d.line(pts, fill=color, width=width)

    plot(closes, CLOSE_C, width=2)
    plot(ma20s, MA20_C, width=2)
    plot(ma50s, MA50_C, width=2)

    # legend
    lx = W - PAD_R - 200
    ly = PAD_T - 30
    d.rectangle([lx, ly, lx + 200, ly + 18], outline=GRID, fill=(255, 255, 255))
    d.line([(lx + 8, ly + 9), (lx + 28, ly + 9)], fill=CLOSE_C, width=2)
    d.text((lx + 32, ly + 1), "Close", fill=TXT, font=F_TINY)
    d.line([(lx + 78, ly + 9), (lx + 98, ly + 9)], fill=MA20_C, width=2)
    d.text((lx + 102, ly + 1), "MA20", fill=TXT, font=F_TINY)
    d.line([(lx + 148, ly + 9), (lx + 168, ly + 9)], fill=MA50_C, width=2)
    d.text((lx + 172, ly + 1), "MA50", fill=TXT, font=F_TINY)

    # RSI sub panel
    d.text((PAD_L, RSI_T - 22), "RSI(14)", fill=TXT, font=F_LBL)
    d.line([(PAD_L, RSI_T + RSI_H / 2), (W - PAD_R, RSI_T + RSI_H / 2)], fill=GRID, width=1)
    d.line([(PAD_L, RSI_T + RSI_H * 0.3), (W - PAD_R, RSI_T + RSI_H * 0.3)], fill=(220, 38, 38), width=1)
    d.line([(PAD_L, RSI_T + RSI_H * 0.7), (W - PAD_R, RSI_T + RSI_H * 0.7)], fill=(16, 152, 86), width=1)
    d.text((W - PAD_R + 4, RSI_T + RSI_H * 0.3 - 7), "70", fill=(220, 38, 38), font=F_TINY)
    d.text((W - PAD_R + 4, RSI_T + RSI_H * 0.7 - 7), "30", fill=(16, 152, 86), font=F_TINY)

    rsi_pts = []
    for i, v in enumerate(rsi_series):
        if v is None:
            continue
        x = PAD_L + i * PLOT_W / (n - 1)
        y = RSI_T + RSI_H - (v / 100) * RSI_H
        rsi_pts.append((x, y))
    if len(rsi_pts) >= 2:
        d.line(rsi_pts, fill=RSI_C, width=2)

    # signals / warnings / plan - plain text, vertical layout
    sig_text = "  ".join(snap["signals"]) if snap["signals"] != ["— 無明確信號 —"] else "無明確信號"
    warn_text = "  ".join(snap["warnings"]) if snap["warnings"] != ["— 暫無風險 —"] else "暫無"

    def draw_line(y, label, text, color):
        d.text((PAD_L, y), label, fill=color, font=F_LBL)
        d.text((PAD_L + 130, y), text, fill=TXT, font=F_S)

    draw_line(INFO_T, "信號:", sig_text, SIG_C)
    draw_line(INFO_T + LINE_H, "警示:", warn_text, WARN_C)
    draw_line(INFO_T + LINE_H * 2, "計劃:", snap["plan"], (35, 99, 210))

    # support / resistance line
    sup_y = PAD_T + PLOT_H - (snap["support_60d"] - ymin) / (ymax - ymin) * PLOT_H
    res_y = PAD_T + PLOT_H - (snap["resistance_60d"] - ymin) / (ymax - ymin) * PLOT_H
    d.line([(PAD_L, sup_y), (W - PAD_R, sup_y)], fill=(120, 120, 120), width=1)
    d.line([(PAD_L, res_y), (W - PAD_R, res_y)], fill=(120, 120, 120), width=1)
    d.text((W - PAD_R - 90, sup_y - 8), f"S ${snap['support_60d']}", fill=(120, 120, 120), font=F_TINY)
    d.text((W - PAD_R - 90, res_y - 8), f"R ${snap['resistance_60d']}", fill=(120, 120, 120), font=F_TINY)

    out = OUT / f"chart_{ticker}_{snap['as_of']}.png"
    img.save(out, optimize=True)
    return out


if __name__ == "__main__":
    import json
    snap = json.loads((ROOT / "data" / "mag7_snapshot.json").read_text())
    for d_ in snap["data"]:
        if "error" not in d_:
            p = draw(d_["ticker"], d_)
            print(f"[chart] {p}")
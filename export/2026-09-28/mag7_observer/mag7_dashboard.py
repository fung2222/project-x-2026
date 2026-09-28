"""Mag7 dashboard - 7 隻股票一張 PNG, 2x4 grid (7格 + 1標題格)。
每格: ticker + 價 + 變幅 + 趨勢色塊 + 90日 sparkline + score + 1-2 個關鍵信號/警示。
"""
from PIL import Image, ImageDraw, ImageFont
import json
from pathlib import Path

ROOT = Path("/opt/data/mag7_observer")
DATA = ROOT / "data" / "mag7_snapshot.json"
OUT = ROOT / "output"

CN_FONT = "/usr/share/fonts/truetype/wqy/wqy-zenhei.ttc"

W = 1400
COLS = 4
ROWS = 2
CELL_W = W // COLS  # 350
CELL_H = 360
HEADER_H = 60
PAD = 8
H = HEADER_H + ROWS * CELL_H + 30

BG = (15, 18, 22)
CARD_BG = (26, 31, 41)
TXT = (232, 234, 240)
DIM = (138, 147, 166)
UP = (16, 176, 90)
DOWN = (239, 65, 70)
WARN = (245, 158, 11)
BRAND = (91, 141, 239)


def fnt(sz):
    return ImageFont.truetype(CN_FONT, sz)


def trend_color(trend):
    if "過熱" in trend or "強升" in trend: return UP
    if "偏多" in trend: return UP
    if "偏空" in trend: return DOWN
    if "下降" in trend: return DOWN
    return DIM


def draw_sparkline(d, x, y, w, h, prices, color):
    if not prices or len(prices) < 2:
        return
    pmin, pmax = min(prices), max(prices)
    if pmax == pmin:
        pmax = pmin + 1
    pts = []
    for i, v in enumerate(prices):
        px = x + i * w / (len(prices) - 1)
        py = y + h - (v - pmin) / (pmax - pmin) * h
        pts.append((px, py))
    d.line(pts, fill=color, width=2)
    d.line([(x, y + h), (x + w, y + h)], fill=(60, 60, 70), width=1)


def short_sig(sig_list):
    out = []
    for s in sig_list[:2]:
        if s.startswith("—"): continue
        # strip "[BUY] " and "[WARN] " prefixes for cleaner label
        s = s.replace("[BUY] ", "▲ ").replace("[WARN] ", "▼ ")
        out.append(s)
    return out


def draw_cell(d, x, y, w, h, it):
    # background
    d.rectangle([x + PAD, y + PAD, x + w - PAD, y + h - PAD], fill=CARD_BG, outline=(40, 48, 60), width=1)

    # ticker + price header
    sym_y = y + PAD + 16
    d.text((x + PAD + 14, sym_y), it["ticker"], fill=TXT, font=fnt(28))
    last = it["last"]
    chg = it["chg_pct"]
    arrow = "▲" if chg >= 0 else "▼"
    chg_col = UP if chg >= 0 else DOWN
    d.text((x + w - PAD - 130, sym_y), f"${last}", fill=TXT, font=fnt(22))
    d.text((x + w - PAD - 130, sym_y + 28), f"{arrow}{abs(chg):.2f}%", fill=chg_col, font=fnt(16))

    # trend pill
    pill_y = y + PAD + 56
    tc = trend_color(it["trend"])
    pill_text = f" {it['trend']} · S{it['score']} "
    bbox = d.textbbox((0, 0), pill_text, font=fnt(13))
    pw, ph = bbox[2] - bbox[0], bbox[3] - bbox[1]
    d.rectangle([x + PAD + 14, pill_y, x + PAD + 14 + pw + 12, pill_y + ph + 6], fill=tc)
    d.text((x + PAD + 20, pill_y + 2), pill_text, fill=(20, 20, 20), font=fnt(13))

    # sparkline
    spark_y = pill_y + 38
    spark_h = 80
    closes = [c["close"] for c in it["chart_90d"]]
    draw_sparkline(d, x + PAD + 14, spark_y, w - 2 * PAD - 28, spark_h, closes, BRAND)

    # stats row (RSI / MA / mom)
    stat_y = spark_y + spark_h + 16
    stats = [
        ("RSI", f"{it['rsi']:.0f}", WARN if it['rsi'] > 70 or it['rsi'] < 30 else TXT),
        ("MA20", f"${it['ma20']:.0f}", TXT),
        ("5d", f"{it['mom5_pct']:+.1f}%", UP if it['mom5_pct'] > 0 else DOWN),
    ]
    col_w = (w - 2 * PAD - 28) // 3
    for i, (label, val, col) in enumerate(stats):
        sx = x + PAD + 14 + i * col_w
        d.text((sx, stat_y), label, fill=DIM, font=fnt(11))
        d.text((sx, stat_y + 16), val, fill=col, font=fnt(15))

    # signals (top 2)
    sig_y = stat_y + 50
    sigs = short_sig(it["signals"])
    if sigs:
        d.text((x + PAD + 14, sig_y), sigs[0][:34], fill=UP, font=fnt(12))
        if len(sigs) > 1:
            d.text((x + PAD + 14, sig_y + 18), sigs[1][:34], fill=UP, font=fnt(12))
    else:
        d.text((x + PAD + 14, sig_y), "— 無信號 —", fill=DIM, font=fnt(12))

    # warnings (top 1)
    warn_y = sig_y + 40
    warns = short_sig(it["warnings"])
    if warns:
        d.text((x + PAD + 14, warn_y), warns[0][:34], fill=DOWN, font=fnt(12))
    else:
        d.text((x + PAD + 14, warn_y), "— 暫無 —", fill=DIM, font=fnt(12))

    # plan line
    plan_y = y + h - PAD - 36
    d.rectangle([x + PAD + 8, plan_y - 4, x + w - PAD - 8, plan_y + 28], fill=(14, 26, 46))
    d.text((x + PAD + 14, plan_y), "計劃:", fill=BRAND, font=fnt(12))
    plan_text = it["plan"]
    # shorter trim to fit ~36 chars on this card width
    if len(plan_text) > 36:
        plan_text = plan_text[:35] + "…"
    d.text((x + PAD + 60, plan_y), plan_text, fill=TXT, font=fnt(12))


def render():
    snap = json.loads(DATA.read_text())
    items = [d for d in snap["data"] if "error" not in d]

    img = Image.new("RGB", (W, H), BG)
    d = ImageDraw.Draw(img)

    # header
    gen = snap["generated_at"]
    avg = sum(i["score"] for i in items) / len(items)
    if avg >= 75: mood = "強勢"
    elif avg >= 60: mood = "偏多"
    elif avg >= 45: mood = "中性"
    elif avg >= 30: mood = "偏空"
    else: mood = "弱勢"
    d.text((20, 14), f"🔥 Mag7 Dashboard · {mood} (均分 {avg:.0f})", fill=TXT, font=fnt(22))
    hot = [i["ticker"] for i in items if i["rsi"] > 75]
    cold = [i["ticker"] for i in items if i["rsi"] < 30]
    bits = []
    if hot: bits.append(f"⚠ 過熱: {','.join(hot)}")
    if cold: bits.append(f"🟢 超賣: {','.join(cold)}")
    bits.append(f"as_of {items[0]['as_of']}")
    d.text((20, 42), "  ·  ".join(bits), fill=DIM, font=fnt(13))

    # grid
    for idx, it in enumerate(items):
        col = idx % COLS
        row = idx // COLS
        x = col * CELL_W
        y = HEADER_H + row * CELL_H
        draw_cell(d, x, y, CELL_W, CELL_H, it)

    # footer
    d.text((20, H - 22), "僅供觀察參考 · 不構成投資建議 · yfinance + rule-based score · 純觀察", fill=DIM, font=fnt(11))

    out = OUT / f"dashboard_{items[0]['as_of']}.png"
    img.save(out, optimize=True)
    print(f"[dashboard] {out}")
    return out


if __name__ == "__main__":
    render()
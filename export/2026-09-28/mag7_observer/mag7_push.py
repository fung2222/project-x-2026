"""Mag7 Telegram 推送 - 真正 send 去 古神 Telegram bot DM。
用 Telegram Bot API (HTTP) + 古神 bot token（profiles/gushen/.env）。

每個 kind：
- daily (21:30 HKT):     摘要 + dashboard PNG + HTML link
- premarket (16:00 HKT): 純摘要
- close (05:05 HKT):     純摘要

數字全部讀 JSON，禁止 LLM 手算。
"""
import json
import os
import subprocess
import sys
from pathlib import Path
from datetime import datetime
import urllib.request
import urllib.parse

ROOT = Path("/opt/data/mag7_observer")
DATA = ROOT / "data" / "mag7_snapshot.json"
# Telegram chat ID — set via env: $MAG7_TELEGRAM_CHAT_ID (REDACTED in public export)
import os as _os
CHAT_ID = _os.environ.get("MAG7_TELEGRAM_CHAT_ID", "REDACTED")


def _load_bot_token():
    """古神 bot first — default/.env 係 Soonoo bot，會推錯 chat。"""
    for path in ("/opt/data/profiles/gushen/.env", "/opt/data/.env"):
        p = Path(path)
        if not p.exists():
            continue
        for line in p.read_text().splitlines():
            if line.startswith("TELEGRAM_BOT_TOKEN="):
                tok = line.split("=", 1)[1].strip().strip('"').strip("'")
                if tok:
                    return tok
    return os.environ.get("TELEGRAM_BOT_TOKEN", "").strip()


BOT_TOKEN = _load_bot_token()
TELEGRAM_API = f"https://api.telegram.org/bot{BOT_TOKEN}"


def _short_label(sig_list):
    out = []
    for s in sig_list:
        if s.startswith("—"): continue
        s = s.replace("[BUY] ", "").replace("[WARN] ", "")
        out.append(s.split(" ")[0] if s else "")
        if len(out) >= 2: break
    return out


def build_summary(items):
    if not items: return ""
    avg = sum(i["score"] for i in items) / len(items)
    if avg >= 75: mood = "強勢"
    elif avg >= 60: mood = "偏多"
    elif avg >= 45: mood = "中性"
    elif avg >= 30: mood = "偏空"
    else: mood = "弱勢"

    hot = [i["ticker"] for i in items if i["rsi"] > 75]
    cold = [i["ticker"] for i in items if i["rsi"] < 30]

    lines = [f"🔥 Mag7 觀察報告 · {mood} (均分 {avg:.0f}/100)"]
    if hot: lines.append(f"⚠️ 過熱: {','.join(hot)}")
    if cold: lines.append(f"🟢 超賣: {','.join(cold)}")
    lines.append("")
    for it in items:
        chg = it["chg_pct"]
        arrow = "▲" if chg >= 0 else "▼"
        sig = _short_label(it["signals"])
        warn = _short_label(it["warnings"])
        sig_s = f" ✓{','.join(sig)}" if sig else ""
        warn_s = f" ⚠{','.join(warn)}" if warn else ""
        lines.append(
            f"{it['ticker']:<5} ${it['last']:<8} {arrow}{abs(chg):>5.2f}%  "
            f"{it['trend']:<10} S{it['score']:>3}{sig_s}{warn_s}"
        )
    return "\n".join(lines)


def build_premarket(items):
    if not items: return ""
    avg = sum(i["score"] for i in items) / len(items)
    if avg >= 75: mood = "強勢"
    elif avg >= 60: mood = "偏多"
    elif avg >= 45: mood = "中性"
    elif avg >= 30: mood = "偏空"
    else: mood = "弱勢"

    lines = [f"🌅 Mag7 盤前 · {mood} (均分 {avg:.0f})"]
    lines.append("")
    for it in items:
        chg = it["chg_pct"]
        arrow = "▲" if chg >= 0 else "▼"
        lines.append(
            f"{it['ticker']:<5} ${it['last']:<8} {arrow}{abs(chg):>5.2f}%  "
            f"{it['trend']:<10} S{it['score']:>3}"
        )
    return "\n".join(lines)


def build_close(items):
    if not items: return ""
    avg = sum(i["score"] for i in items) / len(items)
    if avg >= 75: mood = "強勢"
    elif avg >= 60: mood = "偏多"
    elif avg >= 45: mood = "中性"
    elif avg >= 30: mood = "偏空"
    else: mood = "弱勢"

    lines = [f"🌙 Mag7 收市 · {mood} (均分 {avg:.0f})"]
    lines.append("")
    for it in items:
        chg = it["chg_pct"]
        arrow = "▲" if chg >= 0 else "▼"
        lines.append(
            f"{it['ticker']:<5} ${it['last']:<8} {arrow}{abs(chg):>5.2f}%  "
            f"{it['trend']:<10} S{it['score']:>3}"
        )
    # strongest / weakest
    by_score = sorted(items, key=lambda i: i["score"], reverse=True)
    lines.append("")
    lines.append(f"最強 {by_score[0]['ticker']} S{by_score[0]['score']} · 最弱 {by_score[-1]['ticker']} S{by_score[-1]['score']}")
    return "\n".join(lines)


def _post(url, data=None, files=None):
    """POST to Telegram API. Returns dict."""
    if files:
        boundary = "----mag7boundary"
        body = b""
        for k, v in (data or {}).items():
            body += f"--{boundary}\r\nContent-Disposition: form-data; name=\"{k}\"\r\n\r\n{v}\r\n".encode()
        for k, (fname, fbytes, ctype) in files.items():
            body += f"--{boundary}\r\nContent-Disposition: form-data; name=\"{k}\"; filename=\"{fname}\"\r\nContent-Type: {ctype}\r\n\r\n".encode()
            body += fbytes + b"\r\n"
        body += f"--{boundary}--\r\n".encode()
        req = urllib.request.Request(url, data=body, headers={"Content-Type": f"multipart/form-data; boundary={boundary}"})
    else:
        req = urllib.request.Request(url, data=urllib.parse.urlencode(data).encode())
    try:
        with urllib.request.urlopen(req, timeout=30) as r:
            return json.loads(r.read())
    except Exception as e:
        return {"ok": False, "error": str(e)}


def send_message(text):
    if not BOT_TOKEN:
        return {"ok": False, "error": "no TELEGRAM_BOT_TOKEN"}
    url = f"{TELEGRAM_API}/sendMessage"
    return _post(url, data={"chat_id": CHAT_ID, "text": text})


def send_photo(path, caption=""):
    if not BOT_TOKEN:
        return {"ok": False, "error": "no TELEGRAM_BOT_TOKEN"}
    url = f"{TELEGRAM_API}/sendPhoto"
    with open(path, "rb") as f:
        fbytes = f.read()
    files = {"photo": (Path(path).name, fbytes, "image/png")}
    return _post(url, data={"chat_id": CHAT_ID, "caption": caption}, files=files)


def push(kind="daily"):
    snap = json.loads(DATA.read_text())
    items = [d for d in snap["data"] if "error" not in d]
    if not items:
        print("[push] no data")
        return

    if kind == "premarket":
        text = build_premarket(items)
        r = send_message(text)
        print(f"[push] premarket message ok={r.get('ok')} err={r.get('error') or r.get('description')}")
    elif kind == "close":
        text = build_close(items)
        r = send_message(text)
        print(f"[push] close message ok={r.get('ok')} err={r.get('error') or r.get('description')}")
    else:  # daily
        text = build_summary(items)
        # 1. summary text
        r = send_message(text)
        print(f"[push] daily text ok={r.get('ok')}")
        # 2. dashboard png
        dash = ROOT / "output" / f"dashboard_{items[0]['as_of']}.png"
        if dash.exists():
            cap = f"🔥 Mag7 Dashboard · {items[0]['as_of']}"
            r = send_photo(dash, cap)
            print(f"[push] dashboard ok={r.get('ok')} msg_id={r.get('result',{}).get('message_id')}")
        # 3. html link
        html = ROOT / "output" / f"report_{items[0]['as_of']}.html"
        if html.exists():
            r = send_message(f"📊 完整報表：file://{html}")
            print(f"[push] html link ok={r.get('ok')}")


if __name__ == "__main__":
    kind = sys.argv[1] if len(sys.argv) > 1 else "daily"
    push(kind)
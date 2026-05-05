“””
股票估值分析儀 v4
台股：台灣證交所 / 櫃買中心官方 JSON（持久 Session + Retry + 限速）
美股：Finnhub API
財報補充：FMP API
“””
import streamlit as st
import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry
import pandas as pd
import numpy as np
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from datetime import datetime, timedelta
import time
import random

# ── API Keys ──────────────────────────────────────────────────────────────────

FINNHUB_KEY = “d7s8j19r01qm28g8miggd7s8j19r01qm28g8mih0”
FMP_KEY     = “8Ut6iiNQb0XrVx5fTQGJ1y2htcbLUm3F”

# ── Page Config ───────────────────────────────────────────────────────────────

st.set_page_config(page_title=“股票估值分析儀”, page_icon=“📈”,
layout=“wide”, initial_sidebar_state=“collapsed”)

# ── CSS ───────────────────────────────────────────────────────────────────────

st.markdown(”””

<style>
@import url('https://fonts.googleapis.com/css2?family=Space+Mono:wght@400;700&family=Noto+Sans+TC:wght@300;400;500;700&display=swap');
:root{--bg:#0a0e1a;--bg2:#111827;--bg3:#1c2333;--border:#2a3550;
      --accent:#00d4ff;--accent2:#7c3aed;--green:#10b981;--red:#ef4444;
      --yellow:#f59e0b;--text:#e2e8f0;--text2:#94a3b8;--text3:#64748b;}
html,body,[class*="css"]{background-color:var(--bg)!important;color:var(--text)!important;font-family:'Noto Sans TC',sans-serif;}
.stApp{background:var(--bg);}
.hero-header{background:linear-gradient(135deg,#0a0e1a 0%,#111827 50%,#0f172a 100%);border:1px solid var(--border);border-radius:16px;padding:32px 40px;margin-bottom:24px;position:relative;overflow:hidden;}
.hero-header::before{content:'';position:absolute;top:-50%;left:-20%;width:60%;height:200%;background:radial-gradient(ellipse,rgba(0,212,255,0.06) 0%,transparent 70%);pointer-events:none;}
.hero-title{font-family:'Space Mono',monospace;font-size:2.2rem;font-weight:700;color:var(--accent);letter-spacing:-1px;margin:0 0 8px 0;}
.hero-sub{color:var(--text2);font-size:0.95rem;letter-spacing:2px;text-transform:uppercase;}
.stTextInput>div>div>input{background:var(--bg3)!important;border:1px solid var(--border)!important;border-radius:8px!important;color:var(--text)!important;font-family:'Space Mono',monospace!important;font-size:1.1rem!important;padding:12px 16px!important;}
.stTextInput>div>div>input:focus{border-color:var(--accent)!important;box-shadow:0 0 0 2px rgba(0,212,255,0.15)!important;}
.stButton>button{background:linear-gradient(135deg,var(--accent2),#6d28d9)!important;color:#fff!important;border:none!important;border-radius:8px!important;font-family:'Space Mono',monospace!important;font-weight:700!important;font-size:0.95rem!important;padding:12px 32px!important;letter-spacing:1px;width:100%;}
.stButton>button:hover{background:linear-gradient(135deg,#6d28d9,var(--accent2))!important;transform:translateY(-1px);box-shadow:0 8px 24px rgba(124,58,237,0.4)!important;}
.metric-card{background:var(--bg2);border:1px solid var(--border);border-radius:12px;padding:20px 24px;margin-bottom:12px;position:relative;overflow:hidden;}
.metric-card::after{content:'';position:absolute;top:0;left:0;width:3px;height:100%;background:var(--accent);}
.metric-label{color:var(--text3);font-size:0.75rem;letter-spacing:2px;text-transform:uppercase;margin-bottom:6px;}
.metric-value{font-family:'Space Mono',monospace;font-size:1.6rem;font-weight:700;color:var(--text);line-height:1;}
.metric-sub{color:var(--text2);font-size:0.8rem;margin-top:4px;}
.metric-card.green::after{background:var(--green);}
.metric-card.red::after{background:var(--red);}
.metric-card.yellow::after{background:var(--yellow);}
.metric-card.purple::after{background:var(--accent2);}
.section-header{font-family:'Space Mono',monospace;font-size:0.8rem;letter-spacing:3px;text-transform:uppercase;color:var(--accent);border-bottom:1px solid var(--border);padding-bottom:10px;margin:28px 0 16px 0;}
.verdict-box{border-radius:14px;padding:28px 32px;margin:20px 0;text-align:center;}
.verdict-box.buy{background:linear-gradient(135deg,rgba(16,185,129,0.12),rgba(16,185,129,0.04));border:2px solid var(--green);}
.verdict-box.hold{background:linear-gradient(135deg,rgba(245,158,11,0.12),rgba(245,158,11,0.04));border:2px solid var(--yellow);}
.verdict-box.sell{background:linear-gradient(135deg,rgba(239,68,68,0.12),rgba(239,68,68,0.04));border:2px solid var(--red);}
.verdict-emoji{font-size:2.8rem;}
.verdict-text{font-family:'Space Mono',monospace;font-size:1.8rem;font-weight:700;margin:8px 0;}
.verdict-desc{color:var(--text2);font-size:0.9rem;line-height:1.6;}
.verdict-box.buy .verdict-text{color:var(--green);}
.verdict-box.hold .verdict-text{color:var(--yellow);}
.verdict-box.sell .verdict-text{color:var(--red);}
.info-table{width:100%;border-collapse:collapse;font-size:0.88rem;}
.info-table td{padding:8px 12px;border-bottom:1px solid var(--border);}
.info-table td:first-child{color:var(--text3);font-size:0.78rem;letter-spacing:1px;text-transform:uppercase;width:45%;}
.info-table td:last-child{font-family:'Space Mono',monospace;color:var(--text);font-weight:500;}
.info-table tr:last-child td{border-bottom:none;}
.src-badge{display:inline-block;background:rgba(0,212,255,0.1);border:1px solid rgba(0,212,255,0.3);border-radius:4px;padding:2px 8px;font-size:0.72rem;color:var(--accent);letter-spacing:1px;font-family:'Space Mono',monospace;margin-left:8px;vertical-align:middle;}
[data-testid="stSidebar"]{background:var(--bg2)!important;}
div[data-testid="stExpander"]{background:var(--bg2);border:1px solid var(--border);border-radius:10px;}
.streamlit-expanderHeader{color:var(--text2)!important;}
hr{border-color:var(--border)!important;}
.js-plotly-plot .plotly{background:transparent!important;}
.stSpinner>div{border-top-color:var(--accent)!important;}
</style>

“””, unsafe_allow_html=True)

# ══════════════════════════════════════════════════════════════════════════════

# SECTION 1 — 通用工具

# ══════════════════════════════════════════════════════════════════════════════

def safe_float(v, default=None):
try:
x = float(str(v).replace(”,”, “”).replace(”–”, “”).strip())
return x if not np.isnan(x) and not np.isinf(x) else default
except Exception:
return default

def detect_market(s: str) -> str:
s = s.upper().strip()
base = s.replace(”.TW”, “”).replace(”.TWO”, “”)
if s.endswith(”.TW”) or s.endswith(”.TWO”):
return “TW”
if base.isdigit():
return “TW”
if len(base) <= 6 and base[:4].isdigit():
return “TW”
return “US”

def tw_code(s: str) -> str:
return s.upper().replace(”.TW”, “”).replace(”.TWO”, “”).strip()

def roc_to_iso(roc: str) -> str:
try:
parts = str(roc).strip().split(”/”)
if len(parts) == 3:
return f”{int(parts[0])+1911}-{parts[1].zfill(2)}-{parts[2].zfill(2)}”
except Exception:
pass
return str(roc)

# ══════════════════════════════════════════════════════════════════════════════

# SECTION 2 — 台股網路層（Session + Retry + 限速 + Fallback）

# ══════════════════════════════════════════════════════════════════════════════

# ── 修正 1：用 @st.cache_resource 讓 Session 在所有 request 間共用，

# 不會每次都新建，等同「保持 Cookie / 連線池」 ──────────────────────

@st.cache_resource
def _build_tw_session() -> requests.Session:
“””
建立一個持久 Session：
- 固定 User-Agent、Referer、Accept 讓伺服器認為是瀏覽器
- 自動 Retry：遇到 429/500/502/503/504 最多重試 4 次
- 指數退避：1s -> 2s -> 4s -> 8s
“””
session = requests.Session()

```
# Retry 策略
retry = Retry(
    total=4,
    backoff_factor=1.0,           # 1, 2, 4, 8 秒
    status_forcelist=[429, 500, 502, 503, 504],
    allowed_methods=["GET", "POST"],
    raise_on_status=False,
)
adapter = HTTPAdapter(max_retries=retry)
session.mount("https://", adapter)
session.mount("http://",  adapter)

# 讓 TWSE 伺服器以為是 Chrome 瀏覽器
session.headers.update({
    "User-Agent": (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/124.0.0.0 Safari/537.36"
    ),
    "Accept": "application/json, text/javascript, */*; q=0.01",
    "Accept-Language": "zh-TW,zh;q=0.9,en;q=0.8,en-US;q=0.7",
    "Accept-Encoding": "gzip, deflate, br",
    "Connection": "keep-alive",
    "Cache-Control": "no-cache",
})

# ── 暖機：先造訪首頁讓 Session 取得 Cookie ────────────────────────────
try:
    session.get("https://www.twse.com.tw/zh/", timeout=10,
                headers={"Referer": "https://www.google.com/"})
    time.sleep(0.5)
except Exception:
    pass
return session
```

# ── 修正 2：限速器（Token Bucket）確保對 TWSE 每秒不超過 2 次請求 ────────────

class _RateLimiter:
def **init**(self, min_gap: float = 0.6):
self._last = 0.0
self._gap  = min_gap

```
def wait(self):
    now  = time.time()
    wait = self._gap - (now - self._last)
    if wait > 0:
        time.sleep(wait + random.uniform(0.05, 0.15))   # 加隨機抖動
    self._last = time.time()
```

_tw_rate = _RateLimiter(min_gap=0.7)

# ── 修正 3：tw_fetch 加 retry 邏輯 + 多種 Content-Type 解析 ─────────────────

@st.cache_data(ttl=300, show_spinner=False)
def tw_fetch(url: str, params_key: str = “”, method: str = “GET”,
post_data: str = “”) -> dict | list | None:
“””
params_key 是把 params dict 序列化成字串後傳入，因為 st.cache_data
要求參數可雜湊。呼叫端請用 tw_fetch(url, str(sorted(params.items())))
並把 params 另外傳到 _tw_fetch_inner。
“””
return _tw_fetch_inner(url, params_key, method, post_data)

def _tw_fetch_inner(url: str, params_key: str = “”,
method: str = “GET”, post_data: str = “”) -> dict | list | None:
import urllib.parse
session = _build_tw_session()
_tw_rate.wait()

```
# 從 params_key 還原 dict（格式："[('key','val'),...]"）
params = {}
if params_key:
    try:
        import ast
        params = dict(ast.literal_eval(params_key))
    except Exception:
        pass

referer_map = {
    "twse.com.tw":  "https://www.twse.com.tw/zh/",
    "tpex.org.tw":  "https://www.tpex.org.tw/web/",
    "mops.twse.com.tw": "https://mops.twse.com.tw/mops/web/",
    "openapi.twse.com.tw": "https://openapi.twse.com.tw/",
}
referer = next((v for k, v in referer_map.items() if k in url),
               "https://www.twse.com.tw/zh/")

headers = {"Referer": referer, "X-Requested-With": "XMLHttpRequest"}

for attempt in range(3):
    try:
        if method == "POST":
            r = session.post(url, data=post_data, headers=headers, timeout=20)
        else:
            r = session.get(url, params=params, headers=headers, timeout=20)

        if r.status_code == 429:
            wait_sec = 2 ** (attempt + 1) + random.uniform(0, 1)
            time.sleep(wait_sec)
            continue

        r.raise_for_status()

        ct = r.headers.get("Content-Type", "")
        text = r.text.strip()
        if "json" in ct or text.startswith(("{", "[")):
            return r.json()
        # TWSE sometimes returns text/html but body is JSON
        if text.startswith(("{", "[")):
            import json
            return json.loads(text)
        return None

    except requests.exceptions.Timeout:
        time.sleep(1.5 * (attempt + 1))
    except requests.exceptions.ConnectionError:
        time.sleep(2.0 * (attempt + 1))
    except Exception:
        break

return None
```

def _p(d: dict) -> str:
“”“Serialise params dict to cache-safe string.”””
return str(sorted(d.items()))

# ══════════════════════════════════════════════════════════════════════════════

# SECTION 3 — 台股資料函式（全部走 tw_fetch，內建 fallback）

# ══════════════════════════════════════════════════════════════════════════════

def tw_get_quote(code: str) -> dict:
“””
收盤行情。依序嘗試：
A) TWSE STOCK_DAY（個股當月每日行情）← 最穩定，直接給代號
B) TWSE MI_INDEX（大盤彙整表）
C) TPEX 上櫃
“””
# ── A: TWSE STOCK_DAY ────────────────────────────────────────────────────
for delta in range(0, 4):
d = datetime.now() - timedelta(days=30 * delta)
ym = d.strftime(”%Y%m01”)
data = tw_fetch(
“https://www.twse.com.tw/rwd/zh/afterTrading/STOCK_DAY”,
_p({“response”: “json”, “date”: ym, “stockNo”: code}))
if data and data.get(“stat”) == “OK”:
fields = data.get(“fields”, [])
rows   = data.get(“data”, [])
if not rows:
continue
last = rows[-1]
try:
ci = next(i for i, f in enumerate(fields) if “收盤” in f)
oi = next((i for i, f in enumerate(fields) if “開盤” in f), None)
hi = next((i for i, f in enumerate(fields) if “最高” in f), None)
li = next((i for i, f in enumerate(fields) if “最低” in f), None)
xi = next((i for i, f in enumerate(fields) if “漲跌” in f), None)
vi = next((i for i, f in enumerate(fields) if “成交股數” in f), None)
except StopIteration:
ci, oi, hi, li, xi, vi = 6, 3, 4, 5, 7, 1
close = safe_float(last[ci])
chg   = safe_float(last[xi]) if xi is not None else None
if close:
return {
“price”:      close,
“open”:       safe_float(last[oi]) if oi is not None else None,
“high”:       safe_float(last[hi]) if hi is not None else None,
“low”:        safe_float(last[li]) if li is not None else None,
“volume”:     safe_float(last[vi]) if vi is not None else None,
“change”:     chg,
“change_pct”: round(chg / (close - chg) * 100, 2)
if (chg and close and close - chg != 0) else None,
“date”:       roc_to_iso(last[0]),
“source”:     “TWSE STOCK_DAY”,
}

```
# ── B: TWSE MI_INDEX ─────────────────────────────────────────────────────
for delta in range(0, 5):
    d_str = (datetime.now() - timedelta(days=delta)).strftime("%Y%m%d")
    data = tw_fetch(
        "https://www.twse.com.tw/rwd/zh/afterTrading/MI_INDEX",
        _p({"response": "json", "date": d_str, "type": "ALLBUT0999"}))
    if not (data and data.get("stat") == "OK"):
        continue
    for tbl in data.get("tables", []):
        fields = tbl.get("fields", [])
        rows   = tbl.get("data", [])
        if not rows:
            continue
        try:
            code_idx  = next(i for i, f in enumerate(fields) if "代號" in f)
            close_idx = next(i for i, f in enumerate(fields) if "收盤" in f)
            name_idx  = next((i for i, f in enumerate(fields) if "名稱" in f), None)
            chg_idx   = next((i for i, f in enumerate(fields) if "漲跌價差" in f or "漲跌" in f), None)
        except StopIteration:
            continue
        for row in rows:
            if str(row[code_idx]).strip() == code:
                close = safe_float(row[close_idx])
                chg   = safe_float(row[chg_idx]) if chg_idx is not None else None
                if close:
                    return {
                        "price":      close,
                        "change":     chg,
                        "change_pct": round(chg / (close - chg) * 100, 2)
                                      if (chg and close - chg != 0) else None,
                        "name":       str(row[name_idx]).strip() if name_idx is not None else "",
                        "date":       d_str,
                        "source":     "TWSE MI_INDEX",
                    }

# ── C: TPEX 上櫃 ─────────────────────────────────────────────────────────
for delta in range(0, 5):
    d = datetime.now() - timedelta(days=delta)
    tpex_d = d.strftime("%Y/%m/%d")
    data = tw_fetch(
        "https://www.tpex.org.tw/web/stock/aftertrading/daily_trading_info/st43_result.php",
        _p({"l": "zh-tw", "d": tpex_d, "stkno": code, "o": "json"}))
    if data and data.get("iTotalRecords", 0) > 0:
        rows = data.get("aaData", [])
        if rows:
            last = rows[-1]
            close = safe_float(last[6])
            if close:
                return {
                    "price":  close,
                    "open":   safe_float(last[3]),
                    "high":   safe_float(last[4]),
                    "low":    safe_float(last[5]),
                    "change": safe_float(last[7]),
                    "source": "TPEX",
                }
return {}
```

def tw_get_valuation(code: str) -> dict:
“””
本益比 / 殖利率 / 股價淨值比。
A) TWSE BWIBBU_d（全市場彙整）
B) TPEX 上櫃本益比
“””
# ── A: TWSE BWIBBU_d ─────────────────────────────────────────────────────
data = tw_fetch(
“https://www.twse.com.tw/rwd/zh/afterTrading/BWIBBU_d”,
_p({“response”: “json”, “date”: “”, “selectType”: “ALL”}))
if data and data.get(“stat”) == “OK”:
fields = data.get(“fields”, [])
rows   = data.get(“data”, [])
try:
ci = next(i for i, f in enumerate(fields) if “代號” in f)
ni = next(i for i, f in enumerate(fields) if “名稱” in f)
yi = next(i for i, f in enumerate(fields) if “殖利率” in f)
pi = next(i for i, f in enumerate(fields) if “本益比” in f)
bi = next((i for i, f in enumerate(fields) if “淨值比” in f), None)
except StopIteration:
ci, ni, yi, pi, bi = 0, 1, 2, 4, 5
for row in rows:
if str(row[ci]).strip() == code:
return {
“name”:      str(row[ni]).strip(),
“pe”:        safe_float(row[pi]),
“pb”:        safe_float(row[bi]) if bi is not None else None,
“yield_pct”: safe_float(row[yi]),
“source”:    “TWSE BWIBBU_d”,
}

```
# ── B: TPEX ──────────────────────────────────────────────────────────────
tpex_d = datetime.now().strftime("%Y/%m/%d")
data2 = tw_fetch(
    "https://www.tpex.org.tw/web/stock/aftertrading/peratio_listed/peration_result.php",
    _p({"l": "zh-tw", "o": "json", "d": tpex_d, "c": code, "s": "0,asc"}))
if data2 and data2.get("iTotalRecords", 0) > 0:
    rows2 = data2.get("aaData", [])
    if rows2:
        r = rows2[0]
        return {
            "name":      str(r[1]).strip() if len(r) > 1 else "",
            "pe":        safe_float(r[4]) if len(r) > 4 else None,
            "pb":        safe_float(r[5]) if len(r) > 5 else None,
            "yield_pct": safe_float(r[2]) if len(r) > 2 else None,
            "source":    "TPEX",
        }
return {}
```

def tw_get_price_history(code: str, months: int = 12) -> list:
“””
每月行情。A) TWSE STOCK_DAY  B) TPEX
每月請求之間 sleep 0.8s（限速），避免被封。
“””
results = []
now     = datetime.now()

```
for i in range(months):
    d  = now - timedelta(days=30 * i)
    ym = d.strftime("%Y%m01")

    # ── A: TWSE ──────────────────────────────────────────────────────────
    data = tw_fetch(
        "https://www.twse.com.tw/rwd/zh/afterTrading/STOCK_DAY",
        _p({"response": "json", "date": ym, "stockNo": code}))
    if data and data.get("stat") == "OK":
        fields = data.get("fields", [])
        rows   = data.get("data", [])
        try:
            di = next(i2 for i2, f in enumerate(fields) if "日期" in f)
            ci = next(i2 for i2, f in enumerate(fields) if "收盤" in f)
            oi = next((i2 for i2, f in enumerate(fields) if "開盤" in f), None)
            hi = next((i2 for i2, f in enumerate(fields) if "最高" in f), None)
            li = next((i2 for i2, f in enumerate(fields) if "最低" in f), None)
            vi = next((i2 for i2, f in enumerate(fields) if "成交股數" in f), 1)
        except StopIteration:
            di, ci, oi, hi, li, vi = 0, 6, 3, 4, 5, 1
        for row in rows:
            try:
                close = safe_float(row[ci])
                if close:
                    results.append({
                        "date":   roc_to_iso(row[di]),
                        "close":  close,
                        "open":   safe_float(row[oi]) if oi is not None else None,
                        "high":   safe_float(row[hi]) if hi is not None else None,
                        "low":    safe_float(row[li]) if li is not None else None,
                        "volume": safe_float(row[vi]),
                    })
            except Exception:
                continue
        # 成功就不用跑 TPEX
        time.sleep(0.8 + random.uniform(0, 0.3))
        continue

    # ── B: TPEX fallback ─────────────────────────────────────────────────
    tpex_d = d.strftime("%Y/%m/01")
    data2  = tw_fetch(
        "https://www.tpex.org.tw/web/stock/aftertrading/daily_trading_info/st43_result.php",
        _p({"l": "zh-tw", "d": tpex_d, "stkno": code, "o": "json"}))
    if data2 and data2.get("iTotalRecords", 0) > 0:
        for row in data2.get("aaData", []):
            try:
                parts = str(row[0]).replace("/", "-").split("-")
                if len(parts) == 3 and len(parts[0]) <= 3:
                    iso = f"{int(parts[0])+1911}-{parts[1].zfill(2)}-{parts[2].zfill(2)}"
                else:
                    iso = str(row[0])
                c2 = safe_float(row[6])
                if c2:
                    results.append({
                        "date": iso, "close": c2,
                        "open": safe_float(row[3]), "high": safe_float(row[4]),
                        "low":  safe_float(row[5]), "volume": safe_float(row[1]),
                    })
            except Exception:
                continue
    time.sleep(0.8 + random.uniform(0, 0.3))

# 排序 + 去重
results.sort(key=lambda x: x["date"])
seen, unique = set(), []
for r in results:
    if r["date"] not in seen:
        seen.add(r["date"])
        unique.append(r)
return unique
```

def tw_get_dividends(code: str) -> list:
“””
歷史現金股利。
A) TWSE TWT49U（除權除息結果）
B) 殖利率 * 收盤價 估算（最後手段）
“””
divs = []
start = (datetime.now() - timedelta(days=365 * 7)).strftime(”%Y%m%d”)
end   = datetime.now().strftime(”%Y%m%d”)

```
# ── A: TWSE TWT49U ───────────────────────────────────────────────────────
data = tw_fetch(
    "https://www.twse.com.tw/rwd/zh/exRight/TWT49U",
    _p({"response": "json", "startDate": start, "endDate": end, "stockNo": code}))
if data and data.get("stat") == "OK":
    fields = data.get("fields", [])
    rows   = data.get("data", [])
    try:
        date_i = next(i for i, f in enumerate(fields) if "日期" in f or "除權" in f)
        cash_i = next(i for i, f in enumerate(fields) if "現金股利" in f or "現金" in f)
    except StopIteration:
        date_i, cash_i = 0, 5
    for row in rows:
        try:
            cash = safe_float(row[cash_i])
            if cash and cash > 0:
                divs.append({"date": roc_to_iso(row[date_i]), "dividend": cash})
        except Exception:
            continue

# ── B: 估算 ──────────────────────────────────────────────────────────────
if not divs:
    v = tw_get_valuation(code)
    q = tw_get_quote(code)
    y = v.get("yield_pct")
    p = q.get("price")
    if y and p and y > 0:
        divs.append({
            "date":     datetime.now().strftime("%Y-%m-%d"),
            "dividend": round(y / 100 * p, 2),
        })

divs.sort(key=lambda x: x["date"], reverse=True)
return divs
```

def tw_get_eps(code: str, quote: dict, valuation: dict) -> list:
“””
EPS 清單（由新到舊）。
A) MOPS 公開資訊觀測站（HTML POST，解析 EPS 數字）
B) PE 反推：close / PE
“””
import re
eps_list = []

```
# ── A: MOPS ──────────────────────────────────────────────────────────────
# 嘗試近 4 年的年度 EPS
for yr_offset in range(0, 4):
    roc_year = datetime.now().year - 1911 - yr_offset
    try:
        _tw_rate.wait()
        session = _build_tw_session()
        post_body = (
            f"encodeURIComponent=1&step=1&firstin=1&off=1&keyword4=&code1=&"
            f"TYPEK=sii&isnew=false&co_id={code}&"
            f"year={roc_year}&season=04"
        )
        r = session.post(
            "https://mops.twse.com.tw/mops/web/ajax_t05st09",
            data=post_body,
            headers={
                "Content-Type": "application/x-www-form-urlencoded",
                "Referer":      "https://mops.twse.com.tw/mops/web/t05st09",
                "X-Requested-With": "XMLHttpRequest",
            },
            timeout=20,
        )
        if r.status_code == 200 and ("每股盈餘" in r.text or "EPS" in r.text):
            text = r.text
            # 找含「基本每股盈餘」或「每股盈餘」的數字
            for pattern in [
                r"基本每股盈餘[^>]*>\s*([(\-]?\d[\d,\.]*)",
                r"每股盈餘[^>]*>\s*([(\-]?\d[\d,\.]*)",
                r"EPS[^>]*>\s*([(\-]?\d[\d,\.]*)",
            ]:
                matches = re.findall(pattern, text)
                for m in matches[:2]:
                    v2 = safe_float(m.replace("(", "-").replace(")", ""))
                    if v2 is not None and v2 != 0:
                        eps_list.append(v2)
                if eps_list:
                    break
        time.sleep(1.0)
    except Exception:
        pass
    if len(eps_list) >= 4:
        break

# ── B: PE 反推 ────────────────────────────────────────────────────────────
if not eps_list:
    pe    = valuation.get("pe")
    price = quote.get("price")
    if pe and pe > 0 and price:
        eps_list.append(round(price / pe, 2))

return eps_list
```

def tw_get_company_info(code: str) -> dict:
“””
公司基本資料。
A) TWSE openAPI STOCK_DAY_ALL
B) TWSE openAPI companyBasicInfo
“””
# ── A ────────────────────────────────────────────────────────────────────
data = tw_fetch(“https://openapi.twse.com.tw/v1/exchangeReport/STOCK_DAY_ALL”, “”)
if data and isinstance(data, list):
for row in data:
if str(row.get(“Code”, “”)).strip() == code:
return {
“name”:     row.get(“Name”, “”),
“industry”: row.get(“IndustryType”, “”),
}

```
# ── B ────────────────────────────────────────────────────────────────────
data2 = tw_fetch(
    "https://openapi.twse.com.tw/v1/company/companyBasicInfo",
    _p({"stockNo": code}))
if data2 and isinstance(data2, list) and data2:
    r = data2[0]
    return {
        "name":     r.get("公司名稱", r.get("CompanyName", "")),
        "industry": r.get("產業別", r.get("IndustryType", "")),
        "capital":  safe_float(r.get("實收資本額")),
    }
return {}
```

# ══════════════════════════════════════════════════════════════════════════════

# SECTION 4 — 美股 Finnhub

# ══════════════════════════════════════════════════════════════════════════════

@st.cache_data(ttl=300, show_spinner=False)
def fh_get(endpoint: str, params_key: str = “”):
import ast
params = {}
if params_key:
try:
params = dict(ast.literal_eval(params_key))
except Exception:
pass
params[“token”] = FINNHUB_KEY
try:
r = requests.get(f”https://finnhub.io/api/v1/{endpoint}”,
params=params, timeout=15)
r.raise_for_status()
return r.json()
except Exception:
return None

def _fp(d: dict) -> str:
return str(sorted(d.items()))

def fh_quote(sym):
d = fh_get(“quote”, _fp({“symbol”: sym}))
if d and safe_float(d.get(“c”)):
c, pc = safe_float(d[“c”]), safe_float(d.get(“pc”))
chg = round(c - pc, 2) if (c and pc) else None
return {“price”: c, “open”: safe_float(d.get(“o”)),
“high”:  safe_float(d.get(“h”)), “low”: safe_float(d.get(“l”)),
“prev_close”: pc, “change”: chg,
“change_pct”: round(chg / pc * 100, 2) if (chg and pc) else None}
return {}

def fh_profile(sym):
d = fh_get(“stock/profile2”, _fp({“symbol”: sym}))
return d if isinstance(d, dict) else {}

def fh_metrics(sym):
d = fh_get(“stock/metric”, _fp({“symbol”: sym, “metric”: “all”}))
return d.get(“metric”, {}) if isinstance(d, dict) else {}

def fh_dividends(sym):
end   = datetime.now().strftime(”%Y-%m-%d”)
start = (datetime.now() - timedelta(days=365*7)).strftime(”%Y-%m-%d”)
d = fh_get(“stock/dividend”, _fp({“symbol”: sym, “from”: start, “to”: end}))
return d if isinstance(d, list) else []

def fh_candles(sym, days=365):
et  = int(datetime.now().timestamp())
st2 = int((datetime.now() - timedelta(days=days)).timestamp())
d = fh_get(“stock/candle”, _fp({“symbol”: sym, “resolution”: “D”,
“from”: st2, “to”: et}))
if isinstance(d, dict) and d.get(“s”) == “ok”:
return [{“date”:   datetime.fromtimestamp(t).strftime(”%Y-%m-%d”),
“close”:  safe_float(d[“c”][i]),
“volume”: safe_float(d.get(“v”, [0]*len(d[“t”]))[i])}
for i, t in enumerate(d.get(“t”, []))]
return []

def fh_recommendation(sym):
d = fh_get(“stock/recommendation”, _fp({“symbol”: sym}))
return d if isinstance(d, list) else []

# ══════════════════════════════════════════════════════════════════════════════

# SECTION 5 — FMP 財報補充

# ══════════════════════════════════════════════════════════════════════════════

@st.cache_data(ttl=600, show_spinner=False)
def fmp_get(endpoint, params_key=””):
import ast
params = {“apikey”: FMP_KEY}
if params_key:
try:
params.update(dict(ast.literal_eval(params_key)))
except Exception:
pass
try:
r = requests.get(f”https://financialmodelingprep.com/api/v3/{endpoint}”,
params=params, timeout=15)
r.raise_for_status()
return r.json()
except Exception:
return None

def fmp_income(sym, limit=5):
d = fmp_get(f”income-statement/{sym}”, _fp({“limit”: limit}))
return d if isinstance(d, list) else []

def fmp_balance(sym, limit=5):
d = fmp_get(f”balance-sheet-statement/{sym}”, _fp({“limit”: limit}))
return d if isinstance(d, list) else []

def fmp_key_metrics(sym, limit=5):
d = fmp_get(f”key-metrics/{sym}”, _fp({“limit”: limit}))
return d if isinstance(d, list) else []

# ══════════════════════════════════════════════════════════════════════════════

# SECTION 6 — 估值模型

# ══════════════════════════════════════════════════════════════════════════════

def calc_dcf(eps_list, gr, dr, tg=0.03, years=10):
if not eps_list or gr is None:
return {}
base = safe_float(eps_list[0])
if not base or base <= 0:
return {}
pv_sum, proj = 0.0, []
for yr in range(1, years + 1):
g     = gr if yr <= 5 else gr * 0.5
eps_t = base * ((1 + g) ** yr)
pv    = eps_t / ((1 + dr) ** yr)
pv_sum += pv
proj.append({“year”: yr, “eps”: round(eps_t, 4), “pv”: round(pv, 4)})
final = base * ((1 + gr)**5) * ((1 + gr*0.5)**5)
dr2   = max(dr, tg + 0.01)
tv_pv = (final * (1 + tg) / (dr2 - tg)) / ((1 + dr2)**years)
return {“dcf_value”: round(pv_sum + tv_pv, 2), “pv_earnings”: round(pv_sum, 2),
“terminal_value_pv”: round(tv_pv, 2), “eps_projections”: proj}

def calc_ddm(div_list, gr, rr):
if not div_list:
return {}
recent = safe_float(
div_list[0].get(“dividend”) or div_list[0].get(“adjDividend”) or
div_list[0].get(“amount”) or 0)
if not recent or recent <= 0:
return {}
divs = [safe_float(d.get(“dividend”) or d.get(“adjDividend”) or
d.get(“amount”) or 0) for d in div_list[:5]]
divs = [x for x in divs if x and x > 0]
g = max(gr or 0.03, 0)
if len(divs) >= 2:
try:
g = float(np.clip((divs[0]/divs[-1])**(1/(len(divs)-1)) - 1, 0, 0.25))
except Exception:
pass
rr2 = max(rr, g + 0.01)
return {“ddm_value”: round(recent*(1+g)/(rr2-g), 2),
“recent_div”: recent, “div_growth”: round(g*100, 2),
“d1”: round(recent*(1+g), 4)}

def calc_pe_val(eps, pe_hist):
if not eps or eps <= 0 or not pe_hist:
return {}
valid = [x for x in pe_hist if x and 0 < x < 200]
if not valid:
return {}
used = np.median(valid)
return {“pe_value”: round(eps * used, 2), “pe_used”: round(used, 2)}

def estimate_growth(eps_series):
vals = [x for x in eps_series if x and x > 0]
if len(vals) < 2:
return None
try:
return float(np.clip((vals[0]/vals[-1])**(1/(len(vals)-1)) - 1, -0.3, 0.5))
except Exception:
return None

def capm_return(beta, rf=0.045):
return rf + safe_float(beta, 1.0) * 0.06

def exp_return_3yr(price, dcf, div_list):
if not dcf or not price or price <= 0:
return None
fv = dcf.get(“dcf_value”, 0)
if fv <= 0:
return None
dy = 0.0
if div_list:
d = safe_float(div_list[0].get(“dividend”) or div_list[0].get(“adjDividend”) or
div_list[0].get(“amount”) or 0)
if d:
dy = d / price
return round((fv/price)**(1/3) - 1 + dy, 4)

def score_stock(price, dcf_v, pe_v, ddm_v, div_y, roe, de, er, rr):
score, sigs = 50, []
targets = [v for v in [dcf_v, pe_v, ddm_v] if v and v > 0]
if targets and price and price > 0:
up = (np.mean(targets) - price) / price
if up > 0.30:
score += 20; sigs.append((“✅”, f”估值上漲空間 {up*100:.1f}%，顯著低估”, “green”))
elif up > 0.10:
score += 10; sigs.append((“✅”, f”估值上漲空間 {up*100:.1f}%，略微低估”, “green”))
elif up < -0.30:
score -= 20; sigs.append((“⚠️”, f”估值高估 {-up*100:.1f}%，建議觀望”, “red”))
elif up < -0.10:
score -= 10; sigs.append((“⚠️”, f”估值略高 {-up*100:.1f}%”, “yellow”))
else:
sigs.append((“➡️”, f”估值合理，偏差 {up*100:.1f}%”, “text2”))
if er is not None and rr is not None:
ex = er - rr
if ex > 0.03:
score += 15; sigs.append((“✅”, f”預期報酬 {er*100:.1f}% > 要求報酬 {rr*100:.1f}%”, “green”))
elif ex > 0:
score += 7;  sigs.append((“✅”, “預期報酬小幅超過要求報酬”, “green”))
else:
score -= 10; sigs.append((“⚠️”, f”預期報酬 {er*100:.1f}% 低於要求報酬 {rr*100:.1f}%”, “red”))
if div_y and div_y > 0:
if div_y > 0.06:
score += 10; sigs.append((“💰”, f”殖利率 {div_y*100:.2f}%，高股息”, “green”))
elif div_y > 0.03:
score += 5;  sigs.append((“💰”, f”殖利率 {div_y*100:.2f}%，穩定配息”, “green”))
else:
sigs.append((“💰”, f”殖利率 {div_y*100:.2f}%，偏低”, “yellow”))
if roe is not None:
if roe > 0.20:
score += 10; sigs.append((“📊”, f”ROE {roe*100:.1f}%，優秀獲利能力”, “green”))
elif roe > 0.10:
score += 5;  sigs.append((“📊”, f”ROE {roe*100:.1f}%，良好”, “green”))
elif roe < 0:
score -= 15; sigs.append((“⚠️”, f”ROE {roe*100:.1f}%，目前虧損”, “red”))
else:
sigs.append((“📊”, f”ROE {roe*100:.1f}%，普通”, “yellow”))
if de is not None:
if de < 0.5:
score += 5;  sigs.append((“🏦”, f”負債/權益 {de:.2f}，財務穩健”, “green”))
elif de > 2.0:
score -= 10; sigs.append((“⚠️”, f”負債/權益 {de:.2f}，槓桿較高”, “red”))
else:
sigs.append((“🏦”, f”負債/權益 {de:.2f}，適中”, “yellow”))
return max(0, min(100, score)), sigs

def verdict(score):
if score >= 70:
return “buy”,  “🚀”, “建議買入”,  “估值吸引、預期報酬優於要求報酬，具備投資價值”
elif score >= 45:
return “hold”, “⚖️”, “持有觀察”,  “現值合理，建議持有或等待更佳進場點”
else:
return “sell”, “🔻”, “謹慎看待”,  “高估或獲利能力不足，建議審慎評估”

# ══════════════════════════════════════════════════════════════════════════════

# SECTION 7 — 圖表

# ══════════════════════════════════════════════════════════════════════════════

CL = dict(
paper_bgcolor=“rgba(0,0,0,0)”, plot_bgcolor=“rgba(0,0,0,0)”,
font=dict(color=”#94a3b8”, family=“Space Mono, monospace”, size=11),
margin=dict(l=10, r=10, t=40, b=10),
xaxis=dict(showgrid=False, zeroline=False, color=”#64748b”),
yaxis=dict(showgrid=True,  zeroline=False, color=”#64748b”,
gridcolor=“rgba(42,53,80,0.6)”),
)

def chart_price(history, label):
if not history:
return None
df = pd.DataFrame(history).sort_values(“date”)
has_ohlc = all(c in df.columns and df[c].notna().any()
for c in [“open”, “high”, “low”])
if has_ohlc:
fig = go.Figure(go.Candlestick(
x=df[“date”], open=df[“open”], high=df[“high”],
low=df[“low”],  close=df[“close”],
increasing_line_color=”#10b981”, decreasing_line_color=”#ef4444”,
name=“K線”))
else:
fig = go.Figure(go.Scatter(
x=df[“date”], y=df[“close”], mode=“lines”,
line=dict(color=”#00d4ff”, width=2),
fill=“tozeroy”, fillcolor=“rgba(0,212,255,0.06)”, name=“收盤”))
fig.update_layout(**CL, title=dict(text=f”{label} 股價走勢 (1年)”, x=0.0,
font=dict(size=13, color=”#e2e8f0”)))
return fig

def chart_eps_bar(vals, labels, label):
if not vals:
return None
colors = [”#10b981” if v >= 0 else “#ef4444” for v in vals]
fig = go.Figure(go.Bar(x=labels, y=vals, marker_color=colors, name=“EPS”,
text=[f”{v:.2f}” for v in vals],
textposition=“outside”, textfont=dict(color=”#e2e8f0”)))
fig.update_layout(**CL, title=dict(text=f”{label} 每股盈餘 EPS”, x=0.0,
font=dict(size=13, color=”#e2e8f0”)))
return fig

def chart_rev_profit(income):
if not income:
return None
rows = [{“date”:    x.get(“date”,””),
“revenue”: safe_float(x.get(“revenue”), 0) or 0,
“net”:     safe_float(x.get(“netIncome”), 0) or 0}
for x in income[::-1]]
df  = pd.DataFrame(rows)
fig = make_subplots(specs=[[{“secondary_y”: True}]])
fig.add_trace(go.Bar(x=df[“date”], y=df[“revenue”],
name=“營收”, marker_color=”#7c3aed”, opacity=0.8))
fig.add_trace(go.Scatter(x=df[“date”], y=df[“net”], name=“淨利”,
line=dict(color=”#00d4ff”, width=2),
mode=“lines+markers”), secondary_y=True)
fig.update_layout(**CL, title=dict(text=“營收 vs 淨利”, x=0.0,
font=dict(size=13, color=”#e2e8f0”)),
legend=dict(orientation=“h”, y=1.1, bgcolor=“rgba(0,0,0,0)”))
return fig

def chart_div(div_list):
if not div_list:
return None
rows = [{“date”: d.get(“date”,””),
“div”:  safe_float(d.get(“dividend”) or d.get(“adjDividend”) or
d.get(“amount”) or 0)}
for d in div_list[:20][::-1]]
df = pd.DataFrame(rows)
df = df[df[“div”] > 0]
if df.empty:
return None
fig = go.Figure(go.Bar(x=df[“date”], y=df[“div”], marker_color=”#f59e0b”,
name=“現金股利”,
text=[f”{v:.2f}” for v in df[“div”]],
textposition=“outside”, textfont=dict(color=”#e2e8f0”)))
fig.update_layout(**CL, title=dict(text=“歷史現金股利”, x=0.0,
font=dict(size=13, color=”#e2e8f0”)))
return fig

def chart_dcf_proj(dcf, label):
if not dcf or “eps_projections” not in dcf:
return None
proj = dcf[“eps_projections”]
fig  = go.Figure(go.Scatter(
x=[p[“year”] for p in proj], y=[p[“eps”] for p in proj],
mode=“lines+markers”,
line=dict(color=”#10b981”, width=2), marker=dict(size=7), name=“預測EPS”))
fig.update_layout(**CL, title=dict(text=“EPS 10年預測 (DCF)”, x=0.0,
font=dict(size=13, color=”#e2e8f0”)),
xaxis_title=“年”, yaxis_title=“EPS”)
return fig

def chart_val_compare(price, dcf_v, pe_v, ddm_v):
labels, values, colors = [], [], []
if price:  labels.append(“現價”);    values.append(price);  colors.append(”#94a3b8”)
if dcf_v:  labels.append(“DCF估值”); values.append(dcf_v); colors.append(”#00d4ff”)
if pe_v:   labels.append(“P/E估值”); values.append(pe_v);  colors.append(”#7c3aed”)
if ddm_v:  labels.append(“DDM估值”); values.append(ddm_v); colors.append(”#f59e0b”)
if len(labels) < 2:
return None
fig = go.Figure(go.Bar(x=labels, y=values, marker_color=colors,
text=[f”{v:.2f}” for v in values],
textposition=“outside”, textfont=dict(color=”#e2e8f0”)))
fig.update_layout(**CL, title=dict(text=“估值方法比較”, x=0.0,
font=dict(size=13, color=”#e2e8f0”)))
return fig

def chart_rec(rec_list):
if not rec_list:
return None
lt     = rec_list[0]
cats   = [“strongBuy”,“buy”,“hold”,“sell”,“strongSell”]
labels = [“強烈買入”,“買入”,“持有”,“賣出”,“強烈賣出”]
vals   = [lt.get(c, 0) for c in cats]
cols   = [”#10b981”,”#34d399”,”#f59e0b”,”#f87171”,”#ef4444”]
fig = go.Figure(go.Bar(x=labels, y=vals, marker_color=cols,
text=vals, textposition=“outside”,
textfont=dict(color=”#e2e8f0”)))
fig.update_layout(**CL, title=dict(text=f”分析師評級 ({lt.get(‘period’,’’)})”,
x=0.0, font=dict(size=13, color=”#e2e8f0”)))
return fig

# ══════════════════════════════════════════════════════════════════════════════

# SECTION 8 — UI 小工具

# ══════════════════════════════════════════════════════════════════════════════

BG = {“green”: “rgba(16,185,129,0.08)”, “red”:   “rgba(239,68,68,0.08)”,
“yellow”:“rgba(245,158,11,0.08)”, “text2”: “rgba(148,163,184,0.06)”}
BD = {“green”: “rgba(16,185,129,0.4)”,  “red”:   “rgba(239,68,68,0.4)”,
“yellow”:“rgba(245,158,11,0.4)”,  “text2”: “rgba(148,163,184,0.2)”}

def mc(col, label, value, sub=””, css=””):
with col:
st.markdown(
f’<div class="metric-card {css}">’
f’<div class="metric-label">{label}</div>’
f’<div class="metric-value">{value}</div>’
f’{”<div class=metric-sub>”+sub+”</div>” if sub else “”}’
f’</div>’, unsafe_allow_html=True)

def val_card(col, title, data, vk, hex_color, eps_list, gr, rr, price):
with col:
v    = data.get(vk) if data else None
diff = (v - price) / price * 100 if (v and price and price > 0) else None
uc   = “#10b981” if (diff and diff > 0) else “#ef4444”
dstr = (f’<div style="color:{uc};font-size:0.9rem;margin-top:4px;">’
f’{“▲” if diff>0 else “▼”} {abs(diff):.1f}%’
f’ {“低估” if diff>0 else “高估”}</div>’) if diff is not None else “”
body = (f’<div style="font-family:Space Mono,monospace;font-size:1.8rem;'
f'font-weight:700;color:#e2e8f0;">{v:.2f}</div>{dstr}’
if v else ‘<div style="color:#64748b;">資料不足</div>’)
if data and vk == “dcf_value”:
extra = (f’<div style="color:#64748b;font-size:0.78rem;margin-top:8px;">’
f’成長率 {gr*100:.1f}% | 折現率 {rr*100:.1f}%<br>’
f’盈餘現值 {data.get(“pv_earnings”,0):.2f} | ’
f’終值PV {data.get(“terminal_value_pv”,0):.2f}</div>’)
elif data and vk == “pe_value”:
extra = (f’<div style="color:#64748b;font-size:0.78rem;margin-top:8px;">’
f’使用 P/E {data.get(“pe_used”,0):.1f}x | ’
f’EPS {eps_list[0]:.2f}</div>’) if eps_list else “”
elif data and vk == “ddm_value”:
extra = (f’<div style="color:#64748b;font-size:0.78rem;margin-top:8px;">’
f’近期股息 {data.get(“recent_div”,0):.4f} | ’
f’股息成長 {data.get(“div_growth”,0):.2f}%</div>’)
else:
extra = “”
st.markdown(
f’<div style="background:var(--bg2);border:1px solid var(--border);'
f'border-radius:12px;padding:20px;">’
f’<div style="font-family:Space Mono,monospace;font-size:0.75rem;'
f'letter-spacing:2px;color:{hex_color};margin-bottom:12px;">{title}</div>’
f’{body}{extra}</div>’, unsafe_allow_html=True)

# ══════════════════════════════════════════════════════════════════════════════

# SECTION 9 — 主 UI

# ══════════════════════════════════════════════════════════════════════════════

st.markdown(”””

<div class="hero-header">
  <div class="hero-title">📈 股票估值分析儀</div>
  <div class="hero-sub">
    台股 TWSE/TPEX 官方資料（Session + Retry）&nbsp;·&nbsp;
    美股 Finnhub&nbsp;·&nbsp;DCF · DDM · P/E · Expected Return
  </div>
</div>""", unsafe_allow_html=True)

col_in, col_btn = st.columns([4, 1])
with col_in:
symbol_input = st.text_input(
“”, placeholder=“台股：2330、2317、0050、00878 | 美股：AAPL、NVDA、TSLA”,
label_visibility=“collapsed”, key=“sym”)
with col_btn:
run = st.button(“🔍 分析”, use_container_width=True)

with st.sidebar:
st.markdown(”### ⚙️ 模型參數”)
risk_free     = st.slider(“無風險利率 (%)”, 2.0, 8.0, 4.5, 0.1) / 100
terminal_g    = st.slider(“永續成長率 (%)”, 1.0, 5.0, 3.0, 0.1) / 100
manual_growth = st.slider(“手動成長率 (%)”, -10.0, 40.0, 0.0, 0.5)
use_manual    = st.checkbox(“啟用手動成長率”, value=False)
st.markdown(”—”)
st.markdown(”**台股資料來源（官方）**”)
st.markdown(”- TWSE `STOCK_DAY` 月行情”)
st.markdown(”- TWSE `BWIBBU_d` 本益比/殖利率”)
st.markdown(”- TWSE `TWT49U` 除權除息”)
st.markdown(”- TPEX 上櫃行情（自動 fallback）”)
st.markdown(”- MOPS 公開資訊觀測站（EPS）”)
st.markdown(”- FMP 財報補充”)
st.markdown(”—”)
st.markdown(”**美股資料來源**”)
st.markdown(”- Finnhub API”)
st.markdown(”- FMP API 財報補充”)

if not run or not symbol_input.strip():
st.markdown(”””
<div style="text-align:center;padding:60px 20px;color:var(--text3);">
<div style="font-size:3rem;margin-bottom:16px;">🔭</div>
<div style="font-size:1.1rem;color:var(--text2);">輸入股票代號後按「分析」</div>
<div style="margin-top:12px;font-size:0.85rem;line-height:2.0;">
台股：2330 台積電 ｜ 2317 鴻海 ｜ 0050 元大50 ｜ 00878 國泰高股息<br>
美股：AAPL ｜ TSLA ｜ NVDA ｜ MSFT
</div>
</div>”””, unsafe_allow_html=True)
st.stop()

# ── 偵測市場 & 開始抓資料 ─────────────────────────────────────────────────────

raw  = symbol_input.strip()
mkt  = detect_market(raw)
code = tw_code(raw) if mkt == “TW” else raw.upper()
pb   = st.progress(0, text=“正在初始化連線…”)

# ════════════ 台股 ════════════════════════════════════════════════════════════

if mkt == “TW”:
pb.progress(5,  “台股 — 建立 Session（暖機）…”)
_build_tw_session()           # 確保已暖機

```
pb.progress(12, "TWSE — 收盤行情...")
tw_q = tw_get_quote(code)

pb.progress(24, "TWSE — 本益比 / 殖利率...")
tw_v = tw_get_valuation(code)

pb.progress(34, "TWSE — 公司基本資料...")
tw_c = tw_get_company_info(code)

pb.progress(44, "TWSE — 月 K 線 (12個月)...")
price_hist = tw_get_price_history(code, months=12)

pb.progress(58, "TWSE — 股息歷史...")
dividends = tw_get_dividends(code)

pb.progress(66, "MOPS — EPS...")
tw_eps = tw_get_eps(code, tw_q, tw_v)

pb.progress(75, "FMP — 財報補充...")
income   = fmp_income(code + ".TW")
balance  = fmp_balance(code + ".TW")
km       = fmp_key_metrics(code + ".TW")

pb.progress(88, "計算估值模型...")

# 彙整
price        = tw_q.get("price")
company_name = tw_c.get("name") or tw_v.get("name") or tw_q.get("name") or code
industry     = tw_c.get("industry", "")
sector       = industry
pe           = tw_v.get("pe")
pb_ratio     = tw_v.get("pb")
yield_pct    = tw_v.get("yield_pct")
div_yield    = yield_pct / 100 if (yield_pct and yield_pct > 0) else None
currency     = "TWD"
mkt_cap      = None
beta         = None
roe          = safe_float(km[0].get("roe")) if km else None
de_ratio     = safe_float(km[0].get("debtToEquity")) if km else None
eps_fmp      = [safe_float(x.get("eps")) for x in income
                if safe_float(x.get("eps")) is not None]
eps_list     = eps_fmp if eps_fmp else tw_eps
pe_hist      = [safe_float(x.get("peRatio")) for x in km
                if safe_float(x.get("peRatio"))]
rec_list     = []
fh_m         = {}
fh_q         = {}
fh_prof      = {}
data_src     = tw_v.get("source", "TWSE")
```

# ════════════ 美股 ════════════════════════════════════════════════════════════

else:
pb.progress(10, “Finnhub — 即時行情…”)
fh_q    = fh_quote(code)
pb.progress(20, “Finnhub — 公司資料…”)
fh_prof = fh_profile(code)
pb.progress(30, “Finnhub — 財務指標…”)
fh_m    = fh_metrics(code)
pb.progress(42, “Finnhub — 股息…”)
dividends = fh_dividends(code)
pb.progress(52, “Finnhub — 股價歷史…”)
price_hist = fh_candles(code, 365)
pb.progress(63, “Finnhub — 分析師評級…”)
rec_list = fh_recommendation(code)
pb.progress(72, “FMP — 財報…”)
income   = fmp_income(code)
balance  = fmp_balance(code)
km       = fmp_key_metrics(code)
pb.progress(84, “計算估值模型…”)

```
price        = fh_q.get("price")
company_name = fh_prof.get("name") or code
sector       = fh_prof.get("finnhubIndustry", "")
industry     = ""
pe           = safe_float(fh_m.get("peBasicExclExtraTTM") or fh_m.get("peTTM"))
pb_ratio     = safe_float(fh_m.get("pbAnnual"))
mkt_cap_m    = safe_float(fh_prof.get("marketCapitalization"))
mkt_cap      = mkt_cap_m * 1e6 if mkt_cap_m else None
currency     = fh_prof.get("currency", "USD")
beta         = safe_float(fh_m.get("beta"))
roe          = safe_float(fh_m.get("roeTTM") or (km[0].get("roe") if km else None))
de_ratio     = safe_float(fh_m.get("totalDebt/totalEquityAnnual") or
                           (km[0].get("debtToEquity") if km else None))
yield_pct    = None
div_yield    = None
tw_q  = tw_v = tw_c = {}
if dividends and price and price > 0:
    yr_start = (datetime.now() - timedelta(days=365)).strftime("%Y-%m-%d")
    yr_sum   = sum(safe_float(d.get("amount") or 0)
                   for d in dividends if d.get("date","") >= yr_start)
    if yr_sum > 0:
        div_yield = yr_sum / price
eps_list = [safe_float(x.get("eps")) for x in income
            if safe_float(x.get("eps")) is not None]
pe_hist  = [safe_float(x.get("peRatio")) for x in km
            if safe_float(x.get("peRatio"))]
data_src = "Finnhub"
```

# ── 估值計算 ──────────────────────────────────────────────────────────────────

gr = (manual_growth / 100) if (use_manual and manual_growth != 0) else None
if gr is None:
gr = estimate_growth(eps_list)
if gr is None:
gr = safe_float(fh_m.get(“epsGrowthTTMYoy”)) if fh_m else None
if gr is None:
gr = 0.08

rr    = capm_return(beta, risk_free)
dcf   = calc_dcf(eps_list, gr, rr, terminal_g)
ddm   = calc_ddm(dividends, gr, rr)
pev_d = calc_pe_val(eps_list[0] if eps_list else None,
pe_hist if pe_hist else ([pe] if pe else []))
er    = exp_return_3yr(price or 0, dcf, dividends)
score, sigs = score_stock(price, dcf.get(“dcf_value”), pev_d.get(“pe_value”),
ddm.get(“ddm_value”), div_yield, roe, de_ratio, er, rr)
vtype, vemoji, vlabel, vdesc = verdict(score)

pb.progress(100, “完成！”)
time.sleep(0.15)
pb.empty()

# ── 資料確認 ──────────────────────────────────────────────────────────────────

if not price and not income:
st.error(
f”❌ 找不到「{raw}」的資料。\n\n”
“- 台股請輸入純數字代號，例如 **2330**、**0050**\n”
“- 美股請輸入英文代號，例如 **AAPL**、**TSLA**”)
st.stop()

# ══════════════════════════════════════════════════════════════════════════════

# SECTION 10 — 渲染

# ══════════════════════════════════════════════════════════════════════════════

chg_src   = tw_q if mkt == “TW” else fh_q
chg       = chg_src.get(“change”)
chg_pc    = chg_src.get(“change_pct”)
chg_color = “#10b981” if (chg is not None and chg >= 0) else “#ef4444”
chg_html  = (f’<span style="color:{chg_color};font-family:Space Mono,monospace;font-size:0.9rem;">’
f’{“▲” if chg >= 0 else “▼”} {abs(chg):.2f} ({abs(chg_pc):.2f}%)</span>’
if (chg is not None and chg_pc is not None) else “”)

st.markdown(
f’<div style="display:flex;align-items:baseline;flex-wrap:wrap;gap:12px;margin-bottom:6px;">’
f’<span style="font-family:Space Mono,monospace;font-size:1.5rem;font-weight:700;'
f'color:#e2e8f0;">{company_name}</span>’
f’<span style="color:#64748b;font-size:0.85rem;">{code} · {currency} · ’
f’{“🇹🇼 台股” if mkt==“TW” else “🇺🇸 美股”}’
f’{(” · “+sector) if sector else “”}</span>’
f’{chg_html}’
f’<span class="src-badge">{data_src}</span>’
f’</div>’, unsafe_allow_html=True)

# 1. Verdict + signals

c1, c2 = st.columns([2, 3])
with c1:
sc = “#10b981” if vtype==“buy” else “#f59e0b” if vtype==“hold” else “#ef4444”
st.markdown(
f’<div class="verdict-box {vtype}">’
f’<div class="verdict-emoji">{vemoji}</div>’
f’<div class="verdict-text">{vlabel}</div>’
f’<div class="verdict-desc">{vdesc}</div>’
f’<div style="margin-top:16px;font-family:Space Mono,monospace;font-size:2rem;'
f'font-weight:700;color:{sc};">{score} / 100</div>’
f’<div style="color:var(--text3);font-size:0.75rem;">綜合評分</div>’
f’</div>’, unsafe_allow_html=True)
with c2:
st.markdown(’<div class="section-header">訊號分析</div>’, unsafe_allow_html=True)
for icon, msg, color in sigs:
st.markdown(
f’<div style="background:{BG[color]};border:1px solid {BD[color]};'
f'border-radius:8px;padding:10px 14px;margin:5px 0;font-size:0.86rem;'
f'color:var(--text);">{icon} {msg}</div>’, unsafe_allow_html=True)

# 2. Core metrics

st.markdown(’<div class="section-header">核心指標</div>’, unsafe_allow_html=True)
m1,m2,m3,m4,m5,m6 = st.columns(6)
mc(m1, “現價”,       f”{price:.2f}” if price else “N/A”, currency)
mc(m2, “市值”,       f”{mkt_cap/1e9:.2f}B” if mkt_cap else “N/A”, currency, “purple”)
mc(m3, “本益比 P/E”, f”{pe:.1f}x” if pe else “N/A”)
mc(m4, “EPS”,        f”{eps_list[0]:.2f}” if eps_list else “N/A”, “最新”,
“green” if (eps_list and eps_list[0] > 0) else “red”)
mc(m5, “殖利率”,
f”{div_yield*100:.2f}%” if (div_yield and div_yield > 0) else “無配息”, “”,
“yellow” if (div_yield and div_yield > 0) else “”)
mc(m6, “Beta”, f”{beta:.2f}” if beta else “N/A”, “市場波動”)

# 3. Valuation cards

st.markdown(’<div class="section-header">估值模型</div>’, unsafe_allow_html=True)
vc1, vc2, vc3 = st.columns(3)
val_card(vc1, “DCF  現金流折現”,   dcf,   “dcf_value”, “#00d4ff”, eps_list, gr, rr, price or 0)
val_card(vc2, “P/E  本益比估值”,   pev_d, “pe_value”,  “#7c3aed”, eps_list, gr, rr, price or 0)
val_card(vc3, “DDM  股利折現模型”, ddm,   “ddm_value”, “#f59e0b”, eps_list, gr, rr, price or 0)

# 4. Return analysis

st.markdown(’<div class="section-header">報酬率分析</div>’, unsafe_allow_html=True)
r1,r2,r3,r4 = st.columns(4)
mc(r1, “預期報酬率”, f”{er*100:.2f}%” if er else “N/A”, “3年持有估算”,
“green” if (er and er > rr) else “red”)
mc(r2, “要求報酬率”, f”{rr*100:.2f}%”,
f”CAPM (beta={beta:.2f})” if beta else “CAPM (beta=1.0)”, “purple”)
mc(r3, “歷史成長率”, f”{gr*100:.2f}%”, “EPS CAGR”)
mc(r4, “超額報酬”,   f”{(er-rr)*100:.2f}%” if er else “N/A”, “預期 - 要求”,
“green” if (er and er > rr) else “red”)

# 5. Charts

st.markdown(’<div class="section-header">圖表分析</div>’, unsafe_allow_html=True)
t1,t2,t3,t4,t5,t6 = st.tabs(
[“📈 股價K線”, “💹 估值比較”, “📊 EPS”, “🏭 營收獲利”, “💰 股息”, “🎯 DCF預測”])

with t1:
fig = chart_price(price_hist, f”{company_name} ({code})”)
st.plotly_chart(fig, use_container_width=True) if fig else st.info(“股價歷史資料無法取得”)

with t2:
fig = chart_val_compare(price, dcf.get(“dcf_value”),
pev_d.get(“pe_value”), ddm.get(“ddm_value”))
st.plotly_chart(fig, use_container_width=True) if fig else st.info(“估值資料不足”)
if rec_list:
fig2 = chart_rec(rec_list)
if fig2:
st.plotly_chart(fig2, use_container_width=True)

with t3:
eps_vals   = [safe_float(x.get(“eps”), 0) for x in income[::-1]] if income else []
eps_labels = [x.get(“date”,””) for x in income[::-1]] if income else []
if not eps_vals and eps_list:
n = len(eps_list)
eps_vals   = list(reversed(eps_list))
eps_labels = [f”Y-{n-1-i}” for i in range(n)]
fig = chart_eps_bar(eps_vals, eps_labels, company_name)
st.plotly_chart(fig, use_container_width=True) if fig else st.info(“EPS 資料不足”)

with t4:
fig = chart_rev_profit(income)
st.plotly_chart(fig, use_container_width=True) if fig else st.info(“財報資料不足”)

with t5:
if dividends:
fig = chart_div(dividends)
if fig:
st.plotly_chart(fig, use_container_width=True)
div_rows = [{“日期”: d.get(“date”,””),
f”現金股利 ({currency})”: round(
safe_float(d.get(“dividend”) or d.get(“adjDividend”) or
d.get(“amount”) or 0), 4)}
for d in dividends[:15]]
if div_rows:
st.dataframe(pd.DataFrame(div_rows), use_container_width=True, hide_index=True)
else:
st.info(“此股票無股息資料（成長型或尚未配息）”)

with t6:
fig = chart_dcf_proj(dcf, company_name)
st.plotly_chart(fig, use_container_width=True) if fig else st.info(“EPS 資料不足，無法預測”)

# 6. 詳細財務

with st.expander(“📄 詳細財務數據 (FMP)”):
if income:
st.markdown(”**損益表**”)
st.dataframe(pd.DataFrame([{
“年度”:   x.get(“date”,””),
“營收”:   f”{safe_float(x.get(‘revenue’),0)/1e6:.1f}M”
if safe_float(x.get(‘revenue’)) else “N/A”,
“毛利率”: f”{safe_float(x.get(‘grossProfitRatio’),0)*100:.1f}%”
if safe_float(x.get(‘grossProfitRatio’)) else “N/A”,
“淨利率”: f”{safe_float(x.get(‘netIncomeRatio’),0)*100:.1f}%”
if safe_float(x.get(‘netIncomeRatio’)) else “N/A”,
“EPS”:    f”{safe_float(x.get(‘eps’),0):.2f}”
if safe_float(x.get(‘eps’)) is not None else “N/A”,
} for x in income]), use_container_width=True, hide_index=True)
if balance:
st.markdown(”**資產負債表**”)
st.dataframe(pd.DataFrame([{
“年度”:   x.get(“date”,””),
“總資產”: f”{safe_float(x.get(‘totalAssets’),0)/1e6:.1f}M”
if safe_float(x.get(‘totalAssets’)) else “N/A”,
“總負債”: f”{safe_float(x.get(‘totalLiabilities’),0)/1e6:.1f}M”
if safe_float(x.get(‘totalLiabilities’)) else “N/A”,
“股東權益”: f”{safe_float(x.get(‘totalStockholdersEquity’),0)/1e6:.1f}M”
if safe_float(x.get(‘totalStockholdersEquity’)) else “N/A”,
} for x in balance]), use_container_width=True, hide_index=True)
if not income and not balance:
st.info(“FMP 財報暫無資料”)

# 7. 公司資料

with st.expander(“🏢 公司資料”):
if mkt == “TW”:
items = [
(“市場”,     “台灣證券交易所 / 台灣櫃買中心”),
(“代號”,     code),
(“產業別”,   industry or “N/A”),
(“貨幣”,     “TWD”),
(“資料日期”, tw_q.get(“date”, datetime.now().strftime(”%Y-%m-%d”))),
(“本益比”,   f”{pe:.2f}x” if pe else “N/A”),
(“股價淨值比”, f”{pb_ratio:.2f}x” if pb_ratio else “N/A”),
(“殖利率”,   f”{yield_pct:.2f}%” if yield_pct else “N/A”),
(“開盤”,     f”{tw_q.get(‘open’):.2f}” if tw_q.get(“open”) else “N/A”),
(“最高”,     f”{tw_q.get(‘high’):.2f}” if tw_q.get(“high”) else “N/A”),
(“最低”,     f”{tw_q.get(‘low’):.2f}” if tw_q.get(“low”) else “N/A”),
(“ROE”,      f”{roe*100:.2f}%” if roe else “N/A”),
(“負債/權益”, f”{de_ratio:.2f}” if de_ratio else “N/A”),
(“資料來源”, data_src),
]
else:
items = [
(“交易所”,   fh_prof.get(“exchange”, “N/A”)),
(“產業”,     fh_prof.get(“finnhubIndustry”, “N/A”)),
(“國家”,     fh_prof.get(“country”, “N/A”)),
(“貨幣”,     currency),
(“IPO日期”,  fh_prof.get(“ipo”, “N/A”)),
(“52週高”,   f”{safe_float(fh_m.get(‘52WeekHigh’)):.2f}”
if safe_float(fh_m.get(‘52WeekHigh’)) else “N/A”),
(“52週低”,   f”{safe_float(fh_m.get(‘52WeekLow’)):.2f}”
if safe_float(fh_m.get(‘52WeekLow’)) else “N/A”),
(“Beta”,     f”{beta:.2f}” if beta else “N/A”),
(“ROE”,      f”{roe*100:.2f}%” if roe else “N/A”),
(“負債/權益”, f”{de_ratio:.2f}” if de_ratio else “N/A”),
(“網站”,     fh_prof.get(“weburl”, “N/A”)),
]
st.markdown(
‘<table class="info-table">’
+ “”.join(f”<tr><td>{k}</td><td>{v}</td></tr>” for k, v in items)
+ “</table>”, unsafe_allow_html=True)

st.markdown(”””

<div style="margin-top:32px;padding:16px;border-top:1px solid var(--border);
     color:#475569;font-size:0.78rem;text-align:center;">
  ⚠️ 本工具僅供學術研究與個人參考，不構成任何投資建議。<br>
  台股資料來自台灣證交所 (twse.com.tw) / 櫃買中心 (tpex.org.tw) 官方公開資料。<br>
  所有估值模型均基於歷史數據推算，投資前請自行評估風險。
</div>""", unsafe_allow_html=True)

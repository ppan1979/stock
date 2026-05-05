"""
股票估值分析儀
- 台股：直接爬台灣證券交易所 / 櫃買中心官方網站 JSON (無需 API key)
- 美股：Finnhub API
- 財報補充：FMP API
"""
import streamlit as st
import requests
import pandas as pd
import numpy as np
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from datetime import datetime, timedelta
import time

# ── API Keys (美股 / 財報用) ──────────────────────────────────────────────────
FINNHUB_KEY = "d7s8j19r01qm28g8miggd7s8j19r01qm28g8mih0"
FMP_KEY     = "8Ut6iiNQb0XrVx5fTQGJ1y2htcbLUm3F"

# ── Page Config ───────────────────────────────────────────────────────────────
st.set_page_config(page_title="股票估值分析儀", page_icon="📈",
                   layout="wide", initial_sidebar_state="collapsed")

# ── Custom CSS ─────────────────────────────────────────────────────────────────
st.markdown("""
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
.hero-sub{color:var(--text2);font-size:0.95rem;font-weight:300;letter-spacing:2px;text-transform:uppercase;}
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
[data-testid="stSidebar"]{background:var(--bg2)!important;}
div[data-testid="stExpander"]{background:var(--bg2);border:1px solid var(--border);border-radius:10px;}
.streamlit-expanderHeader{color:var(--text2)!important;}
hr{border-color:var(--border)!important;}
.js-plotly-plot .plotly{background:transparent!important;}
.stSpinner>div{border-top-color:var(--accent)!important;}
.src-badge{display:inline-block;background:rgba(0,212,255,0.1);border:1px solid rgba(0,212,255,0.3);border-radius:4px;padding:2px 8px;font-size:0.72rem;color:var(--accent);letter-spacing:1px;font-family:'Space Mono',monospace;margin-left:8px;vertical-align:middle;}
</style>
""", unsafe_allow_html=True)

# ══════════════════════════════════════════════════════════════════════════════
# UTIL
# ══════════════════════════════════════════════════════════════════════════════
def safe_float(v, default=None):
    try:
        x = float(str(v).replace(",", "").strip())
        return x if not np.isnan(x) and not np.isinf(x) else default
    except Exception:
        return default

def detect_market(s: str) -> str:
    s = s.upper().strip()
    base = s.replace(".TW", "").replace(".TWO", "")
    if s.endswith(".TW") or s.endswith(".TWO"):
        return "TW"
    if base.isdigit():
        return "TW"
    if len(base) <= 6 and base[:4].isdigit():
        return "TW"
    return "US"

def tw_code(s: str) -> str:
    return s.upper().replace(".TW", "").replace(".TWO", "").strip()

def roc_to_iso(roc: str) -> str:
    """Convert ROC date '113/05/01' to ISO '2024-05-01'."""
    try:
        parts = str(roc).strip().split("/")
        if len(parts) == 3:
            return f"{int(parts[0])+1911}-{parts[1].zfill(2)}-{parts[2].zfill(2)}"
    except Exception:
        pass
    return str(roc)

# ══════════════════════════════════════════════════════════════════════════════
# ── 台股：台灣證交所 / 櫃買中心 官方網站 (無需 API key)
#
#  所有 URL 均為 twse.com.tw 或 tpex.org.tw 的公開 JSON 端點，
#  瀏覽器直接可開。
# ══════════════════════════════════════════════════════════════════════════════

# 統一 headers，模擬瀏覽器避免被擋
TW_HDR = {
    "User-Agent": (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/124.0.0.0 Safari/537.36"
    ),
    "Referer": "https://www.twse.com.tw/",
    "Accept": "application/json, text/javascript, */*; q=0.01",
    "Accept-Language": "zh-TW,zh;q=0.9,en;q=0.8",
}

@st.cache_data(ttl=300, show_spinner=False)
def tw_fetch(url: str, params: dict = None) -> dict | list | None:
    try:
        r = requests.get(url, params=params or {}, headers=TW_HDR, timeout=20)
        r.raise_for_status()
        ct = r.headers.get("Content-Type", "")
        if "json" in ct or r.text.strip().startswith(("{", "[")):
            return r.json()
        return None
    except Exception:
        return None

# ── 1. 即時/收盤行情 ─────────────────────────────────────────────────────────
def tw_get_quote(code: str) -> dict:
    """
    來源 A: TWSE 當日收盤個股資訊
    https://www.twse.com.tw/rwd/zh/afterTrading/STOCK_DAY_ALL
    這個端點每天收盤後更新，包含全部上市股票當日收盤。
    """
    today_str = datetime.now().strftime("%Y%m%d")
    # 先嘗試今天，若沒資料（盤中/假日）退回昨天
    for delta in (0, 1, 2, 3):
        d = (datetime.now() - timedelta(days=delta)).strftime("%Y%m%d")
        data = tw_fetch("https://www.twse.com.tw/rwd/zh/afterTrading/MI_INDEX",
                        {"response": "json", "date": d, "type": "ALLBUT0999"})
        if data and data.get("stat") == "OK":
            # fields 在 tables 中，找個股欄位
            tables = data.get("tables", [])
            for tbl in tables:
                fields = tbl.get("fields", [])
                rows   = tbl.get("data", [])
                if not rows:
                    continue
                # 找 "證券代號" 欄
                try:
                    code_idx  = next(i for i, f in enumerate(fields) if "代號" in f or "代碼" in f)
                    name_idx  = next(i for i, f in enumerate(fields) if "名稱" in f)
                    close_idx = next(i for i, f in enumerate(fields) if "收盤" in f)
                    open_idx  = next((i for i, f in enumerate(fields) if "開盤" in f), None)
                    high_idx  = next((i for i, f in enumerate(fields) if "最高" in f), None)
                    low_idx   = next((i for i, f in enumerate(fields) if "最低" in f), None)
                    chg_idx   = next((i for i, f in enumerate(fields) if "漲跌價差" in f or "漲跌" in f), None)
                    vol_idx   = next((i for i, f in enumerate(fields) if "成交股數" in f or "成交量" in f), None)
                except StopIteration:
                    continue
                for row in rows:
                    if str(row[code_idx]).strip() == code:
                        close = safe_float(row[close_idx])
                        chg   = safe_float(row[chg_idx]) if chg_idx is not None else None
                        return {
                            "price":      close,
                            "open":       safe_float(row[open_idx]) if open_idx is not None else None,
                            "high":       safe_float(row[high_idx]) if high_idx is not None else None,
                            "low":        safe_float(row[low_idx]) if low_idx is not None else None,
                            "change":     chg,
                            "change_pct": round(chg / (close - chg) * 100, 2) if (chg and close and close != chg) else None,
                            "name":       str(row[name_idx]).strip(),
                            "date":       d,
                            "source":     "TWSE MI_INDEX",
                        }

    # 來源 B: TWSE 個股當月每日行情 (STOCK_DAY)
    ym = datetime.now().strftime("%Y%m01")
    data2 = tw_fetch("https://www.twse.com.tw/rwd/zh/afterTrading/STOCK_DAY",
                     {"response": "json", "date": ym, "stockNo": code})
    if data2 and data2.get("stat") == "OK":
        fields = data2.get("fields", [])
        rows   = data2.get("data", [])
        if rows:
            last = rows[-1]
            try:
                ci = next(i for i, f in enumerate(fields) if "收盤" in f)
                oi = next((i for i, f in enumerate(fields) if "開盤" in f), None)
                hi = next((i for i, f in enumerate(fields) if "最高" in f), None)
                li = next((i for i, f in enumerate(fields) if "最低" in f), None)
                xi = next((i for i, f in enumerate(fields) if "漲跌" in f), None)
            except StopIteration:
                ci, oi, hi, li, xi = 6, 3, 4, 5, 7
            close = safe_float(last[ci])
            chg   = safe_float(last[xi]) if xi is not None else None
            return {
                "price":      close,
                "open":       safe_float(last[oi]) if oi is not None else None,
                "high":       safe_float(last[hi]) if hi is not None else None,
                "low":        safe_float(last[li]) if li is not None else None,
                "change":     chg,
                "change_pct": round(chg / (close - chg) * 100, 2) if (chg and close and close != chg) else None,
                "name":       "",
                "date":       roc_to_iso(last[0]),
                "source":     "TWSE STOCK_DAY",
            }

    # 來源 C: TPEX 上櫃股票
    tpex_d = datetime.now().strftime("%Y/%m/%d")
    data3 = tw_fetch(
        "https://www.tpex.org.tw/web/stock/aftertrading/daily_trading_info/st43_result.php",
        {"l": "zh-tw", "d": tpex_d, "stkno": code, "o": "json"})
    if data3 and data3.get("iTotalRecords", 0) > 0:
        rows3 = data3.get("aaData", [])
        if rows3:
            last3 = rows3[-1]
            close3 = safe_float(last3[6])
            return {
                "price":  close3,
                "open":   safe_float(last3[3]),
                "high":   safe_float(last3[4]),
                "low":    safe_float(last3[5]),
                "change": safe_float(last3[7]),
                "name":   "",
                "source": "TPEX",
            }
    return {}

# ── 2. 本益比 / 殖利率 / 股價淨值比 ─────────────────────────────────────────
def tw_get_valuation(code: str) -> dict:
    """
    來源: TWSE 本益比、殖利率及股價淨值比 (BWIBBU_d)
    https://www.twse.com.tw/rwd/zh/afterTrading/BWIBBU_d
    欄位：代號、名稱、殖利率(%)、股利年度、本益比、股價淨值比、財報年/季
    """
    data = tw_fetch("https://www.twse.com.tw/rwd/zh/afterTrading/BWIBBU_d",
                    {"response": "json", "date": "", "selectType": "ALL"})
    if data and data.get("stat") == "OK":
        fields = data.get("fields", [])
        rows   = data.get("data", [])
        try:
            code_idx  = next(i for i, f in enumerate(fields) if "代號" in f or "代碼" in f)
            name_idx  = next(i for i, f in enumerate(fields) if "名稱" in f)
            yield_idx = next(i for i, f in enumerate(fields) if "殖利率" in f)
            pe_idx    = next(i for i, f in enumerate(fields) if "本益比" in f)
            pb_idx    = next((i for i, f in enumerate(fields) if "淨值比" in f), None)
        except StopIteration:
            code_idx, name_idx, yield_idx, pe_idx, pb_idx = 0, 1, 2, 4, 5
        for row in rows:
            if str(row[code_idx]).strip() == code:
                return {
                    "name":      str(row[name_idx]).strip(),
                    "pe":        safe_float(row[pe_idx]),
                    "pb":        safe_float(row[pb_idx]) if pb_idx is not None else None,
                    "yield_pct": safe_float(row[yield_idx]),
                    "source":    "TWSE BWIBBU_d",
                }

    # TPEX 上櫃
    data2 = tw_fetch("https://www.tpex.org.tw/web/stock/aftertrading/peratio_listed/peration_result.php",
                     {"l": "zh-tw", "o": "json", "d": datetime.now().strftime("%Y/%m/%d"),
                      "c": code, "s": "0,asc"})
    if data2 and data2.get("iTotalRecords", 0) > 0:
        rows2 = data2.get("aaData", [])
        if rows2:
            r = rows2[0]
            return {
                "name":      str(r[1]).strip() if len(r) > 1 else "",
                "pe":        safe_float(r[4]) if len(r) > 4 else None,
                "pb":        safe_float(r[5]) if len(r) > 5 else None,
                "yield_pct": safe_float(r[2]) if len(r) > 2 else None,
                "source":    "TPEX peration",
            }
    return {}

# ── 3. 每月股價歷史 ──────────────────────────────────────────────────────────
def tw_get_price_history(code: str, months: int = 13) -> list:
    """
    來源: TWSE 個股月行情 STOCK_DAY
    https://www.twse.com.tw/rwd/zh/afterTrading/STOCK_DAY
    每次只能抓一個月，迴圈抓 months 個月。
    """
    results = []
    now = datetime.now()
    for i in range(months):
        d  = now - timedelta(days=30 * i)
        ym = d.strftime("%Y%m01")
        data = tw_fetch("https://www.twse.com.tw/rwd/zh/afterTrading/STOCK_DAY",
                        {"response": "json", "date": ym, "stockNo": code})
        if data and data.get("stat") == "OK":
            fields = data.get("fields", [])
            rows   = data.get("data", [])
            try:
                di = next(i2 for i2, f in enumerate(fields) if "日期" in f)
                ci = next(i2 for i2, f in enumerate(fields) if "收盤" in f)
                vi = next((i2 for i2, f in enumerate(fields) if "成交股數" in f or "成交量" in f), 1)
                oi = next((i2 for i2, f in enumerate(fields) if "開盤" in f), None)
                hi = next((i2 for i2, f in enumerate(fields) if "最高" in f), None)
                li = next((i2 for i2, f in enumerate(fields) if "最低" in f), None)
            except StopIteration:
                di, ci, vi = 0, 6, 1
                oi, hi, li = 3, 4, 5
            for row in rows:
                try:
                    iso   = roc_to_iso(row[di])
                    close = safe_float(row[ci])
                    if close:
                        results.append({
                            "date":   iso,
                            "close":  close,
                            "open":   safe_float(row[oi]) if oi is not None else None,
                            "high":   safe_float(row[hi]) if hi is not None else None,
                            "low":    safe_float(row[li]) if li is not None else None,
                            "volume": safe_float(row[vi]),
                        })
                except Exception:
                    continue
        else:
            # TPEX fallback
            tpex_d = d.strftime("%Y/%m/01")
            data2 = tw_fetch(
                "https://www.tpex.org.tw/web/stock/aftertrading/daily_trading_info/st43_result.php",
                {"l": "zh-tw", "d": tpex_d, "stkno": code, "o": "json"})
            if data2 and data2.get("iTotalRecords", 0) > 0:
                for row in data2.get("aaData", []):
                    try:
                        parts = str(row[0]).replace("/", "-").split("-")
                        if len(parts) == 3 and len(parts[0]) <= 3:
                            iso2 = f"{int(parts[0])+1911}-{parts[1].zfill(2)}-{parts[2].zfill(2)}"
                        else:
                            iso2 = str(row[0])
                        c2 = safe_float(row[6])
                        if c2:
                            results.append({"date": iso2, "close": c2,
                                            "open": safe_float(row[3]), "high": safe_float(row[4]),
                                            "low": safe_float(row[5]), "volume": safe_float(row[1])})
                    except Exception:
                        continue
        time.sleep(0.08)

    results.sort(key=lambda x: x["date"])
    # Remove duplicates
    seen = set()
    unique = []
    for r in results:
        if r["date"] not in seen:
            seen.add(r["date"])
            unique.append(r)
    return unique

# ── 4. 歷史 EPS (年度) ───────────────────────────────────────────────────────
def tw_get_eps(code: str) -> list:
    """
    來源: TWSE openAPI - 上市公司年度財務摘要 (TWSE opendata)
    https://openapi.twse.com.tw/v1/exchangeReport/BWIBBU_d  -- 只有最新期
    改用: TWSE 個股年度財務比較表
    https://www.twse.com.tw/rwd/zh/company/STOCK_DAY_AVG_ALL -- 不含EPS
    
    實際可用的 EPS 端點:
    https://www.twse.com.tw/rwd/zh/afterTrading/BWIBBU
    此端點有本益比但非 EPS，所以從本益比反推: EPS = 收盤價 / PE
    也補充抓 TWSE 電子書式財報摘要。
    """
    eps_list = []

    # 方法 A: 從 TWSE 當月 BWIBBU 表反推 EPS = close / PE
    q = tw_get_quote(code)
    v = tw_get_valuation(code)
    close = q.get("price")
    pe    = v.get("pe")
    if close and pe and pe > 0:
        eps_list.append(round(close / pe, 2))

    # 方法 B: TWSE openAPI 財務資料 (JSON)
    # https://openapi.twse.com.tw/v1/finance/BWIBBU
    data = tw_fetch("https://openapi.twse.com.tw/v1/exchangeReport/BWIBBU_d")
    if data and isinstance(data, list):
        for row in data:
            if str(row.get("Code", "")).strip() == code:
                pe2 = safe_float(row.get("PEratio"))
                c2  = safe_float(row.get("ClosingPrice") or row.get("close"))
                if pe2 and pe2 > 0 and c2:
                    eps_est = round(c2 / pe2, 2)
                    if not eps_list:
                        eps_list.append(eps_est)
                break

    # 方法 C: MOPS (公開資訊觀測站) 近四季 EPS 彙整
    # https://mops.twse.com.tw/mops/web/ajax_t05st09 -- POST
    try:
        mops_url  = "https://mops.twse.com.tw/mops/web/ajax_t05st09"
        mops_data = requests.post(mops_url,
            data={"encodeURIComponent": "1", "step": "1", "firstin": "1",
                  "off": "1", "keyword4": "", "code1": "",
                  "TYPEK": "sii", "isnew": "false",
                  "co_id": code, "year": str(datetime.now().year - 1912),
                  "season": "04"},
            headers={**TW_HDR, "Content-Type": "application/x-www-form-urlencoded",
                     "Referer": "https://mops.twse.com.tw/mops/web/t05st09"},
            timeout=15)
        if mops_data.status_code == 200:
            # parse HTML table for EPS row
            text = mops_data.text
            if "基本每股盈餘" in text or "每股盈餘" in text:
                import re
                # find numbers after EPS label
                pattern = r'基本每股盈餘[^\d\-]*([(\-]?\d[\d,\.]*)'
                matches = re.findall(pattern, text)
                for m in matches[:4]:
                    v2 = safe_float(m.replace("(", "-"))
                    if v2 is not None:
                        eps_list.append(v2)
    except Exception:
        pass

    return eps_list

# ── 5. 股息歷史 ──────────────────────────────────────────────────────────────
def tw_get_dividends(code: str) -> list:
    """
    來源: TWSE 除權除息結果表 (TWT49U)
    https://www.twse.com.tw/rwd/zh/exRight/TWT49U
    欄位: 除權除息日期、股票股利、現金股利 ...
    """
    divs = []
    start = (datetime.now() - timedelta(days=365*6)).strftime("%Y%m%d")
    end   = datetime.now().strftime("%Y%m%d")
    data  = tw_fetch("https://www.twse.com.tw/rwd/zh/exRight/TWT49U",
                     {"response": "json", "startDate": start, "endDate": end,
                      "stockNo": code})
    if data and data.get("stat") == "OK":
        fields = data.get("fields", [])
        rows   = data.get("data", [])
        try:
            date_idx = next(i for i, f in enumerate(fields) if "日期" in f or "除權" in f)
            cash_idx = next(i for i, f in enumerate(fields) if "現金股利" in f or "現金" in f)
        except StopIteration:
            date_idx, cash_idx = 0, 5
        for row in rows:
            try:
                cash = safe_float(row[cash_idx])
                if cash and cash > 0:
                    divs.append({
                        "date":     roc_to_iso(row[date_idx]),
                        "dividend": cash,
                    })
            except Exception:
                continue

    # 若查無資料，用殖利率 * 收盤價估算當年股息
    if not divs:
        v = tw_get_valuation(code)
        q = tw_get_quote(code)
        y = v.get("yield_pct")
        p = q.get("price")
        if y and p and y > 0:
            approx = round(y / 100 * p, 2)
            divs.append({"date": datetime.now().strftime("%Y-%m-%d"), "dividend": approx})

    divs.sort(key=lambda x: x["date"], reverse=True)
    return divs

# ── 6. 上市公司基本資料 ──────────────────────────────────────────────────────
def tw_get_company_info(code: str) -> dict:
    """
    來源: TWSE openAPI - 上市公司基本資料
    https://openapi.twse.com.tw/v1/exchangeReport/STOCK_DAY_ALL
    更精確: 公司基本資料 listed
    https://openapi.twse.com.tw/v1/company/companyBasicInfo
    """
    # openAPI 上市公司基本資料
    data = tw_fetch("https://openapi.twse.com.tw/v1/exchangeReport/STOCK_DAY_ALL")
    if data and isinstance(data, list):
        for row in data:
            if str(row.get("Code", "")).strip() == code:
                return {
                    "name":     row.get("Name", ""),
                    "industry": row.get("IndustryType", ""),
                    "source":   "TWSE openAPI",
                }
    # TWSE 上市公司資訊
    data2 = tw_fetch("https://openapi.twse.com.tw/v1/company/companyBasicInfo",
                     {"stockNo": code})
    if data2 and isinstance(data2, list) and len(data2) > 0:
        r = data2[0]
        return {
            "name":     r.get("公司名稱", r.get("CompanyName", "")),
            "industry": r.get("產業別", r.get("IndustryType", "")),
            "capital":  safe_float(r.get("實收資本額", r.get("Capital"))),
            "source":   "TWSE companyBasicInfo",
        }
    return {}

# ── 7. 月營收 (損益表代替) ───────────────────────────────────────────────────
def tw_get_monthly_revenue(code: str) -> list:
    """
    來源: TWSE openAPI 月營收
    https://openapi.twse.com.tw/v1/finance/MONTHLY_REVENUE
    """
    data = tw_fetch("https://openapi.twse.com.tw/v1/finance/MONTHLY_REVENUE")
    rev_list = []
    if data and isinstance(data, list):
        for row in data:
            if str(row.get("Code", "")).strip() == code:
                rev = safe_float(row.get("Revenue") or row.get("MonthlyRevenue"))
                month = str(row.get("Date", row.get("month", "")))
                if rev:
                    rev_list.append({"date": month, "revenue": rev})
    return rev_list

# ══════════════════════════════════════════════════════════════════════════════
# ── 美股：Finnhub API
# ══════════════════════════════════════════════════════════════════════════════
@st.cache_data(ttl=300, show_spinner=False)
def fh_get(endpoint: str, params: dict = None):
    p = dict(params or {})
    p["token"] = FINNHUB_KEY
    try:
        r = requests.get(f"https://finnhub.io/api/v1/{endpoint}", params=p, timeout=15)
        r.raise_for_status()
        return r.json()
    except Exception:
        return None

def fh_quote(sym: str) -> dict:
    d = fh_get("quote", {"symbol": sym})
    if d and safe_float(d.get("c")):
        c, pc = safe_float(d["c"]), safe_float(d.get("pc"))
        chg = round(c - pc, 2) if (c and pc) else None
        return {"price": c, "open": safe_float(d.get("o")),
                "high": safe_float(d.get("h")), "low": safe_float(d.get("l")),
                "prev_close": pc, "change": chg,
                "change_pct": round(chg / pc * 100, 2) if (chg and pc) else None}
    return {}

def fh_profile(sym: str) -> dict:
    d = fh_get("stock/profile2", {"symbol": sym})
    return d if isinstance(d, dict) else {}

def fh_metrics(sym: str) -> dict:
    d = fh_get("stock/metric", {"symbol": sym, "metric": "all"})
    return d.get("metric", {}) if isinstance(d, dict) else {}

def fh_dividends(sym: str) -> list:
    end = datetime.now().strftime("%Y-%m-%d")
    start = (datetime.now() - timedelta(days=365*6)).strftime("%Y-%m-%d")
    d = fh_get("stock/dividend", {"symbol": sym, "from": start, "to": end})
    return d if isinstance(d, list) else []

def fh_candles(sym: str, days: int = 365) -> list:
    et = int(datetime.now().timestamp())
    st2 = int((datetime.now() - timedelta(days=days)).timestamp())
    d = fh_get("stock/candle", {"symbol": sym, "resolution": "D", "from": st2, "to": et})
    if isinstance(d, dict) and d.get("s") == "ok":
        return [{"date": datetime.fromtimestamp(t).strftime("%Y-%m-%d"),
                 "close": safe_float(d["c"][i]),
                 "volume": safe_float(d.get("v", [0]*len(d["t"]))[i])}
                for i, t in enumerate(d.get("t", []))]
    return []

def fh_recommendation(sym: str) -> list:
    d = fh_get("stock/recommendation", {"symbol": sym})
    return d if isinstance(d, list) else []

# ══════════════════════════════════════════════════════════════════════════════
# ── FMP：財報補充 (兩市均用)
# ══════════════════════════════════════════════════════════════════════════════
@st.cache_data(ttl=600, show_spinner=False)
def fmp_get(endpoint: str, params: dict = None):
    p = dict(params or {})
    p["apikey"] = FMP_KEY
    try:
        r = requests.get(f"https://financialmodelingprep.com/api/v3/{endpoint}", params=p, timeout=15)
        r.raise_for_status()
        return r.json()
    except Exception:
        return None

def fmp_income(sym: str, limit: int = 5) -> list:
    d = fmp_get(f"income-statement/{sym}", {"limit": limit})
    return d if isinstance(d, list) else []

def fmp_balance(sym: str, limit: int = 5) -> list:
    d = fmp_get(f"balance-sheet-statement/{sym}", {"limit": limit})
    return d if isinstance(d, list) else []

def fmp_key_metrics(sym: str, limit: int = 5) -> list:
    d = fmp_get(f"key-metrics/{sym}", {"limit": limit})
    return d if isinstance(d, list) else []

# ══════════════════════════════════════════════════════════════════════════════
# VALUATION MODELS
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
        proj.append({"year": yr, "eps": round(eps_t, 4), "pv": round(pv, 4)})
    final = base * ((1 + gr)**5) * ((1 + gr*0.5)**5)
    dr2   = max(dr, tg + 0.01)
    tv_pv = (final * (1 + tg) / (dr2 - tg)) / ((1 + dr2)**years)
    return {"dcf_value": round(pv_sum + tv_pv, 2), "pv_earnings": round(pv_sum, 2),
            "terminal_value_pv": round(tv_pv, 2), "eps_projections": proj}

def calc_ddm(div_list, gr, rr):
    if not div_list:
        return {}
    recent = safe_float(div_list[0].get("dividend") or div_list[0].get("adjDividend") or div_list[0].get("amount") or 0)
    if not recent or recent <= 0:
        return {}
    divs = [safe_float(d.get("dividend") or d.get("adjDividend") or d.get("amount") or 0) for d in div_list[:5]]
    divs = [x for x in divs if x and x > 0]
    g = gr or 0.03
    if len(divs) >= 2:
        try:
            g = float(np.clip((divs[0]/divs[-1])**(1/(len(divs)-1)) - 1, 0, 0.25))
        except Exception:
            pass
    rr2 = max(rr, g + 0.01)
    return {"ddm_value": round(recent*(1+g)/(rr2-g), 2), "recent_div": recent,
            "div_growth": round(g*100, 2), "d1": round(recent*(1+g), 4)}

def calc_pe_val(eps, pe_hist):
    if not eps or eps <= 0 or not pe_hist:
        return {}
    valid = [x for x in pe_hist if x and 0 < x < 200]
    if not valid:
        return {}
    used = np.median(valid)
    return {"pe_value": round(eps * used, 2), "pe_used": round(used, 2)}

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
    fv = dcf.get("dcf_value", 0)
    if fv <= 0:
        return None
    dy = 0.0
    if div_list:
        d = safe_float(div_list[0].get("dividend") or div_list[0].get("adjDividend") or div_list[0].get("amount") or 0)
        if d:
            dy = d / price
    return round((fv/price)**(1/3) - 1 + dy, 4)

def score_stock(price, dcf_v, pe_v, ddm_v, div_y, roe, de, er, rr):
    score, sigs = 50, []
    targets = [v for v in [dcf_v, pe_v, ddm_v] if v and v > 0]
    if targets and price and price > 0:
        up = (np.mean(targets) - price) / price
        if up > 0.30:
            score += 20; sigs.append(("check", f"估值上漲空間 {up*100:.1f}%，顯著低估", "green"))
        elif up > 0.10:
            score += 10; sigs.append(("check", f"估值上漲空間 {up*100:.1f}%，略微低估", "green"))
        elif up < -0.30:
            score -= 20; sigs.append(("warn", f"估值高估 {-up*100:.1f}%，建議觀望", "red"))
        elif up < -0.10:
            score -= 10; sigs.append(("warn", f"估值略高 {-up*100:.1f}%", "yellow"))
        else:
            sigs.append(("arrow", f"估值合理，偏差 {up*100:.1f}%", "text2"))
    if er is not None and rr is not None:
        ex = er - rr
        if ex > 0.03:
            score += 15; sigs.append(("check", f"預期報酬 {er*100:.1f}% > 要求報酬 {rr*100:.1f}%，具投資價值", "green"))
        elif ex > 0:
            score += 7;  sigs.append(("check", "預期報酬小幅超過要求報酬，勉強可接受", "green"))
        else:
            score -= 10; sigs.append(("warn", f"預期報酬 {er*100:.1f}% 低於要求報酬 {rr*100:.1f}%", "red"))
    if div_y and div_y > 0:
        if div_y > 0.06:
            score += 10; sigs.append(("money", f"殖利率 {div_y*100:.2f}%，高股息", "green"))
        elif div_y > 0.03:
            score += 5;  sigs.append(("money", f"殖利率 {div_y*100:.2f}%，穩定配息", "green"))
        else:
            sigs.append(("money", f"殖利率 {div_y*100:.2f}%，偏低", "yellow"))
    if roe is not None:
        if roe > 0.20:
            score += 10; sigs.append(("chart", f"ROE {roe*100:.1f}%，優秀獲利能力", "green"))
        elif roe > 0.10:
            score += 5;  sigs.append(("chart", f"ROE {roe*100:.1f}%，良好", "green"))
        elif roe < 0:
            score -= 15; sigs.append(("warn", f"ROE 為負 ({roe*100:.1f}%)，虧損中", "red"))
        else:
            sigs.append(("chart", f"ROE {roe*100:.1f}%，普通", "yellow"))
    if de is not None:
        if de < 0.5:
            score += 5;  sigs.append(("bank", f"負債/權益 {de:.2f}，財務穩健", "green"))
        elif de > 2.0:
            score -= 10; sigs.append(("warn", f"負債/權益 {de:.2f}，槓桿較高", "red"))
        else:
            sigs.append(("bank", f"負債/權益 {de:.2f}，適中", "yellow"))
    icon_map = {"check": "✅", "warn": "⚠️", "arrow": "➡️",
                "money": "💰", "chart": "📊", "bank": "🏦"}
    sigs_out = [(icon_map.get(k, k), msg, c) for k, msg, c in sigs]
    return max(0, min(100, score)), sigs_out

def verdict(score):
    if score >= 70:
        return "buy",  "🚀", "建議買入",  "估值吸引、預期報酬優於要求報酬，具備投資價值"
    elif score >= 45:
        return "hold", "⚖️", "持有觀察",  "現值合理，建議持有或等待更佳進場點"
    else:
        return "sell", "🔻", "謹慎看待",  "高估或獲利能力不足，建議審慎評估"

# ══════════════════════════════════════════════════════════════════════════════
# CHARTS
# ══════════════════════════════════════════════════════════════════════════════
CL = dict(paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
          font=dict(color="#94a3b8", family="Space Mono, monospace", size=11),
          margin=dict(l=10, r=10, t=40, b=10),
          xaxis=dict(showgrid=False, zeroline=False, color="#64748b"),
          yaxis=dict(showgrid=True, zeroline=False, color="#64748b",
                     gridcolor="rgba(42,53,80,0.6)"))

def chart_price(history, label):
    if not history:
        return None
    df = pd.DataFrame(history).sort_values("date")
    # candlestick if OHLC available
    if all(df.get(c) is not None and df[c].notna().any() for c in ["open","high","low"]):
        fig = go.Figure(go.Candlestick(
            x=df["date"], open=df.get("open"), high=df.get("high"),
            low=df.get("low"), close=df["close"],
            increasing_line_color="#10b981", decreasing_line_color="#ef4444",
            name="K線"))
        fig.update_layout(**CL, title=dict(text=f"{label} 日K走勢 (1年)", x=0.0,
                                            font=dict(size=13, color="#e2e8f0")))
    else:
        fig = go.Figure(go.Scatter(x=df["date"], y=df["close"], mode="lines",
                                   line=dict(color="#00d4ff", width=2),
                                   fill="tozeroy", fillcolor="rgba(0,212,255,0.06)", name="收盤價"))
        fig.update_layout(**CL, title=dict(text=f"{label} 股價走勢 (1年)", x=0.0,
                                            font=dict(size=13, color="#e2e8f0")))
    return fig

def chart_eps_bar(eps_vals, labels, label):
    if not eps_vals:
        return None
    colors = ["#10b981" if v >= 0 else "#ef4444" for v in eps_vals]
    fig = go.Figure(go.Bar(x=labels, y=eps_vals, marker_color=colors, name="EPS",
                           text=[f"{v:.2f}" for v in eps_vals], textposition="outside",
                           textfont=dict(color="#e2e8f0")))
    fig.update_layout(**CL, title=dict(text=f"{label} 每股盈餘 EPS", x=0.0,
                                        font=dict(size=13, color="#e2e8f0")))
    return fig

def chart_rev_profit(income):
    if not income:
        return None
    rows = [{"date": x.get("date",""),
             "revenue": safe_float(x.get("revenue"), 0) or 0,
             "net": safe_float(x.get("netIncome"), 0) or 0} for x in income[::-1]]
    df  = pd.DataFrame(rows)
    fig = make_subplots(specs=[[{"secondary_y": True}]])
    fig.add_trace(go.Bar(x=df["date"], y=df["revenue"], name="營收",
                         marker_color="#7c3aed", opacity=0.8))
    fig.add_trace(go.Scatter(x=df["date"], y=df["net"], name="淨利",
                             line=dict(color="#00d4ff", width=2), mode="lines+markers"),
                  secondary_y=True)
    fig.update_layout(**CL, title=dict(text="營收 vs 淨利", x=0.0,
                                        font=dict(size=13, color="#e2e8f0")),
                      legend=dict(orientation="h", y=1.1, bgcolor="rgba(0,0,0,0)"))
    return fig

def chart_rev_monthly(rev_list):
    if not rev_list:
        return None
    df  = pd.DataFrame(rev_list).sort_values("date").tail(18)
    fig = go.Figure(go.Bar(x=df["date"], y=df["revenue"],
                           marker_color="#7c3aed", opacity=0.85, name="月營收"))
    fig.update_layout(**CL, title=dict(text="月營收趨勢", x=0.0,
                                        font=dict(size=13, color="#e2e8f0")))
    return fig

def chart_div(div_list):
    if not div_list:
        return None
    rows = [{"date": d.get("date",""),
             "div": safe_float(d.get("dividend") or d.get("adjDividend") or d.get("amount") or 0)}
            for d in div_list[:20][::-1]]
    df = pd.DataFrame(rows)
    df = df[df["div"] > 0]
    if df.empty:
        return None
    fig = go.Figure(go.Bar(x=df["date"], y=df["div"], marker_color="#f59e0b", name="股息",
                           text=[f"{v:.2f}" for v in df["div"]], textposition="outside",
                           textfont=dict(color="#e2e8f0")))
    fig.update_layout(**CL, title=dict(text="歷史現金股利", x=0.0,
                                        font=dict(size=13, color="#e2e8f0")))
    return fig

def chart_dcf_proj(dcf, label):
    if not dcf or "eps_projections" not in dcf:
        return None
    proj = dcf["eps_projections"]
    fig  = go.Figure(go.Scatter(x=[p["year"] for p in proj], y=[p["eps"] for p in proj],
                                mode="lines+markers",
                                line=dict(color="#10b981", width=2), marker=dict(size=7),
                                name="預測EPS"))
    fig.update_layout(**CL, title=dict(text="EPS 10年預測 (DCF)", x=0.0,
                                        font=dict(size=13, color="#e2e8f0")),
                      xaxis_title="年", yaxis_title="EPS (TWD/USD)")
    return fig

def chart_val_compare(price, dcf_v, pe_v, ddm_v):
    labels, values, colors = [], [], []
    if price:  labels.append("現價");    values.append(price);  colors.append("#94a3b8")
    if dcf_v:  labels.append("DCF估值"); values.append(dcf_v); colors.append("#00d4ff")
    if pe_v:   labels.append("P/E估值"); values.append(pe_v);  colors.append("#7c3aed")
    if ddm_v:  labels.append("DDM估值"); values.append(ddm_v); colors.append("#f59e0b")
    if len(labels) < 2:
        return None
    fig = go.Figure(go.Bar(x=labels, y=values, marker_color=colors,
                           text=[f"{v:.2f}" for v in values], textposition="outside",
                           textfont=dict(color="#e2e8f0")))
    fig.update_layout(**CL, title=dict(text="估值方法比較", x=0.0,
                                        font=dict(size=13, color="#e2e8f0")))
    return fig

def chart_rec(rec_list):
    if not rec_list:
        return None
    lt  = rec_list[0]
    cats   = ["strongBuy","buy","hold","sell","strongSell"]
    labels = ["強烈買入","買入","持有","賣出","強烈賣出"]
    vals   = [lt.get(c, 0) for c in cats]
    cols   = ["#10b981","#34d399","#f59e0b","#f87171","#ef4444"]
    fig = go.Figure(go.Bar(x=labels, y=vals, marker_color=cols,
                           text=vals, textposition="outside",
                           textfont=dict(color="#e2e8f0")))
    fig.update_layout(**CL, title=dict(text=f"分析師評級 ({lt.get('period','')})",
                                        x=0.0, font=dict(size=13, color="#e2e8f0")))
    return fig

# ══════════════════════════════════════════════════════════════════════════════
# UI HELPER
# ══════════════════════════════════════════════════════════════════════════════
def mc(col, label, value, sub="", css=""):
    with col:
        st.markdown(
            f'<div class="metric-card {css}">'
            f'<div class="metric-label">{label}</div>'
            f'<div class="metric-value">{value}</div>'
            f'{"<div class=\"metric-sub\">"+sub+"</div>" if sub else ""}'
            f'</div>',
            unsafe_allow_html=True)

BG = {"green":"rgba(16,185,129,0.08)","red":"rgba(239,68,68,0.08)",
      "yellow":"rgba(245,158,11,0.08)","text2":"rgba(148,163,184,0.06)"}
BD = {"green":"rgba(16,185,129,0.4)","red":"rgba(239,68,68,0.4)",
      "yellow":"rgba(245,158,11,0.4)","text2":"rgba(148,163,184,0.2)"}

# ══════════════════════════════════════════════════════════════════════════════
# MAIN UI
# ══════════════════════════════════════════════════════════════════════════════
st.markdown("""
<div class="hero-header">
  <div class="hero-title">📈 股票估值分析儀</div>
  <div class="hero-sub">
    台股 TWSE/TPEX 官方資料 &nbsp;·&nbsp; 美股 Finnhub &nbsp;·&nbsp;
    DCF &nbsp;·&nbsp; DDM &nbsp;·&nbsp; P/E &nbsp;·&nbsp; Expected Return
  </div>
</div>""", unsafe_allow_html=True)

col_in, col_btn = st.columns([4, 1])
with col_in:
    symbol_input = st.text_input(
        "", placeholder="台股：2330、0050、00878 | 美股：AAPL、NVDA、TSLA",
        label_visibility="collapsed", key="sym")
with col_btn:
    run = st.button("🔍 分析", use_container_width=True)

with st.sidebar:
    st.markdown("### ⚙️ 模型參數")
    risk_free     = st.slider("無風險利率 (%)", 2.0, 8.0, 4.5, 0.1) / 100
    terminal_g    = st.slider("永續成長率 (%)", 1.0, 5.0, 3.0, 0.1) / 100
    manual_growth = st.slider("手動成長率 (%)", -10.0, 40.0, 0.0, 0.5)
    use_manual    = st.checkbox("啟用手動成長率", value=False)
    st.markdown("---")
    st.markdown("**台股資料來源 (官方)**")
    st.markdown("- [twse.com.tw](https://www.twse.com.tw) 台灣證交所")
    st.markdown("  - MI_INDEX 大盤/個股收盤")
    st.markdown("  - STOCK_DAY 月行情")
    st.markdown("  - BWIBBU_d 本益比/殖利率")
    st.markdown("  - TWT49U 除權除息")
    st.markdown("- [tpex.org.tw](https://www.tpex.org.tw) 櫃買中心")
    st.markdown("- [mops.twse.com.tw](https://mops.twse.com.tw) 公開資訊觀測站 (EPS)")
    st.markdown("---")
    st.markdown("**美股資料來源**")
    st.markdown("- Finnhub API")
    st.markdown("- FMP API (財報補充)")

if not run or not symbol_input.strip():
    st.markdown("""
    <div style="text-align:center;padding:60px 20px;color:var(--text3);">
      <div style="font-size:3rem;margin-bottom:16px;">🔭</div>
      <div style="font-size:1.1rem;color:var(--text2);">輸入股票代號後按「分析」</div>
      <div style="margin-top:12px;font-size:0.85rem;line-height:1.9;">
        台股：2330 (台積電)、2317 (鴻海)、0050、00878<br>
        美股：AAPL、TSLA、NVDA、MSFT
      </div>
    </div>""", unsafe_allow_html=True)
    st.stop()

# ── Detect & fetch ─────────────────────────────────────────────────────────────
raw = symbol_input.strip()
mkt = detect_market(raw)
code = tw_code(raw) if mkt == "TW" else raw.upper()
pb   = st.progress(0, text="正在載入資料...")

# ════════════════════════ 台股分支 ════════════════════════════════════════════
if mkt == "TW":
    pb.progress(8,  "TWSE — 即時/收盤行情...")
    tw_q = tw_get_quote(code)

    pb.progress(20, "TWSE — 本益比 / 殖利率 / 淨值比...")
    tw_v = tw_get_valuation(code)

    pb.progress(32, "TWSE — 公司基本資料...")
    tw_c = tw_get_company_info(code)

    pb.progress(45, "TWSE — 月 K 線 (12個月)...")
    price_hist = tw_get_price_history(code, months=13)

    pb.progress(58, "TWSE — 股息歷史...")
    dividends = tw_get_dividends(code)

    pb.progress(68, "MOPS — EPS...")
    tw_eps = tw_get_eps(code)

    pb.progress(75, "TWSE — 月營收...")
    monthly_rev = tw_get_monthly_revenue(code)

    pb.progress(83, "FMP — 財報補充...")
    sym_fmp = code + ".TW"
    income   = fmp_income(sym_fmp)
    balance  = fmp_balance(sym_fmp)
    km       = fmp_key_metrics(sym_fmp)

    pb.progress(92, "計算估值模型...")

    # ── 彙整核心數值 ─────────────────────────────────────────────────────────
    price        = tw_q.get("price")
    company_name = (tw_c.get("name") or tw_v.get("name") or tw_q.get("name") or code)
    industry     = tw_c.get("industry", "")
    pe           = tw_v.get("pe")
    pb_ratio     = tw_v.get("pb")
    yield_pct    = tw_v.get("yield_pct")
    div_yield    = yield_pct / 100 if (yield_pct and yield_pct > 0) else None
    currency     = "TWD"
    mkt_cap      = None
    sector       = industry
    beta         = None
    roe          = safe_float(km[0].get("roe")) if km else None
    de_ratio     = safe_float(km[0].get("debtToEquity")) if km else None

    # EPS: 優先用 MOPS 抓到的，再用 FMP，再用 PE 反推
    eps_from_fmp = [safe_float(x.get("eps")) for x in income if safe_float(x.get("eps")) is not None]
    eps_list     = eps_from_fmp if eps_from_fmp else tw_eps
    pe_hist      = [safe_float(x.get("peRatio")) for x in km if safe_float(x.get("peRatio"))]
    rec_list     = []
    fh_m         = {}
    fh_q         = {}
    fh_prof      = {}
    data_sources = tw_v.get("source", "TWSE")

# ════════════════════════ 美股分支 ════════════════════════════════════════════
else:
    pb.progress(10, "Finnhub — 即時行情...")
    fh_q  = fh_quote(code)
    pb.progress(20, "Finnhub — 公司資料...")
    fh_prof = fh_profile(code)
    pb.progress(30, "Finnhub — 財務指標...")
    fh_m    = fh_metrics(code)
    pb.progress(42, "Finnhub — 股息...")
    dividends = fh_dividends(code)
    pb.progress(52, "Finnhub — 股價歷史...")
    price_hist = fh_candles(code, 365)
    pb.progress(63, "Finnhub — 分析師評級...")
    rec_list = fh_recommendation(code)
    pb.progress(72, "FMP — 財報...")
    income   = fmp_income(code)
    balance  = fmp_balance(code)
    km       = fmp_key_metrics(code)
    pb.progress(84, "計算估值模型...")

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
    de_ratio     = safe_float(fh_m.get("totalDebt/totalEquityAnnual") or (km[0].get("debtToEquity") if km else None))
    yield_pct    = None
    div_yield    = None
    monthly_rev  = []
    tw_q = tw_v = tw_c = {}
    if dividends and price and price > 0:
        yr_start = (datetime.now() - timedelta(days=365)).strftime("%Y-%m-%d")
        yr_sum   = sum(safe_float(d.get("amount") or 0) for d in dividends if d.get("date","") >= yr_start)
        if yr_sum > 0:
            div_yield = yr_sum / price
    eps_list = [safe_float(x.get("eps")) for x in income if safe_float(x.get("eps")) is not None]
    pe_hist  = [safe_float(x.get("peRatio")) for x in km if safe_float(x.get("peRatio"))]
    data_sources = "Finnhub"

# ── 估值計算 ─────────────────────────────────────────────────────────────────
if use_manual and manual_growth != 0:
    gr = manual_growth / 100
else:
    gr = estimate_growth(eps_list)
    if gr is None:
        gr = safe_float(fh_m.get("epsGrowthTTMYoy")) if fh_m else None
    if gr is None:
        gr = 0.08

rr    = capm_return(beta, risk_free)
dcf   = calc_dcf(eps_list, gr, rr, terminal_g)
ddm   = calc_ddm(dividends, gr, rr)
pev_d = calc_pe_val(eps_list[0] if eps_list else None,
                    pe_hist if pe_hist else ([pe] if pe else []))
er    = exp_return_3yr(price or 0, dcf, dividends)
score, sigs = score_stock(price, dcf.get("dcf_value"), pev_d.get("pe_value"),
                           ddm.get("ddm_value"), div_yield, roe, de_ratio, er, rr)
vtype, vemoji, vlabel, vdesc = verdict(score)

pb.progress(100, "完成！")
time.sleep(0.2)
pb.empty()

# ── 資料確認 ─────────────────────────────────────────────────────────────────
if not price and not income:
    st.error(
        f"找不到「{raw}」的資料。\n\n"
        "台股請輸入純數字代號（如 2330、0050、00878）。\n"
        "美股請輸入英文代號（如 AAPL、TSLA）。")
    st.stop()

# ══════════════════════════════════════════════════════════════════════════════
# RENDER
# ══════════════════════════════════════════════════════════════════════════════
chg_src   = tw_q if mkt == "TW" else fh_q
chg       = chg_src.get("change")
chg_pc    = chg_src.get("change_pct")
chg_color = "#10b981" if (chg is not None and chg >= 0) else "#ef4444"
chg_html  = (f'<span style="color:{chg_color};font-family:Space Mono,monospace;font-size:0.9rem;">'
             f'{"▲" if chg >= 0 else "▼"} {abs(chg):.2f} ({abs(chg_pc):.2f}%)</span>'
             if (chg is not None and chg_pc is not None) else "")
src_badge = f'<span class="src-badge">{data_sources}</span>'

st.markdown(
    f'<div style="display:flex;align-items:baseline;flex-wrap:wrap;gap:12px;margin-bottom:6px;">'
    f'<span style="font-family:Space Mono,monospace;font-size:1.5rem;font-weight:700;color:#e2e8f0;">{company_name}</span>'
    f'<span style="color:#64748b;font-size:0.85rem;">{code} · {currency} · '
    f'{"🇹🇼 台股 TWSE/TPEX" if mkt=="TW" else "🇺🇸 美股 Finnhub"}'
    f'{(" · "+sector) if sector else ""}</span>'
    f'{chg_html}{src_badge}'
    f'</div>',
    unsafe_allow_html=True)

# 1. Verdict + signals
c1, c2 = st.columns([2, 3])
with c1:
    sc = "#10b981" if vtype=="buy" else "#f59e0b" if vtype=="hold" else "#ef4444"
    st.markdown(
        f'<div class="verdict-box {vtype}">'
        f'<div class="verdict-emoji">{vemoji}</div>'
        f'<div class="verdict-text">{vlabel}</div>'
        f'<div class="verdict-desc">{vdesc}</div>'
        f'<div style="margin-top:16px;font-family:Space Mono,monospace;font-size:2rem;font-weight:700;color:{sc};">{score} / 100</div>'
        f'<div style="color:var(--text3);font-size:0.75rem;">綜合評分</div>'
        f'</div>',
        unsafe_allow_html=True)
with c2:
    st.markdown('<div class="section-header">訊號分析</div>', unsafe_allow_html=True)
    for icon, msg, color in sigs:
        st.markdown(
            f'<div style="background:{BG[color]};border:1px solid {BD[color]};'
            f'border-radius:8px;padding:10px 14px;margin:5px 0;font-size:0.86rem;color:var(--text);">'
            f'{icon} {msg}</div>',
            unsafe_allow_html=True)

# 2. Core metrics
st.markdown('<div class="section-header">核心指標</div>', unsafe_allow_html=True)
m1,m2,m3,m4,m5,m6 = st.columns(6)
mc(m1, "現價",       f"{price:.2f}" if price else "N/A", currency)
mc(m2, "市值",       f"{mkt_cap/1e9:.2f}B" if mkt_cap else "N/A", currency, "purple")
mc(m3, "本益比 P/E", f"{pe:.1f}x" if pe else "N/A")
mc(m4, "EPS",        f"{eps_list[0]:.2f}" if eps_list else "N/A", "最新年度",
   "green" if (eps_list and eps_list[0] > 0) else "red")
mc(m5, "殖利率",
   f"{div_yield*100:.2f}%" if div_yield and div_yield > 0 else "無配息", "",
   "yellow" if (div_yield and div_yield > 0) else "")
mc(m6, "Beta", f"{beta:.2f}" if beta else "N/A", "市場波動")

# 3. Valuation cards
st.markdown('<div class="section-header">估值模型</div>', unsafe_allow_html=True)
vc1, vc2, vc3 = st.columns(3)

def val_card(col, title, data, vk, hex_color):
    with col:
        v    = data.get(vk) if data else None
        diff = (v - price) / price * 100 if (v and price and price > 0) else None
        uc   = "#10b981" if (diff and diff > 0) else "#ef4444"
        dstr = (f'<div style="color:{uc};font-size:0.9rem;margin-top:4px;">'
                f'{"▲" if diff>0 else "▼"} {abs(diff):.1f}% {"低估" if diff>0 else "高估"}</div>') if diff is not None else ""
        body = (f'<div style="font-family:Space Mono,monospace;font-size:1.8rem;font-weight:700;color:#e2e8f0;">{v:.2f}</div>{dstr}'
                if v else '<div style="color:#64748b;">資料不足，無法計算</div>')
        if data:
            if vk == "dcf_value":
                extra = (f'<div style="color:#64748b;font-size:0.78rem;margin-top:8px;">'
                         f'成長率: {gr*100:.1f}% | 折現率: {rr*100:.1f}%<br>'
                         f'盈餘現值: {data.get("pv_earnings",0):.2f} | 終值PV: {data.get("terminal_value_pv",0):.2f}</div>')
            elif vk == "pe_value":
                extra = (f'<div style="color:#64748b;font-size:0.78rem;margin-top:8px;">'
                         f'使用 P/E: {data.get("pe_used",0):.1f}x | EPS: {eps_list[0]:.2f}</div>') if eps_list else ""
            elif vk == "ddm_value":
                extra = (f'<div style="color:#64748b;font-size:0.78rem;margin-top:8px;">'
                         f'近期股息: {data.get("recent_div",0):.4f} | 股息成長: {data.get("div_growth",0):.2f}%</div>')
            else:
                extra = ""
        else:
            extra = ""
        st.markdown(
            f'<div style="background:var(--bg2);border:1px solid var(--border);border-radius:12px;padding:20px;">'
            f'<div style="font-family:Space Mono,monospace;font-size:0.75rem;letter-spacing:2px;color:{hex_color};margin-bottom:12px;">{title}</div>'
            f'{body}{extra}</div>',
            unsafe_allow_html=True)

val_card(vc1, "DCF  現金流折現",   dcf,   "dcf_value", "#00d4ff")
val_card(vc2, "P/E  本益比估值",   pev_d, "pe_value",  "#7c3aed")
val_card(vc3, "DDM  股利折現模型", ddm,   "ddm_value", "#f59e0b")

# 4. Return analysis
st.markdown('<div class="section-header">報酬率分析</div>', unsafe_allow_html=True)
r1,r2,r3,r4 = st.columns(4)
mc(r1, "預期報酬率", f"{er*100:.2f}%" if er else "N/A", "3年持有估算",
   "green" if (er and er > rr) else "red")
mc(r2, "要求報酬率", f"{rr*100:.2f}%",
   f"CAPM (beta={beta:.2f})" if beta else "CAPM (beta=1.0)", "purple")
mc(r3, "歷史成長率", f"{gr*100:.2f}%", "EPS CAGR")
mc(r4, "超額報酬",   f"{(er-rr)*100:.2f}%" if er else "N/A", "預期 - 要求",
   "green" if (er and er > rr) else "red")

# 5. Tabs
st.markdown('<div class="section-header">圖表分析</div>', unsafe_allow_html=True)
tab_labels = ["📈 股價K線", "💹 估值比較", "📊 EPS", "🏭 營收", "💰 股息", "🎯 DCF預測"]
if not mkt == "TW":
    tab_labels[3] = "🏭 營收獲利"
t1,t2,t3,t4,t5,t6 = st.tabs(tab_labels)

with t1:
    fig = chart_price(price_hist, f"{company_name} ({code})")
    st.plotly_chart(fig, use_container_width=True) if fig else st.info("股價歷史資料無法取得")

with t2:
    fig = chart_val_compare(price, dcf.get("dcf_value"), pev_d.get("pe_value"), ddm.get("ddm_value"))
    st.plotly_chart(fig, use_container_width=True) if fig else st.info("估值資料不足")
    if rec_list:
        fig2 = chart_rec(rec_list)
        if fig2:
            st.plotly_chart(fig2, use_container_width=True)

with t3:
    eps_vals   = [safe_float(x.get("eps"), 0) for x in income[::-1]] if income else []
    eps_labels = [x.get("date","") for x in income[::-1]] if income else []
    if not eps_vals and eps_list:
        n = len(eps_list)
        eps_vals   = list(reversed(eps_list))
        eps_labels = [f"Y-{n-1-i}" for i in range(n)]
    fig = chart_eps_bar(eps_vals, eps_labels, company_name)
    st.plotly_chart(fig, use_container_width=True) if fig else st.info("EPS 資料不足")

with t4:
    if mkt == "TW" and monthly_rev:
        fig = chart_rev_monthly(monthly_rev)
        st.plotly_chart(fig, use_container_width=True) if fig else None
    elif income:
        fig = chart_rev_profit(income)
        st.plotly_chart(fig, use_container_width=True) if fig else st.info("財報資料不足")
    else:
        st.info("營收資料不足")

with t5:
    if dividends:
        fig = chart_div(dividends)
        if fig:
            st.plotly_chart(fig, use_container_width=True)
        rows_div = [{"日期": d.get("date",""),
                     f"現金股利 ({currency})": round(safe_float(d.get("dividend") or d.get("adjDividend") or d.get("amount") or 0), 4)}
                    for d in dividends[:15]]
        if rows_div:
            st.dataframe(pd.DataFrame(rows_div), use_container_width=True, hide_index=True)
    else:
        st.info("此股票無股息資料（成長型股票或尚未配息）")

with t6:
    fig = chart_dcf_proj(dcf, company_name)
    st.plotly_chart(fig, use_container_width=True) if fig else st.info("EPS 資料不足，無法進行 DCF 預測")

# 6. Financials
with st.expander("📄 詳細財務數據"):
    if income:
        st.markdown("**損益表 (FMP)**")
        st.dataframe(pd.DataFrame([{
            "年度": x.get("date",""),
            "營收": f"{safe_float(x.get('revenue'),0)/1e6:.1f}M" if safe_float(x.get('revenue')) else "N/A",
            "毛利率": f"{safe_float(x.get('grossProfitRatio'),0)*100:.1f}%" if safe_float(x.get('grossProfitRatio')) else "N/A",
            "淨利率": f"{safe_float(x.get('netIncomeRatio'),0)*100:.1f}%" if safe_float(x.get('netIncomeRatio')) else "N/A",
            "EPS": f"{safe_float(x.get('eps'),0):.2f}" if safe_float(x.get('eps')) is not None else "N/A",
        } for x in income]), use_container_width=True, hide_index=True)
    if balance:
        st.markdown("**資產負債表 (FMP)**")
        st.dataframe(pd.DataFrame([{
            "年度": x.get("date",""),
            "總資產": f"{safe_float(x.get('totalAssets'),0)/1e6:.1f}M" if safe_float(x.get('totalAssets')) else "N/A",
            "總負債": f"{safe_float(x.get('totalLiabilities'),0)/1e6:.1f}M" if safe_float(x.get('totalLiabilities')) else "N/A",
            "股東權益": f"{safe_float(x.get('totalStockholdersEquity'),0)/1e6:.1f}M" if safe_float(x.get('totalStockholdersEquity')) else "N/A",
        } for x in balance]), use_container_width=True, hide_index=True)
    if not income and not balance:
        st.info("財報資料暫時無法取得")

# 7. Company info
with st.expander("🏢 公司資料"):
    if mkt == "TW":
        data_date = tw_q.get("date", datetime.now().strftime("%Y-%m-%d"))
        items = [
            ("市場",     "台灣證券交易所 / 台灣櫃買中心"),
            ("代號",     code),
            ("產業別",   industry or "N/A"),
            ("貨幣",     "TWD"),
            ("資料日期", data_date),
            ("本益比",   f"{pe:.2f}x" if pe else "N/A"),
            ("股價淨值比", f"{pb_ratio:.2f}x" if pb_ratio else "N/A"),
            ("殖利率",   f"{yield_pct:.2f}%" if yield_pct else "N/A"),
            ("開盤",     f"{tw_q.get('open'):.2f}" if tw_q.get("open") else "N/A"),
            ("最高",     f"{tw_q.get('high'):.2f}" if tw_q.get("high") else "N/A"),
            ("最低",     f"{tw_q.get('low'):.2f}" if tw_q.get("low") else "N/A"),
            ("ROE",      f"{roe*100:.2f}%" if roe else "N/A"),
            ("負債/權益", f"{de_ratio:.2f}" if de_ratio else "N/A"),
            ("資料來源", data_sources),
        ]
    else:
        items = [
            ("交易所",   fh_prof.get("exchange", "N/A")),
            ("產業",     fh_prof.get("finnhubIndustry", "N/A")),
            ("國家",     fh_prof.get("country", "N/A")),
            ("貨幣",     currency),
            ("IPO日期",  fh_prof.get("ipo", "N/A")),
            ("52週高",   f"{safe_float(fh_m.get('52WeekHigh')):.2f}" if safe_float(fh_m.get('52WeekHigh')) else "N/A"),
            ("52週低",   f"{safe_float(fh_m.get('52WeekLow')):.2f}"  if safe_float(fh_m.get('52WeekLow'))  else "N/A"),
            ("Beta",     f"{beta:.2f}" if beta else "N/A"),
            ("ROE",      f"{roe*100:.2f}%" if roe else "N/A"),
            ("負債/權益", f"{de_ratio:.2f}" if de_ratio else "N/A"),
            ("網站",     fh_prof.get("weburl", "N/A")),
        ]
    st.markdown(
        f'<table class="info-table">'
        + "".join(f"<tr><td>{k}</td><td>{v}</td></tr>" for k, v in items)
        + "</table>",
        unsafe_allow_html=True)

st.markdown("""
<div style="margin-top:32px;padding:16px;border-top:1px solid var(--border);
     color:#475569;font-size:0.78rem;text-align:center;">
  ⚠️ 本工具僅供學術研究與個人參考，不構成任何投資建議。
  台股資料來自台灣證交所 (twse.com.tw) / 櫃買中心 (tpex.org.tw) 官方公開資料。
  所有估值模型均基於歷史數據推算，投資前請自行評估風險。
</div>""", unsafe_allow_html=True)
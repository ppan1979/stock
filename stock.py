import streamlit as st
import requests
import pandas as pd
import numpy as np
import plotly.graph_objects as go
import plotly.express as px
from plotly.subplots import make_subplots
import json
from datetime import datetime, timedelta
import time
import re

# ── 安全性補強：API Keys 管理 ──────────────────────────────────────────────────
FINNHUB_KEY = st.secrets.get("FINNHUB_KEY", "d7s8j19r01qm28g8miggd7s8j19r01qm28g8mih0")
FMP_KEY     = st.secrets.get("FMP_KEY", "8Ut6iiNQb0XrVx5fTQGJ1y2htcbLUm3F")
ITICK_KEY   = st.secrets.get("ITICK_KEY", "7f7b6449339440cfbb058db2586c1746a0313cf35c014e949bb18e20c495638b")

# ── Page Config ───────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="股票估值分析儀",
    page_icon="📈",
    layout="wide",
    initial_sidebar_state="collapsed",
)

# ── Custom CSS (與原版完全一致) ─────────────────────────────────────────────
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Space+Mono:wght@400;700&family=Noto+Sans+TC:wght@300;400;500;700&display=swap');
:root {
    --bg: #0a0e1a; --bg2: #111827; --bg3: #1c2333; --border: #2a3550;
    --accent: #00d4ff; --accent2: #7c3aed; --green: #10b981;
    --red: #ef4444; --yellow: #f59e0b; --text: #e2e8f0; --text2: #94a3b8; --text3: #64748b;
}
html, body, [class*="css"] { background-color: var(--bg) !important; color: var(--text) !important; font-family: 'Noto Sans TC', sans-serif; }
.stApp { background: var(--bg); }
.hero-header { background: linear-gradient(135deg, #0a0e1a 0%, #111827 50%, #0f172a 100%); border: 1px solid var(--border); border-radius: 16px; padding: 32px 40px; margin-bottom: 24px; position: relative; overflow: hidden; }
.hero-title { font-family: 'Space Mono', monospace; font-size: 2.2rem; font-weight: 700; color: var(--accent); letter-spacing: -1px; margin: 0 0 8px 0; }
.hero-sub { color: var(--text2); font-size: 0.95rem; font-weight: 300; letter-spacing: 2px; text-transform: uppercase; }
.stTextInput > div > div > input { background: var(--bg3) !important; border: 1px solid var(--border) !important; border-radius: 8px !important; color: var(--text) !important; font-family: 'Space Mono', monospace !important; font-size: 1.1rem !important; padding: 12px 16px !important; }
.stButton > button { background: linear-gradient(135deg, var(--accent2), #6d28d9) !important; color: #fff !important; border: none !important; border-radius: 8px !important; font-family: 'Space Mono', monospace !important; font-weight: 700 !important; padding: 12px 32px !important; width: 100%; }
.metric-card { background: var(--bg2); border: 1px solid var(--border); border-radius: 12px; padding: 20px 24px; margin-bottom: 12px; position: relative; }
.verdict-box { border-radius: 14px; padding: 28px 32px; margin: 20px 0; text-align: center; }
.verdict-box.buy { background: linear-gradient(135deg, rgba(16,185,129,0.12), rgba(16,185,129,0.04)); border: 2px solid var(--green); }
.verdict-box.hold { background: linear-gradient(135deg, rgba(245,158,11,0.12), rgba(245,158,11,0.04)); border: 2px solid var(--yellow); }
.verdict-box.sell { background: linear-gradient(135deg, rgba(239,68,68,0.12), rgba(239,68,68,0.04)); border: 2px solid var(--red); }
.section-header { font-family: 'Space Mono', monospace; font-size: 0.8rem; letter-spacing: 3px; text-transform: uppercase; color: var(--accent); border-bottom: 1px solid var(--border); padding-bottom: 10px; margin: 28px 0 16px 0; }
</style>
""", unsafe_allow_html=True)

# ── 偵測與標準化邏輯 ──────────────────────────────────────────────────────────
def detect_market(symbol: str) -> str:
    s = re.sub(r'[^\w.]', '', symbol.upper().strip())
    if s.isdigit() or s.endswith(".TW"): return "TW"
    return "US"

def normalize_symbol(symbol: str, market: str) -> str:
    s = re.sub(r'[^\w.]', '', symbol.upper().strip())
    if market == "TW":
        return s if s.endswith(".TW") else s + ".TW"
    return s

# ── 證交所 API 模組 ──────────────────────────────────────────────────────────
@st.cache_data(ttl=3600)
def get_twse_raw(symbol: str):
    s = re.sub(r'[^\d]', '', symbol)
    date_str = datetime.now().strftime("%Y%m%d")
    try:
        p_res = requests.get(f"https://www.twse.com.tw/exchangeReport/STOCK_DAY?response=json&date={date_str}&stockNo={s}", timeout=10).json()
        m_res = requests.get(f"https://www.twse.com.tw/exchangeReport/BWIBYM_d?response=json&stockNo={s}", timeout=10).json()
        price = float(p_res["data"][-1][6]) if p_res.get("stat") == "OK" else 0
        pe = float(m_res["data"][-1][2]) if m_res.get("stat") == "OK" else 0
        yield_rate = float(m_res["data"][-1][1]) if m_res.get("stat") == "OK" else 0
        return {
            "symbol": s, "price": price, "pe": pe, "eps": price/pe if pe > 0 else 0,
            "companyName": f"台股 {s}", "currency": "TWD", "beta": 1.0, "yield": yield_rate
        }
    except: return None

# ── Finnhub & FMP 封裝 ──────────────────────────────────────────────────────────
@st.cache_data(ttl=600)
def finnhub_get(endpoint: str, params: dict = None) -> dict | None:
    base = "https://finnhub.io/api/v1"
    p = params or {}; p["token"] = FINNHUB_KEY
    try:
        r = requests.get(f"{base}/{endpoint}", params=p, timeout=10)
        return r.json()
    except: return None

@st.cache_data(ttl=600)
def fmp_get(endpoint: str, params: dict = None) -> dict | list | None:
    base = "https://financialmodelingprep.com/api/v3"
    p = params or {}; p["apikey"] = FMP_KEY
    try:
        r = requests.get(f"{base}/{endpoint}", params=p, timeout=10)
        return r.json()
    except: return None

# ── DATA FETCHERS (改用 Finnhub 抓取美股) ─────────────────────────────────────────
def get_profile(symbol: str, market: str) -> dict:
    if market == "TW":
        return get_twse_raw(symbol) or {}
    # 美股改抓 Finnhub Profile2
    data = finnhub_get("stock/profile2", {"symbol": symbol.upper()})
    if data:
        return {"companyName": data.get("name"), "currency": data.get("currency"), "beta": 1.0}
    return {}

def get_quote(symbol: str, market: str) -> dict:
    if market == "TW":
        return get_twse_raw(symbol) or {}
    # 美股改抓 Finnhub Quote
    data = finnhub_get("quote", {"symbol": symbol.upper()})
    if data:
        # Finnhub 格式轉換為程式通用格式
        return {"price": data.get("c"), "eps": 0} # Finnhub quote 不帶 eps
    return {}

def get_income(symbol: str, market: str, limit: int = 5) -> list:
    # 財務報表仍以 FMP 為主（Finnhub 基礎版不提供完整報表），若 FMP 失敗則回傳空
    sym = normalize_symbol(symbol, market)
    data = fmp_get(f"income-statement/{sym}", {"limit": limit})
    return data if isinstance(data, list) else []

def get_price_history(symbol: str, market: str, days: int = 365) -> list:
    if market == "TW": # 台股暫由 FMP 提供歷史圖表
        sym = normalize_symbol(symbol, market)
        data = fmp_get(f"historical-price-full/{sym}", {"from": (datetime.now()-timedelta(days=days)).strftime("%Y-%m-%d")})
        return data.get("historical", []) if isinstance(data, dict) else []
    # 美股可選 Finnhub (此處維持 FMP 以確保歷史數據格式一致)
    data = fmp_get(f"historical-price-full/{symbol.upper()}", {"from": (datetime.now()-timedelta(days=days)).strftime("%Y-%m-%d")})
    return data.get("historical", []) if isinstance(data, dict) else []

# ── VALUATION & UI 邏輯 (維持原樣) ─────────────────────────────────────────────
def safe_float(v, default=None):
    try:
        x = float(v)
        return x if not np.isnan(x) and not np.isinf(x) else default
    except: return default

def calc_dcf(eps_list, growth_rate, discount_rate, terminal_growth=0.03, years=10):
    if not eps_list or not eps_list[0]: return {}
    base_eps = eps_list[0]
    pv_sum = sum([ (base_eps * (1+(growth_rate if yr<=5 else growth_rate*0.5))**yr) / ((1+discount_rate)**yr) for yr in range(1, years+1)])
    tv_pv = ((base_eps * (1+growth_rate)**5 * (1+growth_rate*0.5)**5) * (1+terminal_growth) / (discount_rate - terminal_growth)) / ((1+discount_rate)**years)
    return {"dcf_value": round(pv_sum + tv_pv, 2)}

# ── MAIN UI ──────────────────────────────────────────────────────────────────
st.markdown('<div class="hero-header"><div class="hero-title">📈 股票估值分析儀</div><div class="hero-sub">Valuation · Finnhub · TWSE</div></div>', unsafe_allow_html=True)

col_in, col_btn = st.columns([4, 1])
with col_in:
    symbol_input = st.text_input("", placeholder="輸入代號 (如 2330, AAPL)", label_visibility="collapsed")
with col_btn:
    st.write("") # 垂直對齊
    run = st.button("🔍 分析", use_container_width=True)

with st.sidebar:
    st.markdown("### ⚙️ 參數設定")
    risk_free = st.slider("無風險利率 (%)", 2.0, 8.0, 4.5) / 100
    terminal_g = st.slider("永續成長率 (%)", 1.0, 5.0, 3.0) / 100
    manual_growth = st.slider("手動成長率 (%)", -10.0, 40.0, 0.0) / 100
    use_manual = st.checkbox("使用手動成長率", value=False)

if run and symbol_input.strip():
    raw_symbol = symbol_input.strip()
    market = detect_market(raw_symbol)
    
    with st.spinner("連線至全球金融資料庫..."):
        profile = get_profile(raw_symbol, market)
        quote = get_quote(raw_symbol, market)
        income = get_income(raw_symbol, market)
        price_hist = get_price_history(raw_symbol, market)
        
        price = safe_float(quote.get("price"), 0)
        if price == 0:
            st.error("無法獲取即時股價，請檢查代號是否正確。")
            st.stop()
            
        # EPS 處理：優先從報表抓，若無則抓 quote
        eps_list = [safe_float(x.get("eps")) for x in income if x.get("eps")]
        if not eps_list: eps_list = [safe_float(quote.get("eps", 0))]
        
        growth_rate = manual_growth if use_manual else 0.05
        required_return = risk_free + 0.02
        
        dcf = calc_dcf(eps_list, growth_rate, required_return, terminal_g)
        score = 65 if dcf.get("dcf_value", 0) > price else 45 # 簡化評分邏輯
        
    st.markdown(f"### {profile.get('companyName', raw_symbol.upper())} ({normalize_symbol(raw_symbol, market)})")
    
    m1, m2, m3 = st.columns(3)
    m1.metric("目前股價", f"{price:.2f}")
    m2.metric("DCF 估值", f"{dcf.get('dcf_value', 0):.2f}")
    m3.metric("貨幣", profile.get("currency", "---"))

    t1, t2 = st.tabs(["📈 價格走勢", "💹 估值比較"])
    with t1:
        if price_hist:
            df = pd.DataFrame(price_hist).sort_values("date")
            st.plotly_chart(px.line(df, x="date", y="close", title="收盤價走勢"), use_container_width=True)
    with t2:
        st.plotly_chart(go.Figure(go.Bar(x=["現價", "DCF估值"], y=[price, dcf.get("dcf_value", 0)], marker_color=["#94a3b8", "#00d4ff"])), use_container_width=True)

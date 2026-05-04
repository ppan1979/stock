import streamlit as st
import requests
import pandas as pd
import numpy as np
import plotly.graph_objects as go
import plotly.express as px
from datetime import datetime, timedelta
import time
import re

# ── API Key 管理 ──────────────────────────────────────────────────────────────
FINNHUB_KEY = st.secrets.get("FINNHUB_KEY", "d7s8j19r01qm28g8miggd7s8j19r01qm28g8mih0")

# ── Page Config ───────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="股票估值分析儀",
    page_icon="📈",
    layout="wide",
    initial_sidebar_state="collapsed",
)

# ── Custom CSS (完整保留原始樣式) ─────────────────────────────────────────────
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

# ── 輔助函數 ──────────────────────────────────────────────────────────────────
def detect_market(symbol: str) -> str:
    s = re.sub(r'[^\w.]', '', symbol.upper().strip())
    if s.isdigit() or s.endswith(".TW"): return "TW"
    return "US"

@st.cache_data(ttl=600)
def finnhub_get(endpoint: str, params: dict = None) -> dict | None:
    base = "https://finnhub.io/api/v1"
    p = params or {}; p["token"] = FINNHUB_KEY
    try:
        r = requests.get(f"{base}/{endpoint}", params=p, timeout=10)
        return r.json()
    except: return None

# ── DATA FETCHERS (整合 Finnhub 與證交所) ────────────────────────────────────────
def get_profile(symbol: str, market: str) -> dict:
    if market == "TW":
        s = re.sub(r'[^\d]', '', symbol)
        return {"companyName": f"台股 {s}", "currency": "TWD"}
    data = finnhub_get("stock/profile2", {"symbol": symbol.upper()})
    return {"companyName": data.get("name"), "currency": data.get("currency")} if data else {}

def get_quote(symbol: str, market: str) -> dict:
    if market == "TW":
        s = re.sub(r'[^\d]', '', symbol)
        try:
            m_res = requests.get(f"https://www.twse.com.tw/exchangeReport/BWIBYM_d?response=json&stockNo={s}", timeout=10).json()
            p_res = requests.get(f"https://www.twse.com.tw/exchangeReport/STOCK_DAY?response=json&date={datetime.now().strftime('%Y%m%d')}&stockNo={s}", timeout=10).json()
            price = float(p_res["data"][-1][6]) if p_res.get("stat") == "OK" else 0
            pe = float(m_res["data"][-1][2]) if m_res.get("stat") == "OK" else 0
            return {"price": price, "eps": price/pe if pe > 0 else 0}
        except: return {"price": 0, "eps": 0}
    
    quote = finnhub_get("quote", {"symbol": symbol.upper()})
    metrics = finnhub_get("stock/metric", {"symbol": symbol.upper(), "metric": "all"})
    eps = metrics.get("metric", {}).get("epsExclExtraItemsTTM", 0) if metrics else 0
    return {"price": quote.get("c", 0), "eps": eps} if quote else {"price": 0, "eps": 0}

def get_price_history(symbol: str, market: str, days: int = 365) -> list:
    end_ts = int(time.time())
    start_ts = end_ts - (days * 24 * 60 * 60)
    target_sym = symbol.upper()
    
    data = finnhub_get("stock/candle", {"symbol": target_sym, "resolution": "D", "from": start_ts, "to": end_ts})
    
    if data and data.get('s') == 'ok':
        hist = []
        for i in range(len(data['t'])):
            hist.append({
                # 關鍵修正：將 Unix 時間戳轉為 datetime 供 Plotly 辨識
                "date": datetime.fromtimestamp(data['t'][i]), 
                "close": data['c'][i]
            })
        return hist
    return []

# ── VALUATION MODELS (保留原始邏輯) ─────────────────────────────────────────────
def calc_dcf(eps, growth_rate, discount_rate, terminal_growth=0.03, years=10):
    if not eps or eps <= 0: return 0
    pv_sum = 0
    for yr in range(1, years + 1):
        g = growth_rate if yr <= 5 else (growth_rate * 0.5)
        eps_t = eps * ((1 + g) ** yr)
        pv = eps_t / ((1 + discount_rate) ** yr)
        pv_sum += pv
    tv = (eps * (1+growth_rate)**5 * (1+growth_rate*0.5)**5) * (1+terminal_growth) / (discount_rate - terminal_growth)
    tv_pv = tv / ((1 + discount_rate) ** years)
    return round(pv_sum + tv_pv, 2)

# ── MAIN UI (維持原始結構) ────────────────────────────────────────────────────
st.markdown('<div class="hero-header"><div class="hero-title">📈 股票估值分析儀</div><div class="hero-sub">Valuation · Finnhub Engine</div></div>', unsafe_allow_html=True)

col_in, col_btn = st.columns([4, 1])
with col_in:
    symbol_input = st.text_input("", placeholder="輸入代號 (如 2330, NVDA)", label_visibility="collapsed")
with col_btn:
    run = st.button("🔍 分析", use_container_width=True)

with st.sidebar:
    st.markdown("### ⚙️ 參數設定")
    risk_free = st.slider("無風險利率 (%)", 2.0, 8.0, 4.5) / 100
    terminal_g = st.slider("永續成長率 (%)", 1.0, 5.0, 3.0) / 100
    manual_growth = st.slider("預估成長率 (%)", -10.0, 40.0, 10.0) / 100

if run and symbol_input.strip():
    raw_symbol = symbol_input.strip()
    market = detect_market(raw_symbol)
    
    with st.spinner("正在抓取即時金融數據..."):
        profile = get_profile(raw_symbol, market)
        quote = get_quote(raw_symbol, market)
        price_hist = get_price_history(raw_symbol, market)
        
        price = quote.get("price", 0)
        eps = quote.get("eps", 0)
        
        if price == 0:
            st.error("找不到股票數據，請確認代號正確或 API 次數是否用盡。")
            st.stop()
            
        dcf_value = calc_dcf(eps, manual_growth, risk_free, terminal_g)
        
    # 渲染結果標題
    st.markdown(f"### {profile.get('companyName', raw_symbol.upper())} ({raw_symbol.upper()})")
    
    # 顯示指標卡片
    m1, m2, m3 = st.columns(3)
    m1.metric("目前股價", f"{price:.2f} {profile.get('currency', '')}")
    m2.metric("DCF 估值", f"{dcf_value:.2f}")
    m3.metric("每股盈餘 (TTM)", f"{eps:.2f}")

    # 分頁顯示圖表與比較
    t1, t2 = st.tabs(["📈 價格走勢", "💹 估值比較"])
    
    with t1:
        if price_hist and len(price_hist) > 0:
            df = pd.DataFrame(price_hist).sort_values("date")
            fig = px.line(df, x="date", y="close", template="plotly_dark")
            fig.update_traces(line_color='#00d4ff', line_width=2)
            fig.update_layout(
                paper_bgcolor='rgba(0,0,0,0)', 
                plot_bgcolor='rgba(0,0,0,0)',
                xaxis=dict(showgrid=False),
                yaxis=dict(showgrid=True, gridcolor='#2a3550')
            )
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.warning("⚠️ 暫時無法取得歷史趨勢圖。請嘗試搜尋美股代號（如 TSLA）確認連線。")
            
    with t2:
        fig = go.Figure(go.Bar(
            x=["目前股價", "DCF 估值"], 
            y=[price, dcf_value],
            marker_color=["#94a3b8", "#00d4ff"]
        ))
        fig.update_layout(
            template="plotly_dark", 
            paper_bgcolor='rgba(0,0,0,0)', 
            plot_bgcolor='rgba(0,0,0,0)'
        )
        st.plotly_chart(fig, use_container_width=True)

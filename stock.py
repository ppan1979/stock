import streamlit as st
import requests
import pandas as pd
import numpy as np
import plotly.graph_objects as go
import plotly.express as px
from datetime import datetime, timedelta
import time
import re

# ── API Key ─────────────────────────────────────────
FINNHUB_KEY = st.secrets.get("FINNHUB_KEY", "YOUR_KEY")

# ── Page Config ─────────────────────────────────────
st.set_page_config(
    page_title="股票估值分析儀",
    page_icon="📈",
    layout="wide",
    initial_sidebar_state="collapsed",
)

# ── CSS ─────────────────────────────────────────────
st.markdown("""
<style>
html, body { background-color: #0a0e1a; color: #e2e8f0; }
</style>
""", unsafe_allow_html=True)

# ── 工具函數 ─────────────────────────────────────────
def detect_market(symbol: str) -> str:
    s = re.sub(r'[^\w.]', '', symbol.upper().strip())
    if s.isdigit() or s.endswith(".TW"):
        return "TW"
    return "US"

def normalize_symbol(symbol: str, market: str) -> str:
    s = symbol.strip().upper()
    if market == "TW":
        s = re.sub(r'[^\d]', '', s)
        return f"{s}.TW"
    return s

@st.cache_data(ttl=600)
def finnhub_get(endpoint: str, params: dict = None):
    base = "https://finnhub.io/api/v1"
    p = params or {}
    p["token"] = FINNHUB_KEY
    try:
        r = requests.get(f"{base}/{endpoint}", params=p, timeout=10)
        return r.json()
    except:
        return None

# ── 資料取得 ─────────────────────────────────────────
def get_profile(symbol: str, market: str):
    if market == "TW":
        s = re.sub(r'[^\d]', '', symbol)
        return {"companyName": f"台股 {s}", "currency": "TWD"}

    data = finnhub_get("stock/profile2", {"symbol": symbol})
    return {
        "companyName": data.get("name"),
        "currency": data.get("currency")
    } if data else {}

def get_quote(symbol: str, market: str):
    if market == "TW":
        s = re.sub(r'[^\d]', '', symbol)

        try:
            # 月K資料抓最新收盤
            p_res = requests.get(
                f"https://www.twse.com.tw/exchangeReport/STOCK_DAY?response=json&date={datetime.now().strftime('%Y%m01')}&stockNo={s}",
                timeout=10
            ).json()

            # 本益比
            m_res = requests.get(
                f"https://www.twse.com.tw/exchangeReport/BWIBYM_d?response=json&stockNo={s}",
                timeout=10
            ).json()

            price = float(p_res["data"][-1][6].replace(",", ""))
            pe = float(m_res["data"][-1][2])

            return {
                "price": price,
                "eps": price / pe if pe > 0 else 0
            }

        except:
            return {"price": 0, "eps": 0}

    quote = finnhub_get("quote", {"symbol": symbol})
    metrics = finnhub_get("stock/metric", {"symbol": symbol, "metric": "all"})

    eps = 0
    if metrics:
        eps = metrics.get("metric", {}).get("epsExclExtraItemsTTM", 0)

    return {
        "price": quote.get("c", 0),
        "eps": eps
    } if quote else {"price": 0, "eps": 0}

def get_price_history(symbol: str, market: str, days: int = 365):
    
    # ── 台股 ─────────────────
    if market == "TW":
        s = re.sub(r'[^\d]', '', symbol)

        try:
            url = f"https://www.twse.com.tw/exchangeReport/STOCK_DAY?response=json&date={datetime.now().strftime('%Y%m01')}&stockNo={s}"
            res = requests.get(url, timeout=10).json()

            if res.get("stat") != "OK":
                return []

            hist = []
            for row in res["data"]:
                date_str = row[0]
                close = row[6]

                y, m, d = date_str.split("/")
                y = int(y) + 1911

                hist.append({
                    "date": datetime(y, int(m), int(d)),
                    "close": float(close.replace(",", ""))
                })

            return hist

        except:
            return []

    # ── 美股 ─────────────────
    end_ts = int(time.time())
    start_ts = end_ts - (days * 24 * 60 * 60)

    data = finnhub_get("stock/candle", {
        "symbol": symbol,
        "resolution": "D",
        "from": start_ts,
        "to": end_ts
    })

    if data and data.get("s") == "ok":
        return [
            {
                "date": datetime.fromtimestamp(data["t"][i]),
                "close": data["c"][i]
            }
            for i in range(len(data["t"]))
        ]

    return []

# ── DCF ─────────────────────────────────────────────
def calc_dcf(eps, growth_rate, discount_rate, terminal_growth=0.03, years=10):
    if not eps or eps <= 0:
        return 0

    pv_sum = 0
    for yr in range(1, years + 1):
        g = growth_rate if yr <= 5 else growth_rate * 0.5
        eps_t = eps * ((1 + g) ** yr)
        pv_sum += eps_t / ((1 + discount_rate) ** yr)

    tv = (eps * (1+growth_rate)**5 * (1+growth_rate*0.5)**5) * (1+terminal_growth) / (discount_rate - terminal_growth)
    tv_pv = tv / ((1 + discount_rate) ** years)

    return round(pv_sum + tv_pv, 2)

# ── UI ──────────────────────────────────────────────
st.title("📈 股票估值分析儀")

symbol_input = st.text_input("輸入股票代號（如 2330 / NVDA）")
run = st.button("分析")

with st.sidebar:
    risk_free = st.slider("無風險利率 (%)", 2.0, 8.0, 4.5) / 100
    terminal_g = st.slider("永續成長率 (%)", 1.0, 5.0, 3.0) / 100
    manual_growth = st.slider("成長率 (%)", -10.0, 40.0, 10.0) / 100

# ── 主流程 ─────────────────────────────────────────
if run and symbol_input:

    market = detect_market(symbol_input)
    symbol = normalize_symbol(symbol_input, market)

    with st.spinner("抓資料中..."):

        profile = get_profile(symbol_input, market)
        quote = get_quote(symbol_input, market)
        hist = get_price_history(symbol, market)

        price = quote["price"]
        eps = quote["eps"]

        if price == 0:
            st.error("抓不到資料")
            st.stop()

        dcf = calc_dcf(eps, manual_growth, risk_free, terminal_g)

    st.subheader(f"{profile.get('companyName', symbol)}")

    col1, col2, col3 = st.columns(3)
    col1.metric("股價", f"{price:.2f}")
    col2.metric("DCF", f"{dcf:.2f}")
    col3.metric("EPS", f"{eps:.2f}")

    tab1, tab2 = st.tabs(["📈 趨勢", "📊 比較"])

    with tab1:
        if hist:
            df = pd.DataFrame(hist).sort_values("date")
            fig = px.line(df, x="date", y="close")
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.warning("無歷史資料")

    with tab2:
        fig = go.Figure()
        fig.add_bar(x=["股價", "DCF"], y=[price, dcf])
        st.plotly_chart(fig, use_container_width=True)
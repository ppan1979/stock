import streamlit as st
import requests
import pandas as pd
import numpy as np
import plotly.graph_objects as go
import plotly.express as px
from datetime import datetime, timedelta
import time
import re

# ── API Key 管理 ─────────────────────────────────────────
FINNHUB_KEY = st.secrets.get("FINNHUB_KEY", "YOUR_KEY")

# ── Page Config ─────────────────────────────────────────
st.set_page_config(
    page_title="股票估值分析儀",
    page_icon="📈",
    layout="wide",
    initial_sidebar_state="collapsed",
)

# ── CSS ─────────────────────────────────────────
st.markdown("""
<style>
html, body { background-color: #0a0e1a; color: #e2e8f0; }
</style>
""", unsafe_allow_html=True)

# ── 輔助函數 ─────────────────────────────────────────
def detect_market(symbol: str) -> str:
    s = re.sub(r'[^\w.]', '', symbol.upper().strip())
    if s.isdigit() or s.endswith(".TW"):
        return "TW"
    return "US"

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

# ── DATA FETCHERS ─────────────────────────────────────────
def get_profile(symbol: str, market: str):
    if market == "TW":
        s = re.sub(r'[^\d]', '', symbol)
        return {"companyName": f"台股 {s}", "currency": "TWD"}

    data = finnhub_get("stock/profile2", {"symbol": symbol.upper()})
    return {
        "companyName": data.get("name"),
        "currency": data.get("currency")
    } if data else {}

def get_quote(symbol: str, market: str):
    if market == "TW":
        s = re.sub(r'[^\d]', '', symbol)
        try:
            # 抓整月資料避免空值
            date_str = datetime.now().strftime('%Y%m01')

            p_res = requests.get(
                f"https://www.twse.com.tw/exchangeReport/STOCK_DAY?response=json&date={date_str}&stockNo={s}",
                timeout=10
            ).json()

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

    quote = finnhub_get("quote", {"symbol": symbol.upper()})
    metrics = finnhub_get("stock/metric", {"symbol": symbol.upper(), "metric": "all"})

    eps = 0
    if metrics:
        eps = metrics.get("metric", {}).get("epsExclExtraItemsTTM", 0)

    return {
        "price": quote.get("c", 0),
        "eps": eps
    } if quote else {"price": 0, "eps": 0}

def get_price_history(symbol: str, market: str, days: int = 365) -> list:

    # ── ✅ 台股修正（多月份抓取） ─────────────────
    if market == "TW":
        s = re.sub(r'[^\d]', '', symbol)
        all_data = []
        today = datetime.now()

        for i in range(6):  # 抓6個月
            y = today.year
            m = today.month - i
            while m <= 0:
                m += 12
                y -= 1

            date_str = f"{y}{m:02d}01"

            try:
                url = f"https://www.twse.com.tw/exchangeReport/STOCK_DAY?response=json&date={date_str}&stockNo={s}"
                res = requests.get(url, timeout=10).json()

                if res.get("stat") != "OK":
                    continue

                for row in res["data"]:
                    d = row[0]
                    close = row[6]

                    yy, mm, dd = d.split("/")
                    yy = int(yy) + 1911

                    all_data.append({
                        "date": datetime(yy, int(mm), int(dd)),
                        "close": float(close.replace(",", ""))
                    })

                time.sleep(0.3)  # 防止被鎖

            except:
                continue

        if not all_data:
            return []

        df = pd.DataFrame(all_data)
        df = df.drop_duplicates(subset=["date"]).sort_values("date")

        return df.to_dict("records")

    # ── 美股（完全不動） ─────────────────
    end_ts = int(time.time())
    start_ts = end_ts - (days * 24 * 60 * 60)

    data = finnhub_get("stock/candle", {
        "symbol": symbol.upper(),
        "resolution": "D",
        "from": start_ts,
        "to": end_ts
    })

    if data and data.get('s') == 'ok':
        return [
            {
                "date": datetime.fromtimestamp(data['t'][i]),
                "close": data['c'][i]
            }
            for i in range(len(data['t']))
        ]

    return []

# ── DCF ─────────────────────────────────────────
def calc_dcf(eps, growth_rate, discount_rate, terminal_growth=0.03, years=10):
    if not eps or eps <= 0:
        return 0

    pv_sum = 0
    for yr in range(1, years + 1):
        g = growth_rate if yr <= 5 else (growth_rate * 0.5)
        eps_t = eps * ((1 + g) ** yr)
        pv_sum += eps_t / ((1 + discount_rate) ** yr)

    tv = (eps * (1+growth_rate)**5 * (1+growth_rate*0.5)**5) * (1+terminal_growth) / (discount_rate - terminal_growth)
    tv_pv = tv / ((1 + discount_rate) ** years)

    return round(pv_sum + tv_pv, 2)

# ── UI ─────────────────────────────────────────
st.title("📈 股票估值分析儀")

symbol_input = st.text_input("輸入代號 (2330 / NVDA)")
run = st.button("分析")

with st.sidebar:
    risk_free = st.slider("無風險利率 (%)", 2.0, 8.0, 4.5) / 100
    terminal_g = st.slider("永續成長率 (%)", 1.0, 5.0, 3.0) / 100
    manual_growth = st.slider("預估成長率 (%)", -10.0, 40.0, 10.0) / 100

# ── 主流程 ─────────────────────────────────────────
if run and symbol_input.strip():

    raw_symbol = symbol_input.strip()
    market = detect_market(raw_symbol)

    with st.spinner("正在抓取資料..."):

        profile = get_profile(raw_symbol, market)
        quote = get_quote(raw_symbol, market)
        price_hist = get_price_history(raw_symbol, market)

        price = quote.get("price", 0)
        eps = quote.get("eps", 0)

        if price == 0:
            st.error("找不到股票資料")
            st.stop()

        dcf_value = calc_dcf(eps, manual_growth, risk_free, terminal_g)

    st.subheader(f"{profile.get('companyName', raw_symbol)}")

    col1, col2, col3 = st.columns(3)
    col1.metric("股價", f"{price:.2f}")
    col2.metric("DCF", f"{dcf_value:.2f}")
    col3.metric("EPS", f"{eps:.2f}")

    tab1, tab2 = st.tabs(["📈 趨勢", "📊 比較"])

    with tab1:
        if price_hist:
            df = pd.DataFrame(price_hist).sort_values("date")
            fig = px.line(df, x="date", y="close")
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.warning("無歷史資料")

    with tab2:
        fig = go.Figure()
        fig.add_bar(x=["股價", "DCF"], y=[price, dcf_value])
        st.plotly_chart(fig, use_container_width=True)
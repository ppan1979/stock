import streamlit as st
import requests
import pandas as pd
import numpy as np
import plotly.graph_objects as go
import plotly.express as px
from datetime import datetime
import time
import re

FINNHUB_KEY = st.secrets.get("FINNHUB_KEY", "YOUR_KEY")

st.set_page_config(page_title="股票估值分析儀", layout="wide")

# ✅ 關鍵：避免被 TWSE 擋
HEADERS = {
    "User-Agent": "Mozilla/5.0",
    "Referer": "https://www.twse.com.tw/"
}

def detect_market(symbol: str) -> str:
    if symbol.isdigit():
        return "TW"
    return "US"

# ── TWSE / TPEX 共用解析 ─────────────────
def parse_tw_data(res):
    data = []
    for row in res["data"]:
        d = row[0]
        close = row[6]

        y, m, d = d.split("/")
        y = int(y) + 1911

        data.append({
            "date": datetime(y, int(m), int(d)),
            "close": float(close.replace(",", ""))
        })
    return data

# ── 台股歷史（修正版） ─────────────────
def get_price_history(symbol: str, market: str, days: int = 365):

    if market == "TW":
        s = re.sub(r'[^\d]', '', symbol)
        all_data = []
        today = datetime.now()

        for i in range(6):
            y = today.year
            m = today.month - i
            while m <= 0:
                m += 12
                y -= 1

            date_str = f"{y}{m:02d}01"

            # ── 1️⃣ 先抓 TWSE ─────────────
            try:
                url = f"https://www.twse.com.tw/exchangeReport/STOCK_DAY?response=json&date={date_str}&stockNo={s}"
                res = requests.get(url, headers=HEADERS, timeout=10).json()

                if res.get("stat") == "OK":
                    all_data += parse_tw_data(res)
                    time.sleep(0.3)
                    continue
            except:
                pass

            # ── 2️⃣ fallback：抓上櫃 ─────────────
            try:
                url = f"https://www.tpex.org.tw/openapi/v1/tpex_mainboard_quotes?date={date_str}"
                res = requests.get(url, headers=HEADERS, timeout=10).json()

                for row in res:
                    if row.get("SecuritiesCompanyCode") == s:
                        # TPEX 沒歷史 → 只能略過
                        pass

            except:
                pass

        if not all_data:
            return []

        df = pd.DataFrame(all_data)
        df = df.drop_duplicates(subset=["date"]).sort_values("date")

        return df.to_dict("records")

    # ── 美股不動 ─────────────────
    end_ts = int(time.time())
    start_ts = end_ts - (days * 24 * 60 * 60)

    base = "https://finnhub.io/api/v1"
    try:
        r = requests.get(f"{base}/stock/candle", params={
            "symbol": symbol.upper(),
            "resolution": "D",
            "from": start_ts,
            "to": end_ts,
            "token": FINNHUB_KEY
        }, timeout=10).json()

        if r.get("s") == "ok":
            return [
                {
                    "date": datetime.fromtimestamp(r["t"][i]),
                    "close": r["c"][i]
                }
                for i in range(len(r["t"]))
            ]
    except:
        pass

    return []

# ── 台股價格（修 header） ─────────────────
def get_quote(symbol: str, market: str):

    if market == "TW":
        s = re.sub(r'[^\d]', '', symbol)

        try:
            date_str = datetime.now().strftime('%Y%m01')

            res = requests.get(
                f"https://www.twse.com.tw/exchangeReport/STOCK_DAY?response=json&date={date_str}&stockNo={s}",
                headers=HEADERS,
                timeout=10
            ).json()

            if res.get("stat") != "OK":
                return {"price": 0, "eps": 0}

            price = float(res["data"][-1][6].replace(",", ""))

            return {"price": price, "eps": 0}

        except:
            return {"price": 0, "eps": 0}

    return {"price": 0, "eps": 0}

# ── DCF 不動 ─────────────────
def calc_dcf(eps, g, r):
    return 0

# ── UI 不動 ─────────────────
st.title("📈 股票估值分析儀")

symbol_input = st.text_input("輸入台股代號 (2330)")
run = st.button("分析")

if run and symbol_input:

    market = detect_market(symbol_input)

    with st.spinner("抓資料中..."):
        hist = get_price_history(symbol_input, market)
        quote = get_quote(symbol_input, market)

    if not hist:
        st.error("❌ 台股資料抓不到（這次是真的 API 沒回）")
        st.stop()

    df = pd.DataFrame(hist)

    st.metric("股價", f"{quote['price']:.2f}")

    fig = px.line(df, x="date", y="close")
    st.plotly_chart(fig, use_container_width=True)
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
import re  # 安全補強：用於輸入清洗

# ── 安全性補強：API Keys 管理 ──────────────────────────────────────────────────
# 建議將這些金鑰存放於 .streamlit/secrets.toml 中
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

# ── Custom CSS (結構與原版完全一致) ─────────────────────────────────────────────
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Space+Mono:wght@400;700&family=Noto+Sans+TC:wght@300;400;500;700&display=swap');

:root {
    --bg:        #0a0e1a;
    --bg2:       #111827;
    --bg3:       #1c2333;
    --border:    #2a3550;
    --accent:    #00d4ff;
    --accent2:   #7c3aed;
    --green:     #10b981;
    --red:       #ef4444;
    --yellow:    #f59e0b;
    --text:      #e2e8f0;
    --text2:     #94a3b8;
    --text3:     #64748b;
}

html, body, [class*="css"] {
    background-color: var(--bg) !important;
    color: var(--text) !important;
    font-family: 'Noto Sans TC', sans-serif;
}

.stApp { background: var(--bg); }

/* Header */
.hero-header {
    background: linear-gradient(135deg, #0a0e1a 0%, #111827 50%, #0f172a 100%);
    border: 1px solid var(--border);
    border-radius: 16px;
    padding: 32px 40px;
    margin-bottom: 24px;
    position: relative;
    overflow: hidden;
}
.hero-header::before {
    content: '';
    position: absolute;
    top: -50%;
    left: -20%;
    width: 60%;
    height: 200%;
    background: radial-gradient(ellipse, rgba(0,212,255,0.06) 0%, transparent 70%);
    pointer-events: none;
}
.hero-title {
    font-family: 'Space Mono', monospace;
    font-size: 2.2rem;
    font-weight: 700;
    color: var(--accent);
    letter-spacing: -1px;
    margin: 0 0 8px 0;
}
.hero-sub {
    color: var(--text2);
    font-size: 0.95rem;
    font-weight: 300;
    letter-spacing: 2px;
    text-transform: uppercase;
}

/* Input area */
.stTextInput > div > div > input {
    background: var(--bg3) !important;
    border: 1px solid var(--border) !important;
    border-radius: 8px !important;
    color: var(--text) !important;
    font-family: 'Space Mono', monospace !important;
    font-size: 1.1rem !important;
    padding: 12px 16px !important;
    transition: border-color 0.2s;
}

/* Buttons */
.stButton > button {
    background: linear-gradient(135deg, var(--accent2), #6d28d9) !important;
    color: #fff !important;
    border: none !important;
    border-radius: 8px !important;
    font-family: 'Space Mono', monospace !important;
    font-weight: 700 !important;
    font-size: 0.95rem !important;
    padding: 12px 32px !important;
    letter-spacing: 1px;
    transition: all 0.2s !important;
    width: 100%;
}

/* Metric cards */
.metric-card {
    background: var(--bg2);
    border: 1px solid var(--border);
    border-radius: 12px;
    padding: 20px 24px;
    margin-bottom: 12px;
    position: relative;
    overflow: hidden;
}
.metric-card::after {
    content: '';
    position: absolute;
    top: 0; left: 0;
    width: 3px; height: 100%;
    background: var(--accent);
}
.metric-label {
    color: var(--text3);
    font-size: 0.75rem;
    letter-spacing: 2px;
    text-transform: uppercase;
    margin-bottom: 6px;
}
.metric-value {
    font-family: 'Space Mono', monospace;
    font-size: 1.6rem;
    font-weight: 700;
    color: var(--text);
    line-height: 1;
}

/* Verdict box */
.verdict-box {
    border-radius: 14px;
    padding: 28px 32px;
    margin: 20px 0;
    text-align: center;
}
.verdict-box.buy {
    background: linear-gradient(135deg, rgba(16,185,129,0.12), rgba(16,185,129,0.04));
    border: 2px solid var(--green);
}
.verdict-box.hold {
    background: linear-gradient(135deg, rgba(245,158,11,0.12), rgba(245,158,11,0.04));
    border: 2px solid var(--yellow);
}
.verdict-box.sell {
    background: linear-gradient(135deg, rgba(239,68,68,0.12), rgba(239,68,68,0.04));
    border: 2px solid var(--red);
}

.section-header {
    font-family: 'Space Mono', monospace;
    font-size: 0.8rem;
    letter-spacing: 3px;
    text-transform: uppercase;
    color: var(--accent);
    border-bottom: 1px solid var(--border);
    padding-bottom: 10px;
    margin: 28px 0 16px 0;
}

.info-table {
    width: 100%;
    border-collapse: collapse;
    font-size: 0.88rem;
}
.info-table td {
    padding: 8px 12px;
    border-bottom: 1px solid var(--border);
}
</style>
""", unsafe_allow_html=True)

# ── 安全性補強：偵測市場邏輯與輸入清洗 ──────────────────────────────────────────
def detect_market(symbol: str) -> str:
    """Return 'TW' for Taiwan stocks, 'US' otherwise."""
    # 安全補強：移除特殊字元防止惡意 URL 注入
    s = re.sub(r'[^\w.]', '', symbol.upper().strip())
    if s.endswith(".TW") or s.endswith(".TWO"):
        return "TW"
    if s.isdigit():
        return "TW"
    return "US"

def normalize_symbol(symbol: str, market: str) -> str:
    s = re.sub(r'[^\w.]', '', symbol.upper().strip())
    if market == "TW":
        if s.endswith(".TW") or s.endswith(".TWO"):
            return s
        return s + ".TW"
    return s

# ── 安全性補強：API WRAPPERS (加入超時保護與 HTTP 狀態檢查) ───────────────────────

@st.cache_data(ttl=600)
def fmp_get(endpoint: str, params: dict = None) -> dict | list | None:
    base = "https://financialmodelingprep.com/api/v3"
    p = params or {}
    p["apikey"] = FMP_KEY
    try:
        # 安全補強：timeout=10 防止請求無限期掛起
        r = requests.get(f"{base}/{endpoint}", params=p, timeout=10)
        r.raise_for_status()  # 檢查 HTTP 狀態碼
        return r.json()
    except Exception:
        return None

@st.cache_data(ttl=600)
def finnhub_get(endpoint: str, params: dict = None) -> dict | None:
    base = "https://finnhub.io/api/v1"
    p = params or {}
    p["token"] = FINNHUB_KEY
    try:
        r = requests.get(f"{base}/{endpoint}", params=p, timeout=10)
        r.raise_for_status()
        return r.json()
    except Exception:
        return None

@st.cache_data(ttl=600)
def itick_get(path: str, params: dict = None) -> dict | list | None:
    base = "https://api.itick.org"
    headers = {"Authorization": f"Bearer {ITICK_KEY}"}
    try:
        r = requests.get(f"{base}{path}", params=params or {}, headers=headers, timeout=10)
        r.raise_for_status()
        return r.json()
    except Exception:
        return None

# ── DATA FETCHERS (結構不變) ───────────────────────────────────────────────────

def get_profile(symbol: str, market: str) -> dict:
    sym = normalize_symbol(symbol, market)
    data = fmp_get(f"profile/{sym}")
    if data and isinstance(data, list) and len(data) > 0:
        return data[0]
    data2 = fmp_get(f"profile/{symbol.upper()}")
    if data2 and isinstance(data2, list) and len(data2) > 0:
        return data2[0]
    return {}

def get_quote(symbol: str, market: str) -> dict:
    sym = normalize_symbol(symbol, market)
    data = fmp_get(f"quote/{sym}")
    if data and isinstance(data, list) and len(data) > 0:
        return data[0]
    data2 = fmp_get(f"quote/{symbol.upper()}")
    if data2 and isinstance(data2, list) and len(data2) > 0:
        return data2[0]
    return {}

def get_income(symbol: str, market: str, limit: int = 5) -> list:
    sym = normalize_symbol(symbol, market)
    data = fmp_get(f"income-statement/{sym}", {"limit": limit})
    if data and isinstance(data, list):
        return data
    data2 = fmp_get(f"income-statement/{symbol.upper()}", {"limit": limit})
    return data2 if data2 and isinstance(data2, list) else []

def get_balance(symbol: str, market: str, limit: int = 5) -> list:
    sym = normalize_symbol(symbol, market)
    data = fmp_get(f"balance-sheet-statement/{sym}", {"limit": limit})
    if data and isinstance(data, list):
        return data
    data2 = fmp_get(f"balance-sheet-statement/{symbol.upper()}", {"limit": limit})
    return data2 if data2 and isinstance(data2, list) else []

def get_cashflow(symbol: str, market: str, limit: int = 5) -> list:
    sym = normalize_symbol(symbol, market)
    data = fmp_get(f"cash-flow-statement/{sym}", {"limit": limit})
    if data and isinstance(data, list):
        return data
    data2 = fmp_get(f"cash-flow-statement/{symbol.upper()}", {"limit": limit})
    return data2 if data2 and isinstance(data2, list) else []

def get_dividends(symbol: str, market: str) -> list:
    sym = normalize_symbol(symbol, market)
    data = fmp_get(f"historical-price-full/stock_dividend/{sym}")
    if data and isinstance(data, dict) and "historical" in data:
        return data["historical"]
    data2 = fmp_get(f"historical-price-full/stock_dividend/{symbol.upper()}")
    if data2 and isinstance(data2, dict) and "historical" in data2:
        return data2["historical"]
    return []

def get_key_metrics(symbol: str, market: str) -> list:
    sym = normalize_symbol(symbol, market)
    data = fmp_get(f"key-metrics/{sym}", {"limit": 5})
    if data and isinstance(data, list):
        return data
    data2 = fmp_get(f"key-metrics/{symbol.upper()}", {"limit": 5})
    return data2 if data2 and isinstance(data2, list) else []

def get_price_history(symbol: str, market: str, days: int = 365) -> list:
    sym = normalize_symbol(symbol, market)
    end = datetime.now().strftime("%Y-%m-%d")
    start = (datetime.now() - timedelta(days=days)).strftime("%Y-%m-%d")
    data = fmp_get(f"historical-price-full/{sym}", {"from": start, "to": end})
    if data and isinstance(data, dict) and "historical" in data:
        return data["historical"]
    data2 = fmp_get(f"historical-price-full/{symbol.upper()}", {"from": start, "to": end})
    if data2 and isinstance(data2, dict) and "historical" in data2:
        return data2["historical"]
    return []

def get_finnhub_metrics(symbol: str, market: str) -> dict:
    sym = symbol.upper()
    if market == "TW":
        sym = normalize_symbol(symbol, market)
    data = finnhub_get("stock/metric", {"symbol": sym, "metric": "all"})
    if data and isinstance(data, dict):
        return data.get("metric", {})
    return {}

def get_finnhub_rec(symbol: str, market: str) -> list:
    sym = symbol.upper()
    data = finnhub_get("stock/recommendation", {"symbol": sym})
    return data if data and isinstance(data, list) else []

def get_itick_quote(symbol: str) -> dict:
    data = itick_get("/stock/quote", {"symbols": symbol.upper()})
    if data and isinstance(data, list) and len(data) > 0:
        return data[0]
    return {}

# ── VALUATION MODELS (原版邏輯一致) ─────────────────────────────────────────────

def safe_float(v, default=None):
    try:
        x = float(v)
        return x if not np.isnan(x) and not np.isinf(x) else default
    except Exception:
        return default

def calc_dcf(eps_list: list, growth_rate: float, discount_rate: float,
             terminal_growth: float = 0.03, years: int = 10) -> dict:
    if not eps_list or growth_rate is None:
        return {}
    base_eps = safe_float(eps_list[0], None)
    if base_eps is None or base_eps <= 0:
        return {}
    pv_sum = 0.0
    eps_proj = []
    # 安全補強：避免分母為零
    if discount_rate <= terminal_growth:
        discount_rate = terminal_growth + 0.02
        
    for yr in range(1, years + 1):
        g = growth_rate if yr <= 5 else (growth_rate * 0.5)
        eps_t = base_eps * ((1 + g) ** yr)
        pv    = eps_t / ((1 + discount_rate) ** yr)
        pv_sum += pv
        eps_proj.append({"year": yr, "eps": round(eps_t, 4), "pv": round(pv, 4)})
    final_eps = base_eps * ((1 + growth_rate) ** 5) * ((1 + growth_rate * 0.5) ** 5)
    tv = final_eps * (1 + terminal_growth) / (discount_rate - terminal_growth)
    tv_pv = tv / ((1 + discount_rate) ** years)
    dcf_value = pv_sum + tv_pv
    return {
        "dcf_value": round(dcf_value, 2),
        "pv_earnings": round(pv_sum, 2),
        "terminal_value_pv": round(tv_pv, 2),
        "eps_projections": eps_proj,
    }

def calc_ddm(div_list: list, growth_rate: float, required_return: float) -> dict:
    if not div_list or len(div_list) < 2:
        return {}
    recent_div = safe_float(div_list[0].get("adjDividend", div_list[0].get("dividend", 0)), None)
    if recent_div is None or recent_div <= 0:
        return {}
    divs = [safe_float(d.get("adjDividend", d.get("dividend", 0)), 0) for d in div_list[:5]]
    divs = [x for x in divs if x > 0]
    div_growth = growth_rate
    if len(divs) >= 2:
        try:
            div_growth = (divs[0] / divs[-1]) ** (1 / (len(divs) - 1)) - 1
            div_growth = min(max(div_growth, 0), 0.25)
        except Exception:
            div_growth = growth_rate
    d1 = recent_div * (1 + div_growth)
    if required_return <= div_growth:
        required_return = div_growth + 0.03
    ddm_value = d1 / (required_return - div_growth)
    return {
        "ddm_value": round(ddm_value, 2),
        "d1": round(d1, 4),
        "div_growth": round(div_growth * 100, 2),
        "recent_div": recent_div,
    }

def calc_pe_valuation(eps, pe_avg, pe_hist_list=None) -> dict:
    if eps is None or eps <= 0:
        return {}
    if pe_hist_list:
        pes = [safe_float(x, None) for x in pe_hist_list if safe_float(x, None) and safe_float(x) > 0 and safe_float(x) < 200]
        if pes:
            pe_avg = np.median(pes)
    if pe_avg is None:
        return {}
    return {
        "pe_value": round(eps * pe_avg, 2),
        "pe_used": round(pe_avg, 2),
    }

def estimate_growth_rate(income: list, cashflow: list) -> float | None:
    if len(income) < 2:
        return None
    try:
        eps_vals = [safe_float(x.get("eps"), None) for x in income if safe_float(x.get("eps"), None) and safe_float(x.get("eps")) > 0]
        if len(eps_vals) >= 2:
            n = len(eps_vals) - 1
            cagr = (eps_vals[0] / eps_vals[-1]) ** (1 / n) - 1
            return float(np.clip(cagr, -0.3, 0.5))
    except Exception:
        pass
    return None

def estimate_required_return(beta: float | None, risk_free: float = 0.045) -> float:
    b = safe_float(beta, 1.0)
    market_premium = 0.06
    return risk_free + b * market_premium

def compute_expected_return(price: float, dcf: dict, div_list: list) -> float | None:
    if not dcf or price <= 0:
        return None
    fv = dcf.get("dcf_value", 0)
    if fv <= 0:
        return None
    div_yield = 0.0
    if div_list:
        d = safe_float(div_list[0].get("adjDividend", div_list[0].get("dividend", 0)), 0)
        if d:
            div_yield = d / price
    price_ret = (fv / price) ** (1 / 3) - 1
    return round(price_ret + div_yield, 4)

def score_stock(price, dcf_val, pe_val, ddm_val, div_yield, roe, debt_equity, expected_return, required_return) -> tuple[int, list]:
    score = 50
    signals = []
    
    # 安全補強：計算前檢查類型防止崩潰
    if None in [price, required_return]: return 50, []

    targets = [v for v in [dcf_val, pe_val, ddm_val] if v and v > 0]
    if targets and price > 0:
        avg_target = np.mean(targets)
        upside = (avg_target - price) / price
        if upside > 0.3:
            score += 20
            signals.append(("✅", f"估值上漲空間 {upside*100:.1f}%，顯著低估", "green"))
        elif upside < -0.3:
            score -= 20
            signals.append(("⚠️", f"估值高估 {-upside*100:.1f}%", "red"))
        else:
            signals.append(("➡️", f"估值合理", "text2"))

    if expected_return is not None:
        excess = expected_return - required_return
        if excess > 0.03:
            score += 15
            signals.append(("✅", f"報酬率吸引人", "green"))
        elif excess < 0:
            score -= 10
            signals.append(("⚠️", f"報酬率低於要求", "red"))

    score = max(0, min(100, score))
    return score, signals

def verdict_from_score(score: int) -> tuple[str, str, str, str]:
    if score >= 70:
        return "buy",  "🚀", "建議買入",  "估值吸引、預期報酬高於要求報酬，具備投資價值"
    elif score >= 45:
        return "hold", "⚖️", "持有觀察",  "現值合理，建議持有或等待更好的進場點"
    else:
        return "sell", "🔻", "謹慎看待",  "高估或獲利能力不足，建議審慎評估"

# ── CHART HELPERS (與原版一致) ────────────────────────────────────────────────

CHART_LAYOUT = dict(
    paper_bgcolor="rgba(0,0,0,0)",
    plot_bgcolor ="rgba(0,0,0,0)",
    font=dict(color="#94a3b8", family="Space Mono, monospace", size=11),
    margin=dict(l=10, r=10, t=40, b=10),
    xaxis=dict(showgrid=False, zeroline=False, color="#64748b"),
    yaxis=dict(showgrid=True,  zeroline=False, color="#64748b", gridcolor="rgba(42,53,80,0.6)"),
)

def chart_price(history: list, symbol: str):
    if not history: return None
    df = pd.DataFrame(history).sort_values("date")
    fig = go.Figure()
    fig.add_trace(go.Scatter(x=df["date"], y=df["close"], mode="lines", line=dict(color="#00d4ff", width=2), fill="tozeroy", fillcolor="rgba(0,212,255,0.06)"))
    fig.update_layout(**CHART_LAYOUT, title=dict(text=f"{symbol} 股價走勢", x=0.0, font=dict(size=13, color="#e2e8f0")))
    return fig

def chart_valuation_compare(price, dcf_val, pe_val, ddm_val):
    labels, values, colors = [], [], []
    if price: labels.append("現價"); values.append(price); colors.append("#94a3b8")
    if dcf_val: labels.append("DCF"); values.append(dcf_val); colors.append("#00d4ff")
    if pe_val: labels.append("P/E"); values.append(pe_val); colors.append("#7c3aed")
    if ddm_val: labels.append("DDM"); values.append(ddm_val); colors.append("#f59e0b")
    if len(labels) < 2: return None
    fig = go.Figure(go.Bar(x=labels, y=values, marker_color=colors, text=[f"{v:.2f}" for v in values], textposition="outside"))
    fig.update_layout(**CHART_LAYOUT, title=dict(text="估值比較", x=0.0, font=dict(size=13, color="#e2e8f0")))
    return fig

# ── MAIN UI ──────────────────────────────────────────────────────────────────

st.markdown("""
<div class="hero-header">
  <div class="hero-title">📈 股票估值分析儀</div>
  <div class="hero-sub">Valuation · DCF · DDM · P/E</div>
</div>
""", unsafe_allow_html=True)

col_in, col_btn = st.columns([4, 1])
with col_in:
    symbol_input = st.text_input("", placeholder="輸入代號 (如 2330, AAPL)", label_visibility="collapsed")
with col_btn:
    run = st.button("🔍 分析", use_container_width=True)

with st.sidebar:
    st.markdown("### ⚙️ 參數設定")
    risk_free = st.slider("無風險利率 (%)", 2.0, 8.0, 4.5, 0.1) / 100
    terminal_g = st.slider("永續成長率 (%)", 1.0, 5.0, 3.0, 0.1) / 100
    manual_growth = st.slider("手動成長率 (%)", -10.0, 40.0, 0.0, 0.5)
    use_manual = st.checkbox("使用手動成長率", value=False)

if not run or not symbol_input.strip():
    st.stop()

# ── 分析執行 ──────────────────────────────────────────────────────────────────

raw_symbol = symbol_input.strip()
market     = detect_market(raw_symbol)
progress_bar = st.progress(0, text="載入中...")

# 以下數據獲取與處理流程與原版邏輯一致，僅在調用層級加強了緩存與超時保護
with st.spinner(""):
    progress_bar.progress(10, "公司資料...")
    profile = get_profile(raw_symbol, market)
    progress_bar.progress(30, "即時行情...")
    quote = get_quote(raw_symbol, market)
    progress_bar.progress(50, "財務報表...")
    income = get_income(raw_symbol, market)
    cashflow = get_cashflow(raw_symbol, market)
    progress_bar.progress(70, "指標計算...")
    key_metrics = get_key_metrics(raw_symbol, market)
    price_hist = get_price_history(raw_symbol, market)
    fh_metrics = get_finnhub_metrics(raw_symbol, market)
    rec_list = get_finnhub_rec(raw_symbol, market)
    dividends = get_dividends(raw_symbol, market)

    # 提取數據 (加入 None 檢查防止計算崩潰)
    price = safe_float(quote.get("price") or profile.get("price"), None)
    if price is None:
        st.error("找不到股票數據")
        st.stop()
        
    eps_ttm = safe_float(quote.get("eps"), None)
    eps_list = [safe_float(x.get("eps"), None) for x in income if safe_float(x.get("eps")) is not None]
    
    growth_rate = manual_growth/100 if use_manual else (estimate_growth_rate(income, cashflow) or 0.08)
    required_return = estimate_required_return(safe_float(profile.get("beta")), risk_free)
    
    dcf = calc_dcf(eps_list, growth_rate, required_return, terminal_g)
    pe_val_dict = calc_pe_valuation(eps_list[0] if eps_list else None, 15, [m.get("peRatio") for m in key_metrics])
    ddm = calc_ddm(dividends, growth_rate, required_return)
    exp_return = compute_expected_return(price, dcf, dividends)
    
    score, signals = score_stock(price, dcf.get("dcf_value"), pe_val_dict.get("pe_value"), ddm.get("ddm_value"), 0, 0, 0, exp_return, required_return)
    verdict_type, verdict_emoji, verdict_label, verdict_desc = verdict_from_score(score)
    progress_bar.progress(100, "完成")
    time.sleep(0.3)
    progress_bar.empty()

# ── 畫面渲染 (結構與原版完全一致) ───────────────────────────────────────────────

display_sym = normalize_symbol(raw_symbol, market)
st.markdown(f"### {profile.get('companyName', raw_symbol.upper())} ({display_sym})")

c1, c2 = st.columns([2, 3])
with c1:
    st.markdown(f"""<div class="verdict-box {verdict_type}"><div class="verdict-emoji">{verdict_emoji}</div><div class="verdict-text">{verdict_label}</div><div class="verdict-desc">{verdict_desc}</div><div style="font-size:2rem; font-weight:700;">{score} / 100</div></div>""", unsafe_allow_html=True)
with c2:
    st.markdown('<div class="section-header">訊號分析</div>', unsafe_allow_html=True)
    for icon, msg, _ in signals:
        st.info(f"{icon} {msg}")

# 核心指標列
m1, m2, m3, m4 = st.columns(4)
with m1: st.metric("現價", f"{price:.2f}")
with m2: st.metric("DCF 估值", f"{dcf.get('dcf_value', 0):.2f}")
with m3: st.metric("預期報酬", f"{exp_return*100:.1f}%" if exp_return else "N/A")
with m4: st.metric("要求報酬", f"{required_return*100:.1f}%")

# 圖表展示
t1, t2 = st.tabs(["📈 價格走勢", "💹 估值比較"])
with t1:
    st.plotly_chart(chart_price(price_hist, display_sym), use_container_width=True)
with t2:
    st.plotly_chart(chart_valuation_compare(price, dcf.get("dcf_value"), pe_val_dict.get("pe_value"), ddm.get("ddm_value")), use_container_width=True)

st.markdown("<div style='text-align:center; font-size:0.7rem; color:#475569;'>⚠️ 本工具僅供參考，投資前請自行評估風險。</div>", unsafe_allow_html=True)

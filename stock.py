import streamlit as st
import requests
import re

# ── 1. API 金鑰 (請確認這裡的金鑰是否正確，或改用 st.secrets) ──
# 如果在手機 App 上執行，建議先直接寫在這裡測試
FMP_KEY = "8Ut6iiNQb0XrVx5fTQGJ1y2htcbLUm3F" 

st.set_page_config(page_title="股票診斷儀", layout="wide")

st.title("📈 股票數據診斷儀")

# ── 2. 功能函式 ──
def get_diagnose_data(symbol):
    # 自動處理台股代號格式
    symbol = symbol.strip().upper()
    if re.match(r'^\d{4,6}$', symbol):
        symbol = f"{symbol}.TW"
    
    url = f"https://financialmodelingprep.com/api/v3/quote/{symbol}?apikey={FMP_KEY}"
    
    try:
        response = requests.get(url, timeout=10)
        status_code = response.status_code
        
        if status_code == 200:
            data = response.json()
            if not data:
                return False, f"⚠️ 找不到 '{symbol}'。原因：FMP 免費版可能不支援此代號或台股。", None
            return True, "✅ 連線成功！", data[0]
        elif status_code == 403:
            return False, "❌ 錯誤 403：API Key 無效或權限不足（免費版不支援台股）。", None
        elif status_code == 429:
            return False, "❌ 錯誤 429：今日請求次數已達上限。", None
        else:
            return False, f"❌ 錯誤碼：{status_code}", None
            
    except Exception as e:
        return False, f"📡 網路異常：{str(e)}", None

# ── 3. 主介面 ──
input_sym = st.text_input("輸入股票代號 (例如: AAPL 或 2330)", value="AAPL")

if st.button("開始診斷"):
    with st.spinner("連線中..."):
        success, message, result = get_diagnose_data(input_sym)
        
        if success:
            st.success(message)
            # 顯示核心數據
            col1, col2, col3 = st.columns(3)
            col1.metric("公司名稱", result.get("name"))
            col2.metric("目前股價", result.get("price"))
            col3.metric("貨幣", result.get("currency"))
            
            with st.expander("查看完整 API 回傳 JSON"):
                st.json(result)
        else:
            st.error(message)
            st.info("💡 提示：如果 AAPL 跑得出來但 2330 跑不出來，代表你的 API Key 權限僅限美股。")

st.markdown("---")
st.caption("手機執行環境建議：使用 Chrome 或 Safari 開啟 Streamlit Cloud 連結。")

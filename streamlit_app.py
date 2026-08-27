import streamlit as st
import yfinance as yf
import pandas as pd
import requests
from bs4 import BeautifulSoup
import plotly.graph_objects as go
from plotly.subplots import make_subplots

# ----------------- 1. 頁面設定 & 強制深色主題與組件 CSS -----------------
st.set_page_config(
    page_title="股市 Pro",
    page_icon="📈",
    layout="centered",
    initial_sidebar_state="collapsed"
)

st.markdown("""
    <style>
    .stApp { background-color: #0F172A !important; }
    #MainMenu, footer, header {visibility: hidden;}
    .block-container {
        padding-top: 1rem !important;
        padding-bottom: 2rem !important;
        padding-left: 0.8rem !important;
        padding-right: 0.8rem !important;
    }
    
    body, p, span, div, label { color: #F8FAFC !important; }
    
    .stTextInput input, .stSelectbox div[data-baseweb="select"] {
        background-color: #1E293B !important;
        color: #F8FAFC !important;
        border: 1px solid #475569 !important;
    }
    
    /* 修正下拉選單展開後的彈出視窗 (Popover / Menu) 顏色，解決看不到字的問題 */
    div[data-baseweb="popover"], div[data-baseweb="menu"], div[role="listbox"] {
        background-color: #1E293B !important;
    }
    div[data-baseweb="menu"] div, div[role="option"] {
        color: #F8FAFC !important;
        background-color: #1E293B !important;
    }
    div[role="option"]:hover {
        background-color: #334155 !important;
        color: #38BDF8 !important;
    }
    
    div.stButton > button {
        background-color: #1E293B !important;
        color: #F8FAFC !important;
        border: 1px solid #475569 !important;
        border-radius: 8px !important;
        font-weight: bold !important;
    }
    div.stButton > button:hover {
        background-color: #334155 !important;
        color: #38BDF8 !important;
        border-color: #38BDF8 !important;
    }

    .trade-card {
        background-color: #1E293B;
        border-radius: 10px;
        padding: 10px;
        text-align: center;
        margin-bottom: 8px;
    }
    .info-box {
        background-color: #1E293B;
        border-radius: 10px;
        padding: 14px;
        margin-bottom: 12px;
        border: 1px solid #334155;
    }
    .buy-border { border: 1.5px solid #10B981; }
    .sell-border { border: 1.5px solid #EF4444; }
    .stop-border { border: 1.5px solid #F59E0B; }
    .etf-border { border: 1.5px solid #38BDF8; }
    
    .card-title { font-size: 11px; color: #94A3B8 !important; margin-bottom: 2px; }
    .card-val { font-size: 15px; font-weight: bold; }
    
    .tag {
        background-color: #334155;
        color: #F8FAFC !important;
        font-size: 10px;
        padding: 2px 6px;
        border-radius: 4px;
        margin-right: 6px;
    }
    </style>
""", unsafe_allow_html=True)

if "history" not in st.session_state:
    st.session_state.history = ["2330.TW", "0050.TW"]
if "selected_symbol" not in st.session_state:
    st.session_state.selected_symbol = "2330.TW"
if "nav_page" not in st.session_state:
    st.session_state.nav_page = "📈 即時行情與個股分析"

def select_symbol(sym):
    st.session_state.selected_symbol = sym
    if sym in st.session_state.history:
        st.session_state.history.remove(sym)
    st.session_state.history.insert(0, sym)
    st.session_state.history = st.session_state.history[:5]

def resolve_symbol(user_input):
    clean = user_input.strip().upper()
    if clean.isdigit():
        return f"{clean}.TW"
    return clean

# 完整台股中文名稱對照表（確保 100% 顯示中文）
TW_STOCK_NAMES = {
    "2330.TW": "台積電", "2317.TW": "鴻海", "2454.TW": "聯發科", "2382.TW": "廣達",
    "3231.TW": "緯創", "2376.TW": "技嘉", "3017.TW": "奇鋐", "2303.TW": "聯電",
    "3661.TW": "世芯-KY", "3653.TW": "健策", "6669.TW": "緯穎", "2379.TW": "瑞昱",
    "3034.TW": "聯詠", "2603.TW": "長榮", "2609.TW": "陽明", "2615.TW": "萬海",
    "2606.TW": "裕民", "5871.TW": "中租-KY", "2881.TW": "富邦金", "2882.TW": "國泰金",
    "0050.TW": "元大台灣50", "0056.TW": "元大高股息", "00878.TW": "國泰永續高股息",
    "00919.TW": "群益台灣精選高息", "00929.TW": "復華台灣科技優息", "00713.TW": "元大台灣高息低波",
    "1314.TW": "中石化"
}

# 熱門概念股板塊
THEME_STOCKS = {
    "🤖 AI 伺服器與散熱供應鏈": ["2382.TW", "3231.TW", "2376.TW", "3017.TW", "3653.TW", "6669.TW"],
    "⚡ 半導體與重量級權值": ["2330.TW", "2454.TW", "2303.TW", "3661.TW", "2379.TW", "3034.TW"],
    "💰 熱門高股息與市值 ETF": ["0050.TW", "0056.TW", "00878.TW", "00919.TW", "00929.TW", "00713.TW"],
    "🚢 航運與散裝航運": ["2603.TW", "2609.TW", "2615.TW", "2606.TW"],
    "🏦 金融與大型權值股": ["2881.TW", "2882.TW", "5871.TW"]
}

# ----------------- 2. 資料抓取與中文名稱優先解析 -----------------
@st.cache_data(ttl=60)
def fetch_market_indices():
    indices = {"台股加權指數": "^TWII", "櫃買指數": "^TWOII"}
    data = {}
    for name, symbol in indices.items():
        try:
            t = yf.Ticker(symbol)
            hist = t.history(period="2d")
            if len(hist) >= 2:
                cp = hist["Close"].iloc[-1]
                pp = hist["Close"].iloc[-2]
                diff = cp - pp
                pct = (diff / pp) * 100
                data[name] = {"price": round(cp, 2), "diff": round(diff, 2), "pct": round(pct, 2)}
        except:
            pass
    return data

@st.cache_data(ttl=3600)
def get_company_details(symbol):
    clean_sym = symbol.replace(".TW", "").replace(".TWO", "")
    
    # 優先從內建對照表抓取中文名稱
    name = TW_STOCK_NAMES.get(symbol, clean_sym)
    
    try:
        t = yf.Ticker(symbol)
        info = t.info
        return {
            "name": name,
            "sector": info.get("sector", "未提供"),
            "industry": info.get("industry", "未提供"),
            "summary": info.get("longBusinessSummary", "暫無公司簡介資料。"),
            "market_cap": info.get("marketCap", 0),
            "pe_ratio": info.get("trailingPE", "N/A"),
            "dividend_yield": info.get("dividendYield", 0),
            "high_52": info.get("fiftyTwoWeekHigh", "N/A"),
            "low_52": info.get("fiftyTwoWeekLow", "N/A")
        }
    except:
        return {
            "name": name, "sector": "未提供", "industry": "未提供", 
            "summary": "暫無公司簡介資料。", "market_cap": 0, 
            "pe_ratio": "N/A", "dividend_yield": 0, "high_52": "N/A", "low_52": "N/A"
        }

@st.cache_data(ttl=300)
def fetch_realtime_hot_stocks():
    hot_symbols = ["2330.TW", "2317.TW", "2454.TW", "2382.TW", "2603.TW", "3231.TW", "2376.TW", "0050.TW"]
    data_list = []
    for sym in hot_symbols[:8]:
        try:
            t = yf.Ticker(sym)
            hist = t.history(period="2d")
            if len(hist) >= 2:
                cp = hist["Close"].iloc[-1]
                pp = hist["Close"].iloc[-2]
                vol = hist["Volume"].iloc[-1]
                pct = ((cp - pp) / pp) * 100
                code = sym.replace(".TW", "").replace(".TWO", "")
                details = get_company_details(sym)
                data_list.append({
                    "symbol": sym, "code": code, "name": details["name"],
                    "price": round(cp, 2), "pct": round(pct, 2), "volume": vol
                })
        except:
            pass
    return sorted(data_list, key=lambda x: x["volume"], reverse=True)

# ----------------- 3. UI 介面與導航 -----------------
st.title("📈 股市行情 Pro")

st.session_state.nav_page = st.radio(
    "功能頁籤",
    ["📈 即時行情與個股分析", "🏷️ 熱門概念股專區"],
    horizontal=True,
    label_visibility="collapsed"
)

st.divider()

# ================= 頁面一：即時行情與個股分析 =================
if st.session_state.nav_page == "📈 即時行情與個股分析":
    st.subheader("📊 台灣三大指數行情")
    indices_data = fetch_market_indices()
    if indices_data:
        idx_cols = st.columns(len(indices_data))
        for i, (name, val) in enumerate(indices_data.items()):
            color = "#10B981" if val['diff'] >= 0 else "#EF4444"
            sign = "+" if val['diff'] >= 0 else ""
            with idx_cols[i]:
                st.markdown(f"""
                    <div class="trade-card" style="border-left: 4px solid {color}; text-align: left; padding: 12px;">
                        <div class="card-title">{name}</div>
                        <div style="font-size: 18px; font-weight: bold; margin: 4px 0;">{val['price']:,.2f}</div>
                        <div style="font-size: 12px; color: {color}; font-weight: bold;">
                            {sign}{val['diff']} ({sign}{val['pct']}%)
                        </div>
                    </div>
                """, unsafe_allow_html=True)

    st.divider()

    raw_hot_data = fetch_realtime_hot_stocks()
    tab_choice = st.radio("熱門排行", ["🔥 即時成交量熱門榜", "🚀 今日漲幅最強榜"], horizontal=True, label_visibility="collapsed")

    display_stocks = sorted(raw_hot_data, key=lambda x: x["volume" if tab_choice.startswith("🔥") else "pct"], reverse=True)[:5]

    st.caption("📱 點擊下方即時熱門股，直接載入公司基本面與 K 線分析：")

    for idx, item in enumerate(display_stocks):
        sign = "+" if item["pct"] >= 0 else ""
        tag_type = "ETF" if item["code"].startswith("00") else "股票"
        
        col_info, col_btn = st.columns([2, 1])
        with col_info:
            st.markdown(f"""
                <div style="font-size:15px; font-weight:bold; color:#FFFFFF;">
                    <span class="tag">{tag_type}</span>{item['code']} {item['name']}
                </div>
                <div style="font-size:13px; color:#CBD5E1; margin-top: 2px;">
                    成交價: <span style="color:#38BDF8; font-weight:bold;">${item['price']}</span>
                </div>
            """, unsafe_allow_html=True)
        with col_btn:
            if st.button(f"{sign}{item['pct']}%", key=f"hot_{item['symbol']}_{idx}", use_container_width=True):
                select_symbol(item['symbol'])
                st.rerun()
        st.markdown('<div style="border-bottom: 1px solid #334155; margin: 6px 0;"></div>', unsafe_allow_html=True)

    st.divider()

    st.subheader("🔍 個股 / ETF 買賣點與公司基本面")

    user_input = st.text_input("輸入股票或 ETF 代碼 (如: 2330, 1314, 0050)", value=st.session_state.selected_symbol)
    symbol = resolve_symbol(user_input)

    # 美化歷史紀錄按鈕列（顯示代碼與中文名稱）
    if st.session_state.history:
        st.caption("⏱️ 最近瀏覽紀錄：")
        h_cols = st.columns(len(st.session_state.history))
        for i, h_sym in enumerate(st.session_state.history):
            with h_cols[i]:
                h_code = h_sym.replace(".TW","").replace(".TWO","")
                h_details = get_company_details(h_sym)
                h_name = h_details["name"][:4]
                btn_label = f"{h_code}\n{h_name}"
                if st.button(btn_label, key=f"hist_{h_sym}", use_container_width=True):
                    select_symbol(h_sym)
                    st.rerun()

    if symbol:
        try:
            ticker = yf.Ticker(symbol)
            df = ticker.history(period="1y")
            details = get_company_details(symbol)

            if df.empty or len(df) < 30:
                st.error("查無資料，請確認輸入代碼正確！")
            else:
                is_etf = symbol.startswith("00") or "ETF" in symbol.upper()

                market_cap_val = details['market_cap']
                market_cap_str = f"{market_cap_val / 1e8:,.1f} 億" if market_cap_val and market_cap_val > 0 else "N/A"
                div_yield = details['dividend_yield']
                div_yield_str = f"{div_yield * 100:.2f}%" if div_yield and div_yield > 0 else "N/A"
                pe_str = f"{details['pe_ratio']:.2f}" if isinstance(details['pe_ratio'], (int, float)) else "N/A"

                st.markdown(f"""
                    <div class="info-box">
                        <div style="font-size: 18px; font-weight: bold; color: #38BDF8; margin-bottom: 6px;">
                            {details['name']} ({symbol})
                        </div>
                        <div style="font-size: 13px; color: #94A3B8; margin-bottom: 10px;">
                            產業類別：{details['sector']} / {details['industry']}
                        </div>
                        <div style="display: flex; justify-content: space-between; text-align: center; margin-bottom: 10px;">
                            <div><span style="color:#94A3B8; font-size:11px;">市值</span><br><b>{market_cap_str}</b></div>
                            <div><span style="color:#94A3B8; font-size:11px;">本益比 (PE)</span><br><b>{pe_str}</b></div>
                            <div><span style="color:#94A3B8; font-size:11px;">殖利率</span><br><b>{div_yield_str}</b></div>
                            <div><span style="color:#94A3B8; font-size:11px;">52週高/低</span><br><b>${details['high_52']} / ${details['low_52']}</b></div>
                        </div>
                        <div style="font-size: 12px; color: #CBD5E1; border-top: 1px solid #334155; padding-top: 8px;">
                            <b>公司簡介：</b> {details['summary'][:150]}...
                        </div>
                    </div>
                """, unsafe_allow_html=True)

                df["MA20"] = df["Close"].rolling(20).mean()
                df["MA60"] = df["Close"].rolling(60).mean()
                df["MA120"] = df["Close"].rolling(120).mean()
                df["STD20"] = df["Close"].rolling(20).std()
                df["Upper"] = df["MA20"] + (df["STD20"] * 2)
                df["Lower"] = df["MA20"] - (df["STD20"] * 2)

                latest = df.iloc[-1]
                close_p = round(latest["Close"], 2)
                ma20_val = round(latest["MA20"], 2)
                ma60_val = round(latest["MA60"], 2)
                ma120_val = round(latest["MA120"], 2) if not pd.isna(latest["MA120"]) else round(ma60_val * 0.95, 2)
                target_sell = round(latest["Upper"], 2)

                if is_etf:
                    c1, c2, c3 = st.columns(3)
                    with c1:
                        st.markdown(f'<div class="trade-card buy-border"><div class="card-title">月線分批</div><div class="card-val" style="color:#10B981">${ma20_val}</div></div>', unsafe_allow_html=True)
                    with c2:
                        st.markdown(f'<div class="trade-card etf-border"><div class="card-title">季線加碼</div><div class="card-val" style="color:#38BDF8">${ma60_val}</div></div>', unsafe_allow_html=True)
                    with c3:
                        st.markdown(f'<div class="trade-card sell-border"><div class="card-title">半年抄底</div><div class="card-val" style="color:#A855F7">${ma120_val}</div></div>', unsafe_allow_html=True)
                else:
                    buy_high = ma20_val
                    stop_loss = round(min(ma60_val * 0.97, latest["Lower"]), 2)

                    c1, c2, c3 = st.columns(3)
                    with c1:
                        st.markdown(f'<div class="trade-card buy-border"><div class="card-title">建議買區</div><div class="card-val" style="color:#10B981">${buy_high}</div></div>', unsafe_allow_html=True)
                    with c2:
                        st.markdown(f'<div class="trade-card sell-border"><div class="card-title">停利目標</div><div class="card-val" style="color:#EF4444">${target_sell}</div></div>', unsafe_allow_html=True)
                    with c3:
                        st.markdown(f'<div class="trade-card stop-border"><div class="card-title">停損設定</div><div class="card-val" style="color:#F59E0B">${stop_loss}</div></div>', unsafe_allow_html=True)

                fig = make_subplots(rows=2, cols=1, shared_xaxes=True, vertical_spacing=0.05, row_width=[0.3, 0.7])
                fig.add_trace(go.Candlestick(x=df.index, open=df['Open'], high=df['High'], low=df['Low'], close=df['Close'], name='K線'), row=1, col=1)
                fig.add_trace(go.Scatter(x=df.index, y=df['MA20'], mode='lines', name='20MA', line=dict(color='#FFD700', width=1)), row=1, col=1)
                fig.add_trace(go.Scatter(x=df.index, y=df['MA60'], mode='lines', name='60MA', line=dict(color='#00FF7F', width=1)), row=1, col=1)
                colors = ['#EF4444' if row['Open'] - row['Close'] >= 0 else '#10B981' for index, row in df.iterrows()]
                fig.add_trace(go.Bar(x=df.index, y=df['Volume'], name='成交量', marker_color=colors), row=2, col=1)
                fig.update_layout(template="plotly_dark", xaxis_rangeslider_visible=False, height=380, margin=dict(l=5, r=5, t=20, b=10), showlegend=False)
                fig.update_xaxes(range=[df.index[-45], df.index[-1]])
                st.plotly_chart(fig, use_container_width=True, config={'displayModeBar': False})

        except Exception as e:
            st.error(f"資料取得失敗：{e}")


# ================= 頁面二：熱門概念股專區 =================
elif st.session_state.nav_page == "🏷️ 熱門概念股專區":
    st.subheader("🏷️ 台股熱門產業概念與基本面專區")
    st.caption("點選板塊即可檢視該群組內所有代表公司的即時行情與基本面數據，點擊「深入分析」可直接切換檢視 K 線：")

    selected_theme = st.selectbox("選擇概念板塊", list(THEME_STOCKS.keys()))

    st.markdown(f"### 📌 {selected_theme} 成分股總覽")

    theme_symbols = THEME_STOCKS[selected_theme]

    for sym in theme_symbols:
        try:
            t = yf.Ticker(sym)
            hist = t.history(period="2d")
            details = get_company_details(sym)
            if len(hist) >= 2:
                cp = hist["Close"].iloc[-1]
                pp = hist["Close"].iloc[-2]
                pct = ((cp - pp) / pp) * 100
                sign = "+" if pct >= 0 else ""
                color = "#10B981" if pct >= 0 else "#EF4444"
                code = sym.replace(".TW", "")
                
                pe_val = f"{details['pe_ratio']:.1f}" if isinstance(details['pe_ratio'], (int, float)) else "N/A"
                div_val = f"{details['dividend_yield']*100:.1f}%" if isinstance(details['dividend_yield'], (int, float)) and details['dividend_yield'] > 0 else "N/A"

                col_info, col_btn = st.columns([2.5, 1])
                with col_info:
                    st.markdown(f"""
                        <div style="font-size:15px; font-weight:bold; color:#FFFFFF;">
                            <span class="tag">股票</span>{code} {details['name']}
                        </div>
                        <div style="font-size:12px; color:#CBD5E1; margin-top: 3px;">
                            市價: <span style="color:#38BDF8; font-weight:bold;">${cp:.2f}</span> | 漲跌: <span style="color:{color}; font-weight:bold;">{sign}{pct:.2f}%</span><br>
                            本益比(PE): <b>{pe_val}</b> | 殖利率: <b>{div_val}</b> | 52週高低: <b>${details['high_52']} / ${details['low_52']}</b>
                        </div>
                    """, unsafe_allow_html=True)
                with col_btn:
                    st.markdown("<br>", unsafe_allow_html=True)
                    if st.button("深入分析", key=f"theme_{sym}", use_container_width=True):
                        select_symbol(sym)
                        st.session_state.nav_page = "📈 即時行情與個股分析"
                        st.rerun()
                st.markdown('<div style="border-bottom: 1px solid #334155; margin: 8px 0;"></div>', unsafe_allow_html=True)
        except:
            st.warning(f"無法取得 {sym} 的相關資訊")

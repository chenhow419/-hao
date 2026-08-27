import streamlit as st
import yfinance as yf
import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots

# ----------------- 1. 頁面設定 & PWA 支援 -----------------
st.set_page_config(
    page_title="股票買點分析儀 Pro",
    page_icon="📈",
    layout="centered",
    initial_sidebar_state="collapsed"
)

# 注入 PWA 與 Mobile App 優化 Meta Header 及自訂 CSS
st.markdown("""
    <head>
        <meta name="apple-mobile-web-app-capable" content="yes">
        <meta name="apple-mobile-web-app-status-bar-style" content="black-translucent">
        <meta name="theme-color" content="#0F172A">
        <link rel="apple-touch-icon" href="https://cdn-icons-png.flaticon.com/512/2422/2422796.png">
    </head>
    <style>
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
    header {visibility: hidden;}
    
    .buy-card {
        background-color: #1E293B;
        border: 2px solid #10B981;
        border-radius: 12px;
        padding: 12px;
        text-align: center;
        margin-bottom: 10px;
    }
    .sell-card {
        background-color: #1E293B;
        border: 2px solid #EF4444;
        border-radius: 12px;
        padding: 12px;
        text-align: center;
        margin-bottom: 10px;
    }
    .stop-card {
        background-color: #1E293B;
        border: 2px solid #F59E0B;
        border-radius: 12px;
        padding: 12px;
        text-align: center;
        margin-bottom: 10px;
    }
    .card-title { font-size: 13px; color: #94A3B8; margin-bottom: 4px; }
    .card-val-green { font-size: 20px; font-weight: bold; color: #10B981; }
    .card-val-red { font-size: 20px; font-weight: bold; color: #EF4444; }
    .card-val-yellow { font-size: 20px; font-weight: bold; color: #F59E0B; }
    
    .metric-badge {
        background-color: #334155;
        color: #E2E8F0;
        padding: 4px 10px;
        border-radius: 6px;
        font-size: 13px;
        margin-right: 6px;
        display: inline-block;
    }
    </style>
""", unsafe_allow_html=True)

# 初始化 Session State
if "history" not in st.session_state:
    st.session_state.history = ["2330.TW", "2382.TW", "0050.TW"]
if "selected_theme" not in st.session_state:
    st.session_state.selected_theme = "🚀 AI 伺服器"
if "selected_symbol" not in st.session_state:
    st.session_state.selected_symbol = "2330.TW"

def select_symbol(sym):
    st.session_state.selected_symbol = sym
    # 更新歷史紀錄 (保持最多 5 筆)
    if sym in st.session_state.history:
        st.session_state.history.remove(sym)
    st.session_state.history.insert(0, sym)
    st.session_state.history = st.session_state.history[:5]

# ----------------- 🎯 常用台股名稱與代碼對照表 -----------------
STOCK_DICT = {
    "台積電": "2330.TW", "鴻海": "2317.TW", "聯發科": "2454.TW", "廣達": "2382.TW",
    "緯創": "3231.TW", "技嘉": "2376.TW", "華城": "1519.TW", "奇鋐": "3017.TW",
    "萬潤": "6187.TWO", "弘塑": "3131.TWO", "聯亞": "3081.TWO", "光聖": "6442.TW",
    "國統": "8936.TWO", "世芯": "3661.TW", "緯穎": "6669.TW",
    "元大台灣50": "0050.TW", "0050": "0050.TW", "元大高股息": "0056.TW", "0056": "0056.TW",
    "國泰永續高股息": "00878.TW", "00878": "00878.TW", "群益台灣精選高息": "00919.TW", "00919": "00919.TW",
    "復華台灣科技優息": "00929.TW", "00929": "00929.TW", "富邦台50": "006208.TW", "006208": "006208.TW"
}

def resolve_symbol(user_input):
    clean_input = user_input.strip()
    if clean_input in STOCK_DICT:
        return STOCK_DICT[clean_input]
    # 若為純數字台股代碼，預設補 .TW
    if clean_input.isdigit():
        if len(clean_input) == 4:
            return f"{clean_input}.TW"
    return clean_input.upper()

# ----------------- 🎯 大盤指數 -----------------
st.subheader("🌐 市場大盤速報")

@st.cache_data(ttl=300)
def get_market_indices():
    indices = {
        "台股加權": "^TWII",
        "道瓊工業": "^DJI",
        "標普500": "^GSPC",
        "那斯達克": "^IXIC"
    }
    data = {}
    for name, sym in indices.items():
        try:
            df_idx = yf.Ticker(sym).history(period="2d")
            if len(df_idx) >= 2:
                close = df_idx["Close"].iloc[-1]
                prev = df_idx["Close"].iloc[-2]
                change_pct = ((close - prev) / prev) * 100
                data[name] = (round(close, 2), round(change_pct, 2))
            else:
                data[name] = ("N/A", 0.0)
        except:
            data[name] = ("N/A", 0.0)
    return data

market_data = get_market_indices()
idx_cols = st.columns(4)
for i, (name, (val, pct)) in enumerate(market_data.items()):
    with idx_cols[i]:
        delta_str = f"+{pct}%" if pct >= 0 else f"{pct}%"
        st.metric(label=name, value=f"{val:,}" if isinstance(val, (int, float)) else val, delta=delta_str)

st.divider()

# ----------------- 🎯 今日強勢/接近漲停股 -----------------
st.subheader("🚨 今日強勢/接近漲停股")

@st.cache_data(ttl=120)
def get_limit_up_stocks():
    watch_list = [
        ("台積電", "2330.TW"), ("鴻海", "2317.TW"), ("廣達", "2382.TW"),
        ("華城", "1519.TW"), ("奇鋐", "3017.TW"), ("萬潤", "6187.TWO"),
        ("弘塑", "3131.TWO"), ("聯亞", "3081.TWO"), ("光聖", "6442.TW"),
        ("世芯-KY", "3661.TW"), ("緯穎", "6669.TW")
    ]
    strong_stocks = []
    for name, sym in watch_list:
        try:
            df_s = yf.Ticker(sym).history(period="2d")
            if len(df_s) >= 2:
                cp = df_s["Close"].iloc[-1]
                pp = df_s["Close"].iloc[-2]
                pct = ((cp - pp) / pp) * 100
                if pct >= 4.0:
                    strong_stocks.append((name, sym, round(cp, 1), round(pct, 2)))
        except:
            pass
    return strong_stocks

strong_list = get_limit_up_stocks()
if strong_list:
    limit_cols = st.columns(min(len(strong_list), 4))
    for idx, (name, sym, p, pct) in enumerate(strong_list[:4]):
        with limit_cols[idx % 4]:
            st.button(
                f"🔥 {name}\n${p} (+{pct}%)", 
                on_click=select_symbol, args=(sym,),
                use_container_width=True,
                key=f"limit_{sym}"
            )
else:
    st.info("💡 目前盤中監控無觸及漲停或強勢衝高之標的。")

st.divider()

# ----------------- 🎯 熱門題材與 ETF 分類 -----------------
st.subheader("🔥 今日熱門題材 & 熱門 ETF")

theme_stocks = {
    "🚀 AI 伺服器": [("廣達", "2382.TW"), ("緯創", "3231.TW"), ("技嘉", "2376.TW"), ("英業達", "2356.TW")],
    "⚡ CoWoS 封裝": [("台積電", "2330.TW"), ("萬潤", "6187.TWO"), ("弘塑", "3131.TWO"), ("辛耘", "3583.TW")],
    "💡 矽光子 (CPO)": [("聯亞", "3081.TWO"), ("華星光", "4979.TWO"), ("光聖", "6442.TW"), ("上銓", "3363.TWO")],
    "📊 高股息 ETF": [("元大高股息", "0056.TW"), ("國泰00878", "00878.TW"), ("復華00929", "00929.TW"), ("群益00919", "00919.TW")],
    "🌐 市值型 ETF": [("元大台灣50", "0050.TW"), ("富邦006208", "006208.TW"), ("費半00830", "00830.TW"), ("S&P00646", "00646.TW")]
}

t_cols = st.columns(len(theme_stocks))
for idx, t_name in enumerate(theme_stocks.keys()):
    with t_cols[idx]:
        st.button(
            t_name, 
            on_click=lambda t=t_name: st.session_state.update({"selected_theme": t}), 
            use_container_width=True,
            type="primary" if st.session_state.selected_theme == t_name else "secondary"
        )

@st.cache_data(ttl=60)
def get_theme_prices(stock_list):
    prices = {}
    for name, sym in stock_list:
        try:
            df_s = yf.Ticker(sym).history(period="2d")
            if len(df_s) >= 2:
                cp = df_s["Close"].iloc[-1]
                pp = df_s["Close"].iloc[-2]
                pct = ((cp - pp) / pp) * 100
                prices[sym] = (round(cp, 2), round(pct, 2))
            else:
                prices[sym] = ("N/A", 0)
        except:
            prices[sym] = ("N/A", 0)
    return prices

current_stocks = theme_stocks[st.session_state.selected_theme]
stock_prices = get_theme_prices(current_stocks)

st.markdown(f"**📌【{st.session_state.selected_theme}】標的：**")
s_cols = st.columns(len(current_stocks))

for idx, (name, sym) in enumerate(current_stocks):
    col = s_cols[idx]
    p, pct = stock_prices.get(sym, ("N/A", 0))
    sign = "+" if pct >= 0 else ""
    btn_label = f"{name}\n${p} ({sign}{pct}%)"
    
    with col:
        st.button(
            btn_label, 
            on_click=select_symbol, args=(sym,),
            use_container_width=True, 
            key=f"stock_btn_{sym}"
        )

st.divider()

# ----------------- 🎯 個股與 ETF 買點 + 基本面 + 風控分析 -----------------
st.subheader("🔍 個股與 ETF 合理買點分析")

# 顯示歷史瀏覽紀錄快捷鈕
if st.session_state.history:
    st.caption("🕒 最近瀏覽歷史：")
    h_cols = st.columns(len(st.session_state.history))
    for idx, h_sym in enumerate(st.session_state.history):
        with h_cols[idx]:
            st.button(h_sym, on_click=select_symbol, args=(h_sym,), key=f"hist_{h_sym}_{idx}")

# 輸入框（支援中文與代碼）
user_input = st.text_input("輸入股票名稱或代碼（支援：台積電、廣達、2330、0050 等）：", value=st.session_state.selected_symbol)
symbol = resolve_symbol(user_input)

if st.button("🚀 開始計算與繪製 K 線圖", use_container_width=True) or symbol:
    with st.spinner("載入數據與基本面分析中..."):
        try:
            ticker = yf.Ticker(symbol)
            df = ticker.history(period="1y", interval="1d")

            if df.empty or len(df) < 60:
                st.error("找不到資料或數據不足，請確認代碼/名稱！")
            else:
                # 記錄到歷史
                if symbol not in st.session_state.history:
                    st.session_state.history.insert(0, symbol)
                    st.session_state.history = st.session_state.history[:5]

                # 技術指標計算
                df["MA20"] = df["Close"].rolling(20).mean()
                df["MA60"] = df["Close"].rolling(60).mean()
                df["STD20"] = df["Close"].rolling(20).std()
                df["Upper_Band"] = df["MA20"] + (df["STD20"] * 2)
                df["Lower_Band"] = df["MA20"] - (df["STD20"] * 2)

                latest = df.iloc[-1]
                close_p = round(latest["Close"], 2)
                ma20_val = round(latest["MA20"], 2)
                ma60_val = round(latest["MA60"], 2)
                
                # 風控與買賣點設定
                buy_low = round(max(ma60_val, ma20_val * 0.98), 2)
                buy_high = ma20_val
                target_sell = round(latest["Upper_Band"], 2)
                stop_loss = round(min(ma60_val * 0.97, latest["Lower_Band"]), 2) # 建議停損點

                # 計算風險報酬比 (R/R Ratio)
                potential_gain = target_sell - close_p
                potential_risk = close_p - stop_loss
                rr_ratio = round(potential_gain / potential_risk, 2) if potential_risk > 0 else 0

                # 基本面速覽抓取
                try:
                    info = ticker.info
                    pe_ratio = round(info.get("trailingPE", 0), 1) if info.get("trailingPE") else "N/A"
                    yield_pct = round(info.get("dividendYield", 0) * 100, 2) if info.get("dividendYield") else "N/A"
                    short_name = info.get("shortName", symbol)
                except:
                    pe_ratio, yield_pct, short_name = "N/A", "N/A", symbol

                # 顯示基本面標籤卡
                st.markdown(f"""
                <div style="margin-bottom: 12px;">
                    <span class="metric-badge">標的：{short_name} ({symbol})</span>
                    <span class="metric-badge">本益比 (PE)：{pe_ratio}</span>
                    <span class="metric-badge">殖利率：{yield_pct}%</span>
                </div>
                """, unsafe_allow_html=True)

                # 三卡片（建議買區、動態停利、建議停損）
                c1, c2, c3 = st.columns(3)
                with c1:
                    st.markdown(f"""
                        <div class="buy-card">
                            <div class="card-title">🟢 建議買入區</div>
                            <div class="card-val-green">{buy_low}~{buy_high}</div>
                        </div>
                    """, unsafe_allow_html=True)
                with c2:
                    st.markdown(f"""
                        <div class="sell-card">
                            <div class="card-title">🔴 動態停利價</div>
                            <div class="card-val-red">{target_sell} 元</div>
                        </div>
                    """, unsafe_allow_html=True)
                with c3:
                    st.markdown(f"""
                        <div class="stop-card">
                            <div class="card-title">🟠 建議停損價</div>
                            <div class="card-val-yellow">{stop_loss} 元</div>
                        </div>
                    """, unsafe_allow_html=True)

                # 風險報酬評估
                if close_p <= buy_high and close_p >= buy_low:
                    st.success(f"🎯 現價 {close_p} 元處於合理買區！風報比 (R/R)：{rr_ratio}（> 1.5 適合分批進場）。")
                elif close_p < buy_low:
                    st.warning(f"⚠️ 現價 {close_p} 元已跌破買區，請確認是否觸及停損點 ({stop_loss} 元)。")
                else:
                    diff_pct = round(((close_p - buy_high) / buy_high) * 100, 1)
                    st.info(f"⏳ 現價 {close_p} 元偏高（高於買區 {diff_pct}%），當前風報比僅 {rr_ratio}，建議等待拉回。")

                # K 線圖繪製 (Plotly 互動式)
                fig = make_subplots(
                    rows=2, cols=1, 
                    shared_xaxes=True, 
                    vertical_spacing=0.03, 
                    subplot_titles=(f'{symbol} 互動 K 線圖', '成交量'),
                    row_width=[0.2, 0.8]
                )

                fig.add_trace(go.Candlestick(
                    x=df.index, open=df['Open'], high=df['High'],
                    low=df['Low'], close=df['Close'], name='K線'
                ), row=1, col=1)

                fig.add_trace(go.Scatter(x=df.index, y=df['MA20'], mode='lines', name='20MA', line=dict(color='#FFD700', width=1.5)), row=1, col=1)
                fig.add_trace(go.Scatter(x=df.index, y=df['MA60'], mode='lines', name='60MA', line=dict(color='#00FF7F', width=1.5)), row=1, col=1)
                fig.add_trace(go.Scatter(x=df.index, y=df['Upper_Band'], mode='lines', name='上軌停利', line=dict(color='#FF3366', width=1.5)), row=1, col=1)

                # 繪製買區區間 (半透明綠色)
                fig.add_hrect(
                    y0=buy_low, y1=buy_high,
                    fillcolor="#00FF7F", opacity=0.15,
                    line_width=0, row=1, col=1,
                    annotation_text="建議買區", annotation_position="top left"
                )

                colors = ['#EF4444' if row['Open'] - row['Close'] >= 0 else '#10B981' for index, row in df.iterrows()]
                fig.add_trace(go.Bar(x=df.index, y=df['Volume'], name='成交量', marker_color=colors), row=2, col=1)

                fig.update_layout(
                    template="plotly_dark",
                    xaxis_rangeslider_visible=False,
                    height=480,
                    margin=dict(l=10, r=10, t=40, b=10),
                    hovermode="x unified"
                )

                last_date = df.index[-1]
                first_date = df.index[-60]
                fig.update_xaxes(range=[first_date, last_date])

                st.plotly_chart(fig, use_container_width=True)

        except Exception as e:
            st.error(f"分析時發生錯誤：{e}")

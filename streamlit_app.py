import streamlit as st
import yfinance as yf
import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots

# ----------------- 1. 頁面設定 & PWA / 美化 UI -----------------
st.set_page_config(
    page_title="股票與 ETF 買點分析儀 Pro",
    page_icon="📈",
    layout="centered",
    initial_sidebar_state="collapsed"
)

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
    
    /* 買賣點卡片 */
    .buy-card { background-color: #1E293B; border: 2px solid #10B981; border-radius: 12px; padding: 12px; text-align: center; margin-bottom: 10px; }
    .sell-card { background-color: #1E293B; border: 2px solid #EF4444; border-radius: 12px; padding: 12px; text-align: center; margin-bottom: 10px; }
    .stop-card { background-color: #1E293B; border: 2px solid #F59E0B; border-radius: 12px; padding: 12px; text-align: center; margin-bottom: 10px; }
    .etf-card { background-color: #1E293B; border: 2px solid #38BDF8; border-radius: 12px; padding: 12px; text-align: center; margin-bottom: 10px; }
    .card-title { font-size: 13px; color: #94A3B8; margin-bottom: 4px; }
    .card-val-green { font-size: 20px; font-weight: bold; color: #10B981; }
    .card-val-red { font-size: 20px; font-weight: bold; color: #EF4444; }
    .card-val-yellow { font-size: 20px; font-weight: bold; color: #F59E0B; }
    .card-val-blue { font-size: 20px; font-weight: bold; color: #38BDF8; }
    
    .metric-badge {
        background-color: #334155;
        color: #E2E8F0;
        padding: 4px 10px;
        border-radius: 6px;
        font-size: 13px;
        margin-right: 6px;
        display: inline-block;
    }

    /* 清單標題列與表頭 */
    .list-header {
        display: flex;
        justify-content: space-between;
        color: #94A3B8;
        font-size: 13px;
        padding: 6px 12px;
        border-bottom: 1px solid #334155;
        margin-bottom: 8px;
    }
    .rank-num-top { font-weight: bold; color: #F97316; font-size: 16px; }
    .rank-num { font-weight: bold; color: #64748B; font-size: 16px; }
    .stock-tag {
        background-color: #334155;
        color: #94A3B8;
        font-size: 10px;
        padding: 2px 6px;
        border-radius: 4px;
        margin-right: 4px;
    }
    </style>
""", unsafe_allow_html=True)

# 初始化 Session State
if "history" not in st.session_state:
    st.session_state.history = ["2330.TW", "2382.TW", "0050.TW"]
if "selected_theme" not in st.session_state:
    st.session_state.selected_theme = "🔥 成交量 Top 5"
if "selected_symbol" not in st.session_state:
    st.session_state.selected_symbol = "2330.TW"

def select_symbol(sym):
    st.session_state.selected_symbol = sym
    if sym in st.session_state.history:
        st.session_state.history.remove(sym)
    st.session_state.history.insert(0, sym)
    st.session_state.history = st.session_state.history[:5]

# ----------------- 🎯 常用台股名稱與代碼對照表 -----------------
STOCK_DICT = {
    "台積電": "2330.TW", "鴻海": "2317.TW", "聯發科": "2454.TW", "廣達": "2382.TW",
    "緯創": "3231.TW", "技嘉": "2376.TW", "華城": "1519.TW", "奇鋐": "3017.TW",
    "萬潤": "6187.TWO", "弘塑": "3131.TWO", "聯亞": "3081.TWO", "光聖": "6442.TW",
    "世芯": "3661.TW", "緯穎": "6669.TW", "英業達": "2356.TW", "辛耘": "3583.TW",
    "華星光": "4979.TWO", "上銓": "3363.TWO",
    # 記憶體族群
    "南亞科": "2408.TW", "華邦電": "2344.TW", "旺宏": "2337.TW", 
    "威剛": "3260.TWO", "群聯": "8299.TWO", "晶豪科": "3006.TW",
    # ETF
    "元大台灣50": "0050.TW", "0050": "0050.TW", "元大高股息": "0056.TW", "0056": "0056.TW",
    "國泰永續高股息": "00878.TW", "00878": "00878.TW", "群益台灣精選高息": "00919.TW", "00919": "00919.TW",
    "復華台灣科技優息": "00929.TW", "00929": "00929.TW", "富邦台50": "006208.TW", "006208": "006208.TW"
}

def resolve_symbol(user_input):
    clean_input = user_input.strip()
    if clean_input in STOCK_DICT:
        return STOCK_DICT[clean_input]
    if clean_input.isdigit() and len(clean_input) == 4:
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

# ----------------- 🎯 監控市場熱門庫（含記憶體族群） -----------------
MONITOR_POOL = [
    ("台積電", "2330.TW"), ("鴻海", "2317.TW"), ("聯發科", "2454.TW"), ("廣達", "2382.TW"),
    ("緯創", "3231.TW"), ("技嘉", "2376.TW"), ("英業達", "2356.TW"), ("華城", "1519.TW"),
    ("奇鋐", "3017.TW"), ("萬潤", "6187.TWO"), ("弘塑", "3131.TWO"), ("辛耘", "3583.TW"),
    ("聯亞", "3081.TWO"), ("華星光", "4979.TWO"), ("光聖", "6442.TW"), ("世芯-KY", "3661.TW"),
    ("緯穎", "6669.TW"),
    # 🔹 記憶體族群
    ("南亞科", "2408.TW"), ("華邦電", "2344.TW"), ("旺宏", "2337.TW"),
    ("威剛", "3260.TWO"), ("群聯", "8299.TWO"), ("晶豪科", "3006.TW"),
    # ETF
    ("0050", "0050.TW"), ("0056", "0056.TW"), ("00878", "00878.TW"),
    ("00919", "00919.TW"), ("00929", "00929.TW"), ("006208", "006208.TW")
]

# 分類題材定義
STATIC_THEMES = {
    "🚀 AI 伺服器": [("廣達", "2382.TW"), ("緯創", "3231.TW"), ("技嘉", "2376.TW"), ("英業達", "2356.TW"), ("緯穎", "6669.TW")],
    "⚡ CoWoS 封裝": [("台積電", "2330.TW"), ("萬潤", "6187.TWO"), ("弘塑", "3131.TWO"), ("辛耘", "3583.TW")],
    "💾 記憶體族群": [("群聯", "8299.TWO"), ("威剛", "3260.TWO"), ("南亞科", "2408.TW"), ("華邦電", "2344.TW"), ("旺宏", "2337.TW")],
    "💡 矽光子 (CPO)": [("聯亞", "3081.TWO"), ("華星光", "4979.TWO"), ("光聖", "6442.TW"), ("上銓", "3363.TWO")],
    "📊 高股息 ETF": [("元大高股息", "0056.TW"), ("國泰00878", "00878.TW"), ("復華00929", "00929.TW"), ("群益00919", "00919.TW")],
    "🌐 市值型 ETF": [("元大台灣50", "0050.TW"), ("富邦006208", "006208.TW")]
}

@st.cache_data(ttl=120)
def fetch_stock_market_status():
    results = {}
    for name, sym in MONITOR_POOL:
        try:
            df = yf.Ticker(sym).history(period="2d")
            if len(df) >= 2:
                cp = df["Close"].iloc[-1]
                pp = df["Close"].iloc[-2]
                vol = df["Volume"].iloc[-1]
                pct = ((cp - pp) / pp) * 100
                results[sym] = {
                    "name": name, "symbol": sym, 
                    "price": round(cp, 2), "pct": round(pct, 2), 
                    "volume": vol
                }
        except:
            pass
    return results

market_status = fetch_stock_market_status()

# ----------------- 🎯 今日即時熱門榜 (卡片式清單 UI) -----------------
st.subheader("🔥 今日市場即時焦點 & 熱門題材")

theme_options = ["🔥 成交量 Top 5", "🚀 漲幅榜 Top 5"] + list(STATIC_THEMES.keys())

# 按鈕導航頁籤
t_cols = st.columns(len(theme_options))
for idx, t_name in enumerate(theme_options):
    with t_cols[idx]:
        st.button(
            t_name, 
            on_click=lambda t=t_name: st.session_state.update({"selected_theme": t}), 
            use_container_width=True,
            type="primary" if st.session_state.selected_theme == t_name else "secondary"
        )

# 篩選資料
selected_mode = st.session_state.selected_theme
display_stocks = []

if selected_mode == "🔥 成交量 Top 5":
    sorted_by_vol = sorted(market_status.values(), key=lambda x: x["volume"], reverse=True)
    display_stocks = [(x["name"], x["symbol"], x["price"], x["pct"]) for x in sorted_by_vol[:5]]

elif selected_mode == "🚀 漲幅榜 Top 5":
    sorted_by_pct = sorted(market_status.values(), key=lambda x: x["pct"], reverse=True)
    display_stocks = [(x["name"], x["symbol"], x["price"], x["pct"]) for x in sorted_by_pct[:5]]

else:
    raw_list = STATIC_THEMES[selected_mode]
    temp_list = []
    for name, sym in raw_list:
        if sym in market_status:
            info = market_status[sym]
            temp_list.append((info["name"], info["symbol"], info["price"], info["pct"]))
        else:
            temp_list.append((name, sym, "N/A", 0))
    display_stocks = sorted(temp_list, key=lambda x: x[3] if isinstance(x[3], (int, float)) else -999, reverse=True)

# ----------------- 📱 仿 App 清單式渲染 -----------------
st.markdown(f"**📌【{selected_mode}】即時行情列表：**")

# 表頭
h_c1, h_c2, h_c3, h_c4 = st.columns([1, 4, 3, 3])
with h_c1: st.caption("名次")
with h_c2: st.caption("股票 / 代碼")
with h_c3: st.caption("收盤價")
with h_c4: st.caption("漲跌幅")

# 逐列繪製清單卡片
for idx, (name, sym, price, pct) in enumerate(display_stocks[:5]):
    rank_str = str(idx + 1)
    rank_class = "rank-num-top" if idx < 3 else "rank-num"
    
    # 漲跌顏色判斷
    if isinstance(pct, (int, float)):
        sign = "+" if pct >= 0 else ""
        color_style = "color: #10B981;" if pct >= 0 else "color: #EF4444;"
        pct_str = f"{sign}{pct}%"
    else:
        color_style = "color: #94A3B8;"
        pct_str = "N/A"

    code_clean = sym.replace(".TW", "").replace(".TWO", "")
    type_tag = "ETF" if code_clean.startswith("00") else "股票"

    # 用按鈕包裹整行，點擊即可切換
    c1, c2, c3, c4 = st.columns([1, 4, 3, 3])
    with c1:
        st.markdown(f'<div class="{rank_class}" style="padding-top: 8px;">{rank_str}</div>', unsafe_allow_html=True)
    with c2:
        st.markdown(f'**{name}**<br><span class="stock-tag">{type_tag}</span><span style="color:#94A3B8; font-size:12px;">{code_clean}</span>', unsafe_allow_html=True)
    with c3:
        st.markdown(f'<div style="font-weight: bold; font-size: 16px; padding-top: 8px;">${price}</div>', unsafe_allow_html=True)
    with c4:
        # 切換按鈕包含漲跌幅
        st.button(
            f"{pct_str} ➔", 
            on_click=select_symbol, args=(sym,), 
            key=f"row_btn_{sym}_{idx}",
            use_container_width=True
        )
    st.markdown('<div style="border-bottom: 1px solid #1E293B; margin: 4px 0 8px 0;"></div>', unsafe_allow_html=True)

st.divider()

# ----------------- 🎯 個股與 ETF 買點 + 基本面 + 風控分析 -----------------
st.subheader("🔍 個股與 ETF 合理買點分析")

if st.session_state.history:
    st.caption("🕒 最近瀏覽歷史：")
    h_cols = st.columns(len(st.session_state.history))
    for idx, h_sym in enumerate(st.session_state.history):
        with h_cols[idx]:
            st.button(h_sym, on_click=select_symbol, args=(h_sym,), key=f"hist_{h_sym}_{idx}")

user_input = st.text_input("輸入股票/ETF名稱或代碼：", value=st.session_state.selected_symbol)
symbol = resolve_symbol(user_input)

if st.button("🚀 開始計算與繪製 K 線圖", use_container_width=True) or symbol:
    with st.spinner("載入數據與策略分析中..."):
        try:
            ticker = yf.Ticker(symbol)
            df = ticker.history(period="1y", interval="1d")

            if df.empty or len(df) < 60:
                st.error("找不到資料或數據不足，請確認代碼/名稱！")
            else:
                if symbol not in st.session_state.history:
                    st.session_state.history.insert(0, symbol)
                    st.session_state.history = st.session_state.history[:5]

                is_etf = symbol.startswith("00") or "ETF" in symbol

                # 技術指標計算
                df["MA20"] = df["Close"].rolling(20).mean()   # 月線
                df["MA60"] = df["Close"].rolling(60).mean()   # 季線
                df["MA120"] = df["Close"].rolling(120).mean() # 半年線
                df["STD20"] = df["Close"].rolling(20).std()
                df["Upper_Band"] = df["MA20"] + (df["STD20"] * 2)
                df["Lower_Band"] = df["MA20"] - (df["STD20"] * 2)

                latest = df.iloc[-1]
                close_p = round(latest["Close"], 2)
                ma20_val = round(latest["MA20"], 2)
                ma60_val = round(latest["MA60"], 2)
                ma120_val = round(latest["MA120"], 2) if not pd.isna(latest["MA120"]) else round(ma60_val * 0.95, 2)
                target_sell = round(latest["Upper_Band"], 2)

                try:
                    info = ticker.info
                    yield_pct = round(info.get("dividendYield", 0) * 100, 2) if info.get("dividendYield") else "N/A"
                    short_name = info.get("shortName", symbol)
                except:
                    yield_pct, short_name = "N/A", symbol

                # ----------------- A. ETF 模式 -----------------
                if is_etf:
                    st.markdown(f"""
                    <div style="margin-bottom: 12px;">
                        <span class="metric-badge">標的：{short_name} ({symbol})</span>
                        <span class="metric-badge">類別：ETF (免停損 / 長線佈局)</span>
                        <span class="metric-badge">預估殖利率：{yield_pct}%</span>
                    </div>
                    """, unsafe_allow_html=True)

                    c1, c2, c3 = st.columns(3)
                    with c1:
                        st.markdown(f"""
                            <div class="buy-card">
                                <div class="card-title">🟢 一階：月線分批價</div>
                                <div class="card-val-green">{ma20_val} 元</div>
                            </div>
                        """, unsafe_allow_html=True)
                    with c2:
                        st.markdown(f"""
                            <div class="etf-card">
                                <div class="card-title">🔵 二階：季線加碼價</div>
                                <div class="card-val-blue">{ma60_val} 元</div>
                            </div>
                        """, unsafe_allow_html=True)
                    with c3:
                        st.markdown(f"""
                            <div class="sell-card" style="border-color: #A855F7;">
                                <div class="card-title" style="color: #E9D5FF;">🟣 三階：半年線抄底價</div>
                                <div class="card-val-red" style="color: #A855F7;">{ma120_val} 元</div>
                            </div>
                        """, unsafe_allow_html=True)

                    if close_p <= ma120_val:
                        st.success(f"🔥 現價 {close_p} 元已落入「半年線抄底區」({ma120_val}元)，歷史經驗為極佳長線佈局時機！")
                    elif close_p <= ma60_val:
                        st.success(f"🎯 現價 {close_p} 元已進入「季線加碼區」({ma60_val}元)，可大幅增加扣款/買進比重！")
                    elif close_p <= ma20_val:
                        st.info(f"👍 現價 {close_p} 元進入「月線合理區」({ma20_val}元)，適合定期定額或小額分批建立部位。")
                    else:
                        st.warning(f"⏳ 現價 {close_p} 元高於月線 ({ma20_val}元)，建議維持定期定額，不必急著單筆追高。")

                # ----------------- B. 個股模式 -----------------
                else:
                    buy_low = round(max(ma60_val, ma20_val * 0.98), 2)
                    buy_high = ma20_val
                    stop_loss = round(min(ma60_val * 0.97, latest["Lower_Band"]), 2)

                    potential_gain = target_sell - close_p
                    potential_risk = close_p - stop_loss
                    rr_ratio = round(potential_gain / potential_risk, 2) if potential_risk > 0 else 0

                    try:
                        pe_ratio = round(ticker.info.get("trailingPE", 0), 1) if ticker.info.get("trailingPE") else "N/A"
                    except:
                        pe_ratio = "N/A"

                    st.markdown(f"""
                    <div style="margin-bottom: 12px;">
                        <span class="metric-badge">標的：{short_name} ({symbol})</span>
                        <span class="metric-badge">本益比 (PE)：{pe_ratio}</span>
                        <span class="metric-badge">殖利率：{yield_pct}%</span>
                    </div>
                    """, unsafe_allow_html=True)

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

                    if close_p <= buy_high and close_p >= buy_low:
                        st.success(f"🎯 現價 {close_p} 元處於合理買區！風報比 (R/R)：{rr_ratio}（> 1.5 適合分批進場）。")
                    elif close_p < buy_low:
                        st.warning(f"⚠️ 現價 {close_p} 元已跌破買區，請確認是否觸及停損點 ({stop_loss} 元)。")
                    else:
                        diff_pct = round(((close_p - buy_high) / buy_high) * 100, 1)
                        st.info(f"⏳ 現價 {close_p} 元偏高（高於買區 {diff_pct}%），當前風報比僅 {rr_ratio}，建議等待拉回。")

                # ----------------- K 線圖繪製 -----------------
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

                fig.add_trace(go.Scatter(x=df.index, y=df['MA20'], mode='lines', name='20MA (月線)', line=dict(color='#FFD700', width=1.5)), row=1, col=1)
                fig.add_trace(go.Scatter(x=df.index, y=df['MA60'], mode='lines', name='60MA (季線)', line=dict(color='#00FF7F', width=1.5)), row=1, col=1)
                fig.add_trace(go.Scatter(x=df.index, y=df['MA120'], mode='lines', name='120MA (半年線)', line=dict(color='#A855F7', width=1.5)), row=1, col=1)

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

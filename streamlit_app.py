import streamlit as st
import yfinance as yf
import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots

# 1. 頁面設定
st.set_page_config(
    page_title="股票買點分析儀",
    page_icon="📈",
    layout="centered",
    initial_sidebar_state="collapsed"
)

# 自訂 CSS 手機最佳化與高對比卡片
st.markdown("""
    <style>
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
    header {visibility: hidden;}
    
    .buy-card {
        background-color: #1E293B;
        border: 2px solid #10B981;
        border-radius: 12px;
        padding: 15px;
        text-align: center;
        margin-bottom: 15px;
    }
    .buy-title { font-size: 14px; color: #94A3B8; margin-bottom: 5px; }
    .buy-price { font-size: 22px; font-weight: bold; color: #10B981; }
    .sell-price { font-size: 22px; font-weight: bold; color: #EF4444; }
    
    /* 修正熱門題材對比度 */
    .topic-box {
        background: linear-gradient(135deg, #1e293b 0%, #0f172a 100%);
        border: 1px solid #38bdf8;
        border-radius: 10px;
        padding: 12px 16px;
        margin-bottom: 15px;
        color: #f8fafc;
    }
    .topic-title { color: #38bdf8; font-weight: bold; font-size: 16px; margin-bottom: 6px; }
    .topic-content { color: #f1f5f9; font-size: 14px; line-height: 1.6; }
    .tag {
        background-color: #334155;
        color: #fef08a;
        padding: 3px 8px;
        border-radius: 6px;
        font-size: 13px;
        margin-right: 5px;
        display: inline-block;
        margin-top: 4px;
    }
    </style>
""", unsafe_allow_html=True)

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

# ----------------- 🎯 今日熱門題材 -----------------
st.subheader("🔥 今日熱門題材焦點")

st.markdown("""
<div class="topic-box">
    <div class="topic-title">🚀 資金聚焦主線</div>
    <div class="topic-content">
        <span class="tag">AI 伺服器</span>
        <span class="tag">CoWoS 先進封裝</span>
        <span class="tag">矽光子 (CPO)</span>
        <span class="tag">重電綠能</span>
        <span class="tag">水資源概念</span>
    </div>
</div>
""", unsafe_allow_html=True)

# ----------------- 🎯 注意焦點股（含即時股價點擊） -----------------
st.subheader("⚠️ 觀察警示/焦點股（點擊切換分析）")

# Session State 管理
if "selected_symbol" not in st.session_state:
    st.session_state.selected_symbol = "2330.TW"

def select_stock(sym):
    st.session_state.selected_symbol = sym

# 焦點股清單
focus_stocks = [
    ("台積電", "2330.TW"),
    ("鴻海", "2317.TW"),
    ("聯發科", "2454.TW"),
    ("廣達", "2382.TW"),
    ("緯創", "3231.TW"),
    ("奇鋐", "3017.TW")
]

# 批次抓取焦點股即時股價
@st.cache_data(ttl=60)
def get_focus_prices():
    prices = {}
    for name, sym in focus_stocks:
        try:
            df_s = yf.Ticker(sym).history(period="2d")
            if len(df_s) >= 2:
                cp = df_s["Close"].iloc[-1]
                pp = df_s["Close"].iloc[-2]
                pct = ((cp - pp) / pp) * 100
                prices[sym] = (round(cp, 1), round(pct, 2))
            else:
                prices[sym] = ("N/A", 0)
        except:
            prices[sym] = ("N/A", 0)
    return prices

focus_prices = get_focus_prices()

# 以 3 欄式按鈕呈現焦點股與即時股價
f_cols = st.columns(3)
for idx, (name, sym) in enumerate(focus_stocks):
    col = f_cols[idx % 3]
    p, pct = focus_prices.get(sym, ("N/A", 0))
    sign = "+" if pct >= 0 else ""
    btn_label = f"{name} ({sym.split('.')[0]})\n${p} ({sign}{pct}%)"
    
    with col:
        st.button(btn_label, on_click=select_stock, args=(sym,), use_container_width=True, key=f"btn_{sym}")

st.divider()

# ----------------- 🎯 個股買點分析 -----------------
st.subheader("🔍 個股合理買點分析")

symbol = st.text_input("輸入股票代碼：", value=st.session_state.selected_symbol).upper().strip()

if st.button("🚀 開始計算與繪製 K 線圖", use_container_width=True) or symbol:
    with st.spinner("載入數據中..."):
        try:
            ticker = yf.Ticker(symbol)
            df = ticker.history(period="1y", interval="1d")

            if df.empty or len(df) < 60:
                st.error("找不到資料或數據不足，請確認代碼！")
            else:
                # 指標計算
                df["MA20"] = df["Close"].rolling(20).mean()
                df["MA60"] = df["Close"].rolling(60).mean()
                df["STD20"] = df["Close"].rolling(20).std()
                df["Upper_Band"] = df["MA20"] + (df["STD20"] * 2)

                latest = df.iloc[-1]
                close_p = round(latest["Close"], 2)
                ma20_val = round(latest["MA20"], 2)
                ma60_val = round(latest["MA60"], 2)
                target_sell = round(latest["Upper_Band"], 2)

                buy_low = round(max(ma60_val, ma20_val * 0.98), 2)
                buy_high = ma20_val

                col1, col2 = st.columns(2)
                with col1:
                    st.markdown(f"""
                        <div class="buy-card">
                            <div class="buy-title">🟢 建議買入區間</div>
                            <div class="buy-price">{buy_low} ~ {buy_high} 元</div>
                        </div>
                    """, unsafe_allow_html=True)
                
                with col2:
                    st.markdown(f"""
                        <div class="buy-card" style="border-color: #EF4444;">
                            <div class="buy-title">🔴 動態停利目標</div>
                            <div class="sell-price">{target_sell} 元</div>
                        </div>
                    """, unsafe_allow_html=True)

                if close_p <= buy_high and close_p >= buy_low:
                    st.success(f"🎯 現價 {close_p} 元已進入合理買點區，可分批佈局！")
                elif close_p < buy_low:
                    st.warning(f"⚠️ 現價 {close_p} 元低於買區，留意破位風險，勿急著接刀。")
                else:
                    diff_pct = round(((close_p - buy_high) / buy_high) * 100, 1)
                    st.info(f"⏳ 現價 {close_p} 元偏高（高於買區 {diff_pct}%），建議等待拉回。")

                # K 線圖繪製 (Plotly 拖動式)
                fig = make_subplots(
                    rows=2, cols=1, 
                    shared_xaxes=True, 
                    vertical_spacing=0.03, 
                    subplot_titles=(f'{symbol} 互動 K 線圖', '成交量'),
                    row_width=[0.2, 0.8]
                )

                fig.add_trace(go.Candlestick(
                    x=df.index,
                    open=df['Open'], high=df['High'],
                    low=df['Low'], close=df['Close'],
                    name='K線'
                ), row=1, col=1)

                fig.add_trace(go.Scatter(x=df.index, y=df['MA20'], mode='lines', name='20MA', line=dict(color='#FFD700', width=1.5)), row=1, col=1)
                fig.add_trace(go.Scatter(x=df.index, y=df['MA60'], mode='lines', name='60MA', line=dict(color='#00FF7F', width=1.5)), row=1, col=1)
                fig.add_trace(go.Scatter(x=df.index, y=df['Upper_Band'], mode='lines', name='上軌停利', line=dict(color='#FF3366', width=1.5)), row=1, col=1)

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
                    height=500,
                    margin=dict(l=10, r=10, t=40, b=10),
                    hovermode="x unified"
                )

                last_date = df.index[-1]
                first_date = df.index[-60]
                fig.update_xaxes(range=[first_date, last_date])

                st.plotly_chart(fig, use_container_width=True)

        except Exception as e:
            st.error(f"分析時發生錯誤：{e}")

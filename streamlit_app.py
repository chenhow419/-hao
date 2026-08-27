import streamlit as st
import yfinance as yf
import pandas as pd
import plotly.graph_objects as gg
from plotly.subplots import make_subplots

# 1. 頁面設定
st.set_page_config(
    page_title="股票買點分析儀",
    page_icon="📈",
    layout="centered",
    initial_sidebar_state="collapsed"
)

# 自訂 CSS 手機最佳化與卡片
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
    
    .info-box {
        background-color: #0F172A;
        border-left: 4px solid #3B82F6;
        padding: 10px 15px;
        border-radius: 4px;
        margin-bottom: 15px;
        font-size: 14px;
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

# ----------------- 🎯 今日熱門題材與注意股 -----------------
st.subheader("🔥 今日熱門題材 & 市場焦點")

st.markdown("""
<div class="info-box">
    <b>🚀 市場聚焦題材：</b> AI 伺服器、半導體先進封裝 (CoWoS)、矽光子 (CPO)、綠能與重電、水資源概念股<br><br>
    <b>⚠️ 觀察警示/注意焦點股：</b> 2330 台積電、2317 鴻海、2454 聯發科、2382 廣達、3231 緯創、3017 奇鋐
</div>
""", unsafe_allow_html=True)

st.divider()

# ----------------- 🎯 個股買點分析 (含互動式圖表) -----------------
st.subheader("🔍 個股合理買點分析")

# 手機輸入欄位
symbol = st.text_input("輸入股票代碼（台股請加 .TW，美股直接輸入代碼）：", value="2330.TW").upper().strip()

if st.button("🚀 開始計算與繪製 K 線圖", use_container_width=True) or symbol:
    with st.spinner("載入數據與產生互動圖表中..."):
        try:
            ticker = yf.Ticker(symbol)
            # 抓取 1 年資料以利在圖表上拉動歷史
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

                # 買價下限與上限
                buy_low = round(max(ma60_val, ma20_val * 0.98), 2)
                buy_high = ma20_val

                # 高對比 PWA 卡片顯示
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

                # 即時建議
                if close_p <= buy_high and close_p >= buy_low:
                    st.success(f"🎯 現價 {close_p} 元已進入合理買點區，可分批佈局！")
                elif close_p < buy_low:
                    st.warning(f"⚠️ 現價 {close_p} 元低於買區，留意破位風險，勿急著接刀。")
                else:
                    diff_pct = round(((close_p - buy_high) / buy_high) * 100, 1)
                    st.info(f"⏳ 現價 {close_p} 元偏高（高於買區 {diff_pct}%），建議等待拉回。")

                # ----------------- 🎯 Plotly 可拖動互動 K 線圖 -----------------
                fig = make_subplots(
                    rows=2, cols=1, 
                    shared_xaxes=True, 
                    vertical_spacing=0.03, 
                    subplot_titles=(f'{symbol} 互動 K 線圖 (包含買點區間)', '成交量'),
                    row_width=[0.2, 0.8]
                )

                # K 線
                fig.add_trace(gg.Candlestick(
                    x=df.index,
                    open=df['Open'], high=df['High'],
                    low=df['Low'], close=df['Close'],
                    name='K線'
                ), row=1, col=1)

                # 均線與布林通道
                fig.add_trace(gg.Scatter(x=df.index, y=df['MA20'], mode='lines', name='20MA (月線)', line=dict(color='#FFD700', width=1.5)), row=1, col=1)
                fig.add_trace(gg.Scatter(x=df.index, y=df['MA60'], mode='lines', name='60MA (季線)', line=dict(color='#00FF7F', width=1.5)), row=1, col=1)
                fig.add_trace(gg.Scatter(x=df.index, y=df['Upper_Band'], mode='lines', name='上軌停利', line=dict(color='#FF3366', width=1.5)), row=1, col=1)

                # 畫出綠色半透明買點區間帶
                fig.add_hrect(
                    y0=buy_low, y1=buy_high,
                    fillcolor="#00FF7F", opacity=0.15,
                    line_width=0, row=1, col=1,
                    annotation_text="建議買區", annotation_position="top left"
                )

                # 成交量
                colors = ['#EF4444' if row['Open'] - row['Close'] >= 0 else '#10B981' for index, row in df.iterrows()]
                fig.add_trace(gg.Bar(x=df.index, y=df['Volume'], name='成交量', marker_color=colors), row=2, col=1)

                # 圖表版面配置（開啟時間軸滑桿，利於拖拉）
                fig.update_layout(
                    template="plotly_dark",
                    xaxis_rangeslider_visible=False, # 關閉底下重複的小縮略圖以節省手機空間
                    height=500,
                    margin=dict(l=10, r=10, t=40, b=10),
                    hovermode="x unified"
                )

                # 預設圖表縮放顯示最近 3 個月，但可以往左滑動看整年
                last_date = df.index[-1]
                first_date = df.index[-60]
                fig.update_xaxes(range=[first_date, last_date])

                st.plotly_chart(fig, use_container_width=True)

        except Exception as e:
            st.error(f"分析時發生錯誤：{e}")

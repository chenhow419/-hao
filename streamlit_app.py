import streamlit as st
import yfinance as yf
import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots

# ----------------- 1. 頁面設定 & 手機 App UI 樣式優化 -----------------
st.set_page_config(
    page_title="股市 Pro",
    page_icon="📈",
    layout="centered",
    initial_sidebar_state="collapsed"
)

# 極致手機端 CSS 優化
st.markdown("""
    <style>
    /* 隱藏預設元件 */
    #MainMenu, footer, header {visibility: hidden;}
    .block-container {
        padding-top: 1rem !important;
        padding-bottom: 2rem !important;
        padding-left: 0.8rem !important;
        padding-right: 0.8rem !important;
    }
    
    /* 全域 App 深色主題 */
    body { background-color: #0F172A; }
    
    /* 手機卡片樣式 */
    .app-card {
        background-color: #1E293B;
        border-radius: 10px;
        padding: 10px 12px;
        margin-bottom: 8px;
        border: 1px solid #334155;
    }
    
    /* 買賣價卡片 */
    .trade-card {
        background-color: #1E293B;
        border-radius: 10px;
        padding: 10px;
        text-align: center;
        margin-bottom: 8px;
    }
    .buy-border { border: 1.5px solid #10B981; }
    .sell-border { border: 1.5px solid #EF4444; }
    .stop-border { border: 1.5px solid #F59E0B; }
    .etf-border { border: 1.5px solid #38BDF8; }
    
    .card-title { font-size: 11px; color: #94A3B8; margin-bottom: 2px; }
    .card-val { font-size: 16px; font-weight: bold; }
    
    /* 標籤 Tag */
    .tag {
        background-color: #334155;
        color: #CBD5E1;
        font-size: 10px;
        padding: 2px 5px;
        border-radius: 4px;
        margin-right: 4px;
    }
    </style>
""", unsafe_allow_html=True)

# 初始化狀態
if "history" not in st.session_state:
    st.session_state.history = ["2330.TW", "0050.TW"]
if "selected_symbol" not in st.session_state:
    st.session_state.selected_symbol = "2330.TW"

def select_symbol(sym):
    st.session_state.selected_symbol = sym
    if sym in st.session_state.history:
        st.session_state.history.remove(sym)
    st.session_state.history.insert(0, sym)
    st.session_state.history = st.session_state.history[:5]

# 代碼解析
def resolve_symbol(user_input):
    clean = user_input.strip().upper()
    if clean.isdigit():
        return f"{clean}.TW"
    return clean

# ----------------- 2. 動態爬取熱門台股/ETF -----------------
# 廣泛監控池（自動從中爬取當日即時數據並重新動態排名）
HOT_POOL = [
    "2330.TW", "2317.TW", "2454.TW", "2382.TW", "3231.TW", 
    "2376.TW", "2603.TW", "2609.TW", "2615.TW", "3037.TW",
    "2408.TW", "2344.TW", "3260.TWO", "8299.TWO",
    "0050.TW", "0056.TW", "00878.TW", "00919.TW", "00929.TW", "006208.TW"
]

@st.cache_data(ttl=300)
def fetch_dynamic_hot_stocks():
    data_list = []
    for sym in HOT_POOL:
        try:
            t = yf.Ticker(sym)
            hist = t.history(period="2d")
            if len(hist) >= 2:
                cp = hist["Close"].iloc[-1]
                pp = hist["Close"].iloc[-2]
                vol = hist["Volume"].iloc[-1]
                pct = ((cp - pp) / pp) * 100
                
                # 簡化顯示名稱
                name = sym.replace(".TW", "").replace(".TWO", "")
                data_list.append({
                    "symbol": sym,
                    "code": name,
                    "price": round(cp, 2),
                    "pct": round(pct, 2),
                    "volume": vol
                })
        except:
            pass
    return data_list

# ----------------- 3. 大盤行情與熱門榜 -----------------
st.title("📈 股市行情 Pro")

# 動態抓取熱門股
raw_hot_data = fetch_dynamic_hot_stocks()

# 頁籤選單（手機端適合橫向選擇器）
tab_choice = st.radio("熱門排行", ["🔥 動態熱門成交量", "🚀 動態今日漲幅榜"], horizontal=True, label_visibility="collapsed")

if tab_choice == "🔥 動態熱門成交量":
    sorted_stocks = sorted(raw_hot_data, key=lambda x: x["volume"], reverse=True)[:5]
else:
    sorted_stocks = sorted(raw_hot_data, key=lambda x: x["pct"], reverse=True)[:5]

st.caption("📱 點擊下方股票列，直接載入 K 線分析：")

# 仿 App 列表渲染（適合手機直向閱讀）
for idx, item in enumerate(sorted_stocks):
    color = "#10B981" if item["pct"] >= 0 else "#EF4444"
    sign = "+" if item["pct"] >= 0 else ""
    tag_type = "ETF" if item["code"].startswith("00") else "股票"
    
    col_info, col_btn = st.columns([2, 1])
    with col_info:
        st.markdown(f"""
            <div style="font-size:15px; font-weight:bold; color:#F8FAFC;">
                <span class="tag">{tag_type}</span>{item['code']}
            </div>
            <div style="font-size:12px; color:#94A3B8;">
                成交價: <span style="color:#FFF;">${item['price']}</span>
            </div>
        """, unsafe_allow_html=True)
    with col_btn:
        st.button(
            f"{sign}{item['pct']}%",
            key=f"hot_{item['symbol']}_{idx}",
            on_click=select_symbol,
            args=(item['symbol'],),
            use_container_width=True
        )
    st.markdown('<div style="border-bottom: 1px solid #1E293B; margin: 4px 0;"></div>', unsafe_allow_html=True)

st.divider()

# ----------------- 4. 個股與 ETF 個別分析 -----------------
st.subheader("🔍 個股 / ETF 買賣點與風控")

# 搜尋輸入與歷史紀錄
user_input = st.text_input("輸入股票或 ETF 代碼 (如: 2330, 0050)", value=st.session_state.selected_symbol)
symbol = resolve_symbol(user_input)

# 最近瀏覽 (手機端縮小按鈕)
if st.session_state.history:
    st.caption("最近瀏覽：")
    h_cols = st.columns(len(st.session_state.history))
    for i, h_sym in enumerate(st.session_state.history):
        with h_cols[i]:
            st.button(h_sym.replace(".TW",""), on_click=select_symbol, args=(h_sym,), key=f"hist_{h_sym}")

if symbol:
    try:
        ticker = yf.Ticker(symbol)
        df = ticker.history(period="1y")

        if df.empty or len(df) < 30:
            st.error("查無資料，請確認輸入代碼正確！")
        else:
            is_etf = symbol.startswith("00") or "ETF" in symbol.upper()

            # 指標計算
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

            # ----------------- 手機 2x2 或 3欄卡片渲染 -----------------
            if is_etf:
                st.info(f"📊 標的：{symbol} | 當前市價：${close_p} (ETF 模式)")
                c1, c2, c3 = st.columns(3)
                with c1:
                    st.markdown(f'<div class="trade-card buy-border"><div class="card-title">月線分批</div><div class="card-val" style="color:#10B981">${ma20_val}</div></div>', unsafe_allow_html=True)
                with c2:
                    st.markdown(f'<div class="trade-card etf-border"><div class="card-title">季線加碼</div><div class="card-val" style="color:#38BDF8">${ma60_val}</div></div>', unsafe_allow_html=True)
                with c3:
                    st.markdown(f'<div class="trade-card sell-border"><div class="card-title">半年抄底</div><div class="card-val" style="color:#A855F7">${ma120_val}</div></div>', unsafe_allow_html=True)
            else:
                buy_low = round(max(ma60_val, ma20_val * 0.98), 2)
                buy_high = ma20_val
                stop_loss = round(min(ma60_val * 0.97, latest["Lower"]), 2)

                st.info(f"📌 標的：{symbol} | 當前市價：${close_p}")
                c1, c2, c3 = st.columns(3)
                with c1:
                    st.markdown(f'<div class="trade-card buy-border"><div class="card-title">建議買區</div><div class="card-val" style="color:#10B981">${buy_high}</div></div>', unsafe_allow_html=True)
                with c2:
                    st.markdown(f'<div class="trade-card sell-border"><div class="card-title">停利目標</div><div class="card-val" style="color:#EF4444">${target_sell}</div></div>', unsafe_allow_html=True)
                with c3:
                    st.markdown(f'<div class="trade-card stop-border"><div class="card-title">停損設定</div><div class="card-val" style="color:#F59E0B">${stop_loss}</div></div>', unsafe_allow_html=True)

            # ----------------- K 線圖（適應手機高寬比） -----------------
            fig = make_subplots(rows=2, cols=1, shared_xaxes=True, vertical_spacing=0.05, row_width=[0.3, 0.7])
            
            # K線
            fig.add_trace(go.Candlestick(
                x=df.index, open=df['Open'], high=df['High'],
                low=df['Low'], close=df['Close'], name='K線'
            ), row=1, col=1)
            
            # 均線
            fig.add_trace(go.Scatter(x=df.index, y=df['MA20'], mode='lines', name='20MA', line=dict(color='#FFD700', width=1)), row=1, col=1)
            fig.add_trace(go.Scatter(x=df.index, y=df['MA60'], mode='lines', name='60MA', line=dict(color='#00FF7F', width=1)), row=1, col=1)

            # 成交量
            colors = ['#EF4444' if row['Open'] - row['Close'] >= 0 else '#10B981' for index, row in df.iterrows()]
            fig.add_trace(go.Bar(x=df.index, y=df['Volume'], name='成交量', marker_color=colors), row=2, col=1)

            fig.update_layout(
                template="plotly_dark",
                xaxis_rangeslider_visible=False,
                height=380, # 降低圖表高度以適應手機螢幕
                margin=dict(l=5, r=5, t=20, b=10),
                showlegend=False # 隱藏圖例省空間
            )
            
            # 預設看近 45 天數據
            fig.update_xaxes(range=[df.index[-45], df.index[-1]])
            st.plotly_chart(fig, use_container_width=True, config={'displayModeBar': False})

    except Exception as e:
        st.error(f"資料取得失敗：{e}")

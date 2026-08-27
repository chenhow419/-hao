import streamlit as st
import yfinance as yf
import pandas as pd
import requests
from bs4 import BeautifulSoup
import plotly.graph_objects as go
from plotly.subplots import make_subplots

# ----------------- 1. 頁面設定 & 手機 App UI 樣式優化 -----------------
st.set_page_config(
    page_title="股市 Pro",
    page_icon="📈",
    layout="centered",
    initial_sidebar_state="collapsed"
)

st.markdown("""
    <style>
    #MainMenu, footer, header {visibility: hidden;}
    .block-container {
        padding-top: 1rem !important;
        padding-bottom: 2rem !important;
        padding-left: 0.8rem !important;
        padding-right: 0.8rem !important;
    }
    body, p, span, div { color: #F8FAFC !important; }
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
    .card-title { font-size: 11px; color: #94A3B8 !important; margin-bottom: 2px; }
    .card-val { font-size: 16px; font-weight: bold; }
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

# ----------------- 2. 真正動態爬取 Yahoo 股市即時熱門成交量排行 -----------------
@st.cache_data(ttl=300)
def fetch_realtime_hot_stocks():
    """透過網路爬蟲自動抓取當前 Yahoo 股市成交量排行前幾名"""
    hot_symbols = []
    try:
        url = "https://tw.stock.yahoo.com/rank/volume"
        headers = {"User-Agent": "Mozilla/5.0"}
        res = requests.get(url, headers=headers, timeout=5)
        soup = BeautifulSoup(res.text, "html.parser")
        
        items = soup.find_all("div", class_="Box-MS(a) Pos(r)")
        for item in items[:10]:
            txt = item.get_text()
            for word in txt.split():
                if word.isdigit() and len(word) == 4:
                    sym = f"{word}.TW"
                    if sym not in hot_symbols:
                        hot_symbols.append(sym)
                    break
    except Exception as e:
        print(f"爬取熱門股失敗: {e}")
    
    if not hot_symbols:
        hot_symbols = ["2330.TW", "2317.TW", "2454.TW", "2382.TW", "2603.TW", "3231.TW", "2376.TW", "0050.TW", "00878.TW", "00919.TW"]

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
            
    data_list = sorted(data_list, key=lambda x: x["volume"], reverse=True)
    return data_list

# ----------------- 3. 大盤行情與浮動熱門榜 -----------------
st.title("📈 股市行情 Pro")

raw_hot_data = fetch_realtime_hot_stocks()

tab_choice = st.radio("熱門排行", ["🔥 即時成交量熱門榜", "🚀 今日漲幅最強榜"], horizontal=True, label_visibility="collapsed")

if tab_choice == "🔥 即時成交量熱門榜":
    display_stocks = sorted(raw_hot_data, key=lambda x: x["volume"], reverse=True)[:5]
else:
    display_stocks = sorted(raw_hot_data, key=lambda x: x["pct"], reverse=True)[:5]

st.caption("📱 點擊下方即時熱門股，直接載入 K 線分析：")

for idx, item in enumerate(display_stocks):
    sign = "+" if item["pct"] >= 0 else ""
    tag_type = "ETF" if item["code"].startswith("00") else "股票"
    
    col_info, col_btn = st.columns([2, 1])
    with col_info:
        st.markdown(f"""
            <div style="font-size:15px; font-weight:bold; color:#FFFFFF;">
                <span class="tag">{tag_type}</span>{item['code']}
            </div>
            <div style="font-size:13px; color:#CBD5E1; margin-top: 2px;">
                成交價: <span style="color:#38BDF8; font-weight:bold;">${item['price']}</span>
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
    st.markdown('<div style="border-bottom: 1px solid #334155; margin: 6px 0;"></div>', unsafe_allow_html=True)

st.divider()

# ----------------- 4. 個股與 ETF 個別分析 -----------------
st.subheader("🔍 個股 / ETF 買賣點與風控")

user_input = st.text_input("輸入股票或 ETF 代碼 (如: 2330, 0050)", value=st.session_state.selected_symbol)
symbol = resolve_symbol(user_input)

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

            fig = make_subplots(rows=2, cols=1, shared_xaxes=True, vertical_spacing=0.05, row_width=[0.3, 0.7])
            
            fig.add_trace(go.Candlestick(
                x=df.index, open=df['Open'], high=df['High'],
                low=df['Low'], close=df['Close'], name='K線'
            ), row=1, col=1)
            
            fig.add_trace(go.Scatter(x=df.index, y=df['MA20'], mode='lines', name='20MA', line=dict(color='#FFD700', width=1)), row=1, col=1)
            fig.add_trace(go.Scatter(x=df.index, y=df['MA60'], mode='lines', name='60MA', line=dict(color='#00FF7F', width=1)), row=1, col=1)

            colors = ['#EF4444' if row['Open'] - row['Close'] >= 0 else '#10B981' for index, row in df.iterrows()]
            fig.add_trace(go.Bar(x=df.index, y=df['Volume'], name='成交量', marker_color=colors), row=2, col=1)

            fig.update_layout(
                template="plotly_dark",
                xaxis_rangeslider_visible=False,
                height=380,
                margin=dict(l=5, r=5, t=20, b=10),
                showlegend=False
            )
            
            fig.update_xaxes(range=[df.index[-45], df.index[-1]])
            st.plotly_chart(fig, use_container_width=True, config={'displayModeBar': False})

    except Exception as e:
        st.error(f"資料取得失敗：{e}")

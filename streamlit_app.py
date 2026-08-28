import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import streamlit as st
import twstock
import yfinance as yf

# ----------------- 1. 頁面設定與自定義 CSS -----------------
st.set_page_config(
    page_title="台股 Pro - twstock 即時看板",
    page_icon="📈",
    layout="centered",
    initial_sidebar_state="collapsed",
)

st.markdown(
    """
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
    .up-border { border: 1.5px solid #EF4444; }
    .down-border { border: 1.5px solid #10B981; }
    .etf-border { border: 1.5px solid #38BDF8; }
    .card-title { font-size: 11px; color: #94A3B8 !important; margin-bottom: 2px; }
    .card-val { font-size: 14px; font-weight: bold; }
    .tag {
        background-color: #334155;
        color: #F8FAFC !important;
        font-size: 10px;
        padding: 2px 6px;
        border-radius: 4px;
        margin-right: 6px;
    }
    </style>
""",
    unsafe_allow_html=True,
)

# ----------------- 2. 狀態初始化 -----------------
if "history" not in st.session_state:
  st.session_state.history = ["2330", "0050"]
if "watchlist" not in st.session_state:
  st.session_state.watchlist = ["2330", "0050", "2317", "2454"]
if "selected_symbol" not in st.session_state:
  st.session_state.selected_symbol = "2330"
if "nav_page" not in st.session_state:
  st.session_state.nav_page = "📈 即時行情與個股分析"


def select_symbol(sym):
  st.session_state.selected_symbol = sym
  if sym in st.session_state.history:
    st.session_state.history.remove(sym)
  st.session_state.history.insert(0, sym)
  st.session_state.history = st.session_state.history[:5]


def resolve_symbol(user_input):
  return user_input.strip().upper().replace(".TW", "").replace(".TWO", "")


# ----------------- 3. 使用 twstock 抓取即時排行 -----------------
@st.cache_data(ttl=60)
def fetch_twstock_ranking():
  # 從 twstock 取得常見熱門上市櫃股票清單作為掃描池
  popular_codes = [
      "2330",
      "2317",
      "2454",
      "2382",
      "3231",
      "2376",
      "3017",
      "2303",
      "3661",
      "3653",
      "6669",
      "2379",
      "3034",
      "2603",
      "2609",
      "2615",
      "5871",
      "2881",
      "2882",
      "0050",
      "0056",
      "00878",
      "00919",
      "00929",
      "00713",
      "2327",
      "3711",
      "2412",
      "1301",
      "1303",
      "2002",
      "2891",
      "1504",
      "1519",
      "1605",
      "2049",
      "2618",
      "2610",
  ]
  ranking_data = []

  for code in popular_codes:
    try:
      rt = twstock.realtime.get(code)
      if rt and rt["success"]:
        info = rt["info"]
        real = rt["realtime"]

        # 有時候盤中尚未有成交價會回傳 '-'
        if real["latest_trade_price"] == "-":
          continue

        price = float(real["latest_trade_price"])
        open_p = float(real["open"]) if real["open"] != "-" else price
        high_p = float(real["high"]) if real["high"] != "-" else price
        low_p = float(real["low"]) if real["low"] != "-" else price
        volume = (
            int(real["accumulate_trade_volume"])
            if real["accumulate_trade_volume"] != "-"
            else 0
        )

        # 計算漲跌與漲跌幅
        # twstock 的 realtime 通常有 change 欄位或可透過前收計算
        change = float(real["change"]) if real["change"] != "-" else 0.0
        prev_close = price - change
        pct = (change / prev_close * 100) if prev_close > 0 else 0.0

        ranking_data.append({
            "code": info["code"],
            "name": info["name"],
            "price": round(price, 2),
            "diff": round(change, 2),
            "pct": round(pct, 2),
            "high": round(high_p, 2),
            "low": round(low_p, 2),
            "volume": volume,
        })
    except:
      pass
  return ranking_data


@st.cache_data(ttl=3600)
def get_company_info(code):
  name = (
      twstock.codes[code].name
      if code in twstock.codes
      else f"台股 {code}"
  )
  try:
    t = yf.Ticker(f"{code}.TW")
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
        "low_52": info.get("fiftyTwoWeekLow", "N/A"),
    }
  except:
    return {
        "name": name,
        "sector": "未提供",
        "industry": "未提供",
        "summary": "暫無公司簡介資料。",
        "market_cap": 0,
        "pe_ratio": "N/A",
        "dividend_yield": 0,
        "high_52": "N/A",
        "low_52": "N/A",
    }


# ----------------- 4. UI 介面與導航 -----------------
st.title("📈 股市行情 Pro (twstock 版)")

pages = ["📈 即時行情與個股分析", "🏆 即時行情排行", "⭐ 我的自選股"]
curr_index = (
    pages.index(st.session_state.nav_page)
    if st.session_state.nav_page in pages
    else 0
)

st.session_state.nav_page = st.radio(
    "功能頁籤",
    pages,
    index=curr_index,
    horizontal=True,
    label_visibility="collapsed",
)

st.divider()

# ================= 頁面一：即時行情與個股分析 =================
if st.session_state.nav_page == "📈 即時行情與個股分析":
  st.subheader("🔍 個股 / ETF 買賣點與公司基本面")

  user_input = st.text_input(
      "輸入股票或 ETF 代碼 (如: 2330, 0050)",
      value=st.session_state.selected_symbol,
  )
  code = resolve_symbol(user_input)

  col_w1, col_w2 = st.columns(2)
  with col_w1:
    if code not in st.session_state.watchlist:
      if st.button("⭐ 加入我的自選股", use_container_width=True):
        st.session_state.watchlist.append(code)
        st.success(f"已將 {code} 加入自選！")
        st.rerun()
    else:
      if st.button("🗑️ 從自選股移除", use_container_width=True):
        st.session_state.watchlist.remove(code)
        st.warning(f"已將 {code} 移除自選！")
        st.rerun()

  if st.session_state.history:
    st.caption("⏱️ 最近瀏覽紀錄：")
    h_cols = st.columns(len(st.session_state.history))
    for i, h_code in enumerate(st.session_state.history):
      with h_cols[i]:
        h_info = get_company_info(h_code)
        if st.button(
            f"{h_code}\n{h_info['name'][:4]}",
            key=f"hist_{h_code}",
            use_container_width=True,
        ):
          select_symbol(h_code)
          st.rerun()

  if code:
    try:
      # 用 yfinance 抓取歷史 K 線繪圖
      yf_symbol = f"{code}.TW"
      ticker = yf.Ticker(yf_symbol)
      df = ticker.history(period="1y")
      if df.empty:
        yf_symbol = f"{code}.TWO"
        ticker = yf.Ticker(yf_symbol)
        df = ticker.history(period="1y")

      if isinstance(df.columns, pd.MultiIndex):
        df.columns = df.columns.get_level_values(0)

      details = get_company_info(code)

      if df.empty or len(df) < 20:
        st.error("查無歷史 K 線資料，請確認代碼是否正確！")
      else:
        is_etf = code.startswith("00")
        latest = df.iloc[-1]
        prev_close = df["Close"].iloc[-2] if len(df) >= 2 else latest["Close"]
        close_p = round(latest["Close"], 2)
        price_diff = round(close_p - prev_close, 2)
        price_pct = round((price_diff / prev_close) * 100, 2)
        sign_str = "+" if price_diff >= 0 else ""
        price_color = "#EF4444" if price_diff >= 0 else "#10B981"

        market_cap_val = details["market_cap"]
        market_cap_str = (
            f"{market_cap_val / 1e8:,.1f} 億"
            if market_cap_val and market_cap_val > 0
            else "N/A"
        )
        div_yield = details["dividend_yield"]
        div_yield_str = (
            f"{div_yield * 100:.2f}%"
            if div_yield and div_yield > 0
            else "N/A"
        )
        pe_str = (
            f"{details['pe_ratio']:.2f}"
            if isinstance(details["pe_ratio"], (int, float))
            else "N/A"
        )

        st.markdown(
            f"""
                <div class="info-box">
                    <div style="display: flex; justify-content: space-between; align-items: baseline; margin-bottom: 4px;">
                        <div style="font-size: 18px; font-weight: bold; color: #38BDF8;">
                            {details['name']} ({code})
                        </div>
                        <div>
                            <span style="font-size: 18px; font-weight: bold; color: #FFFFFF;">${close_p:,.2f}</span>
                            <span style="font-size: 13px; font-weight: bold; color: {price_color}; margin-left: 6px;">
                                {sign_str}{price_diff} ({sign_str}{price_pct}%)
                            </span>
                        </div>
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
            """,
            unsafe_allow_html=True,
        )

        df["MA20"] = df["Close"].rolling(20).mean()
        df["MA60"] = df["Close"].rolling(60).mean()
        df["MA120"] = df["Close"].rolling(120).mean()
        df["STD20"] = df["Close"].rolling(20).std()
        df["Upper"] = df["MA20"] + (df["STD20"] * 2)
        df["Lower"] = df["MA20"] - (df["STD20"] * 2)

        latest_ma = df.iloc[-1]
        ma20_val = (
            round(latest_ma["MA20"], 2)
            if not pd.isna(latest_ma["MA20"])
            else close_p
        )
        ma60_val = (
            round(latest_ma["MA60"], 2)
            if not pd.isna(latest_ma["MA60"])
            else close_p
        )
        target_sell = (
            round(latest_ma["Upper"], 2)
            if not pd.isna(latest_ma["Upper"])
            else round(close_p * 1.05, 2)
        )

        fig = make_subplots(
            rows=2,
            cols=1,
            shared_xaxes=True,
            vertical_spacing=0.05,
            row_width=[0.3, 0.7],
        )
        fig.add_trace(
            go.Candlestick(
                x=df.index,
                open=df["Open"],
                high=df["High"],
                low=df["Low"],
                close=df["Close"],
                name="K線",
            ),
            row=1,
            col=1,
        )
        fig.add_trace(
            go.Scatter(
                x=df.index,
                y=df["MA20"],
                mode="lines",
                name="20MA",
                line=dict(color="#FFD700", width=1),
            ),
            row=1,
            col=1,
        )
        fig.add_trace(
            go.Scatter(
                x=df.index,
                y=df["MA60"],
                mode="lines",
                name="60MA",
                line=dict(color="#00FF7F", width=1),
            ),
            row=1,
            col=1,
        )
        colors = [
            "#EF4444"
            if row["Close"] >= row["Open"]
            else "#10B981"
            for index, row in df.iterrows()
        ]
        fig.add_trace(
            go.Bar(
                x=df.index,
                y=df["Volume"],
                name="成交量",
                marker_color=colors,
            ),
            row=2,
            col=1,
        )

        fig.update_layout(
            template="plotly_dark",
            xaxis_rangeslider_visible=False,
            height=380,
            margin=dict(l=5, r=5, t=20, b=10),
            showlegend=False,
        )
        st.plotly_chart(fig, use_container_width=True)

    except Exception as e:
      st.error(f"資料取得錯誤：{e}")


# ================= 頁面二：即時行情排行 =================
elif st.session_state.nav_page == "🏆 即時行情排行":
  st.subheader("🏆 twstock 即時行情排行中心")
  st.caption("透過 twstock 直接抓取盤中即時上市櫃數據：")

  ranking_tab = st.radio(
      "排行分類",
      ["🚀 漲幅排行榜", "📉 跌幅排行榜", "🔥 成交量排行榜"],
      horizontal=True,
      label_visibility="collapsed",
  )

  with st.spinner("正在向 twstock 請求即時市場資料..."):
    all_data = fetch_twstock_ranking()

  if not all_data:
    st.warning("目前無法取得即時行情（可能非盤中交易時間或網路連線異常）。")
  else:
    if "漲幅" in ranking_tab:
      sorted_data = sorted(all_data, key=lambda x: x["pct"], reverse=True)
    elif "跌幅" in ranking_tab:
      sorted_data = sorted(all_data, key=lambda x: x["pct"], reverse=False)
    else:
      sorted_data = sorted(all_data, key=lambda x: x["volume"], reverse=True)

    st.markdown(
        """
        <div style="display: flex; background-color: #1E293B; padding: 10px; border-radius: 8px 8px 0 0; font-size: 12px; font-weight: bold; color: #94A3B8; border-bottom: 1px solid #334155;">
            <div style="flex: 0.6; text-align: center;">名次</div>
            <div style="flex: 2.2;">股名 / 股號</div>
            <div style="flex: 1.2; text-align: right;">股價</div>
            <div style="flex: 1.2; text-align: right;">漲跌</div>
            <div style="flex: 1.2; text-align: right;">漲跌幅</div>
            <div style="flex: 1.2; text-align: right;">最高</div>
            <div style="flex: 1.2; text-align: right;">最低</div>
        </div>
    """,
        unsafe_allow_html=True,
    )

    for i, item in enumerate(sorted_data[:20], 1):
      pct = item["pct"]
      diff = item["diff"]
      sign = "+" if diff >= 0 else ""
      color = "#EF4444" if diff >= 0 else "#10B981"
      bg_color = "#1E293B" if i % 2 == 0 else "#0F172A"

      st.markdown(
          f"""
            <div style="display: flex; align-items: center; background-color: {bg_color}; padding: 10px 8px; font-size: 13px; border-bottom: 1px solid #1E293B;">
                <div style="flex: 0.6; text-align: center; font-weight: bold; color: #38BDF8;">{i}</div>
                <div style="flex: 2.2;">
                    <div style="font-weight: bold; color: #FFFFFF;">{item['name']}</div>
                    <div style="font-size: 11px; color: #94A3B8;">{item['code']}</div>
                </div>
                <div style="flex: 1.2; text-align: right; font-weight: bold; color: #FFFFFF;">${item['price']:,.2f}</div>
                <div style="flex: 1.2; text-align: right; color: {color}; font-weight: bold;">{sign}{diff:,.2f}</div>
                <div style="flex: 1.2; text-align: right; color: {color}; font-weight: bold;">{sign}{pct:.2f}%</div>
                <div style="flex: 1.2; text-align: right; color: #CBD5E1;">${item['high']:,.2f}</div>
                <div style="flex: 1.2; text-align: right; color: #CBD5E1;">${item['low']:,.2f}</div>
            </div>
        """,
          unsafe_allow_html=True,
      )
      col_sp, col_btn = st.columns([8, 2])
      with col_btn:
        if st.button("分析", key=f"tw_rank_{item['code']}_{i}", use_container_width=True):
          select_symbol(item["code"])
          st.session_state.nav_page = "📈 即時行情與個股分析"
          st.rerun()


# ================= 頁面三：我的自選股 =================
elif st.session_state.nav_page == "⭐ 我的自選股":
  st.subheader("⭐ 我的自選股清單")

  col_add_input, col_add_btn = st.columns([3, 1])
  with col_add_input:
    new_watch = st.text_input(
        "輸入代碼新增自選", placeholder="例如: 2317", label_visibility="collapsed"
    )
  with col_add_btn:
    if st.button("➕ 加入", use_container_width=True):
      if new_watch:
        resolved = resolve_symbol(new_watch)
        if resolved not in st.session_state.watchlist:
          st.session_state.watchlist.append(resolved)
          st.success(f"已新增 {resolved}")
          st.rerun()

  if not st.session_state.watchlist:
    st.info("目前尚無自選股。")
  else:
    for sym in st.session_state.watchlist:
      try:
        rt = twstock.realtime.get(sym)
        if rt and rt["success"]:
          name = rt["info"]["name"]
          cp = (
              float(rt["realtime"]["latest_trade_price"])
              if rt["realtime"]["latest_trade_price"] != "-"
              else 0.0
          )
          change = (
              float(rt["realtime"]["change"])
              if rt["realtime"]["change"] != "-"
              else 0.0
          )
          prev = cp - change
          pct = (change / prev * 100) if prev > 0 else 0.0
          sign = "+" if change >= 0 else ""
          color = "#EF4444" if change >= 0 else "#10B981"

          col_info, col_b1, col_b2 = st.columns([2.2, 1, 1])
          with col_info:
            st.markdown(
                f"""
                        <div style="font-size:15px; font-weight:bold; color:#FFFFFF;">{sym} {name}</div>
                        <div style="font-size:14px; margin-top:2px;">
                            <span style="color:#38BDF8; font-weight:bold;">${cp:,.2f}</span> 
                            <span style="color:{color}; font-weight:bold; margin-left:8px;">{sign}{pct:.2f}%</span>
                        </div>
                    """,
                unsafe_allow_html=True,
            )
          with col_b1:
            st.markdown("<br>", unsafe_allow_html=True)
            if st.button("分析", key=f"w_goto_{sym}", use_container_width=True):
              select_symbol(sym)
              st.session_state.nav_page = "📈 即時行情與個股分析"
              st.rerun()
          with col_b2:
            st.markdown("<br>", unsafe_allow_html=True)
            if st.button("刪除", key=f"w_del_{sym}", use_container_width=True):
              st.session_state.watchlist.remove(sym)
              st.rerun()
          st.markdown(
              '<div style="border-bottom: 1px solid #334155; margin: 8px'
              ' 0;"></div>',
              unsafe_allow_html=True,
          )
      except:
        pass

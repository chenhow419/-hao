import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import streamlit as st
import yfinance as yf

# ----------------- 1. 頁面設定與自定義 CSS -----------------
st.set_page_config(
    page_title="台股 Pro - 專業動態看板",
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
    .grid-card {
        background-color: #1E293B;
        border: 1px solid #334155;
        border-radius: 12px;
        padding: 16px;
        text-align: center;
        margin-bottom: 10px;
        position: relative;
    }
    .hot-badge {
        position: absolute;
        top: 8px;
        right: 8px;
        background-color: #F59E0B;
        color: #0F172A;
        font-size: 9px;
        font-weight: bold;
        padding: 1px 5px;
        border-radius: 4px;
    }
    </style>
""",
    unsafe_allow_html=True,
)

# ----------------- 2. 狀態初始化 -----------------
if "history" not in st.session_state:
  st.session_state.history = ["2330.TW", "0050.TW"]
if "watchlist" not in st.session_state:
  st.session_state.watchlist = ["2330.TW", "0050.TW", "2317.TW", "2454.TW"]
if "selected_symbol" not in st.session_state:
  st.session_state.selected_symbol = "2330.TW"
if "nav_page" not in st.session_state:
  st.session_state.nav_page = "📈 即時行情與個股分析"
if "selected_theme" not in st.session_state:
  st.session_state.selected_theme = None

if "theme_stocks" not in st.session_state:
  st.session_state.theme_stocks = {
      "🤖 AI 伺服器與散熱": {
          "tag_desc": "AI 概念強勢供應鏈",
          "external_url": "https://tw.stock.yahoo.com/class-quote?category=AI",
          "stocks": [
              "2382.TW",
              "3231.TW",
              "2376.TW",
              "3017.TW",
              "3653.TW",
              "6669.TW",
          ],
      },
      "⚡ 半導體重量權值": {
          "tag_desc": "護國神山與高階晶片",
          "external_url": (
              "https://tw.stock.yahoo.com/class-quote?category=semiconductor"
          ),
          "stocks": [
              "2330.TW",
              "2454.TW",
              "2303.TW",
              "3661.TW",
              "2379.TW",
              "3034.TW",
          ],
      },
      "💰 熱門高股息與市值ETF": {
          "tag_desc": "存股族最愛配置",
          "external_url": "https://tw.stock.yahoo.com/class-quote?category=etf",
          "stocks": [
              "0050.TW",
              "0056.TW",
              "00878.TW",
              "00919.TW",
              "00929.TW",
              "00713.TW",
          ],
      },
      "🚢 航運與散裝航運": {
          "tag_desc": "景氣循環與高殖利率",
          "external_url": (
              "https://tw.stock.yahoo.com/class-quote?category=shipping"
          ),
          "stocks": ["2603.TW", "2609.TW", "2615.TW", "2606.TW"],
      },
      "🏦 金融與大型權值股": {
          "tag_desc": "穩健收益金控首選",
          "external_url": (
              "https://tw.stock.yahoo.com/class-quote?category=financial"
          ),
          "stocks": ["2881.TW", "2882.TW", "5871.TW"],
      },
      "🔥 近期熱門焦點標的": {
          "tag_desc": "市場高關注度熱股",
          "external_url": "https://tw.stock.yahoo.com/trending/stocks",
          "stocks": ["2330.TW", "2317.TW", "2327.TW", "0050.TW", "2454.TW"],
      },
  }


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


TW_STOCK_NAMES = {
    "2330.TW": "台積電",
    "2317.TW": "鴻海",
    "2454.TW": "聯發科",
    "2382.TW": "廣達",
    "3231.TW": "緯創",
    "2376.TW": "技嘉",
    "3017.TW": "奇鋐",
    "2303.TW": "聯電",
    "3661.TW": "世芯-KY",
    "3653.TW": "健策",
    "6669.TW": "緯穎",
    "2379.TW": "瑞昱",
    "3034.TW": "聯詠",
    "2603.TW": "長榮",
    "2609.TW": "陽明",
    "2615.TW": "萬海",
    "2606.TW": "裕民",
    "5871.TW": "中租-KY",
    "2881.TW": "富邦金",
    "2882.TW": "國泰金",
    "0050.TW": "元大台灣50",
    "0056.TW": "元大高股息",
    "00878.TW": "國泰永續高股息",
    "00919.TW": "群益台灣精選高息",
    "00929.TW": "復華台灣科技優息",
    "00713.TW": "元大台灣高息低波",
    "1314.TW": "中石化",
    "2327.TW": "國巨",
}


# ----------------- 3. 資料抓取函數 -----------------
@st.cache_data(ttl=60)
def fetch_market_indices():
  indices = {"台股加權指數": "^TWII", "櫃買指數": "^TWOII"}
  data = {}
  for name, symbol in indices.items():
    try:
      t = yf.Ticker(symbol)
      hist = t.history(period="2d")
      if isinstance(hist.columns, pd.MultiIndex):
        hist.columns = hist.columns.get_level_values(0)
      if len(hist) >= 2:
        cp = hist["Close"].iloc[-1]
        pp = hist["Close"].iloc[-2]
        diff = cp - pp
        pct = (diff / pp) * 100
        data[name] = {
            "price": round(cp, 2),
            "diff": round(diff, 2),
            "pct": round(pct, 2),
        }
    except:
      pass
  return data


@st.cache_data(ttl=3600)
def get_company_details(symbol):
  clean_sym = symbol.replace(".TW", "").replace(".TWO", "")
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


@st.cache_data(ttl=300)
def fetch_realtime_hot_stocks():
  hot_symbols = [
      "2330.TW",
      "2317.TW",
      "2454.TW",
      "2382.TW",
      "2603.TW",
      "3231.TW",
      "2376.TW",
      "0050.TW",
  ]
  data_list = []
  for sym in hot_symbols[:8]:
    try:
      t = yf.Ticker(sym)
      hist = t.history(period="2d")
      if isinstance(hist.columns, pd.MultiIndex):
        hist.columns = hist.columns.get_level_values(0)
      if len(hist) >= 2:
        cp = hist["Close"].iloc[-1]
        pp = hist["Close"].iloc[-2]
        vol = hist["Volume"].iloc[-1]
        pct = ((cp - pp) / pp) * 100
        code = sym.replace(".TW", "").replace(".TWO", "")
        details = get_company_details(sym)
        data_list.append({
            "symbol": sym,
            "code": code,
            "name": details["name"],
            "price": round(cp, 2),
            "pct": round(pct, 2),
            "volume": vol,
        })
    except:
      pass
  return sorted(data_list, key=lambda x: x["volume"], reverse=True)


def fetch_theme_stocks_dynamic(theme_name, theme_dict):
  theme_symbols = theme_dict[theme_name]["stocks"]
  results = []
  for sym in theme_symbols:
    try:
      t = yf.Ticker(sym)
      hist = t.history(period="2d")
      if isinstance(hist.columns, pd.MultiIndex):
        hist.columns = hist.columns.get_level_values(0)
      details = get_company_details(sym)
      if len(hist) >= 2:
        cp = hist["Close"].iloc[-1]
        pp = hist["Close"].iloc[-2]
        pct = ((cp - pp) / pp) * 100
        results.append({
            "symbol": sym,
            "code": sym.replace(".TW", "").replace(".TWO", ""),
            "name": details["name"],
            "price": round(cp, 2),
            "pct": round(pct, 2),
            "success": True,
        })
      else:
        results.append({
            "symbol": sym,
            "code": sym.replace(".TW", "").replace(".TWO", ""),
            "name": TW_STOCK_NAMES.get(sym, sym),
            "price": 0,
            "pct": 0,
            "success": False,
        })
    except:
      results.append({
          "symbol": sym,
          "code": sym.replace(".TW", "").replace(".TWO", ""),
          "name": TW_STOCK_NAMES.get(sym, sym),
          "price": 0,
          "pct": 0,
          "success": False,
      })
  return results


@st.cache_data(ttl=300)
def fetch_watchlist_cached(symbols_tuple):
  results = []
  for sym in symbols_tuple:
    try:
      t = yf.Ticker(sym)
      hist = t.history(period="2d")
      if isinstance(hist.columns, pd.MultiIndex):
        hist.columns = hist.columns.get_level_values(0)
      details = get_company_details(sym)
      if len(hist) >= 2:
        cp = hist["Close"].iloc[-1]
        pp = hist["Close"].iloc[-2]
        pct = ((cp - pp) / pp) * 100
        results.append({
            "symbol": sym,
            "code": sym.replace(".TW", "").replace(".TWO", ""),
            "name": details["name"],
            "price": round(cp, 2),
            "pct": round(pct, 2),
            "success": True,
        })
      else:
        results.append({
            "symbol": sym,
            "code": sym.replace(".TW", "").replace(".TWO", ""),
            "name": TW_STOCK_NAMES.get(sym, sym),
            "price": 0,
            "pct": 0,
            "success": False,
        })
    except:
      results.append({
          "symbol": sym,
          "code": sym.replace(".TW", "").replace(".TWO", ""),
          "name": TW_STOCK_NAMES.get(sym, sym),
          "price": 0,
          "pct": 0,
          "success": False,
      })
  return results


# ----------------- 4. UI 介面與導航 -----------------
st.title("📈 股市行情 Pro")

pages = ["📈 即時行情與個股分析", "🏷️ 排行選股專區", "⭐ 我的自選股"]
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
  st.subheader("📊 台灣三大指數行情")
  indices_data = fetch_market_indices()
  if indices_data:
    idx_cols = st.columns(len(indices_data))
    for i, (name, val) in enumerate(indices_data.items()):
      color = "#EF4444" if val["diff"] >= 0 else "#10B981"
      sign = "+" if val["diff"] >= 0 else ""
      with idx_cols[i]:
        st.markdown(
            f"""
                <div class="trade-card" style="border-left: 4px solid {color}; text-align: left; padding: 12px;">
                    <div class="card-title">{name}</div>
                    <div style="font-size: 18px; font-weight: bold; margin: 4px 0;">{val['price']:,.2f}</div>
                    <div style="font-size: 12px; color: {color}; font-weight: bold;">
                        {sign}{val['diff']} ({sign}{val['pct']}%)
                    </div>
                </div>
            """,
            unsafe_allow_html=True,
        )

  st.divider()

  raw_hot_data = fetch_realtime_hot_stocks()
  tab_choice = st.radio(
      "熱門排行",
      ["🔥 即時成交量熱門榜", "🚀 今日漲幅最強榜"],
      horizontal=True,
      label_visibility="collapsed",
  )

  display_stocks = sorted(
      raw_hot_data,
      key=lambda x: x["volume" if tab_choice.startswith("🔥") else "pct"],
      reverse=True,
  )[:5]

  st.caption("📱 點擊下方即時熱門股，直接載入公司基本面與 K 線分析：")

  for idx, item in enumerate(display_stocks):
    sign = "+" if item["pct"] >= 0 else ""
    color = "#EF4444" if item["pct"] >= 0 else "#10B981"
    tag_type = "ETF" if item["code"].startswith("00") else "股票"
    is_limit = abs(item["pct"]) >= 9.5
    badge_limit = (
        " 🔥 漲停"
        if (is_limit and item["pct"] > 0)
        else (" ❄️ 跌停" if is_limit else "")
    )

    col_info, col_btn = st.columns([2, 1])
    with col_info:
      st.markdown(
          f"""
                <div style="font-size:15px; font-weight:bold; color:#FFFFFF;">
                    <span class="tag">{tag_type}</span>{item['code']} {item['name']}{badge_limit}
                </div>
                <div style="font-size:13px; color:#CBD5E1; margin-top: 2px;">
                    成交價: <span style="color:#38BDF8; font-weight:bold;">${item['price']}</span>
                </div>
            """,
          unsafe_allow_html=True,
      )
    with col_btn:
      st.markdown(
          f"""<div style='text-align: right; color: {color}; font-weight: bold; font-size: 1.05rem; padding-top: 4px;'>{sign}{item['pct']}%</div>""",
          unsafe_allow_html=True,
      )
      if st.button(
          "查看分析", key=f"hot_{item['symbol']}_{idx}", use_container_width=True
      ):
        select_symbol(item["symbol"])
        st.rerun()
    st.markdown(
        '<div style="border-bottom: 1px solid #334155; margin: 6px 0;"></div>',
        unsafe_allow_html=True,
    )

  st.divider()

  st.subheader("🔍 個股 / ETF 買賣點與公司基本面")

  user_input = st.text_input(
      "輸入股票或 ETF 代碼 (如: 2330, 1314, 0050)",
      value=st.session_state.selected_symbol,
  )
  symbol = resolve_symbol(user_input)

  col_w1, col_w2 = st.columns(2)
  with col_w1:
    if symbol not in st.session_state.watchlist:
      if st.button("⭐ 加入我的自選股", use_container_width=True):
        st.session_state.watchlist.append(symbol)
        st.success(f"已將 {symbol} 加入自選！")
        st.rerun()
    else:
      if st.button("🗑️ 從自選股移除", use_container_width=True):
        st.session_state.watchlist.remove(symbol)
        st.warning(f"已將 {symbol} 移除自選！")
        st.rerun()

  if st.session_state.history:
    st.caption("⏱️ 最近瀏覽紀錄：")
    h_cols = st.columns(len(st.session_state.history))
    for i, h_sym in enumerate(st.session_state.history):
      with h_cols[i]:
        h_code = h_sym.replace(".TW", "").replace(".TWO", "")
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

      # 修正：確保 yfinance 欄位結構為單層，避免 MultiIndex 導致 MA 欄位抓取失敗
      if isinstance(df.columns, pd.MultiIndex):
        df.columns = df.columns.get_level_values(0)

      details = get_company_details(symbol)

      if df.empty or len(df) < 20:
        st.error("查無資料或歷史天數不足，請確認輸入代碼正確！")
      else:
        is_etf = symbol.startswith("00") or "ETF" in symbol.upper()

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
                            {details['name']} ({symbol})
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
        ma120_val = (
            round(latest_ma["MA120"], 2)
            if not pd.isna(latest_ma["MA120"])
            else round(ma60_val * 0.95, 2)
        )
        target_sell = (
            round(latest_ma["Upper"], 2)
            if not pd.isna(latest_ma["Upper"])
            else round(close_p * 1.05, 2)
        )

        if is_etf:
          c1, c2, c3 = st.columns(3)
          with c1:
            st.markdown(
                f'<div class="trade-card down-border"><div'
                ' class="card-title">月線分批</div><div class="card-val"'
                f' style="color:#10B981">${ma20_val}</div></div>',
                unsafe_allow_html=True,
            )
          with c2:
            st.markdown(
                f'<div class="trade-card etf-border"><div'
                ' class="card-title">季線加碼</div><div class="card-val"'
                f' style="color:#38BDF8">${ma60_val}</div></div>',
                unsafe_allow_html=True,
            )
          with c3:
            st.markdown(
                f'<div class="trade-card up-border"><div'
                ' class="card-title">半年抄底</div><div class="card-val"'
                f' style="color:#EF4444">${ma120_val}</div></div>',
                unsafe_allow_html=True,
            )
        else:
          buy_low = round(ma20_val * 0.98, 2)
          buy_high_val = ma20_val
          lower_band = (
              latest_ma["Lower"] if not pd.isna(latest_ma["Lower"]) else close_p
          )
          stop_loss = round(min(ma60_val * 0.97, lower_band), 2)

          c1, c2, c3 = st.columns(3)
          with c1:
            st.markdown(
                f'<div class="trade-card down-border"><div'
                ' class="card-title">建議買區</div><div class="card-val"'
                f' style="color:#10B981">${buy_low} ~ ${buy_high_val}</div></div>',
                unsafe_allow_html=True,
            )
          with c2:
            st.markdown(
                f'<div class="trade-card up-border"><div'
                ' class="card-title">停利目標</div><div class="card-val"'
                f' style="color:#EF4444">${target_sell}</div></div>',
                unsafe_allow_html=True,
            )
          with c3:
            st.markdown(
                f'<div class="trade-card" style="border: 1.5px solid'
                f' #F59E0B;"><div class="card-title">停損設定</div><div'
                f' class="card-val" style="color:#F59E0B">${stop_loss}</div></div>',
                unsafe_allow_html=True,
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
            xaxis=dict(autorange=True),
        )

        st.plotly_chart(
            fig,
            use_container_width=True,
            config={
                "scrollZoom": True,
                "displayModeBar": True,
                "modeBarButtonsToRemove": ["lasso2d", "select2d"],
            },
        )

    except Exception as e:
      st.error(f"資料取得失敗：{e}")


# ================= 頁面二：排行選股專區 =================
elif st.session_state.nav_page == "🏷️ 排行選股專區":
  st.subheader("📊 智慧排行選股中心")

  with st.expander("➕ 點擊展開：動態新增自訂概念股分類"):
    with st.form("add_theme_form"):
      new_t_name = st.text_input("分類名稱 (例如: 🚗 電動車概念股)")
      new_t_desc = st.text_input("分類簡介 (例如: 迎合未來新能源趨勢)")
      new_t_url = st.text_input(
          "外部推薦連結 URL (例如: https://tw.stock.yahoo.com/...)"
      )
      new_t_stocks = st.text_input(
          "包含的股票代碼 (用逗號隔開，例如: 2317.TW, 1504.TW)"
      )
      submitted = st.form_submit_button("確認新增分類")
      if submitted and new_t_name:
        stocks_list = [
            s.strip().upper() for s in new_t_stocks.split(",") if s.strip()
        ]
        formatted_stocks = [
            s if (".TW" in s or ".TWO" in s) else f"{s}.TW" for s in stocks_list
        ]
        st.session_state.theme_stocks[new_t_name] = {
            "tag_desc": new_t_desc or "自訂概念股清單",
            "external_url": new_t_url or "https://tw.stock.yahoo.com/",
            "stocks": (
                formatted_stocks
                if formatted_stocks
                else ["2330.TW", "0050.TW"]
            ),
        }
        st.success(f"成功新增分類：{new_t_name}！")
        st.rerun()

  if st.session_state.selected_theme is None:
    st.caption("請選擇下方熱門選股維度，快速檢視精選標的：")

    themes = list(st.session_state.theme_stocks.keys())
    for i in range(0, len(themes), 2):
      cols = st.columns(2)
      for j in range(2):
        if i + j < len(themes):
          t_name = themes[i + j]
          t_info = st.session_state.theme_stocks[t_name]
          with cols[j]:
            st.markdown(
                f"""
                            <div class="grid-card">
                                <div class="hot-badge">HOT</div>
                                <div style="font-size:15px; font-weight:bold; color:#FFFFFF; margin-bottom:4px;">{t_name}</div>
                                <div style="font-size:11px; color:#94A3B8;">{t_info['tag_desc']}</div>
                            </div>
                        """,
                unsafe_allow_html=True,
            )
            if st.button(
                "進入查看", key=f"grid_btn_{i+j}", use_container_width=True
            ):
              st.session_state.selected_theme = t_name
              st.rerun()
  else:
    current_theme = st.session_state.selected_theme

    col_back, col_title = st.columns([1, 4])
    with col_back:
      if st.button("⬅️ 返回", use_container_width=True):
        st.session_state.selected_theme = None
        st.rerun()
    with col_title:
      st.markdown(
          f"<h4 style='margin:0; color:#38BDF8;'>{current_theme}</h4>",
          unsafe_allow_html=True,
      )

    st.markdown(
        f"<div style='font-size:12px; color:#94A3B8;"
        f" margin-bottom:10px;'>{st.session_state.theme_stocks[current_theme]['tag_desc']}</div>",
        unsafe_allow_html=True,
    )

    external_link = st.session_state.theme_stocks[current_theme].get(
        "external_url", "https://tw.stock.yahoo.com/"
    )
    st.link_button(
        f"🌐 點擊至外部平台查看【{current_theme}】完整推薦概念股解析",
        external_link,
        use_container_width=True,
    )

    sort_col1, sort_col2 = st.columns(2)
    with sort_col1:
      theme_sort = st.selectbox(
          "排序方式",
          ["預設順序", "漲跌幅高到低", "漲跌幅低到高", "股價高到低"],
          key="theme_sort_box",
      )

    st.markdown(
        '<div style="border-bottom: 1px solid #334155; margin-bottom: 10px;"></div>',
        unsafe_allow_html=True,
    )

    theme_results = fetch_theme_stocks_dynamic(
        current_theme, st.session_state.theme_stocks
    )

    if theme_sort == "漲跌幅高到低":
      theme_results = sorted(theme_results, key=lambda x: x["pct"], reverse=True)
    elif theme_sort == "漲跌幅低到高":
      theme_results = sorted(
          theme_results, key=lambda x: x["pct"], reverse=False
      )
    elif theme_sort == "股價高到低":
      theme_results = sorted(
          theme_results, key=lambda x: x["price"], reverse=True
      )

    for item in theme_results:
      sym = item["symbol"]
      if item["success"]:
        cp = item["price"]
        pct = item["pct"]
        sign = "+" if pct >= 0 else ""
        color = "#EF4444" if pct >= 0 else "#10B981"
        code = item["code"]

        is_limit = abs(pct) >= 9.5
        badge_limit = (
            " 🔥 漲停"
            if (is_limit and pct > 0)
            else (" ❄️ 跌停" if is_limit else "")
        )
        custom_tag = (
            "71%存股族加入自選"
            if code.startswith("00")
            else ("EPS>3 優質股" if cp > 100 else "高殖利率關注")
        )

        col_info, col_btn = st.columns([2.5, 1])
        with col_info:
          st.markdown(
              f"""
                    <div style="font-size:15px; font-weight:bold; color:#FFFFFF;">
                        {code} {item['name']}{badge_limit}
                    </div>
                    <div style="font-size:14px; margin-top:2px;">
                        <span style="color:#38BDF8; font-weight:bold;">${cp:,.2f}</span> 
                        <span style="color:{color}; font-weight:bold; margin-left:8px;">{sign}{pct:.2f}%</span>
                    </div>
                    <div style="font-size:11px; color:#94A3B8; margin-top:3px;">
                        <span class="tag">{custom_tag}</span>
                    </div>
                """,
              unsafe_allow_html=True,
          )
        with col_btn:
          st.markdown("<br>", unsafe_allow_html=True)
          if st.button("詳細分析", key=f"theme_{sym}", use_container_width=True):
            select_symbol(sym)
            st.session_state.nav_page = "📈 即時行情與個股分析"
            st.session_state.selected_theme = None
            st.rerun()
        st.markdown(
            '<div style="border-bottom: 1px solid #334155; margin: 8px 0;"></div>',
            unsafe_allow_html=True,
        )


# ================= 頁面三：我的自選股 =================
elif st.session_state.nav_page == "⭐ 我的自選股":
  st.subheader("⭐ 我的自選股清單")
  st.caption("追蹤您專屬的自選標的，即時掌握最新價格與漲跌幅：")

  col_add_input, col_add_btn = st.columns([3, 1])
  with col_add_input:
    new_watch_input = st.text_input(
        "輸入代碼新增自選",
        placeholder="例如: 2317 或 00878",
        label_visibility="collapsed",
    )
  with col_add_btn:
    if st.button("➕ 加入", use_container_width=True):
      if new_watch_input:
        resolved = resolve_symbol(new_watch_input)
        if resolved not in st.session_state.watchlist:
          st.session_state.watchlist.append(resolved)
          st.success(f"已新增 {resolved}")
          st.rerun()
        else:
          st.warning("該標的已在清單中")

  if st.session_state.watchlist:
    w_sort_col1, w_sort_col2 = st.columns(2)
    with w_sort_col1:
      watch_sort = st.selectbox(
          "清單排序",
          ["預設排序", "漲跌幅由高到低", "漲跌幅由低到高", "代碼排序"],
          key="watchlist_sort_box",
      )

  st.markdown(
      '<div style="border-bottom: 1px solid #334155; margin: 10px 0;"></div>',
      unsafe_allow_html=True,
  )

  if not st.session_state.watchlist:
    st.info("目前尚無自選股，請透過上方輸入框新增，或從個股分析頁面加入！")
  else:
    watchlist_tuple = tuple(st.session_state.watchlist)
    watchlist_results = fetch_watchlist_cached(watchlist_tuple)

    if "watch_sort" in locals():
      if watch_sort == "漲跌幅由高到低":
        watchlist_results = sorted(
            watchlist_results, key=lambda x: x.get("pct", 0), reverse=True
        )
      elif watch_sort == "漲跌幅由低到高":
        watchlist_results = sorted(
            watchlist_results, key=lambda x: x.get("pct", 0), reverse=False
        )
      elif watch_sort == "代碼排序":
        watchlist_results = sorted(
            watchlist_results, key=lambda x: x.get("code", "")
        )

    for item in watchlist_results:
      sym = item["symbol"]
      if item["success"]:
        cp = item["price"]
        pct = item["pct"]
        sign = "+" if pct >= 0 else ""
        color = "#EF4444" if pct >= 0 else "#10B981"
        code = item["code"]
        tag_type = "ETF" if code.startswith("00") else "股票"

        is_limit = abs(pct) >= 9.5
        badge_limit = (
            " 🔥 漲停"
            if (is_limit and pct > 0)
            else (" ❄️ 跌停" if is_limit else "")
        )

        col_info, col_btn1, col_btn2 = st.columns([2.2, 1, 1])
        with col_info:
          st.markdown(
              f"""
                    <div style="font-size:15px; font-weight:bold; color:#FFFFFF;">
                        <span class="tag">{tag_type}</span>{code} {item['name']}{badge_limit}
                    </div>
                    <div style="font-size:14px; margin-top:2px;">
                        <span style="color:#38BDF8; font-weight:bold;">${cp:,.2f}</span> 
                        <span style="color:{color}; font-weight:bold; margin-left:8px;">{sign}{pct:.2f}%</span>
                    </div>
                """,
              unsafe_allow_html=True,
          )
        with col_btn1:
          st.markdown("<br>", unsafe_allow_html=True)
          if st.button("詳細分析", key=f"watch_goto_{sym}", use_container_width=True):
            select_symbol(sym)
            st.session_state.nav_page = "📈 即時行情與個股分析"
            st.rerun()
        with col_btn2:
          st.markdown("<br>", unsafe_allow_html=True)
          if st.button("刪除", key=f"watch_del_{sym}", use_container_width=True):
            st.session_state.watchlist.remove(sym)
            st.rerun()
        st.markdown(
            '<div style="border-bottom: 1px solid #334155; margin: 8px 0;"></div>',
            unsafe_allow_html=True,
        )

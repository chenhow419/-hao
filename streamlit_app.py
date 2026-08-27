import streamlit as st
import yfinance as yf
import pandas as pd
import mplfinance as mpf
import matplotlib.pyplot as plt

# 1. 頁面設定 (隱藏預設選單，打造 App 質感)
st.set_page_config(
    page_title="股票買點分析儀",
    page_icon="📈",
    layout="centered",
    initial_sidebar_state="collapsed"
)

# 自訂 CSS 手機最佳化與高對比卡片
st.markdown("""
    <style>
    /* 隱藏 Streamlit 頂部選單與頁尾 */
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
    header {visibility: hidden;}
    
    /* 買點資訊卡片樣式 (高對比設計) */
    .buy-card {
        background-color: #1E293B;
        border: 2px solid #10B981;
        border-radius: 12px;
        padding: 15px;
        text-align: center;
        margin-bottom: 15px;
    }
    .buy-title { font-size: 14px; color: #94A3B8; margin-bottom: 5px; }
    .buy-price { font-size: 24px; font-weight: bold; color: #10B981; }
    .sell-price { font-size: 24px; font-weight: bold; color: #EF4444; }
    </style>
""", unsafe_allow_html=True)

st.title("📈 股票合理買點分析")

# 2. 手機輸入欄位
symbol = st.text_input("輸入股票代碼：", "2330.TW").upper().strip()

if st.button("🔍 計算買點區間", use_container_width=True):
    with st.spinner("抓取最新數據中..."):
        try:
            ticker = yf.Ticker(symbol)
            df = ticker.history(period="6mo", interval="1d")

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

                # 3. 高對比 PWA 卡片顯示
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

                # 4. K 線圖繪製
                custom_style = mpf.make_mpf_style(base_mpf_style="binance")
                addplots = [
                    mpf.make_addplot(df["MA20"], color="#FFD700", width=1.5),
                    mpf.make_addplot(df["MA60"], color="#00FF7F", width=1.5),
                    mpf.make_addplot(df["Upper_Band"], color="#FF3366", width=1.5)
                ]

                fig, axlist = mpf.plot(
                    df, type="candle", style=custom_style, volume=True,
                    addplot=addplots, returnfig=True, figscale=1.2, panel_ratios=(3, 1)
                )
                ax_main = axlist[0]
                # 繪製綠色半透明買點區間
                ax_main.axhspan(buy_low, buy_high, color='#00FF7F', alpha=0.2)

                st.pyplot(fig)

        except Exception as e:
            st.error(f"分析時發生錯誤：{e}")

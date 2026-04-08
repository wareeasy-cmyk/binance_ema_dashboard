#   https://gemini.google.com/app/191010761569e34b
#   2026/04/08 


import ccxt
import pandas as pd
import pandas_ta as ta
import plotly.graph_objects as go
import streamlit as st
from datetime import datetime

# ==========================================
# 1. 페이지 설정
# ==========================================
st.set_page_config(page_title="Binance EMA 실시간 대시보드", layout="wide")

# CSS를 활용한 디자인 살짝 가미
st.markdown("""
    <style>
    .main { background-color: #0e1117; }
    .stMetric { background-color: #1e2130; padding: 15px; border-radius: 10px; }
    </style>
    """, unsafe_allow_html=True)

# 사이드바 설정창
st.sidebar.header("🛠️ 전략 및 인터벌 설정")
SYMBOL = st.sidebar.text_input("종목명", value='BTC/USDT').upper()
TIMEFRAME = st.sidebar.selectbox("캔들 시간", ['1m', '5m', '15m', '1h', '4h', '1d'], index=2)

ema_v1 = st.sidebar.number_input("EMA 1 (단기)", value=10)
ema_v2 = st.sidebar.number_input("EMA 2 (중기)", value=20)
ema_v3 = st.sidebar.number_input("EMA 3 (장기)", value=60)

short_ema_val = st.sidebar.selectbox("교차용 단기 EMA", [ema_v1, ema_v2, ema_v3], index=0)
long_ema_val = st.sidebar.selectbox("교차용 장기 EMA", [ema_v1, ema_v2, ema_v3], index=2)

refresh_sec = st.sidebar.slider("데이터 자동 갱신 (초)", 5, 60, 10)

# ==========================================
# 2. 데이터 처리 함수 (캐싱 적용 고려 가능)
# ==========================================
def get_data(symbol, timeframe):
    try:
        exchange = ccxt.binance()
        ohlcv = exchange.fetch_ohlcv(symbol, timeframe=timeframe, limit=200)
        df = pd.DataFrame(ohlcv, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
        df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')
        
        # 지표 계산
        df['ema_short'] = ta.ema(df['close'], length=short_ema_val)
        df['ema_long'] = ta.ema(df['close'], length=long_ema_val)
        
        # 신호 계산
        df['signal'] = 0
        df.loc[df['ema_short'] > df['ema_long'], 'signal'] = 1
        df.loc[df['ema_short'] < df['ema_long'], 'signal'] = -1
        df['entry'] = df['signal'].diff()

        # 기울기 변곡점 (빨간 점)
        df['diff'] = df['ema_short'].diff()
        df['slope_zero'] = (df['diff'] * df['diff'].shift(1) <= 0) & (df['diff'] != 0)
        
        return df
    except Exception as e:
        st.error(f"데이터를 가져오는 중 오류 발생: {e}")
        return None

# ==========================================
# 3. 화면 렌더링
# ==========================================
st.title(f"📈 {SYMBOL} 실시간 모니터링")

df = get_data(SYMBOL, TIMEFRAME)

if df is not None:
    curr_price = df['close'].iloc[-1]
    prev_price = df['close'].iloc[-2]
    price_diff = curr_price - prev_price
    
    # 상단 지표
    col1, col2, col3, col4 = st.columns(4)
    col1.metric("현재가", f"{curr_price:,} USDT", f"{price_diff:,.2f}")
    col2.metric(f"EMA {short_ema_val}", f"{df['ema_short'].iloc[-1]:,.2f}")
    col3.metric(f"EMA {long_ema_val}", f"{df['ema_long'].iloc[-1]:,.2f}")
    
    status = "대기"
    if df['signal'].iloc[-1] == 1: status = "📈 매수 유지"
    elif df['signal'].iloc[-1] == -1: status = "📉 매도 유지"
    col4.markdown(f"### 상태\n{status}")

    # 차트 시각화
    fig = go.Figure()
    fig.add_trace(go.Candlestick(
        x=df['timestamp'], open=df['open'], high=df['high'], low=df['low'], close=df['close'],
        name='Price'
    ))
    fig.add_trace(go.Scatter(x=df['timestamp'], y=df['ema_short'], line=dict(color='orange', width=1.5), name='Short EMA'))
    fig.add_trace(go.Scatter(x=df['timestamp'], y=df['ema_long'], line=dict(color='dodgerblue', width=1.5), name='Long EMA'))

    # 변곡점 표시
    zero_points = df[df['slope_zero'] == True]
    fig.add_trace(go.Scatter(
        x=zero_points['timestamp'], y=zero_points['ema_short'],
        mode='markers', marker=dict(color='red', size=8), name='변곡점'
    ))

    # 진입 신호 화살표
    buys = df[df['entry'] == 2]
    sells = df[df['entry'] == -2]
    fig.add_trace(go.Scatter(x=buys['timestamp'], y=buys['low']*0.998, mode='markers', marker=dict(symbol='triangle-up', size=12, color='lime'), name='BUY'))
    fig.add_trace(go.Scatter(x=sells['timestamp'], y=sells['high']*1.002, mode='markers', marker=dict(symbol='triangle-down', size=12, color='red'), name='SELL'))

    fig.update_layout(height=600, template='plotly_dark', margin=dict(l=20, r=20, t=20, b=20))
    st.plotly_chart(fig, use_container_width=True)

# 자동 새로고침 설정 (웹 방식)
from streamlit_autorefresh import st_autorefresh
st_autorefresh(interval=refresh_sec * 1000, key="datarefresh")














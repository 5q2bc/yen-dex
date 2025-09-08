import streamlit as st
import yfinance as yf
import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots

# ------------------------------------------------
# アプリの基本設定
# ------------------------------------------------
st.set_page_config(layout="wide")
st.title('Yen-dex 📈')

# ------------------------------------------------
# サイドバー: ユーザー入力
# ------------------------------------------------
st.sidebar.header('表示設定')
# 1. ティッカーシンボルの選択
nasdaq100_tickers = [
    'AAPL', 'MSFT', 'AMZN', 'NVDA', 'GOOGL', 'GOOG', 'META', 'TSLA', 'AVGO', 'ASML', 'ADBE', 'AMD', 'COST', 'PEP',
    'CSCO', 'TMUS', 'NFLX', 'INTC', 'CMCSA', 'QCOM', 'INTU', 'AMGN', 'TXN', 'HON', 'SBUX', 'ISRG', 'BKNG', 'GILD',
    'ADI', 'LRCX', 'REGN', 'VRTX', 'MDLZ', 'ADP', 'PYPL', 'MU', 'AMAT', 'CSX', 'MELI', 'CHTR', 'MAR', 'PANW',
    'KDP', 'AEP', 'SNPS', 'ABNB', 'FTNT', 'KLAC', 'MRVL', 'ORLY', 'DXCM', 'MNST', 'CDNS', 'ADSK', 'PCAR', 'PAYX',
    'EXC', 'BIIB', 'ROST', 'KHC', 'CPRT', 'ON', 'CTAS', 'LULU', 'WBD', 'IDXX', 'WDAY', 'FAST', 'CRWD', 'GFS',
    'CEG', 'GEHC', 'TEAM', 'DDOG', 'VRSK', 'BKR', 'ANSS', 'MRNA', 'ALGN', 'ILMN', 'ZS', 'SIRI', 'TTD', 'ENPH',
    'PDD', 'CTSH', 'EA', 'ZM', 'JD', 'XEL', 'DLTR', 'AZN', 'WBA', 'LCID', 'SGEN', 'ATVI', 'BIDU', 'SWKS',
    'SPLK', 'OKTA', 'DOCU', 'EBAY', 'VOD', 'ADI', 'SIRI'
]
ticker_symbol = st.sidebar.selectbox(
    'ティッカーシンボル',
    nasdaq100_tickers,
    index=nasdaq100_tickers.index('GOOGL') # デフォルトを 'GOOGL' に設定
)
# 2. 表示期間の選択
period = st.sidebar.selectbox(
    '表示期間',
    ('3mo', '6mo', '1y', '2y', '5y', 'ytd'),
    index=2  # デフォルトを '1y' に設定
)

# 3. 移動平均線の選択
sma_periods = st.sidebar.multiselect(
    '移動平均線 (SMA) ',
    [5, 25, 50, 75],
    default=[5, 25] # デフォルト
)

# 4. 円建て/ドル建ての選択
show_jpy = st.sidebar.checkbox('円建て表示', True)


# ------------------------------------------------
# データ取得 (キャッシュ機能付き)
# ------------------------------------------------
@st.cache_data
def get_data(ticker, period):
    try:
        # 株価データを取得
        stock_df = yf.download(ticker, period=period, progress=False)
        # 為替レート(USD/JPY)を取得
        forex_df = yf.download('JPY=X', period=period, progress=False)

        if stock_df.empty:
            return None, None # 株価データが空ならNoneを返す

        return stock_df, forex_df
    except Exception as e:
        return None, None # エラーが発生した場合もNoneを返す

# ------------------------------------------------
# メイン処理
# ------------------------------------------------
stock_data, forex_data = get_data(ticker_symbol, period)

if stock_data is not None and not stock_data.empty:
    # yfinanceが返すMultiIndexの列名をフラット化する
    stock_data.columns = [col[0] if isinstance(col, tuple) else col for col in stock_data.columns]
    if forex_data is not None:
        forex_data.columns = [col[0] if isinstance(col, tuple) else col for col in forex_data.columns]

    df = stock_data.copy()
    # --- 円建て表示の場合の処理 ---
    if show_jpy and forex_data is not None:
        # 1. 為替レート(USD/JPY)の終値をDataFrame化
        forex_close = forex_data[['Close']].rename(columns={'Close': 'forex_rate'})
        # 2. 日付インデックスで join
        df = df.join(forex_close, how='left')
        # 3. 為替レートの欠損値を前方補完 (ffill)
        df['forex_rate'] = df['forex_rate'].ffill()
        # 4. 円建て株価を計算
        for col in ['Open', 'High', 'Low', 'Close']:
            df[f'{col}_jpy'] = df[col].astype(float) * df['forex_rate'].astype(float)

        # --- チャート用の設定 ---
        chart_title = f'{ticker_symbol.upper()}  円建て株価チャート ({period})'
        yaxis_title = '株価 (円)'
        open_col, high_col, low_col, close_col = 'Open_jpy', 'High_jpy', 'Low_jpy', 'Close_jpy'
        preview_cols = ['Open_jpy', 'High_jpy', 'Low_jpy', 'Close_jpy', 'forex_rate']
        checkbox_label = '円建て株価データを表示'

    # --- ドル建て表示の場合の処理 ---
    else:
        # --- チャート用の設定 ---
        chart_title = f'{ticker_symbol.upper()}  株価チャート ({period})'
        yaxis_title = '株価 (USD)'
        open_col, high_col, low_col, close_col = 'Open', 'High', 'Low', 'Close'
        preview_cols = ['Open', 'High', 'Low', 'Close', 'Volume']
        checkbox_label = '株価データを表示'

    # --- チャート作成 ---
    fig = make_subplots(
        rows=2, cols=1, 
        shared_xaxes=True, 
        vertical_spacing=0.05,
        row_heights=[0.7, 0.3]
    )

    # --- 移動平均線の計算と描画 (先に追加して背面に描画) ---
    for period in sma_periods:
        sma_col_name = f'SMA_{period}'
        df[sma_col_name] = df[close_col].rolling(window=period).mean()
        fig.add_trace(go.Scatter(
            x=df.index, 
            y=df[sma_col_name], 
            mode='lines', 
            name=sma_col_name
        ), row=1, col=1) # 株価チャートに追加
        preview_cols.append(sma_col_name) # プレビューにも追加

    # --- 株価チャート (サブプロット1, 後に追加して最前面に描画) ---
    fig.add_trace(go.Candlestick(
        x=df.index,
        open=df[open_col],
        high=df[high_col],
        low=df[low_col],
        close=df[close_col],
        name='株価'
    ), row=1, col=1)

    # --- 出来高チャート (サブプロット2) ---
    fig.add_trace(go.Bar(
        x=df.index, 
        y=df['Volume'],
        name='出来高'
    ), row=2, col=1)

    # --- チャートのレイアウト設定 ---
    fig.update_layout(
        title_text=chart_title,
        xaxis_rangeslider_visible=False, # レンジスライダーを非表示に
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1)
    )
    # サブプロットごとのY軸設定
    fig.update_yaxes(title_text=yaxis_title, row=1, col=1)
    fig.update_yaxes(title_text="出来高", row=2, col=1)

    # --- アプリケーションへの表示 ---
    st.plotly_chart(fig, use_container_width=True)

    # データのプレビューをチェックボックスで表示
    if st.checkbox(checkbox_label):
        st.dataframe(df[preview_cols].round(2))
else:
    # --- エラーハンドリング ---
    st.error(f'「{ticker_symbol}」の株価データを取得できませんでした。ティッカーシンボルが正しいか確認してください。')
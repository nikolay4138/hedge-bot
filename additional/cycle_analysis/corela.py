import requests
import pandas as pd
import numpy as np
import time
import matplotlib.pyplot as plt
import seaborn as sns

def get_binance_futures_klines(symbol="BTCUSDT", interval="15m", start_str="2024-01-01"):
    """Binance Futures'tan geçmiş 15m verilerini çeker."""
    url = "https://fapi.binance.com/fapi/v1/klines"
    start_ts = int(pd.Timestamp(start_str).timestamp() * 1000)
    now_ts = int(pd.Timestamp.now().timestamp() * 1000)

    all_data = []
    while start_ts < now_ts:
        params = {
            "symbol": symbol,
            "interval": interval,
            "limit": 1000,
            "startTime": start_ts
        }
        res = requests.get(url, params=params)
        data = res.json()
        if not data or "code" in data:
            break
        all_data += data
        last_time = data[-1][6]
        start_ts = last_time + 1
        time.sleep(0.1)
        if len(all_data) % 10000 == 0:
            print(f"{symbol}: {len(all_data)} bar alındı...")

    df = pd.DataFrame(all_data, columns=[
        "open_time","open","high","low","close","volume",
        "close_time","quote_asset_volume","trades",
        "taker_base_vol","taker_quote_vol","ignore"
    ])
    df["open_time"] = pd.to_datetime(df["open_time"], unit="ms")
    df = df.astype({"close": float})
    return df[["open_time", "close"]]


def get_correlation(target_symbol="BNBUSDT", start_str="2024-01-01"):
    """Hedef coini BTCUSDT ve ETHUSDT ile korelasyonunu hesaplar."""
    print(f"{target_symbol} verisi alınıyor...")
    df_target = get_binance_futures_klines(target_symbol, "1h", start_str)
    df_btc = get_binance_futures_klines("BTCUSDT", "1h", start_str)
    df_eth = get_binance_futures_klines("ETHUSDT", "1h", start_str)

    # DataFrame'leri zaman bazında hizala
    df = df_target.merge(df_btc, on="open_time", suffixes=("", "_BTC"))
    df = df.merge(df_eth, on="open_time", suffixes=("", "_ETH"))

    # Log getiriler
    df["ret_target"] = np.log(df["close"] / df["close"].shift(1))
    df["ret_btc"] = np.log(df["close_BTC"] / df["close_BTC"].shift(1))
    df["ret_eth"] = np.log(df["close_ETH"] / df["close_ETH"].shift(1))

    df = df.dropna()

    # Korelasyon matrisi
    corr = df[["ret_target", "ret_btc", "ret_eth"]].corr()
    return corr


def plot_correlation_heatmap(corr, target_symbol="BNBUSDT"):
    """Korelasyon matrisini ısı haritası olarak çizer."""
    plt.figure(figsize=(6, 5))
    sns.heatmap(corr, annot=True, cmap="coolwarm", vmin=-1, vmax=1, fmt=".2f",
                linewidths=0.5, cbar_kws={'label': 'Korelasyon'})
    plt.title(f"{target_symbol} - BTCUSDT / ETHUSDT 15m Korelasyon Haritası")
    plt.tight_layout()
    plt.show()


# ---- ÇALIŞTIR ----
target = "ACXUSDT"   # örnek: "SOLUSDT", "XRPUSDT", "DOGEUSDT" vs.
corr = get_correlation(target, "2025-10-10")
print(corr)
plot_correlation_heatmap(corr, target)

import requests
import pandas as pd
import time
import matplotlib.pyplot as plt
import seaborn as sns

def get_binance_futures_klines(symbol="BTCUSDT", interval="15m", start_str="2024-01-01"):
    """Binance Futures'tan geçmiş 15m verileri çeker."""
    url = "https://fapi.binance.com/fapi/v1/klines"
    start_ts = int(pd.Timestamp(start_str).timestamp() * 1000)
    now_ts = int(pd.Timestamp.now().timestamp() * 1000)

    all_data = []
    print(f"{symbol} verileri çekiliyor...")
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
            print(f"{len(all_data)} bar alındı...")

    df = pd.DataFrame(all_data, columns=[
        "open_time","open","high","low","close","volume",
        "close_time","quote_asset_volume","trades",
        "taker_base_vol","taker_quote_vol","ignore"
    ])
    df["open_time"] = pd.to_datetime(df["open_time"], unit="ms")
    df = df.astype({
        "open": float, "high": float, "low": float, "close": float
    })
    return df


def create_heatmap(df, symbol="BTCUSDT"):
    """Günlük saat dilimlerine göre volatilite heatmap'i oluşturur."""
    df["date"] = df["open_time"].dt.date
    df["time"] = df["open_time"].dt.strftime("%H:%M")
    df["volatility"] = df["high"] - df["low"]

    # pivot tablo (her satır gün, sütun saat, değer = ortalama volatilite)
    pivot = df.pivot_table(index="date", columns="time", values="volatility", aggfunc="mean")

    # Görselleştir
    plt.figure(figsize=(18, 7))
    sns.heatmap(pivot, cmap="inferno", cbar_kws={'label': 'Volatilite (High-Low)'})
    plt.title(f"{symbol} Günlük 15 Dakikalık Volatilite Isı Haritası")
    plt.xlabel("Zaman Dilimi (15dk)")
    plt.ylabel("Tarih")
    plt.tight_layout()
    plt.show()


# ---- KULLANIM ----
symbol = "INUSDT"
df = get_binance_futures_klines(symbol, "15m", "2025-10-01")
create_heatmap(df, symbol)

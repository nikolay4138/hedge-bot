import requests
import pandas as pd
import time
import matplotlib.pyplot as plt
import seaborn as sns

def get_binance_futures_klines(symbol="BTCUSDT", interval="15m", start_str="2024-01-01", end_str=None):
    """
    Binance Futures'tan geçmiş 15 dakikalık mum verilerini çeker.
    start_str: başlangıç tarihi (örnek: "2024-01-01")
    end_str: bitiş tarihi (örnek: "2025-10-15"), None ise bugüne kadar
    """
    url = "https://fapi.binance.com/fapi/v1/klines"
    start_ts = int(pd.Timestamp(start_str).timestamp() * 1000)
    end_ts = int(pd.Timestamp(end_str).timestamp() * 1000) if end_str else int(pd.Timestamp.now().timestamp() * 1000)
    all_data = []

    print(f"{symbol} verileri çekiliyor ({start_str} → {end_str or 'şimdi'})...")
    while start_ts < end_ts:
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
            print(f"{len(all_data)} mum alındı...")

        # Eğer gelen verinin son zamanı end_ts'yi geçtiyse döngüyü kır
        if data[-1][6] >= end_ts:
            break

    df = pd.DataFrame(all_data, columns=[
        "open_time","open","high","low","close","volume",
        "close_time","quote_asset_volume","trades",
        "taker_base_vol","taker_quote_vol","ignore"
    ])
    df["open_time"] = pd.to_datetime(df["open_time"], unit="ms")
    df = df.astype({"high": float, "low": float})
    df = df[df["open_time"] <= pd.Timestamp(end_str) if end_str else True]  # end_date sınırı
    return df


def analyze_intraday_volatility(df):
    """Her 15 dakikalık zaman dilimi için ortalama volatiliteyi hesaplar."""
    df["volatility"] = df["high"] - df["low"]
    df["time_of_day"] = df["open_time"].dt.strftime("%H:%M")
    avg_vol = df.groupby("time_of_day")["volatility"].mean().reset_index()
    avg_vol = avg_vol.sort_values("time_of_day")
    return avg_vol


def plot_volatility(avg_vol, symbol="BTCUSDT"):
    """Ortalama volatiliteyi bar chart ve heatmap olarak görselleştirir."""
    plt.figure(figsize=(12, 5))
    plt.bar(avg_vol["time_of_day"], avg_vol["volatility"])
    plt.title(f"{symbol} Gün İçi 15 Dakikalık Ortalama Volatilite")
    plt.xticks(rotation=90)
    plt.ylabel("Ortalama Volatilite (High - Low)")
    plt.xlabel("Zaman Dilimi (15dk)")
    plt.tight_layout()
    plt.show()

    # Heatmap
    plt.figure(figsize=(14, 1.5))
    sns.heatmap([avg_vol["volatility"].values], cmap="inferno", cbar_kws={'label': 'Volatilite'})
    plt.yticks([])
    plt.xticks(ticks=range(len(avg_vol)), labels=avg_vol["time_of_day"], rotation=90)
    plt.title(f"{symbol} Gün İçi Volatilite Isı Haritası")
    plt.tight_layout()
    plt.show()


# ---- KULLANIM ----
symbol = "ETHUSDT"          # Örnek: "BTCUSDT", "SOLUSDT", "BNBUSDT"
start_date = "2025-10-10"   # Başlangıç tarihi
end_date = "2025-10-16"     # Bitiş tarihi

df = get_binance_futures_klines(symbol, "1h", start_date, end_date)
avg_vol = analyze_intraday_volatility(df)

print("\n📈 En yüksek volatiliteye sahip 10 zaman dilimi:")
print(avg_vol.sort_values("volatility", ascending=False).head(10))

plot_volatility(avg_vol, symbol)

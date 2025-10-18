import pandas as pd
import numpy as np
import asyncio
import ta


class AdvancedTechnicalIndicatorsFibLevels:
    def __init__(self, data: pd.DataFrame):
        self.data = data.copy()
        self.data.reset_index(inplace=True, drop=True)

    async def _calculate_rsi(self, period=7):
        rsi = ta.momentum.RSIIndicator(self.data["close"], window=period).rsi()
        self.data["rsi"] = rsi
        return rsi

    async def _calculate_derivatives(self, column_name, prefix, time_delta=60):
        self.data[f"{prefix}_diff1"] = self.data[column_name].diff() / time_delta
        self.data[f"{prefix}_diff2"] = self.data[f"{prefix}_diff1"].diff() / time_delta
        self.data[f"{prefix}_diff3"] = self.data[f"{prefix}_diff2"].diff() / time_delta

    async def _calculate_ema(self, column, span, prefix):
        ema = self.data[column].ewm(span=span, adjust=False).mean()
        self.data[f"{prefix}_ema"] = ema
        return ema

    async def _calculate_atr(self, period=14):
        atr = ta.volatility.AverageTrueRange(
            high=self.data["high"],
            low=self.data["low"],
            close=self.data["close"],
            window=period,
        ).average_true_range()
        self.data["atr"] = atr
        return atr

    async def _calculate_volume_ema(self, span=14):
        ema = self.data["volume"].ewm(span=span, adjust=False).mean()
        self.data["volume_ema"] = ema
        return ema

    async def _calculate_deviation(self, value_col, base_col, prefix):
        deviation = self.data[value_col] - self.data[base_col]
        self.data[f"{prefix}_dev"] = deviation
        return deviation

    async def compute_all_indicators(self):
        # RSI
        await self._calculate_rsi()
        await self._calculate_derivatives("rsi", "rsi", 60)

        # RSI EMA
        await self._calculate_ema("rsi", 14, "rsi")
        await self._calculate_derivatives("rsi_ema", "rsi_ema", 60)

        # RSI sapma
        await self._calculate_deviation("rsi", "rsi_ema", "rsi")
        await self._calculate_ema("rsi_dev", 14, "rsi_dev")
        await self._calculate_derivatives("rsi_dev_ema", "rsi_dev_ema", 60)

        # Fiyat EMA
        await self._calculate_ema("close", 14, "close")
        await self._calculate_derivatives("close_ema", "close_ema", 60)

        # Fiyat sapma
        await self._calculate_deviation("close", "close_ema", "price")
        await self._calculate_ema("price_dev", 14, "price_dev")
        await self._calculate_derivatives("price_dev_ema", "price_dev_ema", 60)

        # ATR
        await self._calculate_atr()
        await self._calculate_derivatives("atr", "atr", 60)

        # ATR EMA
        await self._calculate_ema("atr", 14, "atr")
        await self._calculate_deviation("atr", "atr_ema", "atr")
        await self._calculate_ema("atr_dev", 14, "atr_dev")
        await self._calculate_derivatives("atr_dev_ema", "atr_dev_ema", 60)

        # Hacim EMA
        await self._calculate_volume_ema()
        await self._calculate_derivatives("volume_ema", "volume_ema", 60)

        # Hacim sapma
        await self._calculate_deviation("volume", "volume_ema", "volume")
        await self._calculate_ema("volume_dev", 14, "volume_dev")
        await self._calculate_derivatives("volume_dev_ema", "volume_dev_ema", 60)

        return self.data

    async def get_fib_levels(self, data):
        """Aşırı alım ve satım bölgelerini bul ve Fibonacci seviyelerini hesapla"""
        pd.set_option("future.no_silent_downcasting", True)

        # RSI aşırı bölgeler
        data["in_oversold"] = data["rsi"] < 30
        data["in_overbought"] = data["rsi"] > 70

        data["oversold_start"] = data["in_oversold"] & ~data["in_oversold"].shift(
            1
        ).fillna(False)
        data["oversold_end"] = ~data["in_oversold"] & data["in_oversold"].shift(
            1
        ).fillna(False)

        data["overbought_start"] = data["in_overbought"] & ~data["in_overbought"].shift(
            1
        ).fillna(False)
        data["overbought_end"] = ~data["in_overbought"] & data["in_overbought"].shift(
            1
        ).fillna(False)

        # Tip temizliği
        data = data.infer_objects(copy=False)

        oversold_zones = data[data["oversold_end"] | data["oversold_start"]]
        overbought_zones = data[data["overbought_end"] | data["overbought_start"]]

        # Son bölgeler
        last_oversold = oversold_zones.tail(1)
        last_overbought = overbought_zones.tail(1)

        if last_oversold.empty or last_overbought.empty:
            return None, data

        if last_oversold.index[0] > last_overbought.index[0]:
            wave_start = last_overbought.index[0]
            wave_end = last_oversold.index[0]
            wave_type = 0
        else:
            wave_start = last_oversold.index[0]
            wave_end = last_overbought.index[0]
            wave_type = 1

        wave_data = data.loc[wave_start:wave_end]

        if wave_type == 0:
            start_high = wave_data["high"].max()
            end_low = wave_data["low"].min()
            price_range = start_high - end_low
        else:
            start_low = wave_data["low"].min()
            end_high = wave_data["high"].max()
            price_range = end_high - start_low

        fib_levels = {}
        retracement_ratios = [0.0, 0.236, 0.382, 0.5, 0.618, 0.786, 1.0]

        for ratio in retracement_ratios:
            if wave_type == 0:
                price = start_high - (price_range * ratio)
            else:
                price = start_low + (price_range * ratio)
            fib_levels[f"FIB_{int(ratio*1000)}"] = round(price, 4)

        return {
            "start_time": wave_start,
            "end_time": wave_end,
            "wave_type": wave_type,
            "start_zone": "aşırı alım" if wave_type == 0 else "aşırı satım",
            "end_zone": "aşırı satım" if wave_type == 0 else "aşırı alım",
            "fib_levels": fib_levels,
        }, data

    async def main(self):
        data_with_indicators = await self.compute_all_indicators()
        analysis, df = await self.get_fib_levels(data_with_indicators)
        return analysis, df


"""import pandas as pd
import numpy as np
import asyncio

# === Örnek veri seti oluştur (100 barlık OHLCV datası) ===
np.random.seed(42)
n = 100
dates = pd.date_range("2023-01-01", periods=n, freq="1H")
price = np.cumsum(np.random.randn(n)) + 100  # fiyat hareketi

df = pd.DataFrame({
    "time": dates,
    "open": price + np.random.randn(n),
    "high": price + np.random.rand(n) * 2,
    "low": price - np.random.rand(n) * 2,
    "close": price,
    "volume": np.random.randint(100, 1000, size=n)
})

# === Senin sınıfını kullan ===
async def run_analysis():
    model = AdvancedTechnicalIndicatorsFibLevels(df)

    # Tüm indikatörleri + fibonacci hesapla
    analysis, enriched_df = await model.main()

    print("\n=== Fibonacci Analizi ===")
    print(analysis)

    print("\n=== Enriched DataFrame Son 5 Satır ===")
    print(enriched_df.tail())

# Çalıştır
asyncio.run(run_analysis())
"""

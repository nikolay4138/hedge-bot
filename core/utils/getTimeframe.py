from core.utils.databaseProcess import DBReader

import pandas as pd

from core.getIndicators import AdvancedTechnicalIndicatorsFibLevels


class GeneratorTimeframe:
    def __init__(self):
        self.ohlcv_data = DBReader("binance_data/ohlcv.db")

    def resample_ohlcv(self, df: pd.DataFrame, timeframe: str) -> pd.DataFrame:
        """
        Saniyelik OHLCV datasından belirtilen timeframe üretir.
        """
        df["_ts"] = pd.to_datetime(df["timestamp"], unit="s")
        df = df.set_index("_ts")

        ohlcv = (
            df.resample(timeframe)
            .agg(
                {
                    "open": "first",
                    "high": "max",
                    "low": "min",
                    "close": "last",
                    "volume": "sum",
                }
            )
            .dropna()
        )

        ohlcv = ohlcv.reset_index()
        ohlcv["timestamp"] = ohlcv["_ts"].astype("int64") // 10**9

        return ohlcv[["timestamp", "open", "high", "low", "close", "volume"]]

    async def extract_d_analysis(self, symbol, timeframe):
        data = self.ohlcv_data.get_all_as_df(symbol)

        resampled_data = self.resample_ohlcv(data, timeframe)
        indicator = AdvancedTechnicalIndicatorsFibLevels(resampled_data)
        analysis, enriched_df = await indicator.main()

        return timeframe, enriched_df, analysis

"""
açıklı bilgilerini alır ve kaydeder
pozisyon bilgilerini datadan okur
hem long hem short aktifse, açıklık bilgilerine bakar
15m data yaratır ve son atrye bakar
eğer son atr ile açıklık bilgisi arasındaki farkı da büyüklük küçüklük durumuna kaydeder
data yapısı: symbol, aperture, aperture_compare_atr
start stopdan bağımsız çalışır
"""

import asyncio
import pandas as pd
from core.utils import SQLiteManager, DBReader
from dataGetter.tfCreator.getTf import GeneratorTimeframe
import time


class HedgeApertureController:
    """
    Controller class to calculate and store aperture (price difference)
    between LONG and SHORT positions for symbols that have both sides open.
    """

    def __init__(
        self, hedge_db_path="binance_data/hedge.db", open_db_path="binance_data/open.db"
    ):
        self.generator = GeneratorTimeframe()
        self.db_writer = SQLiteManager(hedge_db_path)
        self.db_reader = DBReader(open_db_path)

    async def main(self):
        """Entry point to process and store apertures for open positions."""
        positions_df = self._get_positions_with_sides()
        both_side_symbols = self._get_symbols_with_both_sides(positions_df)

        for symbol in both_side_symbols:
            aperture = self._calculate_aperture(symbol)
            if aperture is not None:
                self._store_aperture(symbol, aperture)

    def _get_positions_with_sides(self) -> pd.DataFrame:
        """Load positions and split into symbol and side (LONG/SHORT)."""
        df = self.db_reader.get_all_generic_df("positions")
        df["symbol"] = df["pos"].str.replace(r"_(LONG|SHORT)$", "", regex=True)
        df["side"] = df["pos"].str.extract(r"_(LONG|SHORT)$")
        return df

    @staticmethod
    def _get_symbols_with_both_sides(df: pd.DataFrame) -> list[str]:
        """Return list of symbols that have both LONG and SHORT positions."""
        return (
            df.groupby("symbol")["side"].nunique().loc[lambda x: x == 2].index.tolist()
        )

    def _calculate_aperture(self, symbol: str) -> float | None:
        """
        Calculate the aperture (difference between LONG and SHORT entry prices).
        Returns None if data is missing.
        """
        try:
            df_long = self.db_reader.get_all_generic_df(f"{symbol}_LONG")
            df_short = self.db_reader.get_all_generic_df(f"{symbol}_SHORT")

            entry_long = float(df_long.iloc[-1]["entryPrice"])
            entry_short = float(df_short.iloc[-1]["entryPrice"])

            return entry_long - entry_short
        except (IndexError, KeyError, ValueError) as e:
            print(f"Error calculating aperture for {symbol}: {e}")
            return None

    def _store_aperture(self, symbol: str, aperture: float) -> None:
        """Save the aperture value into the hedge database."""
        self.db_writer.create_table(
            symbol, {"aperture": "REAL", "timestamp": "INTEGER"}
        )
        timestamp_ms = int(time.time() * 1000)
        self.db_writer.insert(symbol, {"aperture": aperture, "timestamp": timestamp_ms})
        print(f"[INFO] {symbol} aperture stored: {aperture}")


hpa = HedgeApertureController()
while True:
    asyncio.run(hpa.main())

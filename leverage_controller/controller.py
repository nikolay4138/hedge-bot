from core.utils.databaseProcess import SQLiteManager, DBReader
from core.trading import BinanceFuturesTrader

"""
her 10 saniyede 1 kez kaldıraçları kontrol eder ve değiştirir.
"""


class LeverageController:
    """10 kat büyüklüğün eş değeri olan büyüklüklüklerden max kaldıraç seçilir"""

    def __init__(self) -> None:
        self.read_min_amounts = DBReader("binance_data/min_amounts.db")
        self.read_lev_db = DBReader("binance_data/leverage_data.db")
        self.trader = BinanceFuturesTrader(testnet=False, debug=True, proxy="")
        self.opendDB = DBReader("binance_data/open.db")

    @staticmethod
    def calculate_max_amount(min_amount, kat=10):
        try:
            min_amount = float(min_amount)
            max_amount = min_amount * kat
            return max_amount
        except Exception as e:
            print(f"Error in calculate_max_amount: {e}")
            return None

    def select_nation(self, nation, nation_list):
        int_values = [int(v) for v in nation_list]
        closest = min(int_values, key=lambda x: abs(x - nation))
        indices = [i for i, v in enumerate(int_values) if v == closest]
        leverage = max(indices) + 1
        return closest, leverage

    def get_min_amount(self, symbol):
        min_amount = self.read_min_amounts.get_all_generic_df(symbol)
        return min_amount["min_amounts"].values[0]

    async def get_leverage(self, symbol):
        leverage = self.read_lev_db.get_all_generic_df(symbol)
        return leverage["maxNotionalValue"].to_list()

    async def set_leverage(self, symbol, leverage):
        await self.trader.change_leverage(leverage, symbol)
        await self.trader.close()

    async def main(self):
        while True:
            df = self.opendDB.get_all_generic_df("open_symbol")
            symbols = df["symbol"].to_list()
            for symbol in symbols:
                min_amount = self.get_min_amount(symbol)

                max_amount = self.calculate_max_amount(min_amount, 20)

                leverage_data = await self.get_leverage(symbol)
                closest_nation, leverage = self.select_nation(max_amount, leverage_data)
                print(symbol, closest_nation, leverage)
                await self.set_leverage(symbol, int(leverage))
            await asyncio.sleep(10)


if __name__ == "__main__":
    import asyncio

    lvg = LeverageController()
    asyncio.run(lvg.main())  # Örnek sembol ile test

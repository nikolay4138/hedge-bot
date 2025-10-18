import asyncio
from datetime import datetime

from core.trading import BinanceFuturesTrader
from tMessager.main import TelegramBot
from core.utils.databaseProcess import DBReader, SQLiteManager


class GetPositions:
    def __init__(self) -> None:
        self.PROXY = ""
        self.trader = BinanceFuturesTrader(testnet=False, debug=True, proxy=self.PROXY)
        self.db = SQLiteManager("binance_data/open.db")

    def _store_symbols(self, symbols: list[str]):
        """Store unique symbols into the database."""
        self.db.create_table("open_symbol", {"symbol": "TEXT"})
        self.db.clear_table("open_symbol")

        for symbol in symbols:
            self.db.insert("open_symbol", {"symbol": symbol})

    def _store_positions(self, positions: list[dict]):
        """Store open positions into the database."""
        self.db.create_table("positions", {"pos": "TEXT"})
        self.db.clear_table("positions")

        for pos in positions:
            info = pos["info"]
            symbol, pos_side = info["symbol"], info["positionSide"]
            table_name = f"{symbol}_{pos_side}"

            self.db.create_table(
                table_name,
                {
                    "symbol": "TEXT",
                    "pos_side": "TEXT",
                    "amount": "REAL",
                    "entryPrice": "REAL",
                    "liquidationPrice": "REAL",
                    "initialMargin": "REAL",
                    "unRealizedProfit": "REAL",
                    "updateTime": "INTEGER",
                },
            )

            data = {
                "symbol": symbol,
                "pos_side": pos_side,
                "amount": float(info["positionAmt"]) * float(info["entryPrice"]),
                "entryPrice": float(info["entryPrice"]),
                "liquidationPrice": float(info["liquidationPrice"]),
                "initialMargin": float(info["initialMargin"]),
                "unRealizedProfit": float(info["unRealizedProfit"]),
                "updateTime": int(info["updateTime"]),
            }
            self.db.insert(table_name, data)
            self.db.insert("positions", {"pos": table_name})

    async def main(self):
        """Main loop: fetch, process, and store positions."""
        while True:
            positions = await self.trader.get_positions()
            await self.trader.close()

            unique_symbols = list({pos["info"]["symbol"] for pos in positions})

            # Store symbols & positions
            self._store_symbols(unique_symbols)
            await asyncio.sleep(0.001)

            self._store_positions(positions)
            await asyncio.sleep(0.001)


"""gg = GetPositions()

if __name__ == "__main__":
    import asyncio

    asyncio.run(gg.main())
"""
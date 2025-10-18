import asyncio
import time
from datetime import datetime
from core.trading import BinanceFuturesTrader
from core.utils.databaseProcess import SQLiteManager
from tMessager.main import TelegramBot


class BalanceCollector:
    """
    Periodically collects Binance Futures account balance
    and stores it in a local SQLite database.
    """

    def __init__(
        self, db_path: str = "binance_data/balance.db", proxy: str = ""
    ) -> None:
        self.proxy = proxy
        self.trader = BinanceFuturesTrader(testnet=False, debug=True, proxy=self.proxy)
        self.db = SQLiteManager(db_path)

    async def main(self):
        """Continuously fetch balance and store in DB every `interval_sec` seconds."""
        while True:
            try:
                balance = await self._fetch_balance()
                if balance:
                    self._store_balance(balance)
                    print(f"[{datetime.now()}] Balance stored successfully.")
                else:
                    print("[WARN] No balance data received.")
            except Exception as e:
                print(f"[ERROR] Balance fetch failed: {e}")

            await asyncio.sleep(0.001)

    async def _fetch_balance(self) -> dict | None:
        """Fetch balance from Binance Futures and close connection properly."""
        try:
            balance = await self.trader.get_balance()
            await self.trader.close()
            return balance
        except Exception as e:
            print(f"[ERROR] Failed to fetch balance: {e}")
            return None

    def _store_balance(self, balance: dict) -> None:
        """Insert the fetched balance into SQLite database."""
        self.db.create_table(
            "balance",
            {
                "timestamp": "INTEGER",
                "wallet_balance": "REAL",
                "total": "REAL",
                "available": "REAL",
                "unreal_profit": "REAL",
            },
        )

        # 13 haneli milisaniye timestamp
        timestamp_ms = int(time.time() * 1000)

        data = {
            "timestamp": timestamp_ms,
            "wallet_balance": balance.get("wallet_balance", 0.0),
            "total": balance.get("total", 0.0),
            "available": balance.get("available", 0.0),
            "unreal_profit": balance.get("unreal_profit", 0.0),
        }

        self.db.insert("balance", data)


"""gg = BalanceCollector()

if __name__ == "__main__":
    import asyncio

    asyncio.run(gg.main())"""
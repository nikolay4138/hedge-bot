from core.utils.databaseProcess import SQLiteManager

import ccxt.async_support as ccxt  # async destekli ccxt


class getMin:
    def __init__(self):
        self.DB_FILE = "binance_data/min_amounts.db"
        self.write_min = SQLiteManager(self.DB_FILE)

    async def get_min_amounts(self):
        exchange = ccxt.binanceusdm(
            {
                "enableRateLimit": True,
                "options": {"defaultType": "future"},  # USDⓈ-M futures
            }
        )

        await exchange.load_markets()

        min_amounts = []
        for symbol, market in exchange.markets.items():
            if symbol.endswith("/USDT:USDT"):
                raw_symbol = market["id"]  # ör: BTCUSDT
                min_cost = market["limits"]["cost"]["min"]
                min_amounts.append((raw_symbol, min_cost + 1.5))

        await exchange.close()
        return min_amounts

    async def update_db(self, min_amounts):
        # Eğer klasör yoksa oluştur
        for symbol, min_cost in min_amounts:
            self.write_min.create_table(
                f"{symbol}",
                {
                    "min_amounts": "REAL PRIMARY KEY",
                },
            )
            self.write_min.clear_table(f"{symbol}")

            self.write_min.insert(
                f"{symbol}",
                {
                    "min_amounts": min_cost,
                },
            )
        self.write_min.close()

    async def main(self):
        min_amounts = await self.get_min_amounts()
        await self.update_db(min_amounts)  # sqlite3 db’ye yaz
        print(f"{self.DB_FILE} veritabanı güncellendi ✅")

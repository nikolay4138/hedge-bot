import os
import requests
from core.utils.databaseProcess import SQLiteManager


class getLeverage:
    def __init__(self) -> None:
        self.write_lev = SQLiteManager("binance_data/leverage_data.db")

    async def main(self):
        url = "https://fapi.binance.com/fapi/v1/exchangeInfo"
        response = requests.get(url)
        data = response.json()

        # Tüm semboller
        symbols = data["symbols"]

        # Sadece USDT pariteleri
        usdt_pairs = [s["symbol"] for s in symbols if s["symbol"].endswith("USDT")]

        print(f"Toplam {len(usdt_pairs)} adet USDT futures paritesi var:")
        base_port = os.getenv("BASE_PORT")
        PROXY = "http://100.81.145.12:3150"
        from core.trading import BinanceFuturesTrader

        trader = BinanceFuturesTrader(testnet=False, debug=True, proxy=PROXY)

        for symbol in usdt_pairs:
            for i in range(1, 126):
                try:
                    data = await trader.change_leverage(i, symbol)
                    print(data)
                    self.write_lev.create_table(
                        f"{symbol}",
                        {
                            "leverage": "INTEGER",
                            "maxNotionalValue": "REAL",
                        },
                    )
                    self.write_lev.insert(
                        symbol,
                        {
                            "leverage": int(data["leverage"]),
                            "maxNotionalValue": float(data["maxNotionalValue"]),
                        },
                    )

                except Exception as e:
                    print(f"{symbol}-{i} için hata oluştu: {e}")

        await trader.close()
        self.write_lev.close()

import ccxt.async_support as ccxt
class lastPrice:
    def __init__(self) -> None:
        pass

    async def main(self, symbol: str = "BTC/USDT"):
        exchange = ccxt.binance(
            {
                "options": {"defaultType": "future"},  # Binance Futures için
            }
        )

        try:
            ticker = await exchange.fetch_ticker(symbol)
            return ticker["last"]
        finally:
            await exchange.close()

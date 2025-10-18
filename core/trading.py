import ccxt.async_support as ccxt
import asyncio
import time
from typing import Dict, List, Optional
import os
import json

class BinanceFuturesTrader:
    def __init__(
        self, testnet: bool = False, debug: bool = False, proxy: str | None = None
    ):
        self.filepath = "core/config.json"
        with open(self.filepath, "r") as file:
            config = json.load(file)
        self.API_KEY = config["config"][0]["API_KEY"]
        self.API_SECRET = config["config"][0]["API_SECRET"]
        self.debug = debug
        self.markets_loaded = False

        # .env içinden PROXY tanımlıysa kullan

        exchange_config = {
            "apiKey": self.API_KEY,
            "secret": self.API_SECRET,
            "enableRateLimit": True,
            "options": {"adjustForTimeDifference": True},
        }

        # async sürüm için doğru alan
        if proxy:
            exchange_config["aiohttp_proxy"] = (
                proxy  # örn: "http://user:pass@127.0.0.1:8080"
            )
            if self.debug:
                print(f"[DEBUG] aiohttp_proxy set: {proxy}")

        # usdm futures
        self.exchange = ccxt.binanceusdm(exchange_config)
        if testnet:
            self.exchange.set_sandbox_mode(True)

    async def ensure_markets(self):
        """Market bilgilerini sadece bir kere yükle"""
        if not self.markets_loaded:
            await self.exchange.load_markets()
            self.markets_loaded = True
            if self.debug:
                print("Market bilgileri yüklendi ✅")

    async def market_order(
        self, symbol: str, side: str, position_side: str, usdt_amount: float
    ):
        try:
            ticker = await self.exchange.fetch_ticker(symbol)
            price = ticker["last"]
            amount = usdt_amount / price

            params = {"positionSide": position_side.upper()}

            order = await self.exchange.create_order(
                symbol=symbol, type="market", side=side, amount=amount, params=params
            )
            if self.debug:
                print(
                    f"[{time.strftime('%H:%M:%S')}] Market emri başarılı: {order['id']}"
                )
            return order
        except Exception as e:
            print(f"[{time.strftime('%H:%M:%S')}] Market emir hatası: {str(e)}")
            return {}

    async def get_interval_data(self, symbol, timeframe, limit):
        ohlcv = await self.exchange.fetch_ohlcv(symbol, timeframe, limit)
        return ohlcv

    async def get_balance(self) -> Dict[str, float]:
        retries = 3
        for attempt in range(retries):
            try:
                balance = await self.exchange.fetch_balance()
                timestamp_ms = int(time.time() * 1000)
                info = balance.get("info", {})
                usdt = balance.get("USDT", {})

                return {
                    "wallet_balance": float(info.get("totalWalletBalance", 0)),
                    "total": usdt.get("total", 0.0),
                    "available": usdt.get("free", 0.0),
                    "unreal_profit": float(info.get("totalUnrealizedProfit", 0)),
                    "timestamp": timestamp_ms,
                }

            except Exception as e:
                print(
                    f"[{time.strftime('%H:%M:%S')}] Bakiye hatası (deneme {attempt+1}/{retries}): {str(e)}"
                )
                await asyncio.sleep(1)  # küçük bekleme

        # retries bitti → güvenli fallback
        return {"wallet_balance": 0, "total": 0, "available": 0, "unreal_profit": 0}

    async def get_positions(self, symbol: Optional[str] = None) -> List[dict]:
        try:
            positions = await self.exchange.fetch_positions(
                symbols=[symbol] if symbol else None
            )
            return [p for p in positions if float(p["contracts"]) != 0]
        except Exception as e:
            print(f"[{time.strftime('%H:%M:%S')}] Pozisyon hatası: {str(e)}")
            return []

    async def change_leverage(self, leverage: int, symbol: str):
        try:
            return await self.exchange.set_leverage(leverage, symbol)
        except Exception as e:
            print(f"Hata oluştu: {e}")
            return False

    async def close(self):
        await self.exchange.close()

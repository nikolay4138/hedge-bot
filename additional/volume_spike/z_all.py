import asyncio
import json
import aiohttp
import websockets
import numpy as np
from collections import deque

# ======================
# KULLANICI AYARLARI
INTERVAL = "1s"      # Örnek: "1s", "3s", "5s", "1m", "2m", "5m"
WINDOW = 20          # Ortalama ve standart sapma için son n bar
Z_THRESHOLD = 2.0    # z-score eşiği
# ======================

volume_data = {}  # sembol -> deque(volumes)

async def get_usdt_symbols():
    """Binance Futures'tan tüm USDT paritelerini al."""
    url = "https://fapi.binance.com/fapi/v1/exchangeInfo"
    async with aiohttp.ClientSession() as session:
        async with session.get(url) as resp:
            data = await resp.json()
            return [
                s["symbol"].lower()
                for s in data["symbols"]
                if s["quoteAsset"] == "USDT" and s["status"] == "TRADING"
            ]

async def listen_symbol(symbol):
    """Belirli bir sembolün kline stream'ini dinle ve z-score ile spike tespit et."""
    url = f"wss://fstream.binance.com/ws/{symbol}@kline_{INTERVAL}"
    volume_data[symbol] = deque(maxlen=WINDOW)

    async for ws in websockets.connect(url):
        try:
            async for message in ws:
                data = json.loads(message)
                k = data["k"]
                if k["x"]:  # Kapanan bar
                    vol = float(k["v"])
                    dq = volume_data[symbol]
                    dq.append(vol)

                    if len(dq) == WINDOW:
                        avg = np.mean(dq)
                        std = np.std(dq)
                        if std == 0:
                            continue
                        z_score = (vol - avg) / std
                        if z_score > Z_THRESHOLD:
                            print(f"🚀 {symbol.upper()} Volume spike! {vol:.2f} (avg {avg:.2f}, z {z_score:.2f})")
        except Exception as e:
            print(f"{symbol.upper()} için bağlantı hatası: {e}, yeniden bağlanıyor...")
            await asyncio.sleep(5)

async def main():
    symbols = await get_usdt_symbols()
    print(f"{len(symbols)} USDT paritesi bulundu. Dinleniyor... Interval={INTERVAL}")

    tasks = [asyncio.create_task(listen_symbol(s)) for s in symbols]
    await asyncio.gather(*tasks)

asyncio.run(main())

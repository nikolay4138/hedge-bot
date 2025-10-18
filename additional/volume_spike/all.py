import asyncio
import json
import aiohttp
import websockets
from collections import deque

INTERVAL = "1m"          # Mum aralığı (1s, 1m, 5m, vs.)
WINDOW = 20              # Ortalama alınacak bar sayısı
SPIKE_FACTOR = 3.0       # Hacim artışı eşiği

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
    """Belirli bir sembolün kline stream'ini dinle."""
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
                        avg_vol = sum(dq) / WINDOW
                        if vol > avg_vol * SPIKE_FACTOR:
                            print(f"🚀 {symbol.upper()} - Volume spike! {vol:.2f} (ortalama {avg_vol:.2f})")
        except Exception as e:
            print(f"{symbol.upper()} için bağlantı hatası: {e}, yeniden bağlanıyor...")
            await asyncio.sleep(5)

async def main():
    symbols = await get_usdt_symbols()
    print(f"{len(symbols)} USDT paritesi bulundu. Dinleniyor...")

    # Tüm pariteler için websocket görevlerini paralel başlat
    tasks = [asyncio.create_task(listen_symbol(s)) for s in symbols]
    await asyncio.gather(*tasks)

asyncio.run(main())

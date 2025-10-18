import asyncio
import json
import websockets
import sqlite3
import os
import time
from collections import defaultdict
import math
import multiprocessing as mp
from concurrent.futures import ProcessPoolExecutor

from core.utils import getusdtPairs


class getData:
    def __init__(
        self,
        symbols_file="symbols.sml",
        db_file="binance_data/ohlcv.db",
        proxy_host=None,
    ):
        self.symbols_file = symbols_file
        self.symbols = []
        self.symbol_to_port = {}
        self.base_port = 3133
        self.num_ports = 4

        self.load_symbols()
        self.last_mtime = os.path.getmtime(self.symbols_file)

        self.BINANCE_FUTURES_WS = "wss://fstream.binance.com/ws/"
        self.ohlcv_1s = defaultdict(
            lambda: {
                "open": None,
                "high": None,
                "low": None,
                "close": None,
                "volume": 0.0,
                "last_ts": 0,
            }
        )

        self.symbol_tasks: dict[str, asyncio.Task] = {}
        self.total_requests = 0
        self.symbol_requests = defaultdict(int)

        # Proxy ayarı (zorunlu değil)
        self.proxy_host = proxy_host

        # --- SQLite setup ---
        os.makedirs(os.path.dirname(db_file), exist_ok=True)
        self.db_file = db_file
        self.conn = sqlite3.connect(self.db_file, check_same_thread=False)
        self.conn.execute("PRAGMA journal_mode=WAL;")  # eşzamanlı okuma/yazma için
        self.conn.execute("PRAGMA synchronous=NORMAL;")
        self.cursor = self.conn.cursor()

        print(f"[DB] SQLite başlatıldı: {self.db_file}")

    # ---------------- Symbol yönetimi ----------------

    def load_symbols(self):
        symbols = []
        with open(self.symbols_file, "r", encoding="utf-8") as f:
            for line in f:
                sym = line.strip()
                if sym:
                    symbols.append(sym)

        self.symbols = symbols
        total = len(self.symbols)
        block_size = math.ceil(total / self.num_ports)

        self.symbol_to_port = {}
        for i, sym in enumerate(self.symbols):
            port_index = i // block_size
            if port_index >= self.num_ports:
                port_index = self.num_ports - 1
            self.symbol_to_port[sym] = self.base_port + port_index

        print(f"[INFO] {total} sembol yüklendi.")
        print(
            f"[INFO] {self.num_ports} port kullanılacak ({self.base_port}–{self.base_port + self.num_ports - 1})"
        )

    async def watch_symbols_file(self, interval=5):
        while True:
            try:
                mtime = os.path.getmtime(self.symbols_file)
                if mtime != self.last_mtime:
                    self.last_mtime = mtime
                    old_symbols = set(self.symbols)
                    self.load_symbols()
                    new_symbols = set(self.symbols)

                    for sym in new_symbols - old_symbols:
                        self.create_table(sym)
                        if sym not in self.symbol_tasks:
                            t = asyncio.create_task(self.listen_symbol(sym))
                            self.symbol_tasks[sym] = t
                            print(f"[INFO] {sym} için yeni task başlatıldı")
            except Exception as e:
                print(f"[WARN] symbols.sml izleme hatası: {e}")
            await asyncio.sleep(interval)

    # ---------------- SQLite Yazıcı ----------------

    def create_table(self, symbol):
        """Her sembol için tablo oluştur"""
        table_name = symbol.upper()
        self.cursor.execute(
            f"""
            CREATE TABLE IF NOT EXISTS "{table_name}" (
                timestamp INTEGER PRIMARY KEY,
                open REAL,
                high REAL,
                low REAL,
                close REAL,
                volume REAL
            )
        """
        )
        self.conn.commit()
        print(f"[DB] Tablo hazır: {table_name}")

    def write_db(self, symbol, row):
        """Anlık veri DB’ye yazılır"""
        table_name = symbol.upper()
        try:
            # print(f"[DB WRITE] {table_name} -> {row}")  # DEBUG
            self.cursor.execute(
                f"""
                INSERT OR REPLACE INTO "{table_name}" (timestamp, open, high, low, close, volume)
                VALUES (?, ?, ?, ?, ?, ?)
            """,
                row,
            )
            self.conn.commit()
        except Exception as e:
            print(f"[DB ERROR] {symbol}: {e}")

    async def flush_task(self):
        while True:
            ts = int(time.time())
            for symbol, data in list(self.ohlcv_1s.items()):
                if data["open"] is not None and data.get("last_flush", 0) != ts:
                    self.write_db(
                        symbol,
                        [
                            ts,
                            data["open"],
                            data["high"],
                            data["low"],
                            data["close"],
                            data["volume"],
                        ],
                    )
                    data["last_flush"] = ts
            await asyncio.sleep(1)

    # ---------------- WebSocket dinleyici ----------------

    async def listen_symbol(self, symbol: str):
        url = self.BINANCE_FUTURES_WS + f"{symbol.lower()}@kline_1m"

        proxy_port = self.symbol_to_port[symbol]
        proxy_uri = None
        if self.proxy_host:
            proxy_uri = f"http://{self.proxy_host}:{proxy_port}"

        ws = None
        try:
            kwargs = dict(
                ping_interval=20,
                ping_timeout=20,
                close_timeout=10,
            )
            if proxy_uri:
                kwargs["proxy"] = proxy_uri

            ws = await websockets.connect(url, **kwargs)
            print(
                f"[WS] Connected to {symbol} {'via ' + proxy_uri if proxy_uri else ''}"
            )

            self.create_table(symbol)

            async for msg in ws:
                self.total_requests += 1
                self.symbol_requests[symbol] += 1

                data = json.loads(msg)
                kline = data["k"]

                open_price = float(kline["o"])
                high = float(kline["h"])
                low = float(kline["l"])
                close = float(kline["c"])
                volume = float(kline["v"])
                ts = int(time.time())

                ohlcv = self.ohlcv_1s[symbol]
                if ohlcv["last_ts"] != ts:
                    self.ohlcv_1s[symbol] = {
                        "open": open_price,
                        "high": high,
                        "low": low,
                        "close": close,
                        "volume": volume,
                        "last_ts": ts,
                    }
                else:
                    ohlcv["high"] = max(ohlcv["high"], high)
                    ohlcv["low"] = min(ohlcv["low"], low)
                    ohlcv["close"] = close
                    ohlcv["volume"] += volume

        except asyncio.CancelledError:
            print(f"[WS] {symbol} task cancelled")
            if ws:
                await ws.close()
            raise
        except Exception as e:
            print(f"[ERROR] {symbol} {f'via {proxy_uri}' if proxy_uri else ''}: {e}")
            if ws:
                await ws.close()

    # ---------------- Ana kontrol ----------------

    async def main(self):
        tasks = [
            asyncio.create_task(self.flush_task()),
            asyncio.create_task(self.watch_symbols_file()),
        ]

        for sym in self.symbols:
            if sym not in self.symbol_tasks:
                self.create_table(sym)
                t = asyncio.create_task(self.listen_symbol(sym))
                self.symbol_tasks[sym] = t
                print(f"[INFO] {sym} için başlangıç task başlatıldı")

        await asyncio.gather(*tasks)


async def run_all():
    """Tüm görevleri başlat ve yönet"""
    try:
        # USDT parite izleyici ve veri toplayıcıyı başlat
        usdt = getusdtPairs()
        gd = getData("core/symbolsInfo/usdt_pairs.sml", proxy_host=None)

        # İki görevi paralel çalıştır
        # usdt.main(15) -> her 15 saniyede bir güncellenecek
        await asyncio.gather(
            usdt.main(3600), gd.main()  # 3600 saniyelik güncelleme aralığı
        )
    except asyncio.CancelledError:
        print("\nGörevler sonlandırılıyor...")
    except Exception as e:
        print(f"\nHata oluştu: {e}")


if __name__ == "__main__":
    try:
        print("Veri toplama sistemi başlatılıyor...")
        asyncio.run(run_all())
    except KeyboardInterrupt:
        print("\nUygulama kapatılıyor...")
    finally:
        print("Uygulama kapatıldı.")

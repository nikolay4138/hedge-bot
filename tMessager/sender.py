"""
Tüm DB'leri okuyup belirli aralıklarla (örneğin 5 saniyede bir) Telegram'a mesaj gönderir.
"""

from datetime import datetime
from tMessager.main import TelegramBot
from core.utils import JsonReader, DBReader


class Sender:
    def __init__(self, file_path: str, chat_type: str) -> None:
        """Konfigürasyonu yükler ve Telegram bot nesnesini başlatır."""
        json_reader = JsonReader(file_path)
        config = json_reader.main()

        if not config:
            raise ValueError("Konfigürasyon dosyası okunamadı.")

        self.TOKEN_ID = config["config"]["TOKEN"]
        self.CHAT_ID = config["config"][chat_type]
        self.bot = TelegramBot(chat_id=self.CHAT_ID, token_id=self.TOKEN_ID)

    async def send_last_row(
        self, db_path: str, excluded_tables: list[str] = None
    ) -> None:
        """Verilen veritabanındaki her tablonun son satırını Telegram'a gönderir."""
        excluded_tables = excluded_tables or []

        db = DBReader(db_path)
        for table in db.list_tables():
            if table in excluded_tables:
                continue

            last_rows = db.generic_get_last_row(table, 1)
            if last_rows:
                await self.bot.send_message_dict(last_rows[0])

        db.close()

    async def main(self, interval: int) -> None:
        """Belirtilen saniye aralığında verileri Telegram'a yollar."""
        now = datetime.now()
        if now.second % interval != 0:
            return  # Sadece belirtilen aralıkta çalışır

        # 1️⃣ Balance DB
        await self.send_last_row("binance_data/balance.db")

        # 2️⃣ Open DB (bazı tablolar hariç)
        await self.send_last_row(
            "binance_data/open.db", excluded_tables=["open_symbol", "positions"]
        )

        # 3️⃣ Opened DB
        await self.send_last_row("binance_data/opened.db")

        # 4️⃣ Closed DB
        await self.send_last_row("binance_data/closed.db")

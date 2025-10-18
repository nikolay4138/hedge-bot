import aiohttp
import json


class TelegramBot:
    def __init__(self, token_id: str, chat_id: str):
        self.base_url = f"https://api.telegram.org/bot{token_id}"
        self.chat_id = chat_id

    async def send_message(self, text: str) -> bool:
        """
        Telegram'a mesaj gönderir.
        Başarılı olursa True döner, hata durumunda False.
        """
        url = f"{self.base_url}/sendMessage"
        payload = {"chat_id": self.chat_id, "text": text}

        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(url, data=payload) as response:
                    if response.status == 200:
                        return True
                    else:
                        hata = await response.text()
                        print(f"[HATA] Mesaj gönderilemedi: {response.status} - {hata}")
                        return False
        except aiohttp.ClientError as e:
            print(f"[HATA] Ağ hatası: {e}")
            return False
        except Exception as e:
            print(f"[BEKLENMEYEN HATA] {e}")
            return False

    async def send_message_dict(self, payload: dict) -> bool:
        """
        Telegram'a JSON (dict) formatında mesaj gönderir.
        Başarılı olursa True döner, hata durumunda False.
        """
        url = f"{self.base_url}/sendMessage"

        # chat_id yoksa ekle (bazı payload'lar chat_id içermeyebilir)
        if "chat_id" not in payload:
            payload["chat_id"] = self.chat_id

        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(url, json=payload) as response:
                    if response.status == 200:
                        return True
                    else:
                        hata = await response.text()
                        print(f"[HATA] Mesaj gönderilemedi: {response.status} - {hata}")
                        return False
        except aiohttp.ClientError as e:
            print(f"[HATA] Ağ hatası: {e}")
            return False
        except Exception as e:
            print(f"[BEKLENMEYEN HATA] {e}")
            return False


"""
# Örnek kullanım
async def main():
    token = "8465402931:AAGiZxdLJ4drY18S_yihTzaCrUQTIdB0HfA"   # @BotFather’dan aldığın token
    chat_id = "-1002674862471"   # hedef chat_id (kendi user_id veya grup id olabilir)

    bot = TelegramBot(token, chat_id)
    await bot.send_message("Merhaba! Bu mesaj Python'dan geldi 🚀")
import time
while True:
    asyncio.run(main())  # Çalıştırmak için yorumdan çıkar
    time.sleep(5)
    
"""

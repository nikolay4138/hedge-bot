import asyncio
import nest_asyncio
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes
import os
import time
from datetime import datetime
import psutil
import subprocess
import psutil
import json
nest_asyncio.apply()
from core.utils.getDatabase import dbGetterSetter

start_event = asyncio.Event()
stop_event = asyncio.Event()


class MainProcess:
    def __init__(self):
        with open("core/config.json") as f:
            config = json.load(f)
        self.start_stop_db=dbGetterSetter.startstopdb()

        self.TOKEN = config["config"][0]["TOKEN"]
        self.AUTHORIZED_CHAT_ID = config["config"][0]["wallet_cid"]

        self.tasks = set()
        self.pids = []

    # -------------------- Supervisor Wrapper --------------------
    async def supervisor(self, coro_func, *args, **kwargs):
        """
        Belirtilen coroutine’i sürekli tekrar çalıştırır.
        Hata alırsa loglar, diğer task’lara dokunmaz.
        """
        while True:
            try:
                await coro_func(*args, **kwargs)
            except asyncio.CancelledError:
                # stop() sırasında task iptali buraya düşer
                break
            except Exception as e:
                print(f"[SUPERVISOR] {coro_func.__name__} hata: {e}")
                await asyncio.sleep(5)  # biraz bekle ve tekrar başlat
            else:
                # coroutine normal bitince tekrar başlat
                print(f"[SUPERVISOR] {coro_func.__name__} bitti, yeniden başlatılıyor.")
                await asyncio.sleep(1)


    # -------------------- Telegram Komutları --------------------
    async def start_cmd(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        if self.AUTHORIZED_CHAT_ID and str(update.effective_chat.id) != str(
            self.AUTHORIZED_CHAT_ID
        ):
            return await update.message.reply_text("Yetkin yok.")

        stop_event.clear()
        start_event.set()
       
        print("TÜM GÖREVLER BAŞLATILDI", datetime.now())

        # Supervisor ile task başlat
        if not self.tasks:  # aynı task’ı iki kere başlatma
            await self.start_stop_db.write_start_stop_data("start_stop",{"status":"started","timestamp":time.time()*1000})


        await update.message.reply_text("Görevler başlatıldı.")


 

    async def stop_cmd(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        if self.AUTHORIZED_CHAT_ID and str(update.effective_chat.id) != str(
            self.AUTHORIZED_CHAT_ID
        ):
            return await update.message.reply_text("Yetkin yok.")
        start_event.clear()
        stop_event.set()
        await update.message.reply_text("Görevler durduruldu.")
        await self.start_stop_db.write_start_stop_data("start_stop",{"status":"stopped","timestamp":time.time()*1000})


    # -------------------- Main --------------------
    async def main(self):
        application = ApplicationBuilder().token(self.TOKEN).build()
        application.add_handler(CommandHandler("start", self.start_cmd))
        application.add_handler(CommandHandler("stop", self.stop_cmd))

        await application.run_polling()


# -------------------- Çalıştır --------------------
getMain = MainProcess()
asyncio.run(getMain.main())

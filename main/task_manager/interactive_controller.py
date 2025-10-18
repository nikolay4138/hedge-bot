import asyncio
import sys
import os
from main.task_manager.task_manager import get_task_manager
from main.task_manager.task_library import TASK_LIBRARY

class InteractiveController:
    def __init__(self):
        self.task_manager = None
        self.running = True
    
    async def initialize(self):
        """Controller'ı başlat"""
        self.task_manager = await get_task_manager()
        print("🎮 INTERAKTİF TASK KONTROLÜ")
        print("=" * 50)
        return self
    
    def display_menu(self):
        """Menüyü göster"""
        print("\n" + "=" * 50)
        print("🎯 MENÜ")
        print("=" * 50)
        print("1️⃣  - Mevcut Task'leri Göster")
        print("2️⃣  - Task Başlat")
        print("3️⃣  - Task Durdur") 
        print("4️⃣  - Tüm Task'leri Durdur")
        print("5️⃣  - Task Durumu Sorgula")
        print("6️⃣  - Aktif Task'leri Listele")
        print("7️⃣  - Sistem Durumu")
        print("0️⃣  - Çıkış")
        print("=" * 50)
    
    def display_available_tasks(self):
        """Mevcut task'leri göster"""
        print("\n📚 MEVCUT TASK TÜRLERİ:")
        for task_key, task_info in TASK_LIBRARY.items():
            print(f"   🔸 {task_key}: {task_info['name']}")
            print(f"      📝 {task_info['description']}")
            print(f"      🆔 Varsayılan ID: {task_info['default_id']}")
            print()
    
    async def handle_start_task(self):
        """Task başlatma işlemi"""
        self.display_available_tasks()
        
        task_type = input("🚀 Başlatılacak task türünü girin: ").strip().lower()
        
        if task_type not in TASK_LIBRARY:
            print("❌ Geçersiz task türü!")
            return
        
        custom_id = input(f"🆔 Task ID girin (varsayılan: {TASK_LIBRARY[task_type]['default_id']}): ").strip()
        if not custom_id:
            custom_id = None
        
        # Özel parametreler
        kwargs = {}
        if task_type == "price":
            symbols_input = input("📈 İzlenecek semboller (virgülle ayır, boş bırak varsayılan): ").strip()
            if symbols_input:
                kwargs["symbols"] = [s.strip() for s in symbols_input.split(",")]
        
        try:
            task_id = await self.task_manager.start_task(task_type, custom_id, **kwargs)
            print(f"✅ Task başarıyla başlatıldı: {task_id}")
        except Exception as e:
            print(f"❌ Task başlatılamadı: {e}")
    
    async def handle_stop_task(self):
        """Task durdurma işlemi"""
        active_tasks = self.task_manager.list_active_tasks()
        if not active_tasks:
            return
        
        task_id = input("🛑 Durdurulacak task ID'sini girin: ").strip()
        
        if not task_id:
            print("❌ Task ID gerekli!")
            return
        
        await self.task_manager.stop_task(task_id)
    
    async def handle_task_status(self):
        """Task durumu sorgulama"""
        task_id = input("🔍 Durumu sorgulanacak task ID'sini girin: ").strip()
        
        if not task_id:
            print("❌ Task ID gerekli!")
            return
        
        self.task_manager.get_task_status(task_id)
    
    async def handle_system_status(self):
        """Sistem durumunu göster"""
        print("\n🤖 SİSTEM DURUMU")
        print("=" * 30)
        
        # Aktif task'ler
        active_tasks = self.task_manager.list_active_tasks()
        
        # Tüm task'lerin durumu
        all_tasks = self.task_manager.worker.get_all_tasks()
        status_counts = {}
        for status in all_tasks.values():
            status_name = status.value
            status_counts[status_name] = status_counts.get(status_name, 0) + 1
        
        print(f"\n📊 GENEL DURUM:")
        for status, count in status_counts.items():
            print(f"   {status}: {count}")
        
        print(f"\n👥 Worker durumu: {'🟢 ÇALIŞIYOR' if self.task_manager.worker.is_running else '🔴 DURDU'}")
        print(f"🔧 Worker sayısı: {self.task_manager.worker.worker_count}")
    
    async def run(self):
        """Ana interaktif döngü"""
        await self.initialize()
        
        while self.running:
            try:
                self.display_menu()
                choice = input("👉 Seçiminiz: ").strip()
                
                if choice == "1":
                    self.display_available_tasks()
                elif choice == "2":
                    await self.handle_start_task()
                elif choice == "3":
                    await self.handle_stop_task()
                elif choice == "4":
                    await self.task_manager.stop_all_tasks()
                elif choice == "5":
                    await self.handle_task_status()
                elif choice == "6":
                    self.task_manager.list_active_tasks()
                elif choice == "7":
                    await self.handle_system_status()
                elif choice == "0":
                    print("\n👋 Çıkış yapılıyor...")
                    await self.shutdown()
                    break
                else:
                    print("❌ Geçersiz seçim!")
                
                # Kısa bir bekleme
                await asyncio.sleep(1)
                
            except KeyboardInterrupt:
                print("\n\n🛑 Kapatılıyor...")
                await self.shutdown()
                break
            except Exception as e:
                print(f"❌ Beklenmeyen hata: {e}")
    
    async def shutdown(self):
        """Sistemi kapat"""
        self.running = False
        if self.task_manager:
            print("🧹 Task'ler temizleniyor...")
            await self.task_manager.stop_all_tasks()

# Komut satırı arayüzü
async def main():
    controller = InteractiveController()
    await controller.run()

if __name__ == "__main__":
    print("🚀 Interactive Task Controller")
    print("🎯 İstediğiniz task'leri başlatın, istediklerinizi durdurun!")
    asyncio.run(main())
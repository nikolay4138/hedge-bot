import asyncio
from main.task_manager.worker_manager import get_worker, init_worker
from main.task_manager.task_library import TASK_LIBRARY

class TaskManager:
    def __init__(self):
        self.worker = None
        self.active_tasks = {}
    
    async def initialize(self):
        """Task manager'ı başlat"""
        self.worker = await init_worker(worker_count=5)
        print("✅ Task Manager başlatıldı")
        return self
    
    def get_available_tasks(self):
        """Mevcut task'leri listele"""
        return TASK_LIBRARY
    
    async def start_task(self, task_type: str, task_id: str = None, **kwargs):
        """Yeni task başlat"""
        if task_type not in TASK_LIBRARY:
            raise ValueError(f"❌ Bilinmeyen task türü: {task_type}")
        
        task_info = TASK_LIBRARY[task_type]
        task_class = task_info["class"]
        task_name = task_info["name"]
        default_id = task_info["default_id"]
        
        task_id = task_id or default_id
        
        # Task instance'ını oluştur
        task_instance = task_class()
        
        # Task'i başlat
        actual_task_id = await self.worker.add_task(
            func=task_instance.main,
            task_name=task_name,
            task_id=task_id,
            **kwargs
        )
        
        self.active_tasks[actual_task_id] = {
            "type": task_type,
            "name": task_name,
            "instance": task_instance
        }
        
        print(f"✅ Task başlatıldı: {task_name} (ID: {actual_task_id})")
        return actual_task_id
    
    async def stop_task(self, task_id: str):
        """Task durdur"""
        if task_id not in self.active_tasks:
            print(f"❌ Aktif task bulunamadı: {task_id}")
            return False
        
        success = await self.worker.cancel_task(task_id)
        if success:
            task_info = self.active_tasks[task_id]
            print(f"✅ Task durduruldu: {task_info['name']} (ID: {task_id})")
            del self.active_tasks[task_id]
        else:
            print(f"❌ Task durdurulamadı: {task_id}")
        
        return success
    
    async def stop_all_tasks(self):
        """Tüm task'leri durdur"""
        if not self.active_tasks:
            print("ℹ️ Durdurulacak task yok")
            return 0
        
        task_count = len(self.active_tasks)
        print(f"🛑 {task_count} task durduruluyor...")
        
        for task_id in list(self.active_tasks.keys()):
            await self.stop_task(task_id)
        
        print(f"✅ Tüm task'ler durduruldu")
        return task_count
    
    def list_active_tasks(self):
        """Aktif task'leri listele"""
        if not self.active_tasks:
            print("ℹ️ Aktif task yok")
            return {}
        
        print(f"\n📋 AKTİF TASK'LER ({len(self.active_tasks)}):")
        for task_id, task_info in self.active_tasks.items():
            status = self.worker.get_task_status(task_id)
            print(f"   🔸 {task_info['name']} (ID: {task_id}) - Durum: {status.value}")
        
        return self.active_tasks.copy()
    
    def get_task_status(self, task_id: str):
        """Task durumunu öğren"""
        status = self.worker.get_task_status(task_id)
        if status:
            task_info = self.active_tasks.get(task_id, {})
            task_name = task_info.get('name', 'Bilinmeyen')
            print(f"ℹ️ {task_name} (ID: {task_id}) - Durum: {status.value}")
        else:
            print(f"❌ Task bulunamadı: {task_id}")
        return status

# Global task manager
_task_manager: TaskManager = None

async def get_task_manager():
    """Global task manager'ı al"""
    global _task_manager
    if _task_manager is None:
        _task_manager = TaskManager()
        await _task_manager.initialize()
    return _task_manager
import asyncio
from asyncio import Queue, Task
from typing import Callable, Any, Optional, Dict
import time
import logging
from enum import Enum

class TaskStatus(Enum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"

class AdvancedAsyncWorker:
    def __init__(self, worker_count: int = 3, max_retries: int = 3, timeout: Optional[float] = None):
        self.worker_count = worker_count
        self.queue = Queue()
        self.max_retries = max_retries
        self.timeout = timeout
        self.workers = []
        self.is_running = False
        self.completed_tasks = 0
        self.failed_tasks = 0
        self.cancelled_tasks = 0
        
        # Task takibi için
        self.active_tasks: Dict[str, Task] = {}
        self.task_status: Dict[str, TaskStatus] = {}
        self.task_results: Dict[str, Any] = {}
        
        # Cancellation event
        self.cancellation_events: Dict[str, asyncio.Event] = {}
        
        logging.basicConfig(level=logging.INFO)
        self.logger = logging.getLogger(__name__)

    async def worker(self, worker_id: int):
        """Geliştirilmiş worker - cancellation desteği ile"""
        self.logger.info(f"Worker {worker_id} başlatıldı")
        
        while self.is_running:
            try:
                # Queue'den task al
                task_data = await asyncio.wait_for(
                    self.queue.get(), 
                    timeout=1.0
                )
                
                if task_data is None:
                    self.queue.task_done()
                    break
                
                task_id, task_name, func, args, kwargs, callback = task_data
                
                # Cancellation kontrolü
                if task_id in self.cancellation_events and self.cancellation_events[task_id].is_set():
                    self.logger.info(f"Worker {worker_id} - {task_name} iptal edildi (kuyrukta)")
                    self.task_status[task_id] = TaskStatus.CANCELLED
                    self.cancelled_tasks += 1
                    self.queue.task_done()
                    continue
                
                self.logger.info(f"Worker {worker_id} - {task_name} işleniyor (ID: {task_id})")
                self.task_status[task_id] = TaskStatus.RUNNING
                
                # Task'i çalıştır
                result = await self._execute_with_cancellation(
                    task_id, func, args, kwargs, task_name
                )
                
                # Task durumunu güncelle
                if self.task_status[task_id] != TaskStatus.CANCELLED:
                    if isinstance(result, Exception):
                        self.task_status[task_id] = TaskStatus.FAILED
                        self.failed_tasks += 1
                    else:
                        self.task_status[task_id] = TaskStatus.COMPLETED
                        self.completed_tasks += 1
                        self.task_results[task_id] = result
                
                # Callback çağır
                if callback and self.task_status[task_id] != TaskStatus.CANCELLED:
                    await self._safe_callback(callback, result, task_id, task_name)
                    
            except asyncio.TimeoutError:
                continue
            except Exception as e:
                self.logger.error(f"Worker {worker_id} hatası: {e}")
                self.failed_tasks += 1
            finally:
                if 'task_data' in locals() and task_data is not None:
                    self.queue.task_done()

    async def _execute_with_cancellation(self, task_id: str, func: Callable, args: tuple, 
                                       kwargs: dict, task_name: str) -> Any:
        """Cancellation desteği ile task çalıştır"""
        try:
            # Task'i asenkron olarak başlat
            task = asyncio.create_task(
                self._execute_with_retry(func, args, kwargs, task_id, task_name)
            )
            self.active_tasks[task_id] = task
            
            # Task'in bitmesini veya cancellation'ı bekle
            cancellation_event = self.cancellation_events.get(task_id)
            
            if cancellation_event:
                # Cancellation event'i ve task'i birlikte bekle
                done, pending = await asyncio.wait(
                    [task, asyncio.create_task(cancellation_event.wait())],
                    return_when=asyncio.FIRST_COMPLETED,
                    timeout=self.timeout
                )
                
                # Cancellation kontrolü
                if cancellation_event.is_set():
                    if not task.done():
                        task.cancel()
                    try:
                        await task
                    except asyncio.CancelledError:
                        self.logger.info(f"Task {task_name} (ID: {task_id}) iptal edildi")
                        self.task_status[task_id] = TaskStatus.CANCELLED
                        self.cancelled_tasks += 1
                        return asyncio.CancelledError(f"Task {task_id} cancelled")
                    
                # Pending task'leri iptal et
                for p in pending:
                    p.cancel()
                
                # Task tamamlandıysa sonucu döndür
                if task in done:
                    return task.result()
            else:
                # Cancellation event yoksa direkt çalıştır
                return await task
                
        except Exception as e:
            return e
        finally:
            # Temizlik
            if task_id in self.active_tasks:
                del self.active_tasks[task_id]

    async def _execute_with_retry(self, func: Callable, args: tuple, kwargs: dict, 
                                 task_id: str, task_name: str) -> Any:
        """Retry mekanizması ile task çalıştır"""
        last_exception = None
        
        for attempt in range(self.max_retries):
            try:
                # Cancellation checkpoint
                if task_id in self.cancellation_events and self.cancellation_events[task_id].is_set():
                    raise asyncio.CancelledError(f"Task {task_id} cancelled during execution")
                
                # Fonksiyonu çalıştır - args doğru şekilde iletilmeli
                if self.timeout:
                    result = await asyncio.wait_for(
                        func(*args, **kwargs), 
                        timeout=self.timeout
                    )
                else:
                    result = await func(*args, **kwargs)
                
                return result
                
            except asyncio.TimeoutError:
                last_exception = TimeoutError(f"Task {task_name} timeout after {self.timeout}s")
                self.logger.warning(f"Task {task_name} timeout (attempt {attempt + 1}/{self.max_retries})")
                
            except asyncio.CancelledError:
                raise  # Cancellation'ı yukarı ilet
                
            except Exception as e:
                last_exception = e
                self.logger.warning(f"Task {task_name} failed (attempt {attempt + 1}/{self.max_retries}): {e}")
            
            # Retry arasında bekle (cancellation kontrolü ile)
            if attempt < self.max_retries - 1:
                wait_time = 2 ** attempt
                for i in range(wait_time):
                    if task_id in self.cancellation_events and self.cancellation_events[task_id].is_set():
                        raise asyncio.CancelledError(f"Task {task_id} cancelled during backoff")
                    await asyncio.sleep(1)
        
        # Tüm denemeler başarısız oldu
        raise last_exception

    async def _safe_callback(self, callback: Callable, result: Any, task_id: str, task_name: str):
        """Güvenli callback çalıştırma"""
        try:
            if asyncio.iscoroutinefunction(callback):
                await callback(result, task_id, task_name)
            else:
                callback(result, task_id, task_name)
        except Exception as e:
            self.logger.error(f"Callback hatası for task {task_name}: {e}")

    async def add_task(self, func: Callable, *args, 
                      task_name: Optional[str] = None,
                      task_id: Optional[str] = None,
                      callback: Optional[Callable] = None,
                      **kwargs) -> str:
        """Kuyruğa yeni task ekle - DÜZELTİLMİŞ VERSİYON"""
        if not self.is_running:
            raise RuntimeError("Worker'lar çalışmıyor. Önce start() çağırın.")
        
        task_id = task_id or f"task_{int(time.time() * 1000)}_{self.queue.qsize()}"
        task_name = task_name or func.__name__
        
        # Task takibini başlat
        self.task_status[task_id] = TaskStatus.PENDING
        self.cancellation_events[task_id] = asyncio.Event()
        
        # args tuple olarak iletilmeli, kwargs ayrı
        task_data = (task_id, task_name, func, args, kwargs, callback)
        await self.queue.put(task_data)
        
        self.logger.info(f"Task eklendi: {task_name} (ID: {task_id})")
        return task_id

    async def cancel_task(self, task_id: str) -> bool:
        """Belirli bir task'i iptal et"""
        if task_id not in self.task_status:
            self.logger.warning(f"Task {task_id} bulunamadı")
            return False
        
        if self.task_status[task_id] in [TaskStatus.COMPLETED, TaskStatus.FAILED, TaskStatus.CANCELLED]:
            self.logger.warning(f"Task {task_id} zaten sonlanmış: {self.task_status[task_id]}")
            return False
        
        # Cancellation event'ini tetikle
        if task_id in self.cancellation_events:
            self.cancellation_events[task_id].set()
        
        # Aktif task'i iptal et
        if task_id in self.active_tasks:
            self.active_tasks[task_id].cancel()
            try:
                await self.active_tasks[task_id]
            except asyncio.CancelledError:
                pass
        
        self.task_status[task_id] = TaskStatus.CANCELLED
        self.cancelled_tasks += 1
        self.logger.info(f"Task {task_id} iptal edildi")
        return True

    async def cancel_all_tasks(self) -> int:
        """Tüm aktif ve bekleyen task'leri iptal et"""
        cancelled_count = 0
        
        # Tüm task ID'lerini topla
        all_task_ids = list(self.task_status.keys())
        
        for task_id in all_task_ids:
            if self.task_status[task_id] in [TaskStatus.PENDING, TaskStatus.RUNNING]:
                if await self.cancel_task(task_id):
                    cancelled_count += 1
        
        self.logger.info(f"{cancelled_count} task iptal edildi")
        return cancelled_count

    def get_task_status(self, task_id: str) -> Optional[TaskStatus]:
        """Task durumunu getir"""
        return self.task_status.get(task_id)

    def get_task_result(self, task_id: str) -> Any:
        """Task sonucunu getir"""
        return self.task_results.get(task_id)

    def get_active_tasks(self) -> Dict[str, TaskStatus]:
        """Aktif task'leri getir"""
        return {task_id: status for task_id, status in self.task_status.items() 
                if status in [TaskStatus.PENDING, TaskStatus.RUNNING]}

    async def start(self):
        """Worker'ları başlat"""
        if self.is_running:
            self.logger.warning("Worker'lar zaten çalışıyor")
            return
        
        self.is_running = True
        self.workers = []
        
        for i in range(self.worker_count):
            worker = asyncio.create_task(self.worker(i))
            self.workers.append(worker)
        
        self.logger.info(f"{self.worker_count} worker başlatıldı")

    async def stop(self, graceful: bool = True, cancel_tasks: bool = False):
        """Worker'ları durdur"""
        if not self.is_running:
            return
        
        self.is_running = False
        
        if cancel_tasks:
            # Tüm task'leri iptal et
            await self.cancel_all_tasks()
        
        if graceful and not cancel_tasks:
            # Tüm task'lerin bitmesini bekle
            await self.queue.join()
        
        # Worker'ları sonlandır
        for _ in range(self.worker_count):
            await self.queue.put(None)
        
        if self.workers:
            await asyncio.gather(*self.workers, return_exceptions=True)
        
        self.logger.info("Worker'lar durduruldu")
        self._print_statistics()

    def _print_statistics(self):
        """İstatistikleri yazdır"""
        total_tasks = self.completed_tasks + self.failed_tasks + self.cancelled_tasks
        if total_tasks > 0:
            success_rate = (self.completed_tasks / total_tasks) * 100
            self.logger.info(
                f"İstatistikler: {self.completed_tasks} başarılı, "
                f"{self.failed_tasks} başarısız, "
                f"{self.cancelled_tasks} iptal edildi, "
                f"Başarı Oranı: {success_rate:.1f}%"
            )
from dataGetter.getBal import BalanceCollector
from dataGetter.getPos import GetPositions
# DÜZELTİLMİŞ KULLANIM ÖRNEKLERİ
async def long_running_task(duration: int, task_id: str):
    """Düzeltilmiş task fonksiyonu"""
    print(f"🚀 Task {task_id} başladı - {duration}s sürecek")
    
    for i in range(duration):
        await asyncio.sleep(1)
        print(f"⏳ Task {task_id} - {i+1}/{duration} saniye")
    
    print(f"✅ Task {task_id} tamamlandı")
    return f"Task {task_id} sonucu"
async def long_running_task2( task_id: str):
    """Düzeltilmiş task fonksiyonu"""
    print(f"🚀 Task {task_id} başladı - {10000} cycle sürecek")
    
    for i in range(10000):
        #await asyncio.sleep(1)
        print(f"⏳ Task {task_id} - {i+1}/{10000} cycle")

    print(f"✅ Task {task_id} tamamlandı")
    return f"Task {task_id} sonucu"
async def long_running_task3( task_id: str):
    """Düzeltilmiş task fonksiyonu"""
    print(f"🚀 Task {task_id} başladı - {1000} cycle sürecek")

    for i in range(1000):
        #await asyncio.sleep(1)
        print(f"⏳ Task {task_id} - {i+1}/{1000} cycle")

    print(f"✅ Task {task_id} tamamlandı")
    return f"Task {task_id} sonucu"

async def main():
    bb=BalanceCollector()
    gg=GetPositions()
    worker = AdvancedAsyncWorker(worker_count=2)
    await worker.start()
    
    # DÜZELTİLMİŞ: Parametreler doğru şekilde iletilmeli
    task1_id = await worker.add_task(func=bb.main, task_name="BalanceCollector", task_id="BALANCE_TASK")
    task2_id = await worker.add_task(func=gg.main,  task_name="position_getter", task_id="possition_getter")
    await asyncio.sleep(100)
    await worker.stop()
    print(f"\nTask 1 Durumu: {worker.get_task_status(task1_id)}")
    print(f"Task 2 Durumu: {worker.get_task_status(task2_id)}")
    """print(f"Task ID'leri: {task1_id}, {task2_id}")
    
    # 3 saniye bekle ve task1'i iptal et
    await asyncio.sleep(3)
    print("🛑 Task 1 iptal ediliyor...")
    await worker.cancel_task(task1_id)
    
    # Task 2'nin bitmesini bekle
    await asyncio.sleep(6)
    
    await worker.stop()
    
    # Durumları kontrol et
    print(f"\nTask 1 Durumu: {worker.get_task_status(task1_id)}")
    print(f"Task 2 Durumu: {worker.get_task_status(task2_id)}")"""

if __name__ == "__main__":
    asyncio.run(main())

"""#KULLANIM ÖRNEKLERİ
#1. Tekil Task İptali
import asyncio

# Uzun süren bir task
async def long_running_task(duration: int, task_id: str):
    print(f"🚀 Task {task_id} başladı - {duration}s sürecek")
    
    for i in range(duration):
        await asyncio.sleep(1)
        print(f"⏳ Task {task_id} - {i+1}/{duration} saniye")
        
        # Cancellation checkpoint (opsiyonel)
        await asyncio.sleep(0)  # Diğer task'lerin çalışmasına izin ver
    
    print(f"✅ Task {task_id} tamamlandı")
    return f"Task {task_id} sonucu"

async def main():
    worker = AdvancedAsyncWorker(worker_count=2)
    await worker.start()
    
    # Uzun süren task'ler ekle
    task1_id = await worker.add_task(
        func=long_running_task,
        args=[10, "UZUN_TASK_1"],
        task_name="Uzun_Task_1"
    )
    
    task2_id = await worker.add_task(
        func=long_running_task, 
        args=[5, "UZUN_TASK_2"],
        task_name="Uzun_Task_2"
    )
    print(task1_id, task2_id)
    # 3 saniye bekle ve task1'i iptal et
    await asyncio.sleep(3)
    print("🛑 Task 1 iptal ediliyor...")
    await worker.cancel_task(task1_id)
    
    # Task 2'nin bitmesini bekle
    await asyncio.sleep(6)
    
    await worker.stop()
    
    # Durumları kontrol et
    print(f"\nTask 1 Durumu: {worker.get_task_status(task1_id)}")
    print(f"Task 2 Durumu: {worker.get_task_status(task2_id)}")

asyncio.run(main())
#2. Koşullu İptal
async def conditional_cancellation():
    worker = AdvancedAsyncWorker(worker_count=3)
    await worker.start()
    
    task_ids = []
    
    # Birden fazla task ekle
    for i in range(5):
        task_id = await worker.add_task(
            func=long_running_task,
            args=[8, f"TASK_{i}"],
            task_name=f"Task_{i}"
        )
        task_ids.append(task_id)
    
    # 2 saniye bekle ve belirli task'leri iptal et
    await asyncio.sleep(2)
    
    # Çift numaralı task'leri iptal et
    for i, task_id in enumerate(task_ids):
        if i % 2 == 0:  # Çift index'ler
            print(f"🛑 Task {i} iptal ediliyor...")
            await worker.cancel_task(task_id)
    
    # Kalan task'lerin bitmesini bekle
    await worker.wait_for_completion()
    await worker.stop()

asyncio.run(conditional_cancellation())

#3. Tüm Task'leri İptal Etme
async def cancel_all_example():
    worker = AdvancedAsyncWorker(worker_count=4)
    await worker.start()
    
    # Çok sayıda task ekle
    for i in range(10):
        await worker.add_task(
            func=long_running_task,
            args=[15, f"MASSIVE_TASK_{i}"],
            task_name=f"Massive_Task_{i}"
        )
    
    # 3 saniye çalışsın, sonra hepsini iptal et
    await asyncio.sleep(3)
    
    print("🛑 TÜM TASK'LER İPTAL EDİLİYOR...")
    cancelled_count = await worker.cancel_all_tasks()
    print(f"✅ {cancelled_count} task iptal edildi")
    
    # Aktif task'leri kontrol et
    active_tasks = worker.get_active_tasks()
    print(f"Aktif kalan task'ler: {len(active_tasks)}")
    
    await worker.stop(cancel_tasks=False)  # Zaten iptal edildiler

asyncio.run(cancel_all_example())

#4.GERÇEK ZAMANLI MONİTÖRİNG İLE İPTAL
async def cancel_all_example():
    worker = AdvancedAsyncWorker(worker_count=4)
    await worker.start()
    
    # Çok sayıda task ekle
    for i in range(10):
        await worker.add_task(
            func=long_running_task,
            args=[15, f"MASSIVE_TASK_{i}"],
            task_name=f"Massive_Task_{i}"
        )
    
    # 3 saniye çalışsın, sonra hepsini iptal et
    await asyncio.sleep(3)
    
    print("🛑 TÜM TASK'LER İPTAL EDİLİYOR...")
    cancelled_count = await worker.cancel_all_tasks()
    print(f"✅ {cancelled_count} task iptal edildi")
    
    # Aktif task'leri kontrol et
    active_tasks = worker.get_active_tasks()
    print(f"Aktif kalan task'ler: {len(active_tasks)}")
    
    await worker.stop(cancel_tasks=False)  # Zaten iptal edildiler

asyncio.run(cancel_all_example())"""
import asyncio
import signal
import sys
from main.task_manager.interactive_controller import main as interactive_main

def signal_handler(sig, frame):
    """Sinyal yakalayıcı"""
    print('\n\n🛑 Sinyal alındı, kapatılıyor...')
    sys.exit(0)

if __name__ == "__main__":
    # Sinyal yakalayıcıları
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
    print("=" * 60)
    print("🤖 ADVANCED TASK MANAGEMENT SYSTEM")
    print("=" * 60)
    print("🎯 Özellikler:")
    print("   • İnteraktif task yönetimi")
    print("   • İstediğin task'leri başlat")
    print("   • İstediğin task'leri durdur") 
    print("   • Gerçek zamanlı monitoring")
    print("   • Çoklu worker desteği")
    print("=" * 60)
    
    # İnteraktif modu başlat
    asyncio.run(interactive_main())
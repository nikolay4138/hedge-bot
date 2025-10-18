import asyncio
import time
import random
from typing import Dict, Any, List

class BalanceCollector:
    def __init__(self):
        self.is_running = False
        self.iteration_count = 0
        
    async def main(self):
        """Sürekli balance verisi toplayıcı"""
        self.is_running = True
        self.iteration_count = 0
        
        print("💰 Balance Collector BAŞLATILDI")
        
        while self.is_running:
            try:
                self.iteration_count += 1
                
                # Balance verisi al
                balance_data = await self.fetch_balance_data()
                
                # Veriyi işle
                await self.process_balance_data(balance_data)
                
                print(f"🔄 Balance Iteration {self.iteration_count}")
                
                # 10 saniye bekle
                for i in range(10):
                    if not self.is_running:
                        break
                    await asyncio.sleep(1)
                    
            except asyncio.CancelledError:
                print("❌ Balance Collector İPTAL EDİLDİ")
                break
            except Exception as e:
                print(f"⚠️ Balance Collector Hatası: {e}")
                for i in range(5):
                    if not self.is_running:
                        break
                    await asyncio.sleep(1)
        
        print("🛑 Balance Collector DURDURULDU")
    
    async def fetch_balance_data(self) -> Dict[str, Any]:
        """Balance verisini al"""
        await asyncio.sleep(2)
        return {
            "timestamp": time.time(),
            "balances": {
                "BTC": round(0.1 + random.random() * 0.1, 6),
                "ETH": round(1.0 + random.random() * 0.5, 4),
                "USDT": round(1000 + random.random() * 500, 2),
            },
            "total_usd": round(50000 + random.random() * 20000, 2)
        }
    
    async def process_balance_data(self, balance_data: Dict[str, Any]):
        """Balance verisini işle"""
        print(f"💰 Balance: {balance_data['balances']}")

class PositionGetter:
    def __init__(self):
        self.is_running = False
        self.iteration_count = 0
        
    async def main(self):
        """Sürekli position verisi toplayıcı"""
        self.is_running = True
        self.iteration_count = 0
        
        print("📊 Position Getter BAŞLATILDI")
        
        while self.is_running:
            try:
                self.iteration_count += 1
                
                # Position verisi al
                positions_data = await self.fetch_positions_data()
                
                # Veriyi işle
                await self.process_positions_data(positions_data)
                
                print(f"🔄 Position Iteration {self.iteration_count}")
                
                # 15 saniye bekle
                for i in range(15):
                    if not self.is_running:
                        break
                    await asyncio.sleep(1)
                    
            except asyncio.CancelledError:
                print("❌ Position Getter İPTAL EDİLDİ")
                break
            except Exception as e:
                print(f"⚠️ Position Getter Hatası: {e}")
                for i in range(5):
                    if not self.is_running:
                        break
                    await asyncio.sleep(1)
        
        print("🛑 Position Getter DURDURULDU")
    
    async def fetch_positions_data(self) -> List[Dict[str, Any]]:
        """Position verisini al"""
        await asyncio.sleep(1)
        symbols = ["BTCUSDT", "ETHUSDT", "ADAUSDT"]
        positions = []
        
        for symbol in random.sample(symbols, random.randint(1, 3)):
            position = {
                "symbol": symbol,
                "side": random.choice(["LONG", "SHORT"]),
                "amount": round(random.random() * 10, 4),
                "pnl": round((random.random() - 0.5) * 1000, 2),
            }
            positions.append(position)
        
        return positions
    
    async def process_positions_data(self, positions: List[Dict[str, Any]]):
        """Position verisini işle"""
        total_pnl = sum(pos['pnl'] for pos in positions)
        print(f"📊 Positions: {len(positions)} | PnL: ${total_pnl:+.2f}")

class PriceMonitor:
    def __init__(self):
        self.is_running = False
        self.iteration_count = 0
        
    async def main(self, symbols: List[str] = None):
        """Sürekli fiyat takipçisi"""
        self.is_running = True
        self.iteration_count = 0
        symbols = symbols or ["BTCUSDT", "ETHUSDT", "ADAUSDT"]
        
        print(f"📈 Price Monitor BAŞLATILDI - {symbols}")
        
        while self.is_running:
            try:
                self.iteration_count += 1
                
                # Fiyat verisi al
                prices = await self.fetch_prices(symbols)
                
                # Veriyi işle
                await self.process_prices(prices)
                
                print(f"🔄 Price Monitor Iteration {self.iteration_count}")
                
                # 5 saniye bekle
                for i in range(5):
                    if not self.is_running:
                        break
                    await asyncio.sleep(1)
                    
            except asyncio.CancelledError:
                print("❌ Price Monitor İPTAL EDİLDİ")
                break
            except Exception as e:
                print(f"⚠️ Price Monitor Hatası: {e}")
                for i in range(3):
                    if not self.is_running:
                        break
                    await asyncio.sleep(1)
        
        print("🛑 Price Monitor DURDURULDU")
    
    async def fetch_prices(self, symbols: List[str]) -> Dict[str, float]:
        """Fiyat verisini al"""
        await asyncio.sleep(1)
        prices = {}
        for symbol in symbols:
            prices[symbol] = round(100 + random.random() * 900, 2)
        return prices
    
    async def process_prices(self, prices: Dict[str, float]):
        """Fiyat verisini işle"""
        print(f"📈 Prices: {prices}")

class DataAnalyzer:
    def __init__(self):
        self.is_running = False
        self.iteration_count = 0
        
    async def main(self):
        """Sürekli data analiz edici"""
        self.is_running = True
        self.iteration_count = 0
        
        print("📊 Data Analyzer BAŞLATILDI")
        
        while self.is_running:
            try:
                self.iteration_count += 1
                
                # Analiz yap
                analysis = await self.perform_analysis()
                
                # Sonuçları işle
                await self.process_analysis(analysis)
                
                print(f"🔄 Data Analyzer Iteration {self.iteration_count}")
                
                # 30 saniye bekle
                for i in range(30):
                    if not self.is_running:
                        break
                    await asyncio.sleep(1)
                    
            except asyncio.CancelledError:
                print("❌ Data Analyzer İPTAL EDİLDİ")
                break
            except Exception as e:
                print(f"⚠️ Data Analyzer Hatası: {e}")
                for i in range(10):
                    if not self.is_running:
                        break
                    await asyncio.sleep(1)
        
        print("🛑 Data Analyzer DURDURULDU")
    
    async def perform_analysis(self) -> Dict[str, Any]:
        """Analiz yap"""
        await asyncio.sleep(3)
        return {
            "market_trend": random.choice(["BULLISH", "BEARISH", "SIDEWAYS"]),
            "volatility": round(random.random() * 100, 2),
            "signal": random.choice(["BUY", "SELL", "HOLD"]),
        }
    
    async def process_analysis(self, analysis: Dict[str, Any]):
        """Analiz sonuçlarını işle"""
        print(f"📊 Analysis: {analysis}")

# Task kütüphanesi
TASK_LIBRARY = {
    "balance": {
        "name": "Balance Collector",
        "class": BalanceCollector,
        "description": "Balance verilerini toplar",
        "default_id": "BALANCE_TASK"
    },
    "position": {
        "name": "Position Getter", 
        "class": PositionGetter,
        "description": "Position verilerini toplar",
        "default_id": "POSITION_TASK"
    },
    "price": {
        "name": "Price Monitor",
        "class": PriceMonitor, 
        "description": "Fiyat verilerini takip eder",
        "default_id": "PRICE_TASK"
    },
    "analyzer": {
        "name": "Data Analyzer",
        "class": DataAnalyzer,
        "description": "Veri analizi yapar",
        "default_id": "ANALYZER_TASK"
    }
}
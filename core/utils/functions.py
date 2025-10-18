from core.getIndicators import AdvancedTechnicalIndicatorsFibLevels
import re
from collections import defaultdict
from core.utils.getTimeframe import GeneratorTimeframe
from core.trading import BinanceFuturesTrader
from core.ruleSystem.ruleEngine import ruleExtractor,RuleReader
from typing import Tuple, Union
import time
from datetime import datetime
from core.utils.databaseProcess import SQLiteManager,DBReader
from core.utils.getDatabase import dbGetterSetter as GetterSetter
class Processor:
    def __init__(self):
        pass
    class TimeProcessor:
        def __init__(self):
            pass
        def check_last_data(self):
            #dbye eklenmiş verinin güncel olup olmadığını kontrol eder
            pass
        # verilen zaman damgasını istenen formata çevirir
        def convert_timestamp(self, timestamp: int, fmt: str = "%Y-%m-%d %H:%M:%S") -> str:
            return time.strftime(fmt, time.localtime(timestamp / 1000))
        # verilen zaman damgasını istenen formata çevirir
        def convert_to_unix(self, date_str: str, fmt: str = "%Y-%m-%d %H:%M:%S") -> int:
            return int(time.mktime(time.strptime(date_str, fmt)) * 1000)
        def get_current_timestamp(self) -> int:
            """Şu anki zaman damgasını milisaniye cinsinden döner."""
            return int(time.time() * 1000)
        def get_current_time(self) -> str:
            """Şu anki zamanı 'HH:MM:SS' formatında döner."""
            return datetime.now().strftime("%H:%M:%S")

        async def check_time(self, hedef_saat: str):
            """
            Belirtilen saati bekleyen asenkron fonksiyon.
            hedef_saat formatı: "HH:MM:SS"
            """
            if self.get_current_time() == hedef_saat:
                print(f"⏰ Saat {hedef_saat} oldu!")
                return True
            else:
                return False
        def is_within_minutes(timestamp_ms: int, minutes: float = 5.0) -> bool:
            """
            Verilen 13 haneli (milisaniye) timestamp'in
            şu anki zamana göre 5 dakika içinde olup olmadığını döner.
            """
            now_ms = int(time.time() * 1000)
            diff_ms = abs(now_ms - timestamp_ms)
            return diff_ms <= minutes * 60 * 1000
    class TradeProcessor:
        def __init__(self):
            self.write_close_db = SQLiteManager("binance_data/close.db")

        #kurallara göre piyasayı dinler
        async def listen_exchange(self,key,data):
            rule_ex=ruleExtractor()
            rule_read=RuleReader()
            valid_data=rule_ex.valid_data_getter(key,data)
            rule_read.load_rules_from_dict("core/config.json",key)
            value=rule_read.evaluate_all_rules(variables=valid_data)
            if value["all_passed"]:
                return True
            return False
        # aynı anda farklı yönlerde pozisyon var mı kontrol eder
        async def check_with_both_sides(self,symbol):
            open_db = GetterSetter.opendb()
            open_positions = await open_db.get_open_positions()
            lstprocess = Processor.listProcessor()
            symbols = lstprocess.symbols_with_both_sides_robust(open_positions)
            if symbol in symbols:
                return True 
            return False
            
        async def close_pos(self,symbol,side,position_side,usdt_amount,proxy):
                trader=BinanceFuturesTrader(testnet=False,debug=True,proxy=proxy)
                order=await trader.market_order(symbol,side,position_side,usdt_amount)
                await trader.close()
                if order["info"]["status"]=="FILLED":
                    self.write_close_db.insert(f"symbol", data)
                    return order
                else:
                    return False
        async def close_pos_pnl(self,symbol,side,position_side,usdt_amount,pnl,pnl_threshold,proxy):
            if pnl>=pnl_threshold:
                trader=BinanceFuturesTrader(testnet=False,debug=True,proxy=proxy)
                order=await trader.market_order(symbol,side,position_side,usdt_amount)
                await trader.close()
                if order["info"]["status"]=="FILLED":
                    return True
                else:
                    return False
        async def open_pos(self,symbol,side,position_side,usdt_amount,proxy):
            trader=BinanceFuturesTrader(testnet=False,debug=True,proxy=proxy)
            order=await trader.market_order(symbol,side,position_side,usdt_amount)
            await trader.close()
            if order["info"]["status"]=="FILLED":
                return order
            else:
                return False
        async def how_much_added(self,min_ort=4, max_ort=5, fiyat1=3, adet1=10, fiyat2=5,max_iters=200):
            """
            Ortalama elma fiyatının min_ort ile max_ort arasında kalması için
            ikinci alıştan (fiyat2) kaç adet elma alınması gerektiğini hesaplar.
            """
            amounts = []
            for x in range(1, max_iters):  # 1'den 100'e kadar deneme yapıyoruz
                ortalama = (adet1 * fiyat1 + x * fiyat2) / (adet1 + x)
                if min_ort < ortalama < max_ort:
                    amounts.append(x)
            return amounts,min(amounts)
    class listProcessor:
        def __init__(self):
            pass
        def check_proximity(self,number1,number2, tolerance =0.01):
            """
            Göreceli tolerans kullanarak yaklaşık eşitliği kontrol eder.
            
            Args:
                sayi (float): Kontrol edilecek sayı
                goreceli_tolerans (float): Yüzde olarak tolerans (varsayılan: %1)
            
            Returns:
                bool: Sayı 10'a yakınsa True, değilse False
            """
            tolerans = number2 * tolerance
            return abs(number1 - number2) < tolerans

        
        # bir liste içindeki bir değerden büyük listedeki en küçük sayıyı döndürü
        def select_min_above_threshold(self, liste, threshold=0.5):
            # threshold'tan büyük değerleri filtrele
            bigs = [x for x in liste if x >= threshold]
            # Eğer hiç yoksa None döndür
            if not bigs:
                return None
            # En küçük olanı döndür
            return min(bigs)
        # bir liste içindeki bir değerden büyük listedeki en büyük sayıyı döndürü
        def select_max_above_threshold(self, liste, threshold=0.5):
            # threshold'tan büyük değerleri filtrele
            bigs = [x for x in liste if x >= threshold]
            # Eğer hiç yoksa None döndür
            if not bigs:
                return None
            # En küçük olanı döndür
            return max(bigs)
        # bir liste içindeki bir değerden küçük listedeki en küçük sayıyı döndürü
        def select_min_under_threshold(self, liste, threshold=0.5):
            # threshold'tan büyük değerleri filtrele
            bigs = [x for x in liste if x <= threshold]
            # Eğer hiç yoksa None döndür
            if not bigs:
                return None
            # En küçük olanı döndür
            return min(bigs)
        
        def select_max_under_threshold(self, liste, threshold=0.5):
            # threshold'tan büyük değerleri filtrele
            bigs = [x for x in liste if x <= threshold]
            # Eğer hiç yoksa None döndür
            if not bigs:
                return None
            # En küçük olanı döndür
            return max(bigs)

        

        # ana listeden diğer listedeki elemanları çıkarır
        def remove_second_list(self, base_list, to_remove):
            """
            base_list: Ana sembol listesi
            to_remove: Çıkarılacak semboller listesi
            return: Çıkarılmış yeni liste
            """
            return [sym for sym in base_list if sym not in to_remove]

        # bir listede hem long hem short isimleri sembolleri döner.
        def symbols_with_both_sides_robust(self, pairs):
            """
            Daha esnek bir versiyon:
            - "BTCUSDT_LONG", "BTCUSDT-long", "BTCUSDT-LONG" gibi varyasyonları yakalar
            - Ek boşlukları tolere eder
            """
            pattern = re.compile(
                r"^\s*(?P<sym>.+?)[\-_ ]?(?P<side>LONG|SHORT)\s*$", re.IGNORECASE
            )
            sides = defaultdict(set)

            for token in pairs:
                m = pattern.match(token)
                if not m:
                    continue
                sym = m.group("sym").strip()
                side = m.group("side").upper()
                sides[sym].add(side)

            return sorted(
                [sym for sym, s in sides.items() if {"LONG", "SHORT"}.issubset(s)]
            )
    class TimeframeGenerator:
        def __init__(self):
            pass
        async def generate_one_tf(self, df, timeframe):
            generator = GeneratorTimeframe()
            return generator.resample_ohlcv(df, timeframe)
        
        async def generate_multiple_tf(self, df, timeframes):
            data={}
            generator = GeneratorTimeframe()
            for timeframe in timeframes:
                df=generator.resample_ohlcv(df, timeframe)
                data[f"{timeframe}"]=df
            return data
    class DataAnalyzer:
        def __init__(self):
            pass
        # datası verilen sembolün indikatörlerini ve analizlerini hesaplar.
        async def get_analysis(self, data):
            indicators = AdvancedTechnicalIndicatorsFibLevels(data)
            analysis, _= await indicators.main()
            # Burada göstergeleri hesaplayın
            return analysis
        async def get_indicators(self, data):
            indicators = AdvancedTechnicalIndicatorsFibLevels(data)
            _, indicators = await indicators.main()
            # Burada göstergeleri hesaplayın
            return indicators
        async def get_wave_type(self, data):
            indicators = AdvancedTechnicalIndicatorsFibLevels(data)
            analysis, _= await indicators.main()
            # Burada göstergeleri hesaplayın
            return analysis["wave_type"]
        async def get_fib_levels(self, data):
            indicators = AdvancedTechnicalIndicatorsFibLevels(data)
            analysis, _= await indicators.main()
            # Burada göstergeleri hesaplayın
            return analysis["fib_levels"]
        async def get_fib_level(self, data,fib_level):
            indicators = AdvancedTechnicalIndicatorsFibLevels(data)
            analysis, _= await indicators.main()
            # Burada göstergeleri hesaplayın
            return analysis["fib_levels"].get(fib_level)
    class ProfitStopProcessor:
        def __init__(self):
            pass
        async def calculate_daily_profit(self,balance1,balance2):
            try:
                profit=(balance2-balance1)
                return profit
            except ZeroDivisionError:
                return 0
        async def calculate_total_dist(self,profit,rate):
            try:
                dist=profit*rate/100
                return dist
            except ZeroDivisionError:
                return 0
        async def condition_general_stop(self,balance,unpnl,rate):
            if (unpnl<=balance*rate/100) or (unpnl>=balance*rate/100):
                return True
            return False
        async def calculate_per_position(self,total_dist,position_count):
            try:
                per_position=total_dist/position_count
                return per_position
            except ZeroDivisionError:
                return 0
    class ProfitCalculator:
        def __init__(self) -> None:
            self.generator = GeneratorTimeframe()
            self.read_open_db = GetterSetter.opendb()
            self.read_ohlcv_db = GetterSetter.ohlcvdb()

        @staticmethod
        def calculate_profit_percent(entry_price: float, exit_price: float, position: str) -> float:
            """
            Pozisyon türüne göre kar yüzdesini hesaplar.

            Args:
                entry_price (float): Giriş fiyatı
                exit_price (float): Çıkış fiyatı
                position (str): 'LONG' veya 'SHORT'

            Returns:
                float: Kar yüzdesi
            """
            position = position.upper()

            if position == "LONG":
                return (exit_price - entry_price) / entry_price * 100
            elif position == "SHORT":
                return (entry_price - exit_price) / entry_price * 100
            else:
                raise ValueError("Position must be either 'LONG' or 'SHORT'.")

        async def expected_profit(
            self,  position: str, timeframe: str
        ) -> float:
            """
            Pozisyon, sembol ve zaman dilimine göre beklenen karı hesaplar.

            Args:
                symbol (str): İşlem yapılan sembol, örn: 'BTCUSDT'
                position (str): 'LONG' veya 'SHORT'
                timeframe (str): Örn. '1h', '4h', '1d'

            Returns:
                float: Beklenen kar miktarı
            """
            # --- Veritabanından son pozisyon bilgisini çek ---
            df=self.read_open_db.get_open_data(position)
            last_row = df.iloc[-1]
            entry_price = float(last_row["entryPrice"])
            amount = float(last_row["amount"])

            # --- OHLCV verilerini al ve yeniden örnekle ---
            symbol = position.split("_")[0]
            ohlcv_df = self.read_ohlcv_db.get_ohlcv_data(symbol)
            timeframe_df = self.generator.resample_ohlcv(ohlcv_df, timeframe)

            # --- Gelişmiş teknik indikatörleri uygula ---
            indicator = AdvancedTechnicalIndicatorsFibLevels(timeframe_df)
            _, dx = await indicator.main()

            last_atr = float(dx.iloc[-1]["atr"])

            # --- Pozisyon yönüne göre beklenen çıkış fiyatını hesapla ---
            pos=position.split("_")[1]
            pos = pos.upper()
            if pos == "LONG":
                expected_exit_price = entry_price + last_atr
            elif pos == "SHORT":
                expected_exit_price = entry_price - last_atr
            else:
                raise ValueError("Position must be either 'LONG' or 'SHORT'.")

            # --- Beklenen yüzdesel kar ---
            expected_percent = self.calculate_profit_percent(
                entry_price, expected_exit_price, position
            )

            # --- Beklenen kar miktarını hesapla ---
            profit = amount * expected_percent / 100
            total_with_profit = amount + profit

            # Komisyon veya işlem maliyetlerini düş (örnek: %0.04)
            commission_rate = 0.04 / 100
            net_total = total_with_profit * (1 - commission_rate)

            expected_profit = net_total - amount
            return expected_profit
        async def profit_selector(self,profits,threshold=0.12):
            processor=Processor.listProcessor()
            profit=processor.select_min_above_threshold(profits,threshold)
            return float(profit)
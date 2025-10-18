"""
kuralları takip eder. kuralara göre ture gelirse,
hedge varsa, kapar, tek devam eder
hedge yoksa, açar , çift devam eder


kırılım gelirse aynı anda iki hedgei kapatır,
kırılım yönünde devam eder

bu yapı açık olan sembollerin tammamı için hem üst hem alt kırılımları anlık olarak tarar ve kırılım veritabanına kaydeder
"""

# tek sembol ve tek kural için çalışır

from core.utils.getDatabase import dbGetterSetter as GetterSetter

from core.utils.functions import Processor

class Breakout:
    def __init__(self) -> None:
        self.data_getter = GetterSetter.ohlcvdb()
        self.breakout_getter = GetterSetter.breakoutdb()
        self.trader=Processor.TradeProcessor()
    #tek sembol için çalışır
    async def main(self,symbol,key):
        data=await self.data_getter.get_ohlcv_data(symbol)
        value=await self.trader.listen_exchange(key,data)
        if value:
            await self.breakout_getter.write_breakout_data(symbol, {"value": value})
            return True # Kural geçti
        return False # Kural geçmedi
    

    """ # Her sembol için ohlcv alıp rule_enforcer'a gönderen fonksiyon
    async def process_symbol(self, symbol, key):
        #Tek bir sembol için OHLCV verisini alır ve rule_enforcer'a gönderir
        try:
            # Sembol için OHLCV verisini al
            df = await self.get_ohlcv(symbol)

            # Rule enforcer'a gönder
            result = await self.rule_enfocer(key, df)
            # db ye kaydet
            if result:
                # sadece son kırılımı tut
                self.write_breakout.clear_table(f"{symbol}_x")
                timestamp = int(time.time() * 1000)
                self.write_breakout.insert(
                    f"{symbol}_x",
                    {
                        "direction": f"{key}",
                        "timestamp": timestamp,
                    },
                )
                # tüm kırılımları tut
                self.write_breakout.insert(
                    symbol,
                    {
                        "direction": f"{key}",
                        "timestamp": timestamp,
                    },
                )

            return {"symbol": symbol, "result": result, "status": "success"}
        except Exception as e:
            return {
                "symbol": symbol,
                "result": None,
                "status": "error",
                "error": str(e),
            }

    # Ana fonksiyon: bir key için Tüm semboller için eş zamanlı işlem yapan fonksiyon
    async def process_all_symbols_concurrent(self, key):

        # get_symbol çıktısını alır, her sembol için get_ohlcv çağırır,
        # her DataFrame'i rule_enforcer'a gönderir.
        # Tüm işlemler eş zamanlı (concurrent) çalışır.

        #Args:
        #    key: Rule enforcer için sabit key değeri

        # Returns:
        #    List[dict]: Her sembol için sonuç bilgisi içeren liste
        try:
            # Açık sembolleri al
            symbols = await self.get_symbol()

            if not symbols:
                print("Hiç açık sembol bulunamadı.")
                return []

            print(f"{len(symbols)} sembol için işlem başlatılıyor...")

            # Her sembol için task oluştur
            tasks = []
            for symbol in symbols:
                task = self.process_symbol(symbol, key)
                tasks.append(task)

            # Tüm taskları eş zamanlı çalıştır
            results = await asyncio.gather(*tasks, return_exceptions=True)

            # Sonuçları işle
            processed_results = []
            success_count = 0
            error_count = 0

            for result in results:
                if isinstance(result, Exception):
                    print(f"Beklenmeyen hata: {str(result)}")
                    error_count += 1
                    processed_results.append(
                        {
                            "symbol": "unknown",
                            "result": None,
                            "status": "exception",
                            "error": str(result),
                        }
                    )
                elif isinstance(result, dict):
                    processed_results.append(result)
                    if result.get("status") == "success":
                        success_count += 1
                        print(f"✓ {result.get('symbol')}: {result.get('result')}")
                    else:
                        error_count += 1
                        print(f"✗ {result.get('symbol')}: {result.get('error')}")
                else:
                    print(f"Beklenmeyen sonuç tipi: {type(result)}")
                    error_count += 1

            print(f"\nİşlem tamamlandı: {success_count} başarılı, {error_count} hatalı")
            return processed_results

        except Exception as e:
            print(f"process_all_symbols_concurrent fonksiyonunda hata: {str(e)}")
            return []

    # Örnek kullanım fonksiyonu
    async def run_breakout_analysis(self, rule_key="default_rule"):
        # Tüm açık semboller için breakout analizi yapar

        #Args:
        #    rule_key: Kullanılacak kural anahtarı
        print(f"Breakout analizi başlatılıyor (Kural: {rule_key})...")
        results = await self.process_all_symbols_concurrent(rule_key)

        # Sonuçları kategorize et
        successful_results = [
            r for r in results if r.get("status") == "success" and r.get("result")
        ]
        failed_results = [
            r for r in results if r.get("status") != "success" or not r.get("result")
        ]

        print(f"\n=== BREAKOUT ANALİZ SONUÇLARI ===")
        print(f"Toplam sembol: {len(results)}")
        print(f"Kural geçen: {len(successful_results)}")
        print(f"Kural geçmeyen/Hatalı: {len(failed_results)}")

        if successful_results:
            print(f"\nKuralları geçen semboller:")
            for result in successful_results:
                print(f"  - {result.get('symbol')}")

        return results

    # Birden fazla key ile birden fazla sembol için eş zamanlı işlem
    async def process_symbol_with_key(self, symbol, key):
        # Tek bir sembol-key kombinasyonu için işlem yapar
        try:
            # Sembol için OHLCV verisini al
            df = await self.get_ohlcv(symbol)

            # Rule enforcer'a gönder
            result = await self.rule_enfocer(key, df)

            return {"symbol": symbol, "key": key, "result": result, "status": "success"}
        except Exception as e:
            return {
                "symbol": symbol,
                "key": key,
                "result": None,
                "status": "error",
                "error": str(e),
            }

    # Birden fazla key ve tüm semboller için tam eş zamanlı işlem
    async def process_multiple_keys_all_symbols_concurrent(self, keys):
        # Birden fazla key ile tüm sembolleri eş zamanlı işler.
        # Her key-sembol kombinasyonu bağımsız ve paralel çalışır.

        # Args:
        #    keys: List[str] - Rule enforcer için key listesi

        # Returns:
        #    List[dict]: Her key-sembol kombinasyonu için sonuç
        try:
            # Açık sembolleri al
            symbols = await self.get_symbol()

            if not symbols:
                print("Hiç açık sembol bulunamadı.")
                return []

            if not keys:
                print("Hiç key belirtilmedi.")
                return []

            print(
                f"{len(symbols)} sembol × {len(keys)} key = {len(symbols) * len(keys)} toplam işlem başlatılıyor..."
            )

            # Tüm key-sembol kombinasyonları için task oluştur
            tasks = []
            for key in keys:
                for symbol in symbols:
                    task = self.process_symbol_with_key(symbol, key)
                    tasks.append(task)

            print(f"Toplam {len(tasks)} task eş zamanlı çalıştırılıyor...")

            # Tüm taskları eş zamanlı çalıştır
            results = await asyncio.gather(*tasks, return_exceptions=True)

            # Sonuçları işle
            processed_results = []
            success_count = 0
            error_count = 0

            # Key bazında sonuçları grupla
            key_results = {key: {"success": [], "error": []} for key in keys}

            for result in results:
                if isinstance(result, Exception):
                    print(f"Beklenmeyen hata: {str(result)}")
                    error_count += 1
                    processed_results.append(
                        {
                            "symbol": "unknown",
                            "key": "unknown",
                            "result": None,
                            "status": "exception",
                            "error": str(result),
                        }
                    )
                elif isinstance(result, dict):
                    processed_results.append(result)
                    key = result.get("key")

                    if result.get("status") == "success":
                        success_count += 1
                        if key and key in key_results:
                            key_results[key]["success"].append(result.get("symbol"))
                        print(
                            f"✓ {result.get('key')}-{result.get('symbol')}: {result.get('result')}"
                        )
                    else:
                        error_count += 1
                        if key and key in key_results:
                            key_results[key]["error"].append(result.get("symbol"))
                        print(
                            f"✗ {result.get('key')}-{result.get('symbol')}: {result.get('error')}"
                        )
                else:
                    print(f"Beklenmeyen sonuç tipi: {type(result)}")
                    error_count += 1

            # Özet rapor
            print(f"\n=== ÇOKLU KEY-SEMBOL ANALİZ SONUÇLARI ===")
            print(f"Toplam işlem: {len(processed_results)}")
            print(f"Başarılı: {success_count}")
            print(f"Hatalı: {error_count}")

            # Key bazında özet
            for key, stats in key_results.items():
                success_symbols = len(stats["success"])
                error_symbols = len(stats["error"])
                total_symbols = success_symbols + error_symbols

                print(f"\nKey: {key}")
                print(f"  ✓ Başarılı: {success_symbols}/{total_symbols}")
                print(f"  ✗ Hatalı: {error_symbols}/{total_symbols}")

                if stats["success"]:
                    print(
                        f"  Kuralı geçen semboller: {', '.join(stats['success'][:5])}"
                        + (
                            f" (+{len(stats['success'])-5} daha)"
                            if len(stats["success"]) > 5
                            else ""
                        )
                    )

            return processed_results

        except Exception as e:
            print(
                f"process_multiple_keys_all_symbols_concurrent fonksiyonunda hata: {str(e)}"
            )
            return []

    # Çoklu key analizi için kullanım kolaylığı fonksiyonu
    async def run_multi_key_breakout_analysis(self, keys):
        # Birden fazla key ile breakout analizi yapar

        # Args:
        #     keys: List[str] - Kullanılacak kural anahtarları listesi
        print(f"Çoklu key breakout analizi başlatılıyor...")
        print(f"Kullanılacak keyler: {keys}")

        results = await self.process_multiple_keys_all_symbols_concurrent(keys)

        # Key bazında başarılı sonuçları analiz et
        successful_by_key = {}
        for result in results:
            if result.get("status") == "success" and result.get("result"):
                key = result.get("key")
                if key not in successful_by_key:
                    successful_by_key[key] = []
                successful_by_key[key].append(result.get("symbol"))

        print(f"\n=== KEY BAŞARILI SEMBOL ANALİZİ ===")
        for key, symbols in successful_by_key.items():
            print(f"{key}: {len(symbols)} sembol kuralı geçti")
            if symbols:
                print(f"  Semboller: {', '.join(symbols)}")

        return results


# Kullanım örnekleri
async def main_example():
    # Fonksiyonların nasıl kullanılacağını gösteren örnek
    breakout = Breakout()

    # TEK KEY İLE TÜM SEMBOLLER
    # Belirli bir kural anahtarıyla analiz yap
    single_key_results = await breakout.process_all_symbols_concurrent("my_rule_key")

    # Veya daha detaylı analiz için
    detailed_single_results = await breakout.run_breakout_analysis("my_rule_key")

    # ÇOKLU KEY İLE TÜM SEMBOLLER (YENİ ÖZELLİK)
    # Birden fazla key ile tüm sembolleri eş zamanlı işle
    multiple_keys = ["breakout_rule", "momentum_rule", "volume_rule", "trend_rule"]
    multi_key_results = await breakout.process_multiple_keys_all_symbols_concurrent(
        multiple_keys
    )

    # Veya çoklu key için detaylı analiz
    detailed_multi_results = await breakout.run_multi_key_breakout_analysis(
        multiple_keys
    )

    return {"single_key": single_key_results, "multi_key": multi_key_results}


# Eğer bu dosya doğrudan çalıştırılırsa
if __name__ == "__main__":
    asyncio.run(main_example())
"""
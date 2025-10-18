class usdtPairs:
    def __init__(self) -> None:
        self.url = "https://fapi.binance.com/fapi/v1/exchangeInfo"
        os.makedirs("core/symbolsInfo", exist_ok=True)
        self.pairs_file = "core/symbolsInfo/usdt_pairs.sml"
        self.delist_file = "core/symbolsInfo/delist.sml"
        self.last_pairs = set()

    def load_existing_pairs(self):
        """Mevcut parite listesini yükle"""
        try:
            if os.path.exists(self.pairs_file):
                with open(self.pairs_file, "r", encoding="utf-8") as f:
                    return {line.strip() for line in f if line.strip()}
            return set()
        except Exception as e:
            print(f"Hata: Mevcut liste okunamadı - {e}")
            return set()

    async def get_pairs(self):
        """USDT paritelerini Binance API'den al"""
        try:
            response = requests.get(self.url)
            response.raise_for_status()
            data = response.json()

            # Aktif USDT paritelerini filtrele
            usdt_pairs = {
                s["symbol"]
                for s in data["symbols"]
                if s["quoteAsset"] == "USDT" and s["status"] == "TRADING"
            }
            return usdt_pairs
        except Exception as e:
            print(f"Hata: Pariteler alınamadı - {e}")
            return set()

    async def save_pairs(self, pairs):
        """Parite listesini dosyaya kaydet"""
        try:
            with open(self.pairs_file, "w", encoding="utf-8") as f:
                for pair in sorted(pairs):
                    f.write(pair + "\n")
            return True
        except Exception as e:
            print(f"Hata: Dosya yazılamadı - {e}")
            return False

    async def save_delisted(self, delisted_pairs):
        """Delist olan paritileri dosyaya kaydet"""
        try:
            # Dosya varsa mevcut delistleri oku
            existing_delisted = set()
            if os.path.exists(self.delist_file):
                with open(self.delist_file, "r", encoding="utf-8") as f:
                    existing_delisted = {line.strip() for line in f if line.strip()}

            # Yeni delistleri ekle
            all_delisted = existing_delisted | delisted_pairs

            # Tümünü dosyaya yaz
            with open(self.delist_file, "w", encoding="utf-8") as f:
                for pair in sorted(all_delisted):
                    f.write(pair + "\n")

            if delisted_pairs:
                print(f"Delist olan pariteler: {', '.join(sorted(delisted_pairs))}")
            return True
        except Exception as e:
            print(f"Hata: Delist dosyası yazılamadı - {e}")
            return False

    async def main(self, interval: int = 15):
        """
        Ana işlem akışı - Her interval saniyede bir çalışır
        Args:
            interval (int): Güncelleme aralığı (saniye)
        """
        self.last_pairs = self.load_existing_pairs()

        while True:
            try:
                print("\nUSDT pariteler güncelleniyor...")
                current_pairs = await self.get_pairs()

                if current_pairs:
                    # Delist olanları bul (önceki listede olup yeni listede olmayanlar)
                    delisted_pairs = self.last_pairs - current_pairs

                    # Güncel listeyi kaydet
                    if await self.save_pairs(current_pairs):
                        print(f"{len(current_pairs)} adet USDT parite dosyaya yazıldı.")

                        # Delist olanları kaydet
                        if delisted_pairs:
                            await self.save_delisted(delisted_pairs)

                        # Son listeyi güncelle
                        self.last_pairs = current_pairs
                    else:
                        print("Pariteler dosyaya yazılamadı!")
                else:
                    print("Pariteler alınamadı!")

                # Bir sonraki güncelleme için bekle
                await asyncio.sleep(interval)

            except Exception as e:
                print(f"Hata oluştu: {e}")
                await asyncio.sleep(interval)
            except asyncio.CancelledError:
                print("USDT parite güncelleme görevi sonlandırıldı.")
                break

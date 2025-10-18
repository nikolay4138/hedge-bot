import requests
class listBigVolumes:
    def __init__(self) -> None:
        pass

    def main(self, limit=120):
        url = "https://fapi.binance.com/fapi/v1/ticker/24hr"
        response = requests.get(url)
        data = response.json()

        # Sadece USDT pariteleri
        usdt_pairs = [x for x in data if x["symbol"].endswith("USDT")]

        # Hacme göre sırala
        sorted_pairs = sorted(
            usdt_pairs, key=lambda x: float(x["quoteVolume"]), reverse=True
        )

        # İlk 60
        top = sorted_pairs[:limit]

        # 🔹 Ek: Hacme göre ilk 60 coin listesi
        print("\n=== Hacme Göre İlk 60 Coin ===")
        for i, coin in enumerate(top, start=1):
            print(
                f"{i:02}. {coin['symbol']:<12} "
                f"Fiyat: {coin['lastPrice']:<12} "
                f"Hacim: {float(coin['quoteVolume']):,.0f} USDT"
            )

        # Filtre: fiyatı 0.xxx ve en az 4 ondalık basamak
        filtered = []
        for coin in top:
            price_str = coin["lastPrice"]

            if price_str.startswith("0.") and len(price_str.split(".")[1]) >= 4:
                high = float(coin["highPrice"])
                low = float(coin["lowPrice"])
                last = float(coin["lastPrice"])

                # Basit volatilite hesabı
                volatility = ((high - low) / last) * 100 if last != 0 else 0

                filtered.append(
                    {
                        "symbol": coin["symbol"],
                        "price": price_str,
                        "volume": float(coin["quoteVolume"]),
                        "volatility": volatility,
                    }
                )

        # Volatiliteye göre sırala
        filtered_sorted = sorted(filtered, key=lambda x: x["volatility"], reverse=True)

        print("\n=== Filtrelenen Pariteler (Volatiliteye Göre Sıralı) ===")
        for i, coin in enumerate(filtered_sorted, start=1):
            print(
                f"{i:02}. {coin['symbol']:<12} "
                f"Fiyat: {coin['price']:<12} "
                f"Hacim: {coin['volume']:,.0f} USDT | "
                f"Volatilite: {coin['volatility']:.2f}%"
            )

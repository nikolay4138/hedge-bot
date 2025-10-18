from core.utils.databaseProcess import DBReader, SQLiteManager
from core.main.getIndicators import AdvancedTechnicalIndicatorsFibLevels
from core.utils.getTimeframe import GeneratorTimeframe
import json
import re
from typing import Any, Dict, List
import pandas as pd


class RuleReader:
    """
    Çok katmanlı JSON formatını destekleyen kural değerlendirme sınıfı.
    Örnek JSON:
    {
      "bigTimeframes": {
        "breakout1": {
          "1": { "condition": "last_price>fib" },
          "2": { "condition": "rsi_1m>50 and rsi_5m>89" },
          "3": { "condition": "(atr_1m>78 and atr_5m<8) or (atr_5m>30 and atr_15m<10)" },
          "4": { "condition": "volume_1m>3_avg and volume_5m>5_avg" }
        }
      }
    }
    """

    def __init__(self, variable_mapping: Dict[str, str] = None):
        self.rules: Dict[str, Dict[str, str]] = {}  # sadece seçilen alt grup yüklenecek
        self.variable_mapping = variable_mapping or {}

    # ---------------------------------------------------------------------
    # Yükleme Metodu
    # ---------------------------------------------------------------------
    def load_rules_from_dict(self, file_path: str, key_path: str):
        """
        JSON dosyasından nokta notasyonu (dot notation) ile belirtilen key yolunu kullanarak kuralları yükler.
        Örnek:
            evaluator.load_rules_from_dict("config.json", "bigTimeframes.breakout1")
            evaluator.load_rules_from_dict("config.json", "onlyOneKey")
        """
        with open(file_path, "r", encoding="utf-8") as f:
            data = json.load(f)

        # Nokta ile ayrılmış key'leri parçala
        keys = key_path.split(".")

        try:
            current = data
            for key in keys:
                current = current[key]  # her seferinde bir seviye aşağı in
            self.rules = current
        except KeyError as e:
            raise ValueError(f"Geçersiz JSON yolu: {e} ({key_path})")
            return self.rules

    # ---------------------------------------------------------------------
    # Yardımcı Metodlar
    # ---------------------------------------------------------------------
    def map_variable_names(self, condition: str) -> str:
        """Değişken isimlerini eşleştirir"""
        if not self.variable_mapping:
            return condition

        mapped_condition = condition
        for json_var, python_var in self.variable_mapping.items():
            pattern = r"\b" + re.escape(json_var) + r"\b"
            mapped_condition = re.sub(pattern, python_var, mapped_condition)
        return mapped_condition

    # ---------------------------------------------------------------------
    # Kural Değerlendirme
    # ---------------------------------------------------------------------
    def evaluate_condition(
        self, rule_or_condition: str, variables: Dict[str, Any]
    ) -> bool:
        """
        Tek bir condition veya rule ID ifadesini değerlendirir.
        Eğer parametre bir kural ID'si ise (örneğin '1'),
        self.rules[rule_or_condition]['condition'] otomatik alınır.
        """
        # Eğer parametre bir rule ID ise
        if rule_or_condition in self.rules:
            condition = self.rules[rule_or_condition].get("condition")
            if not condition:
                raise ValueError(
                    f"'{rule_or_condition}' ID'li kuralda 'condition' bulunamadı."
                )
        else:
            # Direkt bir condition string verilmişse
            condition = rule_or_condition

        mapped_condition = self.map_variable_names(condition)

        try:
            return bool(eval(mapped_condition, {}, variables))
        except Exception as e:
            raise ValueError(
                f"Kural değerlendirilirken hata: {e}\nKoşul: {mapped_condition}"
            )

    def evaluate_all_rules(self, variables: Dict[str, Any]) -> Dict[str, Any]:
        """
        Tüm koşulları değerlendirir.
        Her bir kuralın sonucunu döndürür ve tümü True ise 'all_passed' True döner.
        """
        results = {}

        for rule_id, rule_obj in self.rules.items():
            condition = rule_obj.get("condition")
            if not condition:
                continue
            try:
                results[rule_id] = self.evaluate_condition(rule_id, variables)
            except Exception as e:
                print(f"Kural {rule_id} değerlendirilirken hata: {e}")
                results[rule_id] = False

        all_passed = all(results.values()) if results else False

        return {"results": results, "all_passed": all_passed}

    def get_matching_rules(self, variables: Dict[str, Any]) -> List[str]:
        """Koşulu True dönen kural ID'lerini döndürür"""
        result_data = self.evaluate_all_rules(variables)
        return [rid for rid, ok in result_data["results"].items() if ok]

    # ---------------------------------------------------------------------
    # Bilgi Metodları
    # ---------------------------------------------------------------------
    def get_conditions(self) -> List[str]:
        """Yüklü gruptaki tüm koşulları döndürür"""
        return [v["condition"] for v in self.rules.values()]

    def get_rule_variables(self, rule_or_condition: str) -> List[str]:
        """
        Bir koşul içinde geçen değişkenleri bulur.
        Hem doğrudan bir condition string, hem de bir rule ID alabilir.
        Örnek:
            get_rule_variables("1")  → self.rules["1"]["condition"] içinden değişkenleri çıkarır.
        """
        # Eğer rule ID verilmişse
        if rule_or_condition in self.rules:
            condition = self.rules[rule_or_condition].get("condition")
            if not condition:
                raise ValueError(
                    f"'{rule_or_condition}' ID'li kuralda 'condition' bulunamadı."
                )
        else:
            condition = rule_or_condition

        tokens = re.findall(r"\b[a-zA-Z_][a-zA-Z0-9_]*\b", condition)
        ignore = {"and", "or", "not"}
        variables = [t for t in tokens if t not in ignore]
        if self.variable_mapping:
            variables = [self.variable_mapping.get(v, v) for v in variables]
        return list(set(variables))

    def print_rule_status(self, variables: Dict[str, Any]):
        """Tüm koşulları değerlendirip durumlarını yazdırır"""
        print("Kural Değerlendirme Sonuçları:")
        print("-" * 60)
        result_data = self.evaluate_all_rules(variables)
        results = result_data["results"]
        all_passed = result_data["all_passed"]

        for rule_id, result in results.items():
            condition = self.rules[rule_id]["condition"]
            status = "✓ UYUYOR" if result else "✗ UYMUYOR"
            print(f"[{rule_id}] {status} → {condition}")
            print(f"     Değişkenler: {self.get_rule_variables(condition)}")
        print("-" * 60)
        print(
            f"GENEL SONUÇ: {'✅ TÜM KURALLAR UYUYOR' if all_passed else '❌ BAZI KURALLAR UYMUYOR'}"
        )
        print()


class ruleExtractor:
    def __init__(self) -> None:
        self.gen = GeneratorTimeframe()

    async def calculator(self, data, tf):
        df = self.gen.resample_ohlcv(data, tf)
        indi = AdvancedTechnicalIndicatorsFibLevels(df)
        analysis, dx = await indi.main()
        return analysis, dx

    async def valid_data_getter(self, key, data):
        """
        1.kural: last_price equal fib0
        2.kural: rsi_1m<34 and rsi_5m<90(momentum)
        3.kural: atr : (atr_1m >34 and atr_5m <23) or (atr_15m<45 and atr_1m=>65)
        4.kural: trend:ema3_1m<ema7_1m and ema3_5m>ema7_5m
        5.kural: hacim: volume_1m<avg_5 and volume_5m>avg_3
        6.kural: close_1m_3<fib and close_5m_2>fib
        kural tipleri bunlar
        her kural için key ve timeframe çıkarırır.
        """
        valida_data = {}
        evulator = RuleReader()
        evulator.load_rules_from_dict("core/config.json", key)
        # price kuralı
        v_list = evulator.get_rule_variables("1")
        if v_list[0] == "lastPrice":
            valida_data[v_list[0]] = data.iloc[-1]["close"]
        fib = v_list[1].split("_")[0]
        if fib == "fib":
            fib_level = v_list[1].split("_")[1]
            fib_tf = v_list[1].split("_")[2]
            # dataya göre analiz yaptırmak
            analysis, _ = await self.calculator(data, fib_tf)
            fib_value = float(analysis["fib_levels"][f"FIB_{fib_level}"])
            valida_data[v_list[1]] = fib_value

        # momentum kuralı
        v_list = evulator.get_rule_variables("2")
        for k in v_list:
            ky = k.split("_")[0]
            tf = k.split("_")[1]
            print(ky, tf, 2)
            _, data = await self.calculator(data, tf)
            valida_data[k] = data.iloc[-1][ky]
        # atr kuralı
        v_list = evulator.get_rule_variables("3")
        for k in v_list:
            ky = k.split("_")[0]
            tf = k.split("_")[1]
            print(ky, tf, 3)
            _, data = await self.calculator(data, tf)
            valida_data[k] = data.iloc[-1][ky]

        # ema kuralı
        v_list = evulator.get_rule_variables("4")
        for k in v_list:
            ky = k.split("_")[0]
            vl = k.split("_")[1]
            tf = k.split("_")[2]
            _, data = await self.calculator(data, tf)
            valida_data[k] = data.iloc[-1][f"{ky}_{vl}"]

        # volume kuralı
        v_list = evulator.get_rule_variables("5")
        for k in v_list:
            if "avg" not in k:
                ky = k.split("_")[0]
                tf = k.split("_")[1]
                _, data = await self.calculator(data, tf)
                valida_data[k] = data.iloc[-1][f"{ky}"]
            if "avg" in k:
                ky = k.split("_")[0]
                vl = int(k.split("_")[1]) * -1
                tf = k.split("_")[2]
                _, data = await self.calculator(data, tf)
                valida_data[k] = data["volume"].iloc[-1:-vl:-1].mean()

        # close kuralı
        v_list = evulator.get_rule_variables("6")
        for k in v_list:
            if "close" in k:
                ky = k.split("_")[0]
                tf = k.split("_")[1]
                vl = int(k.split("_")[2]) * -1
                _, data = await self.calculator(data, tf)
                valida_data[k] = data.iloc[vl][f"{ky}"]
            if "fib" in k:
                ky = k.split("_")[0]
                vl = k.split("_")[1]
                tf = k.split("_")[2]
                analysis, _ = await self.calculator(data, tf)
                fib_value = analysis["fib_levels"][f"FIB_{vl}"]
                valida_data[k] = fib_value

        return valida_data

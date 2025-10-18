
from core.utils.profitCalculator import ProfitCalculator
from core.utils.getTimeframe import GeneratorTimeframe
from core.utils.databaseProcess import SQLiteManager, DBReader
from core.ruleSystem.ruleEngine import RuleReader, ruleExtractor
from core.trading import BinanceFuturesTrader
from core.main.getIndicators import AdvancedTechnicalIndicatorsFibLevels
import re
from collections import defaultdict
import asyncio
import time
from core.utils.functions import Processor
from core.utils.getDbDatabase import Getter
class PsController:
    def __init__(self) -> None:
        self.trader = BinanceFuturesTrader(testnet=False, debug=True, proxy="")
        self.write_added_db = SQLiteManager("binance_data/added.db")
        self.MIN_APERT = 0.05  # yüzde 5
        self.generator = GeneratorTimeframe()
        self.rule_reader = RuleReader()
        self.rule_extractor = ruleExtractor()
        self.process=Processor()
        self.db_getter=Getter()
        self.write_errorDb = SQLiteManager("binance_data/error.db")


    def get_symbol_pos_side(self):
        return "symbol","pos_side","amount","entry_price"
    #tek bir sembol için config json kurallarını sürekli dinler
    async def listen_exchange(self,key,data):
        valid_data=self.rule_extractor.valid_data_getter(key,data)
        self.rule_reader.load_rules_from_dict("core/config.json",key)
        value=self.rule_reader.evaluate_all_rules()
        return value["all_passed"]
    
    async def main(self,key):
        symbol,pos_side,amount,entry_price=self.get_symbol_pos_side()
        ohlcv_data=self.db_getter.get_ohlcv_data(symbol)
        value=await self.listen_exchange(key,ohlcv_data)
        if value:
            add_amount=self.process.how_much_added()
            order=await self.trader.market_order(symbol,side,pos_side,add_amount)
            if order["info"]["STATUS"]=="FILLED":
                self.write_added_db.insert(symbol,{})
            else:
                self.write_errorDb.insert(symbol,{})
        else:
            return False


   

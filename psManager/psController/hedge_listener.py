# gerekli yerde ekleme yapacak, zaten kapatma emirlerini pscloser hesaplıyor ve yapıyor
from core.utils.getDbDatabase import Getter
from core.utils.getTimeframe import GeneratorTimeframe
from core.main.getIndicators import AdvancedTechnicalIndicatorsFibLevels
from collections import defaultdict
import re
import asyncio
import pandas as pd

from core.utils.functions import Processor
from core.utils.getDatabase import dbGetterSetter

# tek bir sembol için tasarlanacak
# diğer sembolleri eş zamanlı çalıştırma ile bulacak
class checkHedge:
    def __init__(self) -> None:
        self.generator = GeneratorTimeframe()
        self.processor = Processor()
        self.open_db=dbGetterSetter.opendb()
        self.hedge_db=dbGetterSetter.hedgedb()
        self.added_db=dbGetterSetter.addeddb()

    async def check_open_hedge(self):
        open_positions=self.open_db.get_open_positions()
        added_positions=self.added_db.get_added_symbols()
        #open positionsdan added_positions çıkar
        active_pos=self.processor.remove_second_list(open_positions,added_positions)
        active_symbols=self.processor.symbols_with_both_sides_robust(active_pos)
        #active semboller için hedge datalarını al
        aperts=[]
        for symbol in active_symbols:
            apert=self.db_getter.get_hedge_data(symbol)
            aperts.append((symbol,apert))
        return aperts
    async def apert_condition(self,aperts):
        condition=[]
        for symbol,apert in aperts:
            data_ohlcv=self.db_getter.get_ohlcv_data(symbol)
            dx=self.processor.generate_multiple_tf(data_ohlcv,["1min","5min","15min"])
            atr_list=[]
            for tf in ["1min","5min","15min"]:
                _,dfx=self.processor.analyze_data(dx[tf])
                atr_list.append(float(dfx.iloc[-1]["atr"]))
            min_apert=self.processor.select_min_above_threshold(atr_list,0.004)
            if apert>min_apert:
                condition.append((symbol,True))
            else:
                condition.append((symbol,False))
        return condition


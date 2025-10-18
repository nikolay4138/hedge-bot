
from core.utils.getDatabase import dbGetterSetter as GetterSetter
from core.utils.functions import Processor
#tek sembol için hedge kapatma işlemi yapar
class Closer:
    def __init__(self):
        self.read_breakoutDb = GetterSetter.breakoutdb()
        self.read_openDb = GetterSetter.opendb()
        self.trader=Processor.TradeProcessor()
        self.time_utils=Processor.TimeProcessor()
    async def main(self,symbol):
        #sembole dair aynı anda farklı yönlü yakın büyüklükte pozisyon varsa kapat
        s_value=await self.trader.check_with_both_sides(symbol)
        if s_value:
            symbol,timestamp,direction=await self.read_breakoutDb.get_breakout_data(symbol)
            value=self.time_utils.is_within_minutes(timestamp,5)
            if value:
                amount=await self.read_openDb.get_open_data_amount(symbol)
                if direction=="UP":
                    #short pozisyon kapat
                    side="buy"
                    position_side="SHORT"
                    self.read_openDb.get_open_data(symbol)
                    await self.trader.close_pos(symbol,side,position_side,amount*1.2,proxy="")
                elif direction=="DOWN":
                    #long pozisyon kapat
                    side="sell"
                    position_side="LONG"
                    await self.trader.close_pos(symbol,side,position_side,amount*1.2,proxy="")
        
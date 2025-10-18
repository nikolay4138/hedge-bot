from core.utils.getDatabase import dbGetterSetter as GetterSetter
from core.utils.functions import Processor
class Opener:
    def __init__(self):
        self.read_breakoutDb = GetterSetter.breakoutdb()
        self.read_openDb = GetterSetter.opendb()
        self.trader=Processor.TradeProcessor()
        self.time_utils=Processor.TimeProcessor()
        self.PROXY=""
    async def main(self,symbol):
        s_value=await self.trader.check_with_both_sides(symbol)
        if s_value==False:
            symbol,timestamp,direction=await self.read_breakoutDb.get_breakout_data(symbol)
            value=self.time_utils.is_within_minutes(timestamp,5)
            if value:
                amount=await self.read_openDb.get_open_data_amount(symbol)
                #açık olan pozisyonunun bilgisini al
                positions=await self.read_openDb.get_open_positions()
                if direction=="DOWN":
                    #eğer long varsa aç
                    pos_name=f"{symbol}_LONG"
                    if pos_name in positions:
                        #short pozisyon aç
                        side="sell"
                        position_side="SHORT"
                        await self.trader.open_pos(symbol,side,position_side,amount*1.2,proxy=self.PROXY)
                elif direction=="UP":
                    #eğer short varsa aç
                    pos_name=f"{symbol}_SHORT"
                    if pos_name in positions:
                        #long pozisyon aç
                        side="buy"
                        position_side="LONG"
                        await self.trader.open_pos(symbol,side,position_side,amount*1.2,proxy=self.PROXY)
"""
ACİL DURUM SİSTEMİ
1.aşama: tek bir sembol için  açık zarar ve available balance bilgisi alınır.yapı websocket ile yapılır.(gecikme olmaması gerek)
2.aşama: tek bir sembolde tek hedge için açık zarar, kasanın yarısına ulaşılırsa, ki bunu en fazla 10 dakika içinde yaparsa
3.aşama: o sembole ait hedge pozisyonlar kapatılır


NOTE: TÜM SEMBOLLER İÇİN TARAMA YAPAR, TEK SEMBOLDE ANAMOLİ BULDUĞUNDA,TEK SEMBOL İÇİN BİLGİ DÖNER
"""
from core.utils.getDatabase import dbGetterSetter
from core.utils.functions import Processor



class Stoploss:
    def __init__(self):
        self.stoplosser=Processor.ProfitStopProcessor()
        self.trader=Processor.TradeProcessor()
        self.openDb=dbGetterSetter.opendb()
        self.balanceDb = dbGetterSetter.balancedb()
        self.generalStoploss_writer = dbGetterSetter.generalStoplossdb()
        self.PROXY = None 
    async def main(self):
        positions=self.openDb.get_open_positions()
        for pos in positions:
            df=await self.openDb.get_open_data(pos)
            unpnl=float(df["unrealizedProfit"].values[0])
            #get half balance
            balance=await self.balanceDb.get_available_balance_data()
            if balance:
                condition=await self.stoplosser.condition_general_stop(balance,unpnl,50)
                if condition:
                    symbol=pos.split("_")[0]
                    amount=await self.openDb.get_open_amount(pos)
                    await self.trader.close_pos(symbol,"sell","LONG",amount*1.2,self.PROXY)
                    await self.trader.close_pos(symbol,"buy","SHORT",amount*1.2,self.PROXY)
                    #general stoploss db'ye yazılacak
                    await self.generalStoploss_writer.write_general_stoploss_data(symbol,data)


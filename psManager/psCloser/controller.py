
from core.utils.getDatabase import dbGetterSetter as GetterSetter

from core.utils.functions import Processor
class PsCloser:
    def __init__(self) -> None:
        self.data_getter = GetterSetter.opendb()
        self.trader=Processor.TradeProcessor()
        self.added_getter = GetterSetter.addeddb()
        self.list_processor=Processor.listProcessor()
        self.profit_calculator=Processor.ProfitCalculator()
        self.read_min_amounts=GetterSetter.readMinAmounts()
        self.read_ohlcv=GetterSetter.ohlcvdb()
        self.write_added=GetterSetter.addeddb()
        self.PROXY=""
    #tüm semboller için çalışır
    async def normal_closer(self):
        added_positions=await self.added_getter.get_added_symbols()
        positions=await self.data_getter.get_open_positions()
        active_positions=self.list_processor.remove_second_list(positions,added_positions)
        for pos in active_positions:
            symbol=pos.split("_")[0]
            pos_side=pos.split("_")[1]
            amount=await self.data_getter.get_open_amount(pos)
            pnl=await self.data_getter.get_open_pnl(pos)
            if pos_side=="LONG":
                side="SELL"
            else:
                side="BUY"
            #profit calculation
            profits=[]
            for tf in ["1min","5min","15min"]:
                expected_p=await self.profit_calculator.expected_profit(pos,tf)
                profits.append(expected_p)
            expected_profit=await self.profit_calculator.profit_selector(profits)
            order=await self.trader.close_pos_pnl(symbol,side,pos_side,amount,pnl,expected_profit,self.PROXY)
            if order:
                if pos_side=="LONG":
                    side="buy"
                else:
                    side="sell"
                reopen_amount=self.read_min_amounts.get_min_amount(symbol)
                self.trader.open_pos(symbol,side,pos_side,reopen_amount,self.PROXY)
    async def get_added_positions(self):
        added_positions=await self.added_getter.get_added_symbols()
        return added_positions
    #tek pozisyon için çalışır
    async def added_pos_profit_closer(self,key_profit,pos):
            symbol=pos.split("_")[0]
            pos_side=pos.split("_")[1]
            amount=await self.data_getter.get_open_amount(pos)
            pnl=await self.data_getter.get_open_pnl(pos)
            #ohlcv çek sembol için
            data=self.read_ohlcv.get_ohlcv_data(symbol)
            value_profit=self.trader.listen_exchange(key_profit,data)
            if value_profit:
                #eklenmiş pozisyon için orta değer teorimi kuralını okur
                if pos_side=="LONG":
                    side="SELL"
                else:
                    side="BUY"
                #profit calculation
                profits=[]
                for tf in ["1min","5min","15min"]:
                    expected_p=await self.profit_calculator.expected_profit(pos,tf)
                    profits.append(expected_p)
                expected_profit=await self.profit_calculator.profit_selector(profits,0.05)
                order=await self.trader.close_pos_pnl(symbol,side,pos_side,amount,pnl,expected_profit,self.PROXY)
                
            if order:
                if pos_side=="LONG":
                    side="buy"
                else:
                    side="sell"
                reopen_amount=self.read_min_amounts.get_min_amount(symbol)
                self.trader.open_pos(symbol,side,pos_side,reopen_amount,self.PROXY)
                #remove from added.db
                await self.write_added.remove_added_position(pos)
    #tek pozisyon için çalışır
    async def added_pos_stop_closer(self,key_stop,pos):
            symbol=pos.split("_")[0]
            pos_side=pos.split("_")[1]
            amount=await self.data_getter.get_open_amount(pos)
            pnl=await self.data_getter.get_open_pnl(pos)
            #ohlcv çek sembol için
            data=self.read_ohlcv.get_ohlcv_data(symbol)
            value_stop=self.trader.listen_exchange(key_stop,data)
            if value_stop:
                #eklenmiş pozisyon için orta değer teorimi kuralını okur
                if pos_side=="LONG":
                    side="SELL"
                else:
                    side="BUY"
                
                order=await self.trader.close_pos(symbol,side,pos_side,amount,self.PROXY)
                
            if order:
                if pos_side=="LONG":
                    side="buy"
                else:
                    side="sell"
                reopen_amount=self.read_min_amounts.get_min_amount(symbol)
                self.trader.open_pos(symbol,side,pos_side,reopen_amount,self.PROXY)
                #remove from added.db
                await self.write_added.remove_added_position(pos)
    
           

        
"""
pozisyonların anlık olarak miktarlarını kontrol eder
"""

from core.utils.getDatabase import dbGetterSetter
from core.utils.functions import Processor

class checkPosAmount:
    def __init__(self):
        self.db_getter_setter = dbGetterSetter()
        self.processor = Processor()
        self.open_db = self.db_getter_setter.opendb()
        self.add_db = self.db_getter_setter.addeddb()
        self.min_amounts_db=self.db_getter_setter.minamountsdb()
        self.list_process=self.processor.listProcessor()
    async def check_amount(self):
        #açık olan pozisyon isimlerini al
        #ekleme yapılmış pozisyonların isimlerini al
        #açık olan pozisyon isimlerinden ekleme yapılmış olanları çıkar
        #açık olan pozisyonların miktarlarını al

        positions = await self.open_db.get_open_positions()
        added_positions = await self.add_db.added_positions()
        active_positions=self.list_process.remove_second_list(positions, added_positions)
        check_results={}
         #pozisyonların miktarlarını min_amount ile karşılaştır
        for pos in active_positions:
            amount = await self.open_db.get_open_amount(table_name=pos)
            #sembole dair min miktarı al
            symbol=pos.split("_")[0]
            min_amount=await self.min_amounts_db.get_min_amount(symbol)
            value=self.list_process.check_proximity(amount, min_amount, 0.05)
            check_results[pos]=value
        return check_results
         

           
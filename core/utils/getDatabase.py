# tüm veritabanları için veri getirme ve veri yazma,silme işlemlerini yapar.
from core.utils.databaseProcess import DBReader,SQLiteManager




class dbGetterSetter:
    def __init__(self):
        pass
        """
        open.db -> açık pozisyonlar
        closed.db -> kapalı pozisyonlar
        added.db -> eklenen pariteler
        ohlcv.db -> ohlcv verileri
        stoploss.db -> stoploss verileri
        general_stoploss.db -> genel stoploss verileri
        min_amounts.db -> minimum miktar verileri
        leverage_data.db -> kaldıraç verileri
        balance.db -> bakiye verileri
        hedge.db -> hedge pozisyon verileri


        1.Open.db
        2.Opened.db
        3.Closed.db
        4.Hedge.db
        5.Ohlcv.db
        6.Added.db
        7.Stoploss.db
        8.General_stoploss.db
        9.Errors.db
        10.Lost_dist.db
        11.Breakout.db
        12.Balance.db
        13.Min_amounts.db
        14.Leverage_data.db
        15.Total_lost.db
        16.Dist.db
        17.Daily_profit.db

        """
    #veritabanı ismi,tablo ismi,değişken isimine göre son değer
    async def get_last_row_variable(self, db_name, table_name, variable):
            db = DBReader(f"binance_data/{db_name}.db")
            last = db.generic_get_last_row(table_name)
            db.close()
            if not last.empty:
                return last[0][variable]
            else:
                return None
    #db name ve table name göre tüm datayı getirir
    async def get_all_data(self, db_name, table_name):
            db = DBReader(f"binance_data/{db_name}.db")
            df = db.get_all_generic_df(table_name)
            db.close()
            if not df.empty:
                return df
            else:
                return None
    #db name ve table name göre son satırı getirir
    async def get_last_row(self, db_name, table_name):
            db = DBReader(f"binance_data/{db_name}.db")
            last = db.generic_get_last_rows(table_name)
            db.close()
            if not last.empty:
                return last[0]
            else:
                return None
    #db name ve table name göre n satır getirir
    async def get_n_rows(self, db_name, table_name, n):
            db = DBReader(f"binance_data/{db_name}.db")
            lasts = db.generic_get_last_rows(table_name, n)
            db.close()
            if lasts:
                return lasts
            else:
                return None
    #db name ve table name göre veri ekleme yapar
    async def insert_data(self, db_name, table_name, data: dict):
            db = SQLiteManager(f"binance_data/{db_name}.db")
            db.insert_data(table_name, data)
            db.close()
    
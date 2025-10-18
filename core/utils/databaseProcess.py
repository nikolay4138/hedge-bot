import os
import sqlite3
import json
from typing import List, Dict, Any
import datetime
import pandas as pd


class ErrorLogger:
    def __init__(self, db_file="data/error.db"):
        try:
            os.makedirs(os.path.dirname(db_file), exist_ok=True)
            self.conn = sqlite3.connect(db_file, check_same_thread=False)
            self.cursor = self.conn.cursor()
            self._create_error_table()
        except Exception as e:
            print(f"[ERROR LOGGER] Hata log sistemi başlatılamadı: {e}")

    def _create_error_table(self):
        query = """
        CREATE TABLE IF NOT EXISTS errors (
            timestamp TEXT,
            error TEXT,
            method TEXT,
            details TEXT
        )
        """
        self.cursor.execute(query)
        self.conn.commit()

    def log_error(
        self,
        error_message: str,
        class_name: str,
        method_name: str,
        details: str = "",
    ):
        try:
            timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            method = f"{class_name}.{method_name}"
            self.cursor.execute(
                "INSERT INTO errors (timestamp, error, method, details) VALUES (?, ?, ?, ?)",
                (timestamp, error_message, method, details),
            )
            self.conn.commit()
        except Exception as e:
            print(f"[ERROR LOGGER] Hata kaydedilemedi: {e}")

    def close(self):
        try:
            self.conn.close()
        except:
            pass


class SQLiteManager:
    def __init__(self, db_file="data/custom.db"):
        self.error_logger = ErrorLogger()
        try:
            os.makedirs(os.path.dirname(db_file), exist_ok=True)
            self.conn = sqlite3.connect(db_file, check_same_thread=False)
            self.cursor = self.conn.cursor()
            self.conn.execute("PRAGMA journal_mode=WAL;")
            self.conn.execute("PRAGMA synchronous=NORMAL;")
            print(f"[DB] Veritabanı başlatıldı: {db_file}")
        except Exception as e:
            error_msg = f"Veritabanı başlatma hatası: {str(e)}"
            self.error_logger.log_error(error_msg, "SQLiteManager", "__init__", db_file)
            raise

    def create_table(self, table_name: str, columns: dict):
        try:
            cols = ", ".join([f"{col} {dtype}" for col, dtype in columns.items()])
            query = f'CREATE TABLE IF NOT EXISTS "{table_name}" ({cols})'
            self.cursor.execute(query)
            self.conn.commit()
            print(f"[DB] Tablo hazır: {table_name} -> {columns}")
        except Exception as e:
            error_msg = f"Tablo oluşturma hatası: {str(e)}"
            self.error_logger.log_error(
                error_msg, "SQLiteManager", "create_table", f"table={table_name}"
            )
            self.conn.rollback()
            raise

    def insert(self, table_name: str, data: dict):
        try:
            self.create_table(table_name, {k: "TEXT" for k in data.keys()})
            keys = ", ".join(data.keys())
            placeholders = ", ".join(["?" for _ in data])
            values = tuple(
                json.dumps(v) if isinstance(v, (dict, list)) else v for v in data.values()
            )
            query = f'INSERT OR REPLACE INTO "{table_name}" ({keys}) VALUES ({placeholders})'
            self.cursor.execute(query, values)
            self.conn.commit()
            print(f"[DB WRITE] {table_name} -> {data}")
        except Exception as e:
            error_msg = f"Veri ekleme hatası: {str(e)}"
            self.error_logger.log_error(error_msg, "SQLiteManager", "insert", f"table={table_name}")
            self.conn.rollback()
            raise

    def clear_table(self, table_name: str):
        try:
            self.cursor.execute(f'DELETE FROM "{table_name}"')
            self.conn.commit()
            print(f"[DB CLEAR] {table_name} tablosu temizlendi.")
        except Exception as e:
            error_msg = f"Tablo temizleme hatası: {str(e)}"
            self.error_logger.log_error(error_msg, "SQLiteManager", "clear_table", f"table={table_name}")
            self.conn.rollback()
            raise

    def delete_rows(self, table_name: str, condition: str):
        try:
            query = f'DELETE FROM "{table_name}" WHERE {condition}'
            self.cursor.execute(query)
            self.conn.commit()
            print(f"[DB DELETE] {table_name} tablosundan '{condition}' koşuluna uyan satırlar silindi.")
        except Exception as e:
            error_msg = f"Satır silme hatası: {str(e)}"
            self.error_logger.log_error(error_msg, "SQLiteManager", "delete_rows", f"table={table_name}, condition={condition}")
            self.conn.rollback()
            raise

    def close(self):
        try:
            self.conn.close()
            self.error_logger.close()
            print("[DB] Bağlantı kapatıldı")
        except Exception as e:
            error_msg = f"Bağlantı kapatma hatası: {str(e)}"
            self.error_logger.log_error(error_msg, "SQLiteManager", "close")


class DBReader:
    def __init__(self, db_file: str = "binance_data/ohlcv.db"):
        self.error_logger = ErrorLogger()
        try:
            self.db_file = db_file
            self.conn = sqlite3.connect(self.db_file, check_same_thread=False)
            self.conn.execute("PRAGMA journal_mode=WAL;")
            self.conn.execute("PRAGMA wal_checkpoint(PASSIVE);")
            self.cursor = self.conn.cursor()
        except Exception as e:
            error_msg = f"DBReader başlatma hatası: {str(e)}"
            self.error_logger.log_error(error_msg, "DBReader", "__init__", db_file)
            raise



    def get_n_rows(self, table_name: str, n: int = 100, from_start: bool = True) -> pd.DataFrame:
        try:
            if from_start:
                query = f'SELECT * FROM "{table_name}" LIMIT {n}'
            else:
                query = f'SELECT * FROM "{table_name}" ORDER BY ROWID DESC LIMIT {n}'
            
            df = pd.read_sql_query(query, self.conn)
            if not from_start:
                df = df.iloc[::-1].reset_index(drop=True)
            return df
        except Exception as e:
            error_msg = f"N satır okuma hatası: {str(e)}"
            self.error_logger.log_error(error_msg, "DBReader", "get_n_rows", f"table={table_name}, n={n}")
            return pd.DataFrame()

    def get_table_names(self) -> list:
        try:
            query = "SELECT name FROM sqlite_master WHERE type='table'"
            self.cursor.execute(query)
            return [row[0] for row in self.cursor.fetchall()]
        except Exception as e:
            error_msg = f"Tablo listesi alma hatası: {str(e)}"
            self.error_logger.log_error(error_msg, "DBReader", "get_table_names")
            return []

    def get_row_count(self, table_name: str) -> int:
        try:
            query = f'SELECT COUNT(*) FROM "{table_name}"'
            self.cursor.execute(query)
            return self.cursor.fetchone()[0]
        except Exception as e:
            error_msg = f"Satır sayısı alma hatası: {str(e)}"
            self.error_logger.log_error(error_msg, "DBReader", "get_row_count", f"table={table_name}")
            return 0

    def get_column_names(self, table_name: str) -> list:
        try:
            query = f'SELECT * FROM "{table_name}" LIMIT 0'
            self.cursor.execute(query)
            return [description[0] for description in self.cursor.description]
        except Exception as e:
            error_msg = f"Kolon isimleri alma hatası: {str(e)}"
            self.error_logger.log_error(error_msg, "DBReader", "get_column_names", f"table={table_name}")
            return []

    def generic_get_last_rows(self, table: str, n: int = 1) -> List[Dict[str, Any]]:
        try:
            self.cursor.execute(f'PRAGMA table_info("{table}")')
            columns_info = self.cursor.fetchall()
            column_names = [col[1] for col in columns_info]

            if not column_names:
                raise ValueError(f"Tablo bulunamadı: {table}")

            query = f'SELECT * FROM "{table}" ORDER BY ROWID DESC LIMIT ?'
            self.cursor.execute(query, (n,))
            rows = self.cursor.fetchall()
            return [dict(zip(column_names, row)) for row in rows]
        except Exception as e:
            error_msg = f"Son satır alma hatası: {str(e)}"
            self.error_logger.log_error(error_msg, "DBReader", "generic_get_last_row", f"table={table}, n={n}")
            return []

    
    

    

    def get_all_generic_df(self, table: str, order: str = "desc") -> pd.DataFrame:
        try:
            self.cursor.execute(f'PRAGMA table_info("{table}")')
            cols = [row[1] for row in self.cursor.fetchall()]
            if not cols:
                raise ValueError(f"Tablo bulunamadı: {table}")

            self.cursor.execute(f'PRAGMA table_info("{table}")')
            pk_col = None
            for row in self.cursor.fetchall():
                if row[5] == 1:
                    pk_col = row[1]
                    break
            if pk_col is None:
                pk_col = cols[0]

            if order.lower() == "asc":
                query = f'SELECT * FROM "{table}" ORDER BY "{pk_col}" ASC'
            else:
                query = f'SELECT * FROM "{table}" ORDER BY "{pk_col}" DESC'

            return pd.read_sql_query(query, self.conn)
        except Exception as e:
            error_msg = f"Genel DataFrame alma hatası: {str(e)}"
            self.error_logger.log_error(error_msg, "DBReader", "get_all_generic_df", f"table={table}")
            return pd.DataFrame()

    def close(self):
        try:
            self.conn.close()
            self.error_logger.close()
        except Exception as e:
            error_msg = f"Bağlantı kapatma hatası: {str(e)}"
            self.error_logger.log_error(error_msg, "DBReader", "close")

    def __del__(self):
        self.close()

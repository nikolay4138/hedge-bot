"""
tüm veri tabanlarını ve temel tabloları oluşturur.(boş tabloları oluşturur.)
"""


from core.utils.databaseProcess import SQLiteManager

class CreateDatabase:
    def __init__(self):
        self.db = SQLiteManager()

    def create_added(self):
        self.db.create_table("users", {"id": "INTEGER PRIMARY KEY", "name": "TEXT", "age": "INTEGER"})
        self.db.create_table("transactions", {"id": "INTEGER PRIMARY KEY", "user_id": "INTEGER", "amount": "REAL"})
    
    
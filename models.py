from peewee import *
import datetime

# Initialize SQLite database
db = SqliteDatabase('database.db')

class BaseModel(Model):
    class Meta:
        database = db

class DataRecord(BaseModel):
    name = CharField()
    category = CharField()
    value = FloatField()
    created_at = DateTimeField(default=datetime.datetime.now)

    class Meta:
        table_name = 'data_records'

def initialize_db():
    """Initialize the database and create tables if they don't exist."""
    db.connect()
    db.create_tables([DataRecord], safe=True)
    db.close()

if __name__ == '__main__':
    initialize_db()
from models import db, DataRecord

# Connect to the database
db.connect()

# Get all records
records = DataRecord.select()

print("Total records:", records.count())
print("\nSample records:")
for record in records.limit(5):
    print(f"Name: {record.name}, Category: {record.category}, Value: {record.value}")

# Close the connection
db.close()
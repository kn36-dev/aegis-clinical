import sqlite3

conn = sqlite3.connect("data/clinical_registry.db")
cursor = conn.cursor()

# Query a nested category row to confirm contextual path tracking
cursor.execute("SELECT * FROM icd11_taxonomy WHERE code = '1A03.2';")
record = cursor.fetchone()
conn.close()

if record:
    print("✅ Database verification passed.")
    print(f"Code:         {record[0]}")
    print(f"Title:        {record[1]}")
    print(f"Class Kind:   {record[2]}")
    print(f"Context Path: {record[3]}")
else:
    print("❌ Verification failed: Code not found.")

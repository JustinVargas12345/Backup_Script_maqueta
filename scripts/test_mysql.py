import pymysql

try:
    conn = pymysql.connect(
        host="localhost", port=3306,
        user="test", password="test123", database="sampledb"
    )
    print("MySQL OK ✓")
except Exception as e:
    print("MySQL ERROR:", e)

import psycopg2

try:
    conn = psycopg2.connect(
        host="localhost", port=5432,
        user="test", password="test123", dbname="sampledb"
    )
    print("PostgreSQL OK ✓")
except Exception as e:
    print("PostgreSQL ERROR:", e)

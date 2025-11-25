'''
import psycopg2
import pymysql
from pymongo import MongoClient

# Postgres
conn = psycopg2.connect(
    host="127.0.0.1", port=5432, user="test", password="test123", dbname="sampledb"
)
print(conn.cursor().execute("SELECT * FROM users;").fetchall())

# MySQL
conn = pymysql.connect(
    host="127.0.0.1", port=3306, user="test", password="test123", database="sampledb"
)

# Mongo
client = MongoClient("mongodb://test:test123@127.0.0.1:27017/sampledb")
print(client.sampledb.users.find_one())
'''
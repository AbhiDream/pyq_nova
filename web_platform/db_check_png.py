import psycopg2
import json

conn=psycopg2.connect(dbname='neet_db', user='postgres', password='Dream@1234', host='localhost')
cur=conn.cursor()
cur.execute("SELECT id, options FROM neet_pyqs WHERE options::text LIKE '%.png%' OR options::text LIKE '%.jpg%' LIMIT 5")
rows = cur.fetchall()
for r in rows:
    print("ID:", r[0])
    print("Options:", r[1])

import psycopg2
import json

conn=psycopg2.connect(dbname='neet_db', user='postgres', password='Dream@1234', host='localhost')
cur=conn.cursor()
cur.execute("SELECT id, options, question_text FROM neet_pyqs WHERE chapter LIKE '%Semiconductor%' LIMIT 5")
rows = cur.fetchall()
for r in rows:
    print("ID:", r[0])
    print("Options type:", type(r[1]))
    print("Options str slice:", str(r[1])[:100])
    print("-" * 50)

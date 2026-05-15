import psycopg2
conn=psycopg2.connect(dbname='neet_db', user='postgres', password='Dream@1234', host='localhost')
cur=conn.cursor()
cur.execute("SELECT DISTINCT chapter FROM neet_pyqs")
print(cur.fetchall())

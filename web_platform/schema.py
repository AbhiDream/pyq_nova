import psycopg2
conn=psycopg2.connect(dbname='neet_db', user='postgres', password='Dream@1234', host='localhost')
cur=conn.cursor()
cur.execute("SELECT column_name FROM information_schema.columns WHERE table_name = 'neet_pyqs'")
print([r[0] for r in cur.fetchall()])

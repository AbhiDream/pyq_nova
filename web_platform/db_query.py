import psycopg2
conn=psycopg2.connect(dbname='neet_db', user='postgres', password='Dream@1234', host='localhost')
cur=conn.cursor()
cur.execute("SELECT id, image_path, subject FROM neet_pyqs WHERE image_path IS NOT NULL LIMIT 5")
print("With image:", cur.fetchall())
